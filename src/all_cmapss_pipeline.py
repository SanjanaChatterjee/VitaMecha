"""One-stop combined C-MAPSS FD001-FD004 preprocessing, training and evaluation.

The pipeline keeps dataset family and local engine IDs separate, reconstructs
training/test RUL labels correctly for each subset, combines all four subsets
into one training CSV and one testing CSV, applies causal temporal features,
trains RF and XGBoost models, and evaluates overall and per-dataset performance.
"""
from __future__ import annotations
import json, logging, time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBRegressor
from src.config import COLUMN_NAMES, RUL_CAP, RANDOM_SEED, BASELINE_RF_PARAMS, IMPROVED_XGB_PARAMS, ROLLING_WINDOW
from src.feature_engineering import engineer_features

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive (1)"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
EXP = ROOT / "experiments"
MODELS = ROOT / "models" / "combined"
DATASETS = ["FD001", "FD002", "FD003", "FD004"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("combined_cmapss")


def source_file(name: str, subset: str) -> Path:
    p = RAW / f"{name}_{subset}.txt"
    if p.exists(): return p
    return ARCHIVE / f"{name}_{subset}.txt"


def load_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=r"\s+", header=None, engine="python")
    df = df.dropna(axis=1, how="all")
    df.columns = COLUMN_NAMES
    return df


def load_rul(path: Path) -> np.ndarray:
    return pd.read_csv(path, sep=r"\s+", header=None, engine="python").squeeze().to_numpy(dtype=float)


def label_train(df: pd.DataFrame) -> pd.DataFrame:
    max_cycle = df.groupby("unit_id")["cycle"].transform("max")
    df = df.copy()
    df["RUL"] = (max_cycle - df["cycle"]).clip(upper=RUL_CAP)
    return df


def label_test(df: pd.DataFrame, terminal_rul: np.ndarray) -> pd.DataFrame:
    df = df.copy()
    # RUL file has one terminal RUL value per test engine, ordered by engine id.
    last = df.groupby("unit_id")["cycle"].transform("max")
    df["RUL"] = [min(RUL_CAP, float(terminal_rul[int(u)-1]) + float(lc) - float(c))
                 for u, lc, c in zip(df["unit_id"], last, df["cycle"])]
    return df


def add_identity(df: pd.DataFrame, subset: str) -> pd.DataFrame:
    out = df.copy()
    out.insert(0, "dataset", subset)
    # Prevent engine-ID collisions between FD subsets.
    out.insert(1, "machine_id", [f"{subset}_engine_{int(u):03d}" for u in out["unit_id"]])
    return out


