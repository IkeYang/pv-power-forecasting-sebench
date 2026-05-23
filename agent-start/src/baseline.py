"""Baseline models for the PV forecasting task."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


MODEL_FILE = "model.json"


def load_training_data(train_dir: Path) -> pd.DataFrame:
    files = sorted(train_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No training CSV files found in {train_dir}")
    frames = [pd.read_csv(path) for path in files]
    return pd.concat(frames, ignore_index=True)


def _bin_edges(values: pd.Series, bins: int = 80) -> list[float]:
    quantiles = np.linspace(0.0, 1.0, bins + 1)
    edges = np.unique(np.quantile(values.to_numpy(dtype=float), quantiles))
    if len(edges) < 3:
        lo = float(values.min())
        hi = float(values.max()) + 1.0
        edges = np.linspace(lo, hi, bins + 1)
    return [float(x) for x in edges]


def train_sunlight_baseline(frame: pd.DataFrame) -> dict:
    data = frame.copy()
    data["Sunlight(Lux)"] = pd.to_numeric(data["Sunlight(Lux)"], errors="coerce").fillna(0.0)
    data["Power(mW)"] = pd.to_numeric(data["Power(mW)"], errors="coerce").fillna(0.0).clip(lower=0.0)
    data["LocationCode"] = pd.to_numeric(data["LocationCode"], errors="coerce").fillna(-1).astype(int)

    edges = _bin_edges(data["Sunlight(Lux)"])
    bin_ids = np.digitize(data["Sunlight(Lux)"], edges, right=False)
    global_by_bin = data.assign(_bin=bin_ids).groupby("_bin")["Power(mW)"].mean().to_dict()
    location_mean = data.groupby("LocationCode")["Power(mW)"].mean().to_dict()
    capacity = data.groupby("LocationCode")["Power(mW)"].quantile(0.995).to_dict()
    return {
        "model_type": "sunlight_bin_mean",
        "sunlight_edges": edges,
        "global_mean": float(data["Power(mW)"].mean()),
        "global_by_bin": {str(int(k)): float(v) for k, v in global_by_bin.items()},
        "location_mean": {str(int(k)): float(v) for k, v in location_mean.items()},
        "location_capacity": {str(int(k)): max(float(v), 1.0) for k, v in capacity.items()},
    }


def save_model(model: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / MODEL_FILE
    path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_model(model_dir: Path) -> dict:
    return json.loads((model_dir / MODEL_FILE).read_text(encoding="utf-8"))


def predict(model: dict, features: pd.DataFrame) -> pd.DataFrame:
    data = features.copy()
    data["Sunlight(Lux)"] = pd.to_numeric(data["Sunlight(Lux)"], errors="coerce").fillna(0.0)
    data["LocationCode"] = pd.to_numeric(data["LocationCode"], errors="coerce").fillna(-1).astype(int)
    edges = np.asarray(model["sunlight_edges"], dtype=float)
    bin_ids = np.digitize(data["Sunlight(Lux)"], edges, right=False)
    global_by_bin = model["global_by_bin"]
    global_mean = float(model["global_mean"])
    location_mean = model.get("location_mean", {})
    location_capacity = model.get("location_capacity", {})

    predictions = []
    for location, bin_id in zip(data["LocationCode"], bin_ids):
        value = global_by_bin.get(str(int(bin_id)), global_mean)
        # Weak location correction where the location appeared in training.
        loc_mean = location_mean.get(str(int(location)))
        if loc_mean is not None and global_mean > 0:
            value *= float(loc_mean) / global_mean
        cap = float(location_capacity.get(str(int(location)), max(value * 1.5, 1.0)))
        predictions.append(float(np.clip(value, 0.0, cap * 1.15)))

    result = features[["LocationCode", "DateTime"]].copy()
    result["PredictedPower(mW)"] = np.asarray(predictions).round(6)
    return result
