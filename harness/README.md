# SE-Bench Harness Integration

This directory contains the Harness task definition for the multi-site PV power
forecasting benchmark.

## Assets

Build the two data tarballs from the local task package:

```bash
python "Xpert/SE-Bench Research/tools/package_pv_harness_assets.py"
```

The script writes:

```text
Xpert/SE-Bench Research/harness-assets/pv_power/pv_work.tar.gz
Xpert/SE-Bench Research/harness-assets/pv_power/pv_judge.tar.gz
```

`pv_work.tar.gz` contains only agent-visible files. `pv_judge.tar.gz` also
contains hidden eval labels, scorer code, baselines, and audit docs.

## Harness Install

Copy the task JSON into the harness checkout:

```bash
cp "Xpert/SE-Bench Research/pv-power-forecasting/harness/pv_power_forecasting.json" \
  /root/SE-bench-main/tasks/pv_power_forecasting.json
```

Host the assets from the Harness server host:

```bash
mkdir -p /opt/sebench-assets/pv_power
cp "Xpert/SE-Bench Research/harness-assets/pv_power/"pv_*.tar.gz /opt/sebench-assets/pv_power/
python3 -m http.server 8000 --bind 0.0.0.0 --directory /opt/sebench-assets
```

The task JSON uses Docker bridge URLs:

```text
http://172.17.0.1:8000/pv_power/pv_work.tar.gz
http://172.17.0.1:8000/pv_power/pv_judge.tar.gz
```

## Build And Run

```bash
cd /root/SE-bench-main
uv run sebench build --task pv_power_forecasting
uv run sebench serve --port 8080
```

In another terminal:

```bash
uv run sebench run \
  --task pv_power_forecasting \
  --agent codex-or \
  --model gpt-5.5-0424 \
  --judge-url http://172.17.0.1:8080 \
  --timeout 7200 \
  --eval-interval 300 \
  --run-id pv_agent_2h
```

When using the project-provided agent endpoint, set
`SEBENCH_AGENT_API_KEY`, `SEBENCH_AGENT_API_BASE_URL`, and
`SEBENCH_NODEJS_MIRROR_URL` in the shell before invoking `sebench run`.

For a no-agent smoke test, use a custom workflow that calls `sebench-submit`.
The verified clean curve run used two submissions:

```text
agent-1: score=0.0, passed=0/1000
agent-2: low double-digit score after the 2026-05-23 scoring recalibration
```

The 2026-05-23 difficulty calibration used real Harness runs rather than a
synthetic proxy. A previous run crossed the 30-point acceptance ceiling after
about 1h under the old curve (`weighted_error=129.706352`,
old `score=30.822215`), so the current score anchors map that performance level
to 15 points and reserve 30 points for `weighted_error=112.000000`.

The final acceptance run `pv_agent_2h_newkey_20260523_1226` timed out naturally
after `7200.029923439026` seconds, completed 81 rounds with 57 Agent
submissions, and reached final best score `14.887849`. The highest observed
submission report was `14.938906` with `weighted_error=129.841525`, so the task
shows progress over the 30min run but remains below the 30-point ceiling.

## Local Validation

```bash
python -m pytest \
  "Xpert/SE-Bench Research/tests/test_prepare_pv_benchmark.py" \
  "Xpert/SE-Bench Research/tests/test_pv_scorer.py" \
  -q
```
