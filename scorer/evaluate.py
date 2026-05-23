#!/usr/bin/env python3
"""Evaluate PV forecasting submissions."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_SUBMISSION_COLUMNS = ["LocationCode", "DateTime", "PredictedPower(mW)"]

DEFAULT_WEIGHTS = {
    "day_rmse": 0.20,
    "ramp_rmse": 0.12,
    "extreme_ramp_rmse": 0.08,
    "peak_rmse": 0.10,
    "edge_rmse": 0.06,
    "low_sun_rmse": 0.05,
    "sunlight_transition_rmse": 0.06,
    "station_norm_rmse": 0.07,
    "station_bias_mae": 0.04,
    "daily_energy_rmse": 0.06,
    "horizon_short_rmse": 0.03,
    "horizon_mid_rmse": 0.04,
    "horizon_long_rmse": 0.07,
    "mae": 0.02,
}


def _zero_score(error: str) -> dict:
    return {
        "valid": False,
        "error": error,
        "total_score": 0.0,
        "format_penalty": 100.0,
    }


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return 0.0
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return 0.0
    return float(np.mean(np.abs(actual - predicted)))


def _masked_rmse(actual: np.ndarray, predicted: np.ndarray, mask: np.ndarray) -> float:
    if len(actual) == 0 or not mask.any():
        return 0.0
    return _rmse(actual[mask], predicted[mask])


def _load_metrics(metrics_path: Path | None) -> dict:
    if metrics_path is None or not metrics_path.exists():
        return {}
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def _validate_submission(
    features: pd.DataFrame, submission: pd.DataFrame
) -> tuple[pd.DataFrame | None, str | None]:
    missing = [col for col in REQUIRED_SUBMISSION_COLUMNS if col not in submission.columns]
    if missing:
        return None, f"missing required columns: {missing}"
    submission = submission[REQUIRED_SUBMISSION_COLUMNS].copy()
    if len(submission) != len(features):
        return None, f"row count mismatch: expected {len(features)}, got {len(submission)}"

    expected = features[["LocationCode", "DateTime"]].copy()
    expected["DateTime"] = pd.to_datetime(expected["DateTime"], errors="coerce")
    submission["DateTime"] = pd.to_datetime(submission["DateTime"], errors="coerce")
    if expected["DateTime"].isna().any() or submission["DateTime"].isna().any():
        return None, "DateTime parse failure"

    expected["LocationCode"] = pd.to_numeric(expected["LocationCode"], errors="coerce").astype("Int64")
    submission["LocationCode"] = pd.to_numeric(submission["LocationCode"], errors="coerce").astype("Int64")
    if submission["LocationCode"].isna().any():
        return None, "LocationCode parse failure"
    if submission.duplicated(["LocationCode", "DateTime"]).any():
        return None, "duplicate LocationCode-DateTime rows in submission"

    aligned = expected.merge(
        submission,
        on=["LocationCode", "DateTime"],
        how="left",
        validate="one_to_one",
    )
    if aligned["PredictedPower(mW)"].isna().any():
        return None, "submission keys do not match eval features"
    aligned["PredictedPower(mW)"] = pd.to_numeric(aligned["PredictedPower(mW)"], errors="coerce")
    if aligned["PredictedPower(mW)"].isna().any():
        return None, "PredictedPower(mW) contains non-numeric or missing values"
    if np.isinf(aligned["PredictedPower(mW)"].to_numpy()).any():
        return None, "PredictedPower(mW) contains infinite values"
    return aligned, None


def _ramp_mask(labels: pd.DataFrame, quantile: float = 0.85) -> np.ndarray:
    ordered = labels[["LocationCode", "DateTime", "Power(mW)"]].copy()
    ordered["DateTime"] = pd.to_datetime(ordered["DateTime"])
    ordered["_order"] = np.arange(len(ordered))
    ordered = ordered.sort_values(["LocationCode", "DateTime"])
    diff = ordered.groupby("LocationCode")["Power(mW)"].diff().abs().fillna(0.0)
    positive = diff[diff > 0]
    if positive.empty:
        mask_sorted = np.zeros(len(ordered), dtype=bool)
    else:
        threshold = float(positive.quantile(quantile))
        mask_sorted = diff.to_numpy() >= threshold
    ordered["_mask"] = mask_sorted
    return ordered.sort_values("_order")["_mask"].to_numpy(dtype=bool)


def _sunlight_transition_mask(features: pd.DataFrame) -> np.ndarray:
    ordered = features[["LocationCode", "DateTime", "Sunlight(Lux)"]].copy()
    ordered["_order"] = np.arange(len(ordered))
    ordered = ordered.sort_values(["LocationCode", "DateTime"])
    sunlight = pd.to_numeric(ordered["Sunlight(Lux)"], errors="coerce").fillna(0.0)
    diff = sunlight.groupby(ordered["LocationCode"]).diff().abs().fillna(0.0)
    positive = diff[diff > 0]
    if positive.empty:
        mask_sorted = np.zeros(len(ordered), dtype=bool)
    else:
        threshold = float(positive.quantile(0.85))
        mask_sorted = (diff.to_numpy() >= threshold) & (sunlight.to_numpy() > 100.0)
    ordered["_mask"] = mask_sorted
    return ordered.sort_values("_order")["_mask"].to_numpy(dtype=bool)


def _horizon_masks(features: pd.DataFrame) -> dict[str, np.ndarray]:
    """Split each station's hidden time tail into short, mid, and long spans.

    The benchmark gives future meteorological features, so horizon difficulty is
    measured by elapsed time inside each station's withheld tail. Short-horizon
    cases reward basic interpolation, while long-horizon cases reward seasonal
    calibration, station capacity normalization, and stable post-processing.
    """
    ordered = features[["LocationCode", "DateTime"]].copy()
    ordered["_order"] = np.arange(len(ordered))
    ordered = ordered.sort_values(["LocationCode", "DateTime"])
    start = ordered.groupby("LocationCode")["DateTime"].transform("min")
    elapsed_days = (ordered["DateTime"] - start).dt.total_seconds() / 86400.0
    ordered["_short"] = elapsed_days <= 7.0
    ordered["_mid"] = (elapsed_days > 7.0) & (elapsed_days <= 28.0)
    ordered["_long"] = elapsed_days > 28.0
    if not ordered["_long"].any():
        position = ordered.groupby("LocationCode").cumcount()
        size = ordered.groupby("LocationCode")["DateTime"].transform("size").clip(lower=1)
        fraction = (position + 1) / size
        ordered["_short"] = fraction <= 0.35
        ordered["_mid"] = (fraction > 0.35) & (fraction <= 0.70)
        ordered["_long"] = fraction > 0.70
    ordered = ordered.sort_values("_order")
    return {
        "short": ordered["_short"].to_numpy(dtype=bool),
        "mid": ordered["_mid"].to_numpy(dtype=bool),
        "long": ordered["_long"].to_numpy(dtype=bool),
    }


def _station_normalized_rmse(
    actual: np.ndarray,
    predicted: np.ndarray,
    labels: pd.DataFrame,
    metrics: dict,
) -> float:
    station_meta = metrics.get("station_capacity") or metrics.get("station_meta") or {}
    if not station_meta:
        return _rmse(actual, predicted)
    errors = []
    capacities = []
    for location, group in labels.assign(_actual=actual, _pred=predicted).groupby("LocationCode"):
        meta = station_meta.get(str(int(location)), {})
        cap = float(meta.get("capacity_proxy_mw", 0.0) or 0.0)
        if cap <= 0:
            continue
        errors.append(_rmse(group["_actual"].to_numpy(dtype=float) / cap, group["_pred"].to_numpy(dtype=float) / cap))
        capacities.append(cap)
    if not errors:
        return _rmse(actual, predicted)
    return float(np.mean(errors) * np.median(capacities))


def _station_bias_mae(actual: np.ndarray, predicted: np.ndarray, labels: pd.DataFrame) -> float:
    grouped = (
        labels.assign(_actual=actual, _pred=predicted)
        .groupby("LocationCode")
        .agg(actual_mean=("_actual", "mean"), pred_mean=("_pred", "mean"))
    )
    if grouped.empty:
        return 0.0
    return float(np.mean(np.abs(grouped["actual_mean"].to_numpy() - grouped["pred_mean"].to_numpy())))


def _daily_energy_rmse(
    actual: np.ndarray,
    predicted: np.ndarray,
    labels: pd.DataFrame,
    daylight: np.ndarray,
) -> float:
    if len(actual) == 0:
        return 0.0
    daily = labels[["LocationCode", "DateTime"]].copy()
    daily["_actual"] = actual
    daily["_pred"] = predicted
    daily = daily[daylight].copy()
    if daily.empty:
        return 0.0
    daily["_date"] = daily["DateTime"].dt.date
    grouped = (
        daily.groupby(["LocationCode", "_date"])
        .agg(actual_mean=("_actual", "mean"), pred_mean=("_pred", "mean"), rows=("_actual", "size"))
        .query("rows >= 3")
    )
    if grouped.empty:
        return 0.0
    return _rmse(grouped["actual_mean"].to_numpy(), grouped["pred_mean"].to_numpy())


def _weighted_error(metric_values: dict, weights: dict | None = None) -> float:
    active_weights = dict(DEFAULT_WEIGHTS)
    if weights:
        active_weights.update({str(k): float(v) for k, v in weights.items()})
    total_weight = sum(active_weights.values())
    if total_weight <= 0:
        total_weight = 1.0
    return float(
        sum(float(metric_values.get(name, 0.0)) * weight for name, weight in active_weights.items())
        / total_weight
    )


def _score_from_anchors(weighted_error: float, metrics: dict, fallback_reference: float) -> tuple[float, dict]:
    configured_anchors = metrics.get("score_anchors")
    if configured_anchors:
        anchors = []
        for item in configured_anchors:
            try:
                anchors.append(
                    {
                        "name": str(item.get("name", f"anchor_{len(anchors)}")),
                        "weighted_error": float(item["weighted_error"]),
                        "score": float(item["score"]),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
        anchors = sorted(anchors, key=lambda item: item["weighted_error"], reverse=True)
        clean_anchors = []
        best_score = -float("inf")
        last_error = float("inf")
        for item in anchors:
            if item["weighted_error"] >= last_error:
                continue
            score = max(0.0, min(100.0, item["score"]))
            if score < best_score:
                continue
            clean_anchors.append(
                {
                    "name": item["name"],
                    "weighted_error": item["weighted_error"],
                    "score": score,
                }
            )
            best_score = score
            last_error = item["weighted_error"]
        if len(clean_anchors) >= 2:
            if weighted_error >= clean_anchors[0]["weighted_error"]:
                raw_score = clean_anchors[0]["score"]
            elif weighted_error <= clean_anchors[-1]["weighted_error"]:
                raw_score = clean_anchors[-1]["score"]
            else:
                raw_score = clean_anchors[-1]["score"]
                for left, right in zip(clean_anchors, clean_anchors[1:]):
                    if left["weighted_error"] >= weighted_error >= right["weighted_error"]:
                        denom = max(left["weighted_error"] - right["weighted_error"], 1e-9)
                        raw_score = left["score"] + (right["score"] - left["score"]) * (
                            left["weighted_error"] - weighted_error
                        ) / denom
                        break
            return max(0.0, min(100.0, raw_score)), {
                "score_anchors": [
                    {
                        "name": item["name"],
                        "weighted_error": round(float(item["weighted_error"]), 6),
                        "score": round(float(item["score"]), 6),
                    }
                    for item in clean_anchors
                ]
            }

    baseline_error = float(metrics.get("baseline_weighted_error", weighted_error * 1.35 + 1.0))
    reference_error = float(metrics.get("reference_weighted_error", fallback_reference))
    strong_reference_error = float(metrics.get("strong_reference_weighted_error", (reference_error + weighted_error) / 2.0))
    expert_error = float(metrics.get("expert_weighted_error", reference_error * 0.82))
    reference_score = float(metrics.get("reference_anchor_score", 25.0))
    strong_reference_score = float(metrics.get("strong_reference_anchor_score", 70.0))
    expert_score = float(metrics.get("expert_anchor_score", 100.0))
    if expert_error >= reference_error:
        expert_error = reference_error * 0.82
    if strong_reference_error >= reference_error:
        strong_reference_error = (reference_error + expert_error) / 2.0
    if strong_reference_error <= expert_error:
        strong_reference_error = (reference_error + expert_error) / 2.0
    reference_score = max(1.0, min(60.0, reference_score))
    strong_reference_score = max(reference_score + 1.0, min(95.0, strong_reference_score))
    expert_score = max(strong_reference_score + 1.0, min(100.0, expert_score))

    if weighted_error >= baseline_error:
        raw_score = 0.0
    elif weighted_error >= reference_error:
        denom = max(baseline_error - reference_error, 1e-9)
        raw_score = reference_score * (baseline_error - weighted_error) / denom
    elif weighted_error >= strong_reference_error:
        denom = max(reference_error - strong_reference_error, 1e-9)
        raw_score = reference_score + (strong_reference_score - reference_score) * (
            reference_error - weighted_error
        ) / denom
    else:
        denom = max(strong_reference_error - expert_error, 1e-9)
        raw_score = strong_reference_score + (expert_score - strong_reference_score) * (
            strong_reference_error - weighted_error
        ) / denom

    return max(0.0, min(100.0, raw_score)), {
        "baseline_weighted_error": round(float(baseline_error), 6),
        "reference_weighted_error": round(float(reference_error), 6),
        "strong_reference_weighted_error": round(float(strong_reference_error), 6),
        "expert_weighted_error": round(float(expert_error), 6),
        "reference_anchor_score": round(float(reference_score), 6),
        "strong_reference_anchor_score": round(float(strong_reference_score), 6),
        "expert_anchor_score": round(float(expert_score), 6),
    }


def _capacity_penalty(prediction: pd.Series, labels: pd.DataFrame, metrics: dict) -> float:
    pred = prediction.to_numpy(dtype=float)
    negative_frac = float((pred < 0).mean())
    penalty = negative_frac * 35.0
    station_meta = metrics.get("station_capacity") or metrics.get("station_meta") or {}
    over_count = 0
    total = len(labels)
    if total and station_meta:
        for location, group in labels.assign(_pred=pred).groupby("LocationCode"):
            meta = station_meta.get(str(int(location)), {})
            cap = float(meta.get("capacity_proxy_mw", 0.0) or 0.0)
            if cap > 0:
                over_count += int((group["_pred"] > cap * 1.25).sum())
        penalty += (over_count / total) * 20.0
    return min(40.0, penalty)


def evaluate_submission(
    *,
    features_path: Path,
    labels_path: Path,
    submission_path: Path,
    metrics_path: Path | None = None,
) -> dict:
    started = time.time()
    try:
        features = pd.read_csv(features_path)
        labels = pd.read_csv(labels_path)
        submission = pd.read_csv(submission_path)
    except Exception as exc:
        return _zero_score(f"failed to read input files: {exc}")

    features = features.copy()
    features["DateTime"] = pd.to_datetime(features["DateTime"], errors="coerce")
    features["LocationCode"] = pd.to_numeric(features["LocationCode"], errors="coerce").astype("Int64")
    if features[["LocationCode", "DateTime"]].isna().any().any():
        return _zero_score("features contain invalid LocationCode or DateTime values")

    aligned, error = _validate_submission(features, submission)
    if error:
        return _zero_score(error)

    labels = labels[["LocationCode", "DateTime", "Power(mW)"]].copy()
    labels["DateTime"] = pd.to_datetime(labels["DateTime"], errors="coerce")
    labels["LocationCode"] = pd.to_numeric(labels["LocationCode"], errors="coerce").astype("Int64")
    labels["Power(mW)"] = pd.to_numeric(labels["Power(mW)"], errors="coerce")
    if labels.isna().any().any():
        return _zero_score("labels contain invalid values")

    labels = features[["LocationCode", "DateTime"]].copy().merge(
        labels, on=["LocationCode", "DateTime"], how="left", validate="one_to_one"
    )
    if labels["Power(mW)"].isna().any():
        return _zero_score("labels do not match eval features")

    metrics = _load_metrics(metrics_path)
    actual = labels["Power(mW)"].to_numpy(dtype=float)
    predicted_raw = aligned["PredictedPower(mW)"]
    predicted = predicted_raw.clip(lower=0.0).to_numpy(dtype=float)
    sunlight = pd.to_numeric(features["Sunlight(Lux)"], errors="coerce").fillna(0.0).to_numpy()

    daylight = (sunlight > 100) | (actual > 1.0)
    peak = actual >= float(np.quantile(actual, 0.85)) if len(actual) else np.array([], dtype=bool)
    ramp = _ramp_mask(labels)
    extreme_ramp = _ramp_mask(labels, quantile=0.95)
    hours = features["DateTime"].dt.hour.to_numpy(dtype=float) + features["DateTime"].dt.minute.to_numpy(dtype=float) / 60.0
    edge = daylight & (((hours >= 5.5) & (hours <= 8.5)) | ((hours >= 15.5) & (hours <= 19.5)))
    low_sun_threshold = float(np.quantile(sunlight[daylight], 0.35)) if daylight.any() else 0.0
    low_sun_day = daylight & (sunlight <= low_sun_threshold)
    sunlight_transition = _sunlight_transition_mask(features)
    horizon = _horizon_masks(features)
    metric_values = {
        "mae": _mae(actual, predicted),
        "day_rmse": _masked_rmse(actual, predicted, daylight),
        "ramp_rmse": _masked_rmse(actual, predicted, ramp),
        "extreme_ramp_rmse": _masked_rmse(actual, predicted, extreme_ramp),
        "peak_rmse": _masked_rmse(actual, predicted, peak),
        "edge_rmse": _masked_rmse(actual, predicted, edge),
        "low_sun_rmse": _masked_rmse(actual, predicted, low_sun_day),
        "sunlight_transition_rmse": _masked_rmse(actual, predicted, sunlight_transition),
        "station_norm_rmse": _station_normalized_rmse(actual, predicted, labels, metrics),
        "station_bias_mae": _station_bias_mae(actual, predicted, labels),
        "daily_energy_rmse": _daily_energy_rmse(actual, predicted, labels, daylight),
        "horizon_short_rmse": _masked_rmse(actual, predicted, horizon["short"]),
        "horizon_mid_rmse": _masked_rmse(actual, predicted, horizon["mid"]),
        "horizon_long_rmse": _masked_rmse(actual, predicted, horizon["long"]),
    }
    weighted_error = _weighted_error(metric_values, metrics.get("metric_weights"))

    format_penalty = _capacity_penalty(predicted_raw, labels, metrics)
    base_score, normalization = _score_from_anchors(
        weighted_error,
        metrics,
        fallback_reference=weighted_error * 0.80,
    )
    total_score = max(0.0, base_score - format_penalty)

    result = {
        "valid": True,
        "error": "",
        "total_score": round(float(total_score), 6),
        "format_penalty": round(float(format_penalty), 6),
        "weighted_error": round(float(weighted_error), 6),
        "metrics": {name: round(float(value), 6) for name, value in metric_values.items()},
        "metric_weights": {name: round(float(value), 6) for name, value in dict(DEFAULT_WEIGHTS, **metrics.get("metric_weights", {})).items()},
        "normalization": normalization,
        "runtime_seconds": round(time.time() - started, 6),
    }
    if not math.isfinite(result["total_score"]):
        return _zero_score("non-finite score")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = evaluate_submission(
        features_path=args.features,
        labels_path=args.labels,
        submission_path=args.submission,
        metrics_path=args.metrics,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
