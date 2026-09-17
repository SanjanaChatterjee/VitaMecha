"""Controlled robustness experiments for sensor noise and missing values."""
from __future__ import annotations
import sys, json
from pathlib import Path
import joblib, numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parent.parent; sys.path.insert(0,str(ROOT))
from src.config import *
from src.data_processing import load_processed, build_feature_matrix
from src.feature_engineering import engineer_features
from src.evaluate import compute_metrics

RNG=np.random.default_rng(RANDOM_SEED)

def perturb_raw(df, noise=0.0, missing=0.0):
    out=df.copy(); sensors=[c for c in out if c.startswith('sensor_')]
    if noise:
        for c in sensors:
            scale=float(out[c].max()-out[c].min()) or 1.0
            out[c]+=RNG.normal(0,noise*scale,len(out))
    if missing:
        mask=RNG.random((len(out),len(sensors)))<missing
        for j,c in enumerate(sensors): out.loc[mask[:,j],c]=np.nan
        out[sensors]=out[sensors].ffill().bfill().fillna(out[sensors].median())
    return out

def eval_model(label, raw, improved):
    if improved:
        data=engineer_features(raw,window=ROLLING_WINDOW,add_extrema=False)
        model=joblib.load(IMPROVED_MODEL); features=json.loads(FEATURE_LIST_PATH.read_text())
    else:
        data=raw; model=joblib.load(BASELINE_MODEL); features=json.loads(BASELINE_FEATURE_LIST.read_text())
    X,y=build_feature_matrix(data); X=X.reindex(columns=features,fill_value=0)
    pred=np.clip(model.predict(X),0,RUL_CAP)
    return compute_metrics(y,pred)|{"model":label}

def run():
    _,test=load_processed(); rows=[]
    conditions=[('Clean',0,0),('Noise 5%',.05,0),('Noise 10%',.10,0),('Missing 10%',0,.10),('Missing 20%',0,.20)]
    for name,n,m in conditions:
        # Independent but deterministic perturbation per condition.
        global RNG; RNG=np.random.default_rng(RANDOM_SEED+int(n*1000)+int(m*1000))
        raw=perturb_raw(test,n,m)
        rows += [eval_model('Baseline RF',raw,False)|{'condition':name}, eval_model('Improved XGBoost',raw,True)|{'condition':name}]
    out=pd.DataFrame(rows); EXPERIMENTS_DIR.mkdir(exist_ok=True); out.to_csv(ROBUSTNESS_RESULTS,index=False); return out

if __name__=='__main__': print(run().to_string(index=False))
