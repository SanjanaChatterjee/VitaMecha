import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import json
import pandas as pd
import numpy as np
from src.predict import VitaMechaPredictor
DATA_PROCESSED = ROOT / "data" / "processed"
EXPERIMENTS = ROOT / "experiments"
JS_DIR = ROOT / "js"
JS_DIR.mkdir(parents=True, exist_ok=True)

def export_all():
    print("Initializing predictor...")
    p = VitaMechaPredictor(use_quantile=True, use_shap=True)
    df = pd.read_csv(DATA_PROCESSED / "test_FD001_FD004_combined.csv")

    selected_engines = [
        'FD001_engine_001', 'FD001_engine_034',
        'FD002_engine_001', 'FD002_engine_015',
        'FD003_engine_001', 'FD003_engine_020',
        'FD004_engine_001', 'FD004_engine_010'
    ]

    engines_data = {}
    for eng in selected_engines:
        sub = df[df['machine_id'] == eng].sort_values('cycle')
        if sub.empty:
            continue
        print(f"Processing {eng} ({len(sub)} cycles)...")
        cycles = []
        p.clear_history(eng)
        total_rows = len(sub)
        # Select key cycles to keep data fast and lightweight for edge deployment
        step = 1 if total_rows <= 75 else (2 if total_rows <= 150 else 3)
        for i in range(total_rows):
            row = sub.iloc[i]
            c = int(row['cycle'])
            if i % step == 0 or i == total_rows - 1:
                frame = sub.iloc[:i+1].copy()
                res = p.predict_from_frame(frame, eng, c)
                sensors = {f'sensor_{k}': round(float(row[f'sensor_{k}']), 2) for k in range(1, 22)}
                ops = {f'op_setting_{k}': round(float(row[f'op_setting_{k}']), 4) for k in range(1, 4)}
                cycles.append({
                    'cycle': c,
                    'true_rul': round(float(row['RUL']), 1) if 'RUL' in row else None,
                    'predicted_rul': round(res.predicted_rul, 1),
                    'rul_lower': round(res.rul_lower, 1) if res.rul_lower is not None else None,
                    'rul_upper': round(res.rul_upper, 1) if res.rul_upper is not None else None,
                    'health_status': res.health.health_status,
                    'risk_level': res.health.risk_level,
                    'trend': res.trend,
                    'inference_ms': round(res.inference_ms, 2),
                    'recommendation': res.recommendation.to_dict(),
                    'top_features': res.top_features[:6],
                    'sensors': sensors,
                    'op_settings': ops
                })
        engines_data[eng] = {
            'engine_id': eng,
            'dataset': eng.split('_')[0],
            'total_cycles': int(sub['cycle'].max()),
            'trajectory': cycles
        }

    # Load experimental benchmarks
    benchmarks = {}
    for fname in ["combined_model_comparison.csv", "combined_per_dataset_results.csv", "robustness_results.csv"]:
        fpath = EXPERIMENTS / fname
        if fpath.exists():
            benchmarks[fname.replace('.csv', '')] = pd.read_csv(fpath).to_dict(orient="records")

    output = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "available_engines": list(engines_data.keys()),
        "engines": engines_data,
        "benchmarks": benchmarks
    }

    out_file = JS_DIR / "telemetry-data.js"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("/** VitaMecha Telemetry & Benchmark Data for Vercel Edge Simulation */\n")
        f.write("window.VITAMECHA_DATA = " + json.dumps(output, indent=2) + ";\n")

    print(f"Exported successfully to {out_file} ({out_file.stat().st_size / 1024:.1f} KB)")

if __name__ == "__main__":
    export_all()
