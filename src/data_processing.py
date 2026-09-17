"""Canonical VitaMecha data loader for the combined FD001-FD004 CSV."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
import pandas as pd
from src.config import COMBINED_MASTER_CSV, COMBINED_TRAIN_CSV, COMBINED_TEST_CSV, RUL_CAP

logger=logging.getLogger(__name__)

def check_missing(df: pd.DataFrame, label: str="DATA") -> None:
    """Log missing-value counts; do not mutate the input."""
    missing=int(df.isna().sum().sum())
    if missing:
        logger.warning("%s contains %d missing values",label,missing)
    else:
        logger.info("%s contains no missing values",label)

def drop_constant_sensors(df: pd.DataFrame, threshold: float=1e-6) -> pd.DataFrame:
    """Drop sensor columns with variance at or below threshold."""
    out=df.copy()
    sensors=[c for c in out.columns if c.startswith("sensor_")]
    from src.config import CONSTANT_SENSORS
    drop=[c for c in sensors if pd.to_numeric(out[c],errors="coerce").var() <= threshold or c in CONSTANT_SENSORS]
    return out.drop(columns=drop)

def label_train_rul(df: pd.DataFrame, rul_cap: int=RUL_CAP) -> pd.DataFrame:
    """Generate capped training RUL from each engine's maximum observed cycle."""
    out=df.copy(); max_cycle=out.groupby("unit_id")["cycle"].transform("max")
    out["RUL"]=(max_cycle-out["cycle"]).clip(upper=rul_cap)
    return out

def label_test_rul(df: pd.DataFrame, true_rul: np.ndarray, rul_cap: int=RUL_CAP) -> pd.DataFrame:
    """Reconstruct every test-cycle RUL from terminal RUL values."""
    out=df.copy(); last=out.groupby("unit_id")["cycle"].transform("max")
    out["RUL"]=[min(rul_cap,float(true_rul[int(u)-1])+float(lc)-float(c)) for u,lc,c in zip(out.unit_id,last,out.cycle)]
    return out

def load_combined_master(path: Path = COMBINED_MASTER_CSV) -> pd.DataFrame:
    """Load the single combined FD001-FD004 master CSV."""
    if not path.exists():
        raise FileNotFoundError(f"Combined C-MAPSS CSV not found: {path}")
    df=pd.read_csv(path)
    required={"split","dataset","machine_id","unit_id","cycle","RUL"}
    missing=required-set(df.columns)
    if missing: raise ValueError(f"Combined CSV missing required columns: {sorted(missing)}")
    return df

def load_processed() -> Tuple[pd.DataFrame,pd.DataFrame]:
    """Return train/test partitions from the canonical combined CSV.

    The master CSV is the source of truth; separate train/test CSVs are used as
    cached partitions for faster application startup.
    """
    if COMBINED_TRAIN_CSV.exists() and COMBINED_TEST_CSV.exists():
        train=pd.read_csv(COMBINED_TRAIN_CSV); test=pd.read_csv(COMBINED_TEST_CSV)
    else:
        master=load_combined_master(); train=master[master.split.eq("train")].copy(); test=master[master.split.eq("test")].copy()
    logger.info("Loaded combined C-MAPSS — train=%s test=%s",train.shape,test.shape)
    return train,test

def build_feature_matrix(df: pd.DataFrame, drop_id_cols: bool=True):
    """Build X/y while removing identifiers that must not be model features."""
    y=df["RUL"].copy() if "RUL" in df.columns else None
    drop=[]
    if drop_id_cols: drop += [c for c in ["unit_id","machine_id","dataset","split","cycle"] if c in df.columns]
    if "RUL" in df.columns: drop.append("RUL")
    X=df.drop(columns=drop,errors="ignore").copy()
    X=X.replace([np.inf,-np.inf],np.nan).fillna(0.0)
    return X,y

def prepare_combined_cmapss() -> Tuple[pd.DataFrame,pd.DataFrame]:
    """Validate and return the canonical combined dataset."""
    master=load_combined_master()
    train=master[master.split.eq("train")].copy(); test=master[master.split.eq("test")].copy()
    return train,test

# Backwards-compatible name: it now means the combined FD001-FD004 dataset.
def prepare_cmapss(save_processed: bool=True):
    train,test=prepare_combined_cmapss()
    return train,test,train["RUL"].copy(),test["RUL"].copy()

if __name__=="__main__":
    train,test,_,_=prepare_cmapss()
    print("VitaMecha combined C-MAPSS dataset")
    print(f"Train: {len(train):,} rows / {train.machine_id.nunique():,} engines")
    print(f"Test : {len(test):,} rows / {test.machine_id.nunique():,} engines")
    print(f"Datasets: {sorted(train.dataset.unique())}")
    print(f"Features: {len([c for c in train.columns if c.startswith('sensor_') or c.startswith('op_setting_')])}")
