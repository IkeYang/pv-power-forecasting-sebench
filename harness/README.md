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

`pv_work.tar.gz` contains only agent-visible files. `pv_judge.tar.gz` contains
hidden eval labels, scorer code, baselines, and audit docs for the judge image.

The refreshed public Release is:

```text
Tag: v2026.06.06-canonical
Title: PV Power Forecasting SE-Bench Canonical Data Refresh
```

Release assets:

```text
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.06-canonical/pv_work.tar.gz
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.06-canonical/pv_judge.tar.gz
```

## Harness Install

Copy the task JSON into the harness checkout:

```bash
cp "Xpert/SE-Bench Research/pv-power-forecasting/harness/pv_power_forecasting.json" \
  /root/SE-bench-main/tasks/pv_power_forecasting.json
```

For local smoke tests, host both assets from the Harness server host:

```bash
mkdir -p /opt/sebench-assets/pv_power
cp "Xpert/SE-Bench Research/harness-assets/pv_power/"pv_*.tar.gz /opt/sebench-assets/pv_power/
python3 -m http.server 8000 --bind 0.0.0.0 --directory /opt/sebench-assets
```

The final task JSON downloads both assets from the GitHub Release:

```text
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.06-canonical/pv_work.tar.gz
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.06-canonical/pv_judge.tar.gz
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

## Current Calibration Status

The 2026-06-06 data refresh keeps only canonical raw `site_v1` observations,
excludes shifted `site_v2/site_v3` variants before splitting, and fully holds
out hidden eval locations from public train labels. The prepared data now has
1,372,483 cleaned rows, 1,012,131 agent-visible train rows, 96,839 public dev
rows, and 263,513 hidden eval rows across 17 canonical locations.

Local recalibration on the refreshed data uses these anchors:

```text
weak baseline: weighted_error=211.329112, score=0.0
location-agnostic HGB reference: weighted_error=200.552306, score=5.0
observed 30min simple ensemble: weighted_error=182.502598, score=14.5
target 2h improvement band: weighted_error=158.000000, score=22.0
target 2h cap band: weighted_error=125.000000, score=30.0
expert target: weighted_error=90.000000, score=100.0
```

Recalibrated Harness acceptance completed on 2026-06-06:

```text
30min run pv_agent_recalibrated_30m_20260606_1921: best score=12.757743
2h run    pv_agent_recalibrated_2h_20260606_2000: best score=17.009971
```

Both runs used structured JSON reports with 14 metric values and no bad
reports. The 30min score stayed below 15, and the 2h score improved while
remaining below 30.

## Local Validation

```bash
python -m pytest \
  "Xpert/SE-Bench Research/tests/test_prepare_pv_benchmark.py" \
  "Xpert/SE-Bench Research/tests/test_audit_pv_leakage.py" \
  "Xpert/SE-Bench Research/tests/test_pv_scorer.py" \
  "Xpert/SE-Bench Research/tests/test_pv_harness_config.py" \
  "Xpert/SE-Bench Research/tests/test_package_pv_harness_assets.py" \
  -q
```
