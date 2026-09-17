"""
Proper baseline evaluation of vitamecha_rul_model.pkl.

The model was trained with ALL 21 raw sensors (no constant sensor dropping).
We must reconstruct features using the same approach: raw data + rolling
stats on the non-constant sensors listed in model_dict['sensors'].
"""

import time
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

COLUMN_NAMES = (
    ["unit_id", "cycle", "op_setting_1", "op_setting_2", "op_setting_3"]
    + [f"sensor_{i}" for i in range(1, 22)]
)

RUL_CAP = 125
WINDOW = 10  # assume same rolling window as training

# 1. Load RAW test data (keeping all 21 sensors)
test_raw = pd.read_csv("data/raw/test_FD001.txt", sep=r"\s+", header=None, engine="python")
test_raw = test_raw.dropna(axis=1, how="all")
test_raw.columns = COLUMN_NAMES

# 2. Label test RUL
true_rul = pd.read_csv("data/raw/RUL_FD001.txt", sep=r"\s+", header=None).squeeze().values
unit_ids = test_raw["unit_id"].unique()
rul_records = []
for uid in sorted(unit_ids):
    udf = test_raw[test_raw["unit_id"] == uid].copy()
    last_cycle = udf["cycle"].max()
    terminal_rul = float(true_rul[uid - 1])
    udf["RUL"] = (terminal_rul + last_cycle - udf["cycle"]).clip(upper=RUL_CAP)
    rul_records.append(udf)
test_df = pd.concat(rul_records, ignore_index=True)

# 3. Load model
model_dict = joblib.load("models/vitamecha_rul_model.pkl")
model = model_dict["model"]
expected_features = model_dict["features"]
rolling_sensors = model_dict["sensors"]

# 4. Build rolling features on the same sensors the model was trained on
test_df = test_df.sort_values(["unit_id", "cycle"])
groups = []
for uid, grp in test_df.groupby("unit_id", sort=True):
    grp = grp.sort_values("cycle").copy()
    roll = grp[rolling_sensors].rolling(window=WINDOW, min_periods=1)
    for col in rolling_sensors:
        grp[f"{col}_rolling_mean"] = roll[col].mean().values
        grp[f"{col}_rolling_std"] = roll[col].std(ddof=0).fillna(0).values
        grp[f"{col}_diff"] = grp[col].diff().fillna(0).values
    groups.append(grp)
test_eng = pd.concat(groups, ignore_index=True)

# 5. Align to expected features
for col in expected_features:
    if col not in test_eng.columns:
        test_eng[col] = 0.0
X_test = test_eng[expected_features]
y_test = test_eng["RUL"]

# 6. Timed prediction
t0 = time.perf_counter()
y_pred = model.predict(X_test)
inference_ms = (time.perf_counter() - t0) * 1000
y_pred = np.clip(y_pred, 0, None)

# 7. Metrics
rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
mae = float(mean_absolute_error(y_test, y_pred))
r2 = float(r2_score(y_test, y_pred))
d = y_pred - y_test.values
phm = float(np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1).sum())
latency = inference_ms / len(y_test)

print("\n" + "=" * 60)
print("PRE-TRAINED BASELINE — vitamecha_rul_model.pkl")
print("=" * 60)
print(f"Model type          : {type(model).__name__}")
print(f"Total features      : {len(expected_features)}")
print(f"Test samples        : {len(y_test):,}")
print(f"")
print(f"RMSE                : {rmse:.4f}")
print(f"MAE                 : {mae:.4f}")
print(f"R2                  : {r2:.4f}")
print(f"PHM Score           : {phm:.2f}")
print(f"Inference latency   : {latency:.4f} ms/sample")
print(f"Total inference     : {inference_ms:.2f} ms")
print("=" * 60)

# 8. Save to experiments/baseline_results.csv
import os
os.makedirs("experiments", exist_ok=True)
row = pd.DataFrame([{
    "model": "Pre-trained Baseline (XGBoost)",
    "MAE": round(mae, 4),
    "RMSE": round(rmse, 4),
    "R2": round(r2, 4),
    "PHM_Score": round(phm, 2),
    "Inference_ms_per_sample": round(latency, 4),
    "N_samples": len(y_test),
    "note": "Evaluated with all 21 raw sensors + rolling features (as trained)"
}])
row.to_csv("experiments/baseline_results.csv", index=False)
print("Saved -> experiments/baseline_results.csv")
