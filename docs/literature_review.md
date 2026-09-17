# VitaMecha Literature Review and Research Gap

## Review scope

The review focuses on 2020–2026 work on RUL estimation, predictive maintenance, robustness, explainability, online inference and maintenance decision support, with emphasis on 2023–2026.

## Selected evidence

| Year | Study | Dataset / context | Method | Main relevance | Limitation relevant to VitaMecha |
|---|---|---|---|---|---|
| 2021 | Xiao et al., *Remaining useful life prediction based on intentional noise injection and feature reconstruction* | NASA C-MAPSS | LSTM, feature reconstruction, intentional Gaussian noise | Demonstrates that feature engineering and noise-aware modelling can improve robustness and RUL accuracy | Focuses on a neural RUL model rather than an end-to-end lightweight decision-support/deployment pipeline |
| 2022 | Knowledge + deep-learning RUL study | NASA C-MAPSS | Knowledge-guided CNN/LSTM | Shows that domain knowledge can improve accuracy and interpretability | Model-centric contribution; does not provide the complete lightweight API/UI/maintenance-policy workflow |
| 2023 | *An Explainable Artificial Intelligence Approach for Remaining Useful Life Prediction* | NASA C-MAPSS FD004 | LSTM + feature clustering + SHAP | Direct evidence that SHAP can be used to explain RUL predictions and support maintenance interpretation | Focuses on FD004 and model explanation rather than robustness + streaming + deployment as one evaluated prototype |
| 2023 | *A concise self-adapting deep learning network for machine remaining useful life prediction* | C-MAPSS + wind-turbine gearbox data | Adaptive neural architecture + dropout uncertainty | Addresses generalization and uncertainty | Higher model complexity than needed for a lightweight academic deployment |
| 2023 | *Interaction models for remaining useful lifetime estimation* | C-MAPSS | Multi-block temporal feature aggregation | Studies sequence modelling and Gaussian sensor noising for robustness | Does not establish the complete human-facing decision-support workflow used by VitaMecha |
| 2024 | *Multiscale BLS-Based Lightweight Prediction Model for Remaining Useful Life of Aero-Engine* | C-MAPSS + N-CMAPSS | Lightweight broad learning system | Demonstrates the importance of low computational cost for online RUL prediction | Primarily model/efficiency focused |
| 2024 | *A Dual-Scale Transformer-Based Remaining Useful Life Prediction Model in Industrial Internet of Things* | C-MAPSS FD001–FD003 | Transformer + temporal convolution | Shows strong temporal/sensor modelling under IIoT settings | Deep architecture is heavier than the intended VitaMecha prototype |
| 2024/25 | *Decision-making systems improvement based on explainable artificial intelligence approaches for predictive maintenance* | Wind-turbine IoT data | Predictive model + anomaly explanation + web-based human-machine interface | Strong evidence that prediction + explanation + an interactive decision-support interface is useful for maintenance planning | Uses a different real-world domain/dataset; not an open C-MAPSS reproducibility study |
| 2025 | *Improving predictive maintenance: Evaluating the impact of preprocessing and model complexity on the effectiveness of XAI methods* | C-MAPSS | LSTM + LIME/SHAP/L2X | Demonstrates that preprocessing choices materially affect explanation quality | Concentrates on XAI evaluation rather than robustness and deployable maintenance decision support |
| 2025 | *Human-in-the-Loop XAI for Predictive Maintenance: A Systematic Review...* | Literature review | HITL-XAI | Identifies transparency, trust and human decision-making as important adoption challenges | Review-level work; reinforces the need for practical interactive systems |
| 2025 | *Remaining useful life prediction for complex systems with missing multi-sensor features* | C-MAPSS + battery data | Missing-feature-aware deep model + uncertainty | Directly motivates missing-sensor robustness and uncertainty evaluation | More complex architecture; not focused on lightweight deployment |
| 2026 | *Variance-Controlled Stacked Hybrid Ensemble...* | C-MAPSS FD001–FD004 | DeepSSM + LightGBM + CatBoost ensemble + SHAP + threshold policy | Shows the current trend toward combining prediction, robustness, SHAP and maintenance thresholds | High-capacity ensemble is more complex than a compact academic deployment and does not remove the need for a reproducible API/UI workflow |

## Actual research gap for VitaMecha

The literature does **not** support the claim that predictive maintenance + RUL + XAI + deployment is itself novel. Those components have already been studied individually and in combinations.

A defensible gap for this project is narrower:

> **There is room for a reproducible, lightweight and experimentally transparent decision-support prototype that evaluates an inherited RUL baseline, replaces future-dependent feature construction with online-safe causal temporal features, explicitly tests sensor-noise and missing-data robustness, exposes local/global SHAP explanations, converts RUL into an auditable maintenance policy, and evaluates the end-to-end sequential inference path through a Python API and human-facing dashboard.**

This is a **systems/evaluation contribution**, not a claim of a new RUL algorithm or first-of-its-kind PdM/XAI architecture.

## Design consequence

VitaMecha therefore uses:

1. The inherited `vitamecha_rul_model.pkl` as the original project baseline artifact, while avoiding the inaccurate label “pre-trained” unless its training provenance can be documented.
2. A reproducible Random Forest baseline.
3. A causal XGBoost model using current sensors, cycle, rolling mean/std and first differences. The previous `cycle / max_cycle` and full-sequence degradation normalization were removed because they can use information unavailable during live inference.
4. Controlled Gaussian-noise and missing-sensor experiments.
5. SHAP local and global explanations.
6. A transparent rule-based health/risk and maintenance layer.
7. Simulated sequential C-MAPSS streaming, FastAPI and Streamlit deployment.

## Important interpretation rule

SHAP contribution is a model attribution, not proof of physical causation. Statements in the UI and paper must use wording such as “associated with a lower predicted RUL” rather than “causes failure.”
