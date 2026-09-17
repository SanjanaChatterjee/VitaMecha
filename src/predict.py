"""VitaMecha inference engine: predict -> explain -> assess -> recommend."""
from __future__ import annotations
import datetime, json, logging, time
from typing import Dict, List, Optional
import joblib, numpy as np, pandas as pd
from src.config import *
from src.evaluate import load_model_artefacts
from src.explain import VitaMechaExplainer
from src.health import HealthAssessment, classify_health, get_trend
from src.recommendation import generate_recommendation
from src.feature_engineering import engineer_features

logger=logging.getLogger(__name__)

class PredictionResult:
    def __init__(self,machine_id,cycle,predicted_rul,health,recommendation,top_features,inference_ms,rul_lower=None,rul_upper=None,trend="Unknown"):
        self.machine_id=machine_id; self.cycle=cycle; self.predicted_rul=predicted_rul; self.rul_lower=rul_lower; self.rul_upper=rul_upper
        self.health=health; self.recommendation=recommendation; self.top_features=top_features; self.inference_ms=inference_ms
        self.trend=trend; self.timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.true_rul=None
    def to_dict(self):
        return {"machine_id":self.machine_id,"cycle":self.cycle,"predicted_rul":round(self.predicted_rul,2),"rul_lower":self.rul_lower,"rul_upper":self.rul_upper,"health":self.health.to_dict(),"trend":self.trend,"recommendation":self.recommendation.to_dict(),"top_features":self.top_features,"inference_ms":round(self.inference_ms,3),"timestamp":self.timestamp}

class VitaMechaPredictor:
    def __init__(self, model_path=IMPROVED_MODEL, scaler_path=SCALER_PATH, feature_list_path=FEATURE_LIST_PATH, use_quantile=True, use_shap=True):
        self.model, self.scaler, self.feature_names = load_model_artefacts(model_path, scaler_path, feature_list_path)
        self.use_quantile=use_quantile; self.q_lower_model=self.q_upper_model=None
        if use_quantile:
            try:
                self.q_lower_model=joblib.load(QUANTILE_LOWER_MODEL); self.q_upper_model=joblib.load(QUANTILE_UPPER_MODEL)
            except FileNotFoundError: self.use_quantile=False
        self.use_shap=use_shap; self.explainer=None
        if use_shap:
            try: self.explainer=VitaMechaExplainer(self.model,self.feature_names)
            except Exception as e: logger.warning("SHAP disabled: %s",e); self.use_shap=False
        self._rul_history={}

    def predict_from_frame(self, frame: pd.DataFrame, machine_id="unknown", cycle=None, top_n_shap=SHAP_TOP_N_FEATURES):
        """Predict using a chronological raw/processed machine-history frame."""
        t0=time.perf_counter(); eng=engineer_features(frame,window=ROLLING_WINDOW,add_extrema=False)
        latest=eng.iloc[[-1]].copy(); current_cycle=int(latest["cycle"].iloc[0] if cycle is None else cycle)
        X=latest.reindex(columns=self.feature_names,fill_value=0.0)
        pred=float(min(float(RUL_CAP), max(0.0,self.model.predict(X)[0]))); lo=hi=None
        if self.use_quantile:
            lo=float(min(float(RUL_CAP), max(0.0,self.q_lower_model.predict(X)[0]))); hi=float(min(float(RUL_CAP), max(0.0,self.q_upper_model.predict(X)[0]))); lo,hi=min(lo,hi,pred),max(hi,lo,pred)
        hist=self._rul_history.setdefault(machine_id,[]); hist.append(pred); self._rul_history[machine_id]=hist[-MAX_HISTORY_PER_MACHINE:]
        trend=get_trend(hist); health=classify_health(pred,lo,hi)
        top=[]
        if self.use_shap and self.explainer:
            try: top=self.explainer.explain_local(X,top_n=top_n_shap)
            except Exception as e: logger.warning("SHAP failed: %s",e)
        rec=generate_recommendation(health,trend,top)
        return PredictionResult(machine_id,current_cycle,pred,health,rec,top,(time.perf_counter()-t0)*1000,lo,hi,trend)

    def predict(self,sensor_dict,machine_id="unknown",cycle=0,rul_history=None,top_n_shap=SHAP_TOP_N_FEATURES):
        """Single-observation fallback. Temporal features use current values and zero differences."""
        row={"unit_id":1,"cycle":cycle,**sensor_dict}; return self.predict_from_frame(pd.DataFrame([row]),machine_id,cycle,top_n_shap)
    def get_history(self,machine_id): return self._rul_history.get(machine_id,[])
    def clear_history(self,machine_id): self._rul_history.pop(machine_id,None)

def predict_baseline(sensor_dict,machine_id="unknown",cycle=0):
    model,_,features=load_model_artefacts(BASELINE_MODEL,None,BASELINE_FEATURE_LIST); X=pd.DataFrame([{k:sensor_dict.get(k,0.0) for k in features}],columns=features)
    t=time.perf_counter(); pred=float(max(0,model.predict(X)[0])); return {"machine_id":machine_id,"cycle":cycle,"predicted_rul":round(pred,2),"inference_ms":round((time.perf_counter()-t)*1000,3)}
