"""Evaluate two fixed rules against recorded outcomes."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def score(frame, loss="absolute"):
    difference=frame[["baseline", "candidate"]].sub(frame["actual"], axis=0)
    errors=difference.abs() if loss=="absolute" else difference.pow(2)
    gap=errors["candidate"]-errors["baseline"]
    if frame.empty or not np.isfinite(errors.to_numpy()).all():
        raise ValueError("No finite scores for the requested benchmark")
    worst=gap.idxmax()
    return {
        "cases":len(frame),
        "baseline_loss":round(float(errors["baseline"].mean()), 6),
        "candidate_loss":round(float(errors["candidate"].mean()), 6),
        "candidate_wins":int((gap < -1e-9).sum()),
        "baseline_wins":int((gap > 1e-9).sum()),
        "ties":int((gap.abs() <= 1e-9).sum()),
        "largest_candidate_disadvantage":round(float(gap.loc[worst]), 6),
        "worst_case":str(worst),
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        result=evaluate(args.input)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    except (OSError, ValueError, KeyError, ImportError) as error:
        parser.exit(2,f"Observed benchmark failed: {error}\n")


def evaluate(path):
    data=pd.read_excel(path,sheet_name="Performance",header=None)
    header=data.iloc[13]
    period=header[header.eq("Period")].index.item()
    measure=header[header.eq("Percentage in 4 hours or less (type 1)")].index.item()
    month=pd.to_datetime(data.loc[14:,period],errors="coerce")
    observed=pd.to_numeric(data.loc[14:,measure],errors="coerce")
    values=pd.Series((100*(1-observed)).to_numpy(),index=pd.PeriodIndex(month,freq="M")).dropna()
    values=values.loc[values.index.notna()].sort_index().loc["2023-06":"2026-10"]
    if len(values)!=41 or values.index.has_duplicates:
        raise ValueError("Expected continuous comparable observations from June 2023 through October 2026")
    panel=pd.DataFrame({"actual":values,"baseline":values.shift(2),"candidate":values.shift(12)})
    test=panel.loc["2024-11":"2026-10"].dropna()
    if len(test)!=24:
        raise ValueError("Expected 24 scored months")
    winter=test.index.month.isin([12,1,2])
    return {"source":"NHS England October 2026 monthly A&E time series, Performance worksheet",
            "metric":"MAE in percentage points, national Type 1 over-four-hours rate",
            "baseline":"Most recent assumed available rate, t-2","candidate":"Same calendar month last year",
            "holdout":["2024-11","2026-10"],"metrics":score(test),
            "by_season":{"winter":score(test.loc[winter]),"other_months":score(test.loc[~winter])}}


if __name__=="__main__":
    main()
