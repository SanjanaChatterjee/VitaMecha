"""VitaMecha — operator-first predictive-maintenance dashboard."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import TEST_PROCESSED
from src.predict import VitaMechaPredictor
from src.problem_assessment import assess_problem

st.set_page_config(page_title="VitaMecha", page_icon="⚙️", layout="wide")

@st.cache_data
def load_test():
    return pd.read_csv(TEST_PROCESSED)

@st.cache_resource
def predictor_fast():
    return VitaMechaPredictor(use_quantile=True, use_shap=False)

@st.cache_resource
def predictor_xai():
    return VitaMechaPredictor(use_quantile=True, use_shap=True)


def status_text(s):
    return {"HEALTHY": "Healthy", "WARNING": "Warning", "DEGRADED": "Degraded", "CRITICAL": "Critical"}.get(s, s)


def assess_engine(machine_id: str, cycle: int):
    df = load_test()
    seq = df[(df.machine_id.astype(str) == str(machine_id)) & (df.cycle <= cycle)].sort_values("cycle").copy()
    if seq.empty:
        raise ValueError("No observation found for that machine/cycle.")
    machine = str(machine_id)
    fast = predictor_fast(); fast.clear_history(machine)
    for i in range(len(seq)):
        fast.predict_from_frame(seq.iloc[: i + 1].copy(), machine, int(seq.iloc[i].cycle))
    history = fast.get_history(machine).copy()
    xai = predictor_xai(); xai.clear_history(machine)
    xai._rul_history[machine] = history[:-1] if len(history) > 1 else []
    result = xai.predict_from_frame(seq, machine, int(cycle))
    return seq, result, history


def render_problem_assessment():
    st.subheader("🧑‍🔧 Tell VitaMecha what is wrong")
    st.write("Start with the problem as a maintenance operator would describe it. VitaMecha will identify the reported symptoms and tell you what telemetry should be collected.")
    problem = st.text_area(
        "Describe the machine problem",
        placeholder="Example: The machine is getting unusually hot, making a loud grinding sound, and its efficiency has dropped.",
        height=120,
    )
    if st.button("🔍 Analyse reported problem", type="primary"):
        assessment = assess_problem(problem)
        st.session_state["problem_assessment"] = assessment
        st.session_state["problem_text"] = problem

    if "problem_assessment" not in st.session_state:
        st.info("Example: “The machine is overheating and making abnormal noise.”")
        return

    a = st.session_state["problem_assessment"]
    st.divider()
    st.subheader("Operator report assessment")
    c1, c2, c3 = st.columns(3)
    c1.metric("Reported condition", a.severity)
    c2.metric("Detected symptom groups", len(a.symptoms))
    c3.metric("Advisory urgency", "Immediate review" if a.urgent else "Review telemetry")

    if a.symptoms:
        st.markdown("**Detected symptoms**")
        for s in a.symptoms:
            st.write(f"• {s}")
    else:
        st.warning(a.summary)

    if a.measurements:
        st.markdown("**Recommended measurements to collect**")
        for m in a.measurements:
            st.write(f"• {m}")

    st.warning(a.note)
    st.markdown("### Next step: obtain model-based RUL")
    st.write("The current FD001–FD004 model was trained on numerical C-MAPSS telemetry. Free-text symptoms are therefore used as context, not silently converted into fake sensor values.")
    st.info("For a defensible RUL prediction, use the **Machine Assessment** tab with sensor telemetry or the **Live Simulation** tab with a C-MAPSS engine stream.")


df = load_test()
units = sorted(df.machine_id.astype(str).unique())

st.markdown("# ⚙️ VitaMecha")
st.caption("A Life to Your Machines — Predict • Explain • Recommend • Deploy")
st.info("**Operator-first academic prototype:** describe a machine problem in plain language, then use measured telemetry for model-based RUL. C-MAPSS streaming is simulated; no physical machine is controlled.")

tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "🧑‍🔧 Report a Problem", "🔎 Machine Assessment", "📡 Live Simulation", "🧠 Why? (XAI)", "📊 Research Evidence"
])

with tab0:
    render_problem_assessment()

with tab1:
    st.subheader("Model-based machine assessment")
    st.write("Select a C-MAPSS engine and observation cycle. VitaMecha replays observations up to that cycle so temporal processing remains causal.")
    c1, c2 = st.columns(2)
    unit = c1.selectbox("Machine / Engine", units, index=0)
    max_cycle = int(df[df.machine_id.astype(str) == str(unit)].cycle.max())
    cycle = c2.slider("Observation cycle", 1, max_cycle, max_cycle)
    if st.button("🚀 Assess Machine", type="primary", use_container_width=True):
        with st.spinner("Processing telemetry, predicting RUL and generating explanation..."):
            seq, res, history = assess_engine(unit, cycle)
        st.session_state["last"] = (seq, res, history)

    if "last" in st.session_state:
        seq, res, history = st.session_state["last"]
        st.divider(); st.subheader(f"Assessment — {unit} · Cycle {res.cycle}")
        a,b,c,d = st.columns(4)
        a.metric("Predicted RUL", f"{res.predicted_rul:.1f} cycles")
        b.metric("Health", status_text(res.health.health_status))
        c.metric("Risk", res.health.risk_level)
        d.metric("Trend", res.trend)
        if res.rul_lower is not None:
            st.caption(f"Estimated 80% prediction band: **{res.rul_lower:.1f}–{res.rul_upper:.1f} cycles**. This is an empirical model interval, not a guaranteed failure date.")
        left, right = st.columns([1.35, 1])
        with left:
            hist_df = pd.DataFrame({"cycle": seq.cycle.values, "predicted_rul": history[-len(seq):]})
            fig = px.line(hist_df, x="cycle", y="predicted_rul", markers=True, title="RUL trend")
            fig.add_hline(y=80, line_dash="dot", annotation_text="Healthy threshold")
            fig.add_hline(y=40, line_dash="dot", annotation_text="Warning threshold")
            fig.add_hline(y=15, line_dash="dot", annotation_text="Critical threshold")
            st.plotly_chart(fig, use_container_width=True)
        with right:
            st.subheader("Maintenance decision support")
            if res.recommendation.priority in ("ROUTINE", "MONITOR"):
                st.success(res.recommendation.action)
            elif res.recommendation.priority == "URGENT":
                st.warning(res.recommendation.action)
            else:
                st.error(res.recommendation.action)
            for item in res.recommendation.details:
                st.write(f"• {item}")
            if res.recommendation.sensor_note:
                st.caption(res.recommendation.sensor_note)
        st.subheader("Current sensor profile")
        sensor_cols = [c for c in seq.columns if c.startswith("sensor_")]
        latest = seq.iloc[-1][sensor_cols].sort_values(ascending=False).reset_index()
        latest.columns = ["sensor", "value"]
        st.dataframe(latest, use_container_width=True, hide_index=True)
        st.caption(res.recommendation.disclaimer)

with tab2:
    st.subheader("📡 Simulated live sensor stream")
    st.write("This replays historical C-MAPSS telemetry one observation at a time. It is the deployment demonstration of sequential inference, not a physical live feed.")
    unit2 = st.selectbox("Simulation machine", units, key="sim_unit")
    speed = st.slider("Delay per observation (seconds)", 0.0, 0.5, 0.05, 0.05)
    if st.button("▶ Run simulation", type="primary"):
        import time
        data = df[df.machine_id.astype(str) == str(unit2)].sort_values("cycle")
        prog = st.progress(0); rows = []
        p = predictor_fast(); machine = str(unit2); p.clear_history(machine)
        for i, (_, row) in enumerate(data.iterrows(), 1):
            r = p.predict_from_frame(data.iloc[:i].copy(), machine, int(row.cycle))
            rows.append([r.cycle, r.predicted_rul, r.health.health_status, r.health.risk_level, r.inference_ms])
            prog.progress(i / len(data))
            if speed: time.sleep(speed)
        sim = pd.DataFrame(rows, columns=["cycle", "RUL", "health", "risk", "latency_ms"])
        st.dataframe(sim.tail(15), use_container_width=True, hide_index=True)
        st.line_chart(sim.set_index("cycle")["RUL"])
        st.success(f"Completed {len(sim)} sequential observations. Mean inference latency: {sim.latency_ms.mean():.2f} ms/observation.")

with tab3:
    st.subheader("Why did VitaMecha make this prediction?")
    st.write("SHAP values show contribution to the model prediction. They do **not** prove that a sensor is the physical cause of failure.")
    if "last" not in st.session_state:
        st.info("Run a Machine Assessment first.")
    else:
        seq, res, _ = st.session_state["last"]
        ex = pd.DataFrame([{"Feature": f["feature"], "SHAP contribution (cycles)": f["impact"], "Interpretation": f["description"]} for f in res.top_features])
        st.dataframe(ex, use_container_width=True, hide_index=True)
        fig = px.bar(ex.sort_values("SHAP contribution (cycles)"), x="SHAP contribution (cycles)", y="Feature", orientation="h", title="Local feature contributions")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Negative contribution → lowers predicted RUL. Positive contribution → raises predicted RUL.")

with tab4:
    st.subheader("Experimental evidence")
    for fname, title in [("combined_model_comparison.csv", "Combined FD001–FD004 model comparison"), ("combined_robustness_results.csv", "Robustness experiments"), ("combined_per_dataset_results.csv", "Per-dataset performance")]:
        path = ROOT / "experiments" / fname
        if path.exists():
            st.markdown(f"### {title}"); st.dataframe(pd.read_csv(path), use_container_width=True, hide_index=True)
    st.markdown("### Research framing")
    st.write("VitaMecha is a human-in-the-loop decision-support prototype. The operator report is a transparent contextual triage layer; the RUL model uses numerical C-MAPSS telemetry. This separation avoids inventing a text-to-sensor mapping that is not supported by the training data.")

with st.sidebar:
    st.markdown("## VitaMecha")
    st.caption("Predict → Explain → Recommend → Deploy")
    st.markdown("**Operator input:** plain-language problem report")
    st.markdown("**RUL input:** numerical C-MAPSS telemetry")
    st.markdown("**Dataset:** FD001–FD004 combined")
    st.markdown("**Model:** XGBoost")
    st.markdown("**XAI:** SHAP")
    st.markdown("**Deployment:** FastAPI + Streamlit")
