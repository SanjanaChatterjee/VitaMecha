# VitaMecha — A Life to Your Machines

**Academic title:** *VitaMecha: An Explainable Predictive Maintenance Framework for Remaining Useful Life Estimation and Intelligent Maintenance Decision Support*

VitaMecha is a Python-based academic decision-support prototype for sensor-driven predictive maintenance. It follows **Predict → Explain → Recommend → Deploy**.

## Canonical dataset

The final project uses **one combined CSV containing C-MAPSS FD001, FD002, FD003 and FD004**. The FD001 text files are no longer the training/testing source for the final pipeline.

Canonical source:

```text
data/processed/C_MAPSS_FD001_FD004_ALL_COMBINED.csv
```

The CSV contains `split`, `dataset`, globally unique `machine_id`, `unit_id`, `cycle`, 3 operating settings, 21 sensors and `RUL`. It contains 265,256 rows: 160,359 training observations from 709 engines and 104,897 test observations from 707 engines.

Separate cached partitions are also stored as `train_FD001_FD004_combined.csv` and `test_FD001_FD004_combined.csv`.

## Final model

The final model is an XGBoost regressor trained on the combined training partition. It uses the 25 raw observation features: cycle, 3 operating settings and 21 sensors. A causal temporal-feature candidate was experimentally evaluated but was not selected because it did not improve the combined benchmark.

The model is therefore selected by evidence rather than complexity.

## Final combined test result

| Model | MAE | RMSE | R² | PHM Score |
|---|---:|---:|---:|---:|
| Combined XGB Baseline | 12.3587 | 17.8542 | 0.5583 | 855,449.31 |
| **Final VitaMecha XGBoost** | **11.4479** | **16.7926** | **0.6092** | **834,687.09** |

These are regression metrics; R² must not be described as classification accuracy.

### Per-dataset performance

| Dataset | MAE | RMSE | R² |
|---|---:|---:|---:|
| FD001 | 10.5396 | 15.9396 | 0.6660 |
| FD002 | 12.1418 | 17.4634 | 0.6330 |
| FD003 | 9.2274 | 13.9866 | 0.6829 |
| FD004 | 12.0584 | 17.5126 | 0.5270 |

## One-command training and testing

From the project root:

```bash
python -m src.all_cmapss_pipeline
```

This command:

1. Loads the combined CSV.
2. Separates train/test using `split`.
3. Validates the four dataset families and globally unique engine IDs.
4. Trains the reproducible baseline.
5. Trains the final VitaMecha XGBoost model.
6. Trains empirical quantile models for an RUL interval.
7. Evaluates overall and per-dataset performance.
8. Saves predictions, feature importance and metadata.

Equivalent entry point:

```bash
python -m src.train
```

## Explainability

SHAP TreeExplainer provides local and global explanations. SHAP values describe **model contribution**, not physical causality.

Global artifacts:

```text
experiments/global_shap_importance.csv
experiments/figures/global_shap_importance.png
```

## Robustness

The project evaluates clean data, Gaussian sensor noise and missing-sensor conditions. These experiments are deliberately reported as robustness evidence rather than assumed strengths.

## Health and maintenance

Predicted RUL is translated through a transparent configurable rule layer into Healthy, Warning, Degraded or Critical states and Low/Medium/High/Critical risk. The recommendation engine is advisory; qualified engineers retain final authority.

## API

Start the backend:

```bash
uvicorn api.main:app --reload
```

Open the interactive API documentation at `/docs`. Main endpoints:

- `GET /` — system status
- `GET /health` — health check
- `GET /machines` — combined C-MAPSS machines
- `POST /predict` — RUL + health + recommendation + SHAP features
- `POST /stream` — sequential observation inference
- `POST /explain` — local explanation
- `GET /history/{machine_id}` — prediction history
- `DELETE /history/{machine_id}` — clear history

The API expects cycle, all three operating settings and all 21 sensor values.

## Dashboard

Start Streamlit:

```bash
streamlit run dashboard/app.py
```

The dashboard provides:

- machine selection across FD001–FD004
- cycle-based assessment
- predicted RUL
- health/risk
- RUL trend
- sensor profile
- maintenance recommendation
- local SHAP explanation
- simulated sequential streaming
- experimental results

## Simulated streaming

C-MAPSS is historical benchmark data, not physical telemetry. VitaMecha therefore simulates near-real-time streaming by replaying observations from a selected combined-dataset machine.

```bash
python -m src.streaming --machine FD001_engine_001 --benchmark
```

## Tests

```bash
pytest -q
```

The current project test suite passes **46 tests**.

## Project structure

```text
VitaMecha/
├── data/processed/
│   ├── C_MAPSS_FD001_FD004_ALL_COMBINED.csv
│   ├── train_FD001_FD004_combined.csv
│   └── test_FD001_FD004_combined.csv
├── models/combined/
├── src/
├── api/main.py
├── dashboard/app.py
├── experiments/
├── tests/
├── docs/
├── requirements.txt
├── Dockerfile
└── README.md
```

## Research framing

The project does not claim to be the first system to combine RUL prediction, XAI, decision support and deployment. The defensible contribution is the experimentally evaluated lightweight pipeline: combined FD001–FD004 training/testing, baseline comparison, causal-feature investigation, robustness evaluation, SHAP explanations, transparent maintenance policy, sequential inference and deployable Python API/dashboard.

## Limitations

- C-MAPSS is a simulated historical benchmark and does not represent every industrial machine.
- The combined model is sensitive to substantial sensor corruption; robustness is an active limitation and research direction.
- RUL predictions are probabilistic estimates, not guaranteed failure dates.
- SHAP does not establish physical causality.
- Maintenance recommendations are decision support only.
- Streaming is simulated rather than connected to physical industrial hardware.

## Reproducibility

Use Python 3.11+ where possible, install `requirements.txt`, keep the combined CSV at the canonical path, and run the one-command pipeline before starting the API/dashboard. Random seed is 42.
