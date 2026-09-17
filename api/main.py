"""VitaMecha FastAPI backend.

The API keeps a short per-machine history so causal rolling features can be
computed as observations arrive. C-MAPSS streaming is explicitly simulated.
"""
from __future__ import annotations
import sys, logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
ROOT=Path(__file__).resolve().parent.parent; sys.path.insert(0,str(ROOT))
from src.config import *
from src.predict import VitaMechaPredictor
from src.streaming import SensorBuffer

logger=logging.getLogger(__name__)
predictor:Optional[VitaMechaPredictor]=None
buffers:Dict[str,SensorBuffer]={}

async def lifespan(app):
    global predictor
    try:
        predictor=VitaMechaPredictor(use_quantile=True,use_shap=True)
        logger.info("VitaMecha inference engine loaded")
    except Exception:
        logger.exception("Could not load inference engine")
        predictor=None
    yield

app=FastAPI(title=API_TITLE,version=API_VERSION,description=API_DESCRIPTION,lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

ACTIVE_SENSORS=[f"sensor_{i}" for i in range(1,22)]

class SensorReading(BaseModel):
    machine_id:str=Field(...,min_length=1,max_length=100)
    cycle:int=Field(...,ge=1)
    op_setting_1:float; op_setting_2:float; op_setting_3:float
    sensor_1:float; sensor_2:float; sensor_3:float; sensor_4:float; sensor_5:float; sensor_6:float
    sensor_7:float; sensor_8:float; sensor_9:float; sensor_10:float; sensor_11:float; sensor_12:float
    sensor_13:float; sensor_14:float; sensor_15:float; sensor_16:float; sensor_17:float; sensor_18:float
    sensor_19:float; sensor_20:float; sensor_21:float
    def row(self):
        d=self.model_dump(); return {"unit_id":1,**d}


class FeatureContribution(BaseModel): feature:str; impact:float; description:str
class Recommendation(BaseModel): action:str; priority:str; details:List[str]; sensor_note:str=""; disclaimer:str
class PredictResponse(BaseModel):
    machine_id:str; cycle:int; predicted_rul:float; rul_lower:Optional[float]; rul_upper:Optional[float]
    health_status:str; risk_level:str; trend:str; recommendation:Recommendation; top_features:List[FeatureContribution]; inference_ms:float; timestamp:str
class ExplainResponse(BaseModel): machine_id:str; cycle:int; predicted_rul:float; top_features:List[FeatureContribution]; base_value:float; note:str


def require():
    if predictor is None: raise HTTPException(503,"Inference engine unavailable. Train the model first.")
    return predictor

def run(reading:SensorReading):
    p=require(); buf=buffers.setdefault(reading.machine_id,SensorBuffer(reading.machine_id)); buf.push(reading.row())
    return p.predict_from_frame(buf.frame(),machine_id=reading.machine_id,cycle=reading.cycle)

def response(r):
    return PredictResponse(machine_id=r.machine_id,cycle=r.cycle,predicted_rul=round(r.predicted_rul,2),rul_lower=r.rul_lower,rul_upper=r.rul_upper,health_status=r.health.health_status,risk_level=r.health.risk_level,trend=r.trend,recommendation=Recommendation(**r.recommendation.to_dict()),top_features=[FeatureContribution(**x) for x in r.top_features],inference_ms=round(r.inference_ms,3),timestamp=r.timestamp)

@app.get("/")
def root(): return {"name":"VitaMecha","version":API_VERSION,"model_loaded":predictor is not None,"mode":"C-MAPSS simulated streaming"}
@app.get("/health")
def health(): return {"status":"ok","model_loaded":predictor is not None}
@app.get("/machines")
def machines():
    try:
        _,test=__import__("src.data_processing",fromlist=["load_processed"]).load_processed()
        machines=sorted(test["machine_id"].astype(str).unique().tolist())
    except Exception:
        machines=[]
    return {"machines":machines,"note":"C-MAPSS FD001-FD004 combined test engines"}
@app.post("/predict",response_model=PredictResponse)
def predict(reading:SensorReading): return response(run(reading))
@app.post("/stream",response_model=PredictResponse)
def stream(reading:SensorReading): return response(run(reading))
@app.post("/explain",response_model=ExplainResponse)
def explain(reading:SensorReading):
    r=run(reading); p=require(); base=p.explainer.get_expected_value() if p.explainer else 0.0
    return ExplainResponse(machine_id=r.machine_id,cycle=r.cycle,predicted_rul=round(r.predicted_rul,2),top_features=[FeatureContribution(**x) for x in r.top_features],base_value=round(base,3),note="SHAP values describe model contribution, not physical causality.")
@app.get("/history/{machine_id}")
def history(machine_id:str):
    p=require(); h=p.get_history(machine_id); return {"machine_id":machine_id,"n_observations":len(h),"rul_history":h}
@app.delete("/history/{machine_id}")
def clear(machine_id:str):
    require().clear_history(machine_id); buffers.pop(machine_id,None); return {"status":"cleared","machine_id":machine_id}
