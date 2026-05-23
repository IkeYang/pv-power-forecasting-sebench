#!/usr/bin/env python3
"""Generate PV power predictions with the starter baseline."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.baseline import load_model, predict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("submission.csv"))
    parser.add_argument("--model-dir", type=Path, default=Path("artifacts"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_model(args.model_dir)
    features = pd.read_csv(args.input)
    submission = predict(model, features)
    submission.to_csv(args.output, index=False)
    print(f"Wrote predictions to {args.output}")


if __name__ == "__main__":
    main()
