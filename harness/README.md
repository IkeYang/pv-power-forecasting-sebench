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

The final public Release is:

```text
Tag: v2026.06.03-final
Title: PV Power Forecasting SE-Bench Final Submission
```

Release assets:

```text
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.03-final/pv_work.tar.gz
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.03-final/pv_judge.tar.gz
```

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

The final task JSON uses GitHub Release asset URLs:

```text
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.03-final/pv_work.tar.gz
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.03-final/pv_judge.tar.gz
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
The current judge uses `parser: structured_json`. A smoke report should contain
one structured report with `total_score`, `weighted_error`, and 14 named metric
details (`total_tests=16`: score, weighted error, and the 14 metric rows), plus
a non-empty `metrics` object with `metric_values`, `metric_weights`,
`normalization`, and `weighted_error`. It should not print synthetic `CASE`
lines.

The verified clean curve run used two submissions:

```text
agent-1: score=0.0, structured metrics present
agent-2: low double-digit score after the 2026-05-23 scoring recalibration
```

The difficulty calibration uses real Harness runs rather than a synthetic
proxy. A structured 2h run on 2026-06-02 produced 62 valid reports and reached
`weighted_error=135.446758`; the current score anchors map that performance
level to 24 points. A stronger historical run at `weighted_error=129.706352`
maps to 30 points, while 50 points are reserved for `weighted_error=112.000000`.

The structured revalidation run `pv_agent_2h_structured_20260602_194356` timed
out at `7200.03037571907` seconds, produced 62 valid structured reports, and
reached `weighted_error=135.446758`; under the current curve this is a readable
mid-range score, while still remaining below the strong-solution band. The
calibrated 8h run `pv_agent_8h_calibrated_20260602_222150` timed out at
`28800.041011810303` seconds, produced 152 valid structured reports, and reached
`score=41.982139` with `weighted_error=119.098354`.

## Local Validation

```bash
python -m pytest \
  "Xpert/SE-Bench Research/tests/test_prepare_pv_benchmark.py" \
  "Xpert/SE-Bench Research/tests/test_pv_scorer.py" \
  -q
```