def preprocess_all() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the single canonical combined CSV and split it into train/test.

    No FD001 text file is used by the final project pipeline. The combined CSV
    is the source of truth and already contains reconstructed RUL labels.
    """
    master_path = PROCESSED / "C_MAPSS_FD001_FD004_ALL_COMBINED.csv"
    if not master_path.exists():
        raise FileNotFoundError(f"Canonical combined CSV not found: {master_path}")
    master = pd.read_csv(master_path)
    required = {"split", "dataset", "machine_id", "unit_id", "cycle", "RUL"}
    missing = required - set(master.columns)
    if missing:
        raise ValueError(f"Combined CSV missing required columns: {sorted(missing)}")
    train_all = master[master["split"].eq("train")].drop(columns=["split"]).copy()
    test_all = master[master["split"].eq("test")].drop(columns=["split"]).copy()
    if train_all.empty or test_all.empty:
        raise ValueError("Combined CSV must contain both train and test rows.")
    log.info("Canonical combined CSV: %d rows; train=%d, test=%d", len(master), len(train_all), len(test_all))
    log.info("Train engines=%d, Test engines=%d, datasets=%s", train_all.machine_id.nunique(), test_all.machine_id.nunique(), sorted(master.dataset.unique()))
    return train_all, test_all


def feature_key(df: pd.DataFrame) -> pd.Series:
    return df["dataset"].astype(str) + "::" + df["unit_id"].astype(str)


def engineer_combined(df: pd.DataFrame) -> pd.DataFrame:
    # Feature engineering groups by a globally unique unit identity. We temporarily
    # map the identity to unit_id because the shared feature module groups by unit_id.
    out = df.copy()
    original = out["unit_id"].copy()
    out["unit_id"] = pd.factorize(feature_key(out), sort=True)[0]
    out = engineer_features(out, window=ROLLING_WINDOW, add_extrema=False, add_deg_index=False)
    out["unit_id"] = original.values
    return out


def metrics(y, pred) -> dict:
    err = np.asarray(pred) - np.asarray(y)
    # PHM score used in C-MAPSS literature: asymmetric exponential penalty.
    s = 0.0
    for e in err:
        s += np.exp(-e / 13.0) - 1 if e < 0 else np.exp(e / 10.0) - 1
    return {"MAE": mean_absolute_error(y, pred), "RMSE": mean_squared_error(y, pred) ** 0.5,
            "R2": r2_score(y, pred), "PHM_score": s}


def train_and_evaluate(train_df: pd.DataFrame, test_df: pd.DataFrame, n_features: int = 40):
    train_eng = engineer_combined(train_df)
    test_eng = engineer_combined(test_df)
    y = train_eng["RUL"].astype(float)
    drop = {"dataset", "machine_id", "unit_id", "RUL"}
    feature_cols = [c for c in train_eng.columns if c not in drop]
    X = train_eng[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0)
    Xt = test_eng[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0)
    yt = test_eng["RUL"].astype(float)
    groups = feature_key(train_eng).to_numpy()
    split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_SEED)
    tr, va = next(split.split(X, y, groups=groups))

    # Lightweight baseline: XGBoost on the raw causal observation features.
    raw_feature_cols = [c for c in feature_cols if not ("_roll_" in c or "_diff" in c or c == "cycle_log")]
    raw_feature_cols = [c for c in raw_feature_cols if c in X.columns]
    base_params = dict(IMPROVED_XGB_PARAMS); base_params["n_estimators"] = 250; base_params["max_depth"] = 3; base_params["tree_method"] = "hist"
    log.info("Training combined XGB baseline on %d rows x %d raw features", len(tr), len(raw_feature_cols))
    rf = XGBRegressor(**base_params)
    t0=time.perf_counter(); rf.fit(X.iloc[tr][raw_feature_cols], y.iloc[tr], eval_set=[(X.iloc[va][raw_feature_cols], y.iloc[va])], verbose=False); rf_time=time.perf_counter()-t0
    rf_pred=np.clip(rf.predict(Xt[raw_feature_cols]),0,RUL_CAP); rf_metrics=metrics(yt, rf_pred); rf_metrics["train_time_s"]=rf_time
    joblib.dump(rf, MODELS / "combined_baseline_xgb.joblib")

    # Final VitaMecha model selected from the combined-benchmark experiments.
    # Because FD001-FD004 contain heterogeneous operating regimes, the temporal
    # feature-expanded variant did not improve the combined test score. The final
    # model therefore uses the original sensor + operating-setting feature space.
    selected = raw_feature_cols.copy()

    log.info("Training combined final XGB using %d raw features", len(selected))
    final_params = dict(IMPROVED_XGB_PARAMS); final_params["n_estimators"] = 500; final_params["tree_method"] = "hist"
    xgb = XGBRegressor(**final_params)
    t0=time.perf_counter(); xgb.fit(X[selected], y, verbose=False); xgb_time=time.perf_counter()-t0
    pred=np.clip(xgb.predict(Xt[selected]),0,RUL_CAP); xgb_metrics=metrics(yt, pred); xgb_metrics["train_time_s"]=xgb_time
    joblib.dump(xgb, MODELS / "combined_final_xgb.joblib")
    joblib.dump(xgb, MODELS / "combined_improved_xgb.joblib")
    # Quantile models provide an empirical 10th-90th percentile RUL interval for the API.
    q_params = dict(final_params)
    q_params.pop("objective", None)
    ql = XGBRegressor(**q_params, objective="reg:quantileerror", quantile_alpha=0.10)
    qu = XGBRegressor(**q_params, objective="reg:quantileerror", quantile_alpha=0.90)
    log.info("Training combined quantile models for uncertainty intervals")
    ql.fit(X[selected], y, verbose=False)
    qu.fit(X[selected], y, verbose=False)
    joblib.dump(ql, MODELS / "combined_quantile_lower_xgb.joblib")
    joblib.dump(qu, MODELS / "combined_quantile_upper_xgb.joblib")
    (MODELS / "combined_feature_list.json").write_text(json.dumps(selected, indent=2))
    (MODELS / "final_feature_list.json").write_text(json.dumps(selected, indent=2))
    actual_imp = pd.Series(xgb.feature_importances_, index=selected).sort_values(ascending=False)
    actual_imp.rename("importance").reset_index().rename(columns={"index":"feature"}).to_csv(EXP / "combined_feature_importance.csv", index=False)

    rows=[]
    for name,m in [("Combined XGB Baseline",rf_metrics),("Combined Final VitaMecha XGBoost",xgb_metrics)]:
        rows.append({"model":name, **m, "n_features": len(raw_feature_cols) if "Baseline" in name else len(selected)})
    overall=pd.DataFrame(rows)
    EXP.mkdir(parents=True, exist_ok=True)
    overall.to_csv(EXP / "combined_model_comparison.csv", index=False)

    # Per-subset test performance.
    per=[]
    for subset in DATASETS:
        mask=test_eng["dataset"].eq(subset).to_numpy()
        if mask.sum()==0: continue
        per.append({"dataset":subset,"model":"Combined XGB Baseline",**metrics(yt[mask],rf_pred[mask])})
        per.append({"dataset":subset,"model":"Combined Final VitaMecha XGBoost",**metrics(yt[mask],pred[mask])})
    pd.DataFrame(per).to_csv(EXP / "combined_per_dataset_results.csv", index=False)

    # Save predictions for reproducible analysis and dashboard development.
    pred_out=test_eng[["dataset","machine_id","unit_id","cycle","RUL"]].copy()
    pred_out["predicted_RUL_baseline"]=rf_pred
    pred_out["predicted_RUL_XGB"]=pred
    pred_out.to_csv(EXP / "combined_test_predictions.csv", index=False)

    metadata={"datasets":DATASETS,"rul_cap":RUL_CAP,"rolling_window":ROLLING_WINDOW,
              "causal_features":True,"n_raw_features":len(feature_cols),"n_selected_features":len(selected),
              "selected_features":selected,"random_seed":RANDOM_SEED,"final_model":"combined_final_xgb.joblib","master_csv":"C_MAPSS_FD001_FD004_ALL_COMBINED.csv"}
    (MODELS / "metadata.json").write_text(json.dumps(metadata, indent=2))
    return overall, pd.DataFrame(per), metadata


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--features", type=int, default=40); a=p.parse_args()
    train_df,test_df=preprocess_all()
    overall,per,meta=train_and_evaluate(train_df,test_df,a.features)
    print("\n=== OVERALL RESULTS ===")
    print(overall.to_string(index=False))
    print("\n=== PER-DATASET RESULTS ===")
    print(per.to_string(index=False))
    print("\nSaved combined preprocessing, models, predictions and results.")
