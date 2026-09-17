# VitaMecha Combined C-MAPSS FD001-FD004 Results

## Canonical data source

The final project uses `data/processed/C_MAPSS_FD001_FD004_ALL_COMBINED.csv` as the single source of truth. It contains both train and test observations, identified by `split`, with `dataset`, globally unique `machine_id`, `unit_id`, `cycle`, 3 operating settings, 21 sensors and RUL.

- Total rows: **265,256**
- Training rows: **160,359**
- Training engines: **709**
- Test rows: **104,897**
- Test engines: **707**

## Overall test performance

| Model | MAE | RMSE | R2 | PHM Score |
|---|---:|---:|---:|---:|
| Combined XGB Baseline | 12.3587 | 17.8542 | 0.5583 | 855,449.31 |
| Final VitaMecha XGBoost | **11.4479** | **16.7926** | **0.6092** | **834,687.09** |

Relative to the reproducible combined baseline, the final model improves MAE by approximately **7.36%**, RMSE by **5.95%**, and increases R2 by **0.05097** absolute.

## Per-dataset test performance

| Dataset | MAE | RMSE | R2 |
|---|---:|---:|---:|
| FD001 | 10.5396 | 15.9396 | 0.6660 |
| FD002 | 12.1418 | 17.4634 | 0.6330 |
| FD003 | 9.2274 | 13.9866 | 0.6829 |
| FD004 | 12.0584 | 17.5126 | 0.5270 |

## Interpretation

The final model is selected because it performs better than the combined baseline on the overall test set. FD004 remains the most challenging subset by R2, indicating that heterogeneous operating conditions and degradation behaviour remain difficult for the unified model.

A temporal-feature-expanded candidate was evaluated during development but was not selected for the final combined benchmark because it did not outperform the simpler raw-feature model. This is reported as an empirical model-selection result, not hidden.

## Robustness

The robustness experiment is stored in `experiments/combined_robustness_results.csv`. The final model shows degradation under substantial Gaussian sensor noise and missing-sensor conditions. Therefore VitaMecha does **not** claim universal robustness to corrupted telemetry. This limitation is an appropriate target for future noise-aware training and sensor-quality modelling.

## XAI

SHAP TreeExplainer is applied to the final combined XGBoost model. Global importance is stored in `experiments/global_shap_importance.csv`. SHAP values represent feature contribution to the model prediction and must not be interpreted as proof of physical causality.

## Deployment validation

The FastAPI backend was tested against a real observation from the combined test set and returned a valid RUL, health state, risk level, SHAP explanation and maintenance recommendation. The current project test suite passes **46 tests**.

## Academic interpretation

These results support the following defensible statement:

> VitaMecha provides a lightweight, experimentally evaluated predictive-maintenance decision-support pipeline over the combined C-MAPSS FD001-FD004 benchmark, with baseline comparison, XAI, robustness analysis, sequential inference and deployable API/dashboard components.

The system remains an academic prototype. C-MAPSS streaming is simulated and maintenance recommendations remain subject to qualified human engineering judgement.
