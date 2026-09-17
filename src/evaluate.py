"""Evaluation for the canonical combined FD001-FD004 VitaMecha models."""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
import joblib,numpy as np,pandas as pd
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from src.config import *
from src.data_processing import load_processed

def phm_score(y_true,y_pred):
    d=np.asarray(y_pred)-np.asarray(y_true)
    return float(np.where(d<0,np.exp(-d/13)-1,np.exp(d/10)-1).sum())

def compute_metrics(y_true,y_pred,latency_ms=0):
    return {"MAE":round(float(mean_absolute_error(y_true,y_pred)),4),"RMSE":round(float(np.sqrt(mean_squared_error(y_true,y_pred))),4),"R2":round(float(r2_score(y_true,y_pred)),4),"PHM_Score":round(phm_score(y_true,y_pred),2),"Inference_ms_per_sample":round(float(latency_ms/max(1,len(y_true))),5),"N_samples":int(len(y_true))}

def load_model_artefacts(model_path,scaler_path=None,feature_list_path=None):
    model=joblib.load(model_path); features=json.loads(Path(feature_list_path).read_text()) if feature_list_path else None
    scaler=joblib.load(scaler_path) if scaler_path and Path(scaler_path).exists() else None
    return model,scaler,features

def _evaluate(model_path,feature_path,name):
    _,test=load_processed(); model,_,features=load_model_artefacts(model_path,None,feature_path)
    X=test.reindex(columns=features,fill_value=0).replace([np.inf,-np.inf],np.nan).fillna(0.0)
    y=test.RUL.to_numpy(float)
    t=time.perf_counter(); pred=np.clip(model.predict(X),0,RUL_CAP); ms=(time.perf_counter()-t)*1000
    return compute_metrics(y,pred,ms)|{"model":name}

def evaluate_baseline(): return _evaluate(BASELINE_MODEL,BASELINE_FEATURE_LIST,"Combined XGB Baseline")
def evaluate_improved(): return _evaluate(IMPROVED_MODEL,FEATURE_LIST_PATH,"Combined Final VitaMecha XGBoost")

def evaluate_all(save=True):
    rows=[evaluate_baseline(),evaluate_improved()]
    out=pd.DataFrame(rows)
    if save: EXPERIMENTS_DIR.mkdir(parents=True,exist_ok=True); out.to_csv(EXPERIMENTS_DIR/"model_comparison.csv",index=False)
    return out

if __name__=="__main__":
    print(evaluate_all().to_string(index=False))
