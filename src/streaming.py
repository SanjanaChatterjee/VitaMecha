"""Simulated sequential C-MAPSS streaming and online feature buffering."""
from __future__ import annotations
import argparse, logging, time
from typing import Callable, Generator, Optional
import numpy as np, pandas as pd
from src.config import *
from src.data_processing import load_processed
from src.predict import VitaMechaPredictor, PredictionResult

logger=logging.getLogger(__name__)
class SensorBuffer:
    def __init__(self,machine_id,max_size=MAX_HISTORY_PER_MACHINE): self.machine_id=machine_id; self.max_size=max_size; self.rows=[]
    def push(self,row):
        self.rows.append(dict(row)); self.rows=self.rows[-self.max_size:]
    def frame(self): return pd.DataFrame(self.rows)

def stream_engine(unit_id=1,delay_s=STREAM_DELAY_SECONDS,predictor=None,on_result:Optional[Callable]=None):
    _,test=load_processed(); unit=test[test.unit_id==unit_id].sort_values('cycle')
    if unit.empty: raise ValueError(f"Engine unit {unit_id} not found")
    predictor=predictor or VitaMechaPredictor(use_quantile=True,use_shap=True); machine=f"engine_{unit_id:03d}"; buf=SensorBuffer(machine)
    for _,row in unit.iterrows():
        buf.push(row.to_dict()); result=predictor.predict_from_frame(buf.frame(),machine_id=machine,cycle=int(row.cycle)); result.true_rul=float(row.RUL)
        if on_result: on_result(result)
        yield result
        if delay_s: time.sleep(delay_s)

def benchmark_streaming(machine_id="FD001_engine_001",n_cycles=50):
    p=VitaMechaPredictor(use_quantile=True,use_shap=False); lat=[]
    for i,r in enumerate(stream_engine(machine_id,0,p)):
        lat.append(r.inference_ms)
        if i+1>=n_cycles: break
    return {"n_cycles":len(lat),"mean_latency_ms":round(float(np.mean(lat)),3),"p95_latency_ms":round(float(np.percentile(lat,95)),3),"max_latency_ms":round(float(np.max(lat)),3),"throughput_cycles_per_s":round(1000/np.mean(lat),2)}

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--machine',default='FD001_engine_001'); a.add_argument('--delay',type=float,default=.2); a.add_argument('--benchmark',action='store_true'); a.add_argument('--n-cycles',type=int,default=50); args=a.parse_args()
    if args.benchmark: print(benchmark_streaming(args.machine,args.n_cycles))
    else:
        print('SIMULATED STREAMING — historical C-MAPSS data, not a physical machine.')
        for r in stream_engine(args.machine,args.delay): print(f"Cycle {r.cycle:3d} | RUL {r.predicted_rul:6.1f} | {r.health.health_status:9s} | {r.trend:17s} | {r.inference_ms:.1f} ms")
