"""Canonical VitaMecha training entry point.

The final project trains from the single combined FD001-FD004 CSV.
"""
from __future__ import annotations
import argparse
from src.all_cmapss_pipeline import preprocess_all, train_and_evaluate

def train_all():
    train_df, test_df = preprocess_all()
    return train_and_evaluate(train_df, test_df)

if __name__ == "__main__":
    p=argparse.ArgumentParser(description="Train/test VitaMecha on combined FD001-FD004 CSV")
    p.add_argument("--features",type=int,default=40,help="Candidate engineered features; final model selection is empirical")
    args=p.parse_args()
    train_df,test_df=preprocess_all()
    overall,per,meta=train_and_evaluate(train_df,test_df,args.features)
    print("\n=== OVERALL RESULTS ===")
    print(overall.to_string(index=False))
    print("\n=== PER-DATASET RESULTS ===")
    print(per.to_string(index=False))
