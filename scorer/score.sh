#!/usr/bin/env bash
set -euo pipefail

AGENT_DIR_INPUT="${1:-$(pwd)}"
AGENT_DIR="$(cd "${AGENT_DIR_INPUT}" && pwd)"
SCORER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCORER_DIR}/.." && pwd)"
SUBMISSION="${AGENT_DIR}/submission.csv"

cd "${AGENT_DIR}"

if [[ ! -f "artifacts/model.json" ]]; then
  python train.py --train-dir dev-data/train --model-dir artifacts >&2
fi

python predict.py \
  --input "${TASK_DIR}/scorer/eval-data/eval_features.csv" \
  --output "${SUBMISSION}" \
  --model-dir artifacts >&2

python "${SCORER_DIR}/evaluate.py" \
  --features "${TASK_DIR}/scorer/eval-data/eval_features.csv" \
  --labels "${TASK_DIR}/scorer/eval-data/eval_labels.csv" \
  --submission "${SUBMISSION}" \
  --metrics "${TASK_DIR}/scorer/eval-data/baseline_metrics.json"
