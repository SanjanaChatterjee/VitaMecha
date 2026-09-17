"""Central VitaMecha configuration."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT_DIR / "data" / "raw"
DATA_PROCESSED = ROOT_DIR / "data" / "processed"
COMBINED_MASTER_CSV = DATA_PROCESSED / "C_MAPSS_FD001_FD004_ALL_COMBINED.csv"
COMBINED_TRAIN_CSV = DATA_PROCESSED / "train_FD001_FD004_combined.csv"
COMBINED_TEST_CSV = DATA_PROCESSED / "test_FD001_FD004_combined.csv"
# Legacy raw FD001 paths are retained only for archival compatibility.
TRAIN_FILE = DATA_RAW / "train_FD001.txt"
TEST_FILE = DATA_RAW / "test_FD001.txt"
RUL_FILE = DATA_RAW / "RUL_FD001.txt"
# Canonical VitaMecha data source: the combined FD001-FD004 CSV.
TRAIN_PROCESSED = COMBINED_TRAIN_CSV
TEST_PROCESSED = COMBINED_TEST_CSV
TRAIN_ENGINEERED = DATA_PROCESSED / "train_FD001_FD004_engineered.csv"
TEST_ENGINEERED = DATA_PROCESSED / "test_FD001_FD004_engineered.csv"

MODEL_DIR = ROOT_DIR / "models"
BASELINE_DIR = MODEL_DIR / "combined"
IMPROVED_DIR = MODEL_DIR / "combined"
BASELINE_MODEL = IMPROVED_DIR / "combined_baseline_xgb.joblib"
BASELINE_SCALER = IMPROVED_DIR / "scaler.joblib"
BASELINE_FEATURE_LIST = IMPROVED_DIR / "combined_feature_list.json"
IMPROVED_MODEL = IMPROVED_DIR / "combined_final_xgb.joblib"
SCALER_PATH = IMPROVED_DIR / "scaler.joblib"  # tree model does not require scaling
FEATURE_LIST_PATH = IMPROVED_DIR / "final_feature_list.json"
QUANTILE_LOWER_MODEL = IMPROVED_DIR / "combined_quantile_lower_xgb.joblib"
QUANTILE_UPPER_MODEL = IMPROVED_DIR / "combined_quantile_upper_xgb.joblib"

EXPERIMENTS_DIR = ROOT_DIR / "experiments"
BASELINE_RESULTS = EXPERIMENTS_DIR / "baseline_results.csv"
IMPROVEMENT_RESULTS = EXPERIMENTS_DIR / "improvement_results.csv"
ROBUSTNESS_RESULTS = EXPERIMENTS_DIR / "robustness_results.csv"
STREAMING_RESULTS = EXPERIMENTS_DIR / "streaming_results.csv"

COLUMN_NAMES = ["unit_id", "cycle", "op_setting_1", "op_setting_2", "op_setting_3"] + [f"sensor_{i}" for i in range(1, 22)]
CONSTANT_SENSORS = ["sensor_1", "sensor_5", "sensor_6", "sensor_10", "sensor_16", "sensor_18", "sensor_19"]
DROP_COLUMNS = ["unit_id", "cycle"] + CONSTANT_SENSORS
RUL_CAP = 125
ROLLING_WINDOW = 5
RANDOM_SEED = 42

HEALTH_THRESHOLDS = {"HEALTHY": 80, "WARNING": 40, "DEGRADED": 15, "CRITICAL": 0}

BASELINE_RF_PARAMS = {"n_estimators": 200, "max_depth": 15, "min_samples_leaf": 4, "random_state": RANDOM_SEED, "n_jobs": -1}
IMPROVED_XGB_PARAMS = {
    "n_estimators": 1200, "max_depth": 3, "learning_rate": 0.03,
    "subsample": 0.85, "colsample_bytree": 0.85, "min_child_weight": 5,
    "reg_alpha": 0.1, "reg_lambda": 5.0, "objective": "reg:squarederror",
    "random_state": RANDOM_SEED, "n_jobs": -1,
}
QUANTILE_LOWER = 0.10
QUANTILE_UPPER = 0.90

API_HOST = "0.0.0.0"
API_PORT = 8000
API_TITLE = "VitaMecha API"
API_DESCRIPTION = "Explainable predictive-maintenance decision-support API for C-MAPSS RUL estimation."
API_VERSION = "2.0.0"
MAX_HISTORY_PER_MACHINE = 500
STREAM_DELAY_SECONDS = 0.15
SHAP_TOP_N_FEATURES = 8
