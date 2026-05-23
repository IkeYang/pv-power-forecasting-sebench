#!/usr/bin/env python3
"""Train the starter PV forecasting baseline."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.baseline import load_training_data, save_model, train_sunlight_baseline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dir", type=Path, default=Path("dev-data/train"))
    parser.add_argument("--model-dir", type=Path, default=Path("artifacts"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    training = load_training_data(args.train_dir)
    model = train_sunlight_baseline(training)
    path = save_model(model, args.model_dir)
    print(f"Wrote baseline model to {path}")


if __name__ == "__main__":
    main()
