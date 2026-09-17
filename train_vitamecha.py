import os
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor


# ============================================================
# 1. CONFIGURATION
# ============================================================

TRAIN_PATH = "data/train_FD001.txt"
TEST_PATH = "data/test_FD001.txt"
RUL_PATH = "data/RUL_FD001.txt"

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "vitamecha_rul_model.pkl")

os.makedirs(MODEL_DIR, exist_ok=True)


# ============================================================
# 2. COLUMN NAMES
# ============================================================

columns = [
    "unit",
    "cycle",
    "op_setting_1",
    "op_setting_2",
    "op_setting_3",
]

sensor_columns = [f"sensor_{i}" for i in range(1, 22)]

columns.extend(sensor_columns)


# ============================================================
# 3. LOAD DATA
# ============================================================

print("\nLoading dataset...")

train_df = pd.read_csv(
    TRAIN_PATH,
    sep=r"\s+",
    header=None,
    names=columns
)

test_df = pd.read_csv(
    TEST_PATH,
    sep=r"\s+",
    header=None,
    names=columns
)

rul_df = pd.read_csv(
    RUL_PATH,
    sep=r"\s+",
    header=None,
    names=["RUL"]
)

print("Training shape:", train_df.shape)
print("Testing shape :", test_df.shape)


# ============================================================
# 4. CALCULATE RUL FOR TRAINING DATA
# ============================================================

print("\nCreating RUL labels...")

max_cycle = train_df.groupby("unit")["cycle"].max()

train_df["max_cycle"] = train_df["unit"].map(max_cycle)

train_df["RUL"] = (
    train_df["max_cycle"] - train_df["cycle"]
)

train_df.drop(columns=["max_cycle"], inplace=True)


# ============================================================
# 5. PREPROCESS TEST DATA
# ============================================================

print("Creating test RUL labels...")

max_test_cycle = test_df.groupby("unit")["cycle"].max()

test_df["max_cycle"] = test_df["unit"].map(max_test_cycle)

# Actual RUL of the final observation of every test engine
test_last_rul = rul_df["RUL"].values

test_df["RUL"] = 0.0

for i, unit in enumerate(
    test_df["unit"].unique()
):

    unit_data = test_df[test_df["unit"] == unit]

    last_cycle = unit_data["cycle"].max()

    test_df.loc[
        test_df["unit"] == unit,
        "RUL"
    ] = (
        test_last_rul[i]
        + last_cycle
        - test_df.loc[
            test_df["unit"] == unit,
            "cycle"
        ]
    )


# ============================================================
# 6. REMOVE USELESS SENSORS
# ============================================================

print("\nChecking sensor variance...")

variance = train_df[sensor_columns].var()

useful_sensors = variance[
    variance > 0.0
].index.tolist()

print(
    f"Useful sensors: {len(useful_sensors)} / "
    f"{len(sensor_columns)}"
)

print("Removed sensors:")

for sensor in sensor_columns:
    if sensor not in useful_sensors:
        print("  ", sensor)


# ============================================================
# 7. FEATURE ENGINEERING
# ============================================================

print("\nCreating features...")


def create_features(df, sensors):

    result = df.copy()

    for sensor in sensors:

        # Rolling mean
        result[f"{sensor}_rolling_mean"] = (
            result.groupby("unit")[sensor]
            .transform(
                lambda x:
                x.rolling(
                    window=5,
                    min_periods=1
                ).mean()
            )
        )

        # Rolling standard deviation
        result[f"{sensor}_rolling_std"] = (
            result.groupby("unit")[sensor]
            .transform(
                lambda x:
                x.rolling(
                    window=5,
                    min_periods=1
                ).std()
            )
        )

        # Sensor trend / rate of change
        result[f"{sensor}_diff"] = (
            result.groupby("unit")[sensor]
            .diff()
        )

    result = result.fillna(0)

    return result


train_df = create_features(
    train_df,
    useful_sensors
)

test_df = create_features(
    test_df,
    useful_sensors
)


# ============================================================
# 8. SELECT FEATURES
# ============================================================

exclude_columns = [
    "unit",
    "RUL"
]

features = [
    col
    for col in train_df.columns
    if col not in exclude_columns
]

X_train = train_df[features]
y_train = train_df["RUL"]

X_test = test_df[features]
y_test = test_df["RUL"]


print("\nNumber of features:", len(features))


# ============================================================
# 9. TRAIN XGBOOST MODEL
# ============================================================

print("\nTraining XGBoost model...")

model = XGBRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)


# ============================================================
# 10. PREDICTION
# ============================================================

print("\nGenerating predictions...")

predictions = model.predict(X_test)

# RUL cannot be negative
predictions = np.maximum(
    predictions,
    0
)


# ============================================================
# 11. EVALUATION
# ============================================================

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        predictions
    )
)

r2 = r2_score(
    y_test,
    predictions
)

print("\n===================================")
print("        VITAMECHA RESULTS")
print("===================================")

print(f"MAE  : {mae:.3f}")
print(f"RMSE : {rmse:.3f}")
print(f"R²   : {r2:.3f}")

print("===================================")


# ============================================================
# 12. SAVE MODEL
# ============================================================

print("\nSaving model...")

model_data = {
    "model": model,
    "features": features,
    "sensors": useful_sensors
}

joblib.dump(
    model_data,
    MODEL_PATH
)

print(
    f"Model saved to: {MODEL_PATH}"
)


# ============================================================
# 13. VISUALIZE ACTUAL VS PREDICTED RUL
# ============================================================

plt.figure(
    figsize=(10, 6)
)

plt.scatter(
    y_test,
    predictions,
    alpha=0.5
)

plt.plot(
    [y_test.min(), y_test.max()],
    [y_test.min(), y_test.max()],
    linestyle="--"
)

plt.xlabel(
    "Actual RUL"
)

plt.ylabel(
    "Predicted RUL"
)

plt.title(
    "VitaMecha - Actual vs Predicted RUL"
)

plt.grid(
    True,
    alpha=0.3
)

plt.tight_layout()

plt.show()


# ============================================================
# 14. FEATURE IMPORTANCE
# ============================================================

importance = pd.Series(
    model.feature_importances_,
    index=features
)

importance = (
    importance
    .sort_values(
        ascending=False
    )
    .head(15)
)

print("\nTop 15 important features:")

print(importance)


plt.figure(
    figsize=(10, 6)
)

importance.sort_values().plot(
    kind="barh"
)

plt.title(
    "VitaMecha - Top Feature Importance"
)

plt.xlabel(
    "Importance"
)

plt.tight_layout()

plt.show()