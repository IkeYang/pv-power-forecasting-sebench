#!/usr/bin/env python3
"""SE-Bench Harness structured evaluator for the PV forecasting task."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import time
from typing import Any


ROOT = pathlib.Path("/home/workspace/pv-power-forecasting")
SOURCE_AGENT = ROOT / "agent-start"
EXEC_ROOT = pathlib.Path("/tmp/pv_exec")
EXEC_AGENT = EXEC_ROOT / "agent-start"
FEATURE_ROOT = pathlib.Path("/tmp/pv_eval_features")
FEATURE_PATH = FEATURE_ROOT / "eval_features.csv"
SUBMISSION_PATH = EXEC_AGENT / "submission.csv"

TRAIN_TIMEOUT_SECONDS = int(os.environ.get("PV_TRAIN_TIMEOUT_SECONDS", "1200"))
PREDICT_TIMEOUT_SECONDS = int(os.environ.get("PV_PREDICT_TIMEOUT_SECONDS", "600"))
SCORER_TIMEOUT_SECONDS = int(os.environ.get("PV_SCORER_TIMEOUT_SECONDS", "300"))


def harden_path(path: pathlib.Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        for child in path.rglob("*"):
            try:
                child.chmod(0o700 if child.is_dir() else 0o600)
            except FileNotFoundError:
                pass
        path.chmod(0o700)
    else:
        path.chmod(0o600)


def chown_tree(path: pathlib.Path, uid: int = 65534, gid: int = 65534) -> None:
    for current, _dirs, files in os.walk(path):
        os.chown(current, uid, gid)
        os.chmod(current, 0o755)
        for name in files:
            target = os.path.join(current, name)
            os.chown(target, uid, gid)
            os.chmod(target, 0o644)


def run_as_nobody(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = "/tmp"
    env["PYTHONUNBUFFERED"] = "1"

    def drop_privileges() -> None:
        os.setgid(65534)
        os.setuid(65534)

    return subprocess.run(
        args,
        cwd=EXEC_AGENT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        env=env,
        preexec_fn=drop_privileges,
    )


def prepare_execution_tree() -> None:
    for target in ["scorer", "baseline", "docs", "split_manifest.json", "task.yaml"]:
        harden_path(ROOT / target)

    shutil.rmtree(EXEC_ROOT, ignore_errors=True)
    shutil.rmtree(FEATURE_ROOT, ignore_errors=True)
    FEATURE_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "scorer" / "eval-data" / "eval_features.csv", FEATURE_PATH)
    shutil.copytree(
        SOURCE_AGENT,
        EXEC_AGENT,
        ignore=shutil.ignore_patterns("artifacts", "submission.csv", "baseline_submission.csv"),
    )
    chown_tree(EXEC_ROOT)
    chown_tree(FEATURE_ROOT)


def run_submission() -> dict[str, Any]:
    train = run_as_nobody(
        ["python", "train.py", "--train-dir", "dev-data/train", "--model-dir", "artifacts"],
        TRAIN_TIMEOUT_SECONDS,
    )
    print("PV_AGENT_TRAIN_OUTPUT_START")
    print(train.stdout[-12000:])
    print("PV_AGENT_TRAIN_OUTPUT_END")
    if train.returncode != 0:
        raise RuntimeError(f"train failed with exit code {train.returncode}")

    pred = run_as_nobody(
        [
            "python",
            "predict.py",
            "--input",
            str(FEATURE_PATH),
            "--output",
            str(SUBMISSION_PATH),
            "--model-dir",
            "artifacts",
        ],
        PREDICT_TIMEOUT_SECONDS,
    )
    print("PV_AGENT_PREDICT_OUTPUT_START")
    print(pred.stdout[-12000:])
    print("PV_AGENT_PREDICT_OUTPUT_END")
    if pred.returncode != 0:
        raise RuntimeError(f"predict failed with exit code {pred.returncode}")

    eval_proc = subprocess.run(
        [
            "python",
            str(ROOT / "scorer" / "evaluate.py"),
            "--features",
            str(ROOT / "scorer" / "eval-data" / "eval_features.csv"),
            "--labels",
            str(ROOT / "scorer" / "eval-data" / "eval_labels.csv"),
            "--submission",
            str(SUBMISSION_PATH),
            "--metrics",
            str(ROOT / "scorer" / "eval-data" / "baseline_metrics.json"),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=SCORER_TIMEOUT_SECONDS,
    )
    print("PV_SCORER_OUTPUT_START")
    print(eval_proc.stdout)
    print("PV_SCORER_OUTPUT_END")
    if eval_proc.returncode != 0:
        raise RuntimeError(f"scorer failed with exit code {eval_proc.returncode}")

    start = eval_proc.stdout.find("{")
    end = eval_proc.stdout.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError("scorer output did not contain a JSON payload")
    return json.loads(eval_proc.stdout[start : end + 1])


def metric_details(payload: dict[str, Any]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    total_score = float(payload.get("total_score", 0.0) or 0.0)
    weighted_error = payload.get("weighted_error")
    details.append(
        {
            "name": "total_score",
            "status": "PASSED" if payload.get("valid", False) else "FAILED",
            "score": round(total_score, 6),
            "message": f"continuous score={total_score:.6f}; higher is better",
        }
    )
    if weighted_error is not None:
        details.append(
            {
                "name": "weighted_error",
                "status": "PASSED",
                "score": round(float(weighted_error), 6),
                "message": "weighted error from 14 PV forecasting metrics; lower is better",
            }
        )

    metrics = payload.get("metrics") or {}
    weights = payload.get("metric_weights") or {}
    for name in sorted(metrics):
        value = float(metrics[name])
        weight = float(weights.get(name, 0.0) or 0.0)
        contribution = value * weight
        details.append(
            {
                "name": name,
                "status": "PASSED",
                "score": round(value, 6),
                "weight": round(weight, 6),
                "message": f"value={value:.6f}; weight={weight:.4f}; weighted contribution={contribution:.6f}",
            }
        )
    return details


def summarize_payload(payload: dict[str, Any]) -> str:
    if not payload.get("valid", False):
        return f"invalid submission: {payload.get('error', '')}".strip()
    metrics = payload.get("metrics") or {}
    weights = payload.get("metric_weights") or {}
    ranked = sorted(
        (
            (float(metrics[name]) * float(weights.get(name, 0.0) or 0.0), name, float(metrics[name]))
            for name in metrics
        ),
        reverse=True,
    )
    top = ", ".join(f"{name}={value:.3f}" for _contrib, name, value in ranked[:4])
    return (
        f"score={float(payload.get('total_score', 0.0) or 0.0):.6f}; "
        f"weighted_error={float(payload.get('weighted_error', 0.0) or 0.0):.6f}; "
        f"largest weighted-error components: {top}"
    )


def structured_result_from_payload(payload: dict[str, Any], runtime_seconds: float) -> dict[str, Any]:
    score = max(0.0, min(100.0, float(payload.get("total_score", 0.0) or 0.0)))
    valid = bool(payload.get("valid", False))
    return {
        "valid": valid,
        "score": round(score, 6),
        "pass_rate": round(score / 100.0, 6),
        "total_tests": 1,
        "passed": 1 if valid else 0,
        "failed": 0 if valid else 1,
        "errors": 0,
        "summary": summarize_payload(payload),
        "details": metric_details(payload),
        "metrics": {
            "total_score": round(score, 6),
            "weighted_error": payload.get("weighted_error"),
            "format_penalty": payload.get("format_penalty"),
            "metric_values": payload.get("metrics", {}),
            "metric_weights": payload.get("metric_weights", {}),
            "normalization": payload.get("normalization", {}),
            "runtime_seconds": round(runtime_seconds, 6),
        },
    }


def structured_error(exc: BaseException, runtime_seconds: float) -> dict[str, Any]:
    return {
        "valid": False,
        "score": 0.0,
        "pass_rate": 0.0,
        "total_tests": 1,
        "passed": 0,
        "failed": 0,
        "errors": 1,
        "summary": f"PV evaluation failed: {type(exc).__name__}: {exc}",
        "details": [
            {
                "name": "pv_evaluation",
                "status": "ERROR",
                "score": 0.0,
                "message": f"{type(exc).__name__}: {exc}",
            }
        ],
        "metrics": {
            "error_type": type(exc).__name__,
            "error": str(exc),
            "runtime_seconds": round(runtime_seconds, 6),
        },
    }


def print_structured_result(result: dict[str, Any]) -> None:
    print(">>>>> Start Structured Result")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(">>>>> End Structured Result")


def main() -> None:
    started = time.time()
    try:
        prepare_execution_tree()
        payload = run_submission()
        result = structured_result_from_payload(payload, time.time() - started)
    except Exception as exc:
        print(f"PV_EVAL_ERROR {type(exc).__name__}: {exc}")
        result = structured_error(exc, time.time() - started)
    print_structured_result(result)


if __name__ == "__main__":
    main()
