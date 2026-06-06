# PV Power Forecasting SE-Bench Task

Clean repository package for `pv_power_forecasting`.

## Repository Structure

- `agent-start/`: Agent-visible starter project and public train/dev data.
- `scorer/`: Hidden evaluation data, deterministic scorer, and scoring anchors.
- `harness/pv_power_forecasting.json`: SE-Bench Harness task definition.
- `harness/README.md`: Harness asset/build/run instructions.
- `docs/`: Data audit, pre-submission review, and real Agent acceptance evidence.
- `task.yaml`: Task specification.

## Key Files

- Agent prompt/readme: `agent-start/README.md`
- Scorer entrypoint: `scorer/score.sh`
- Scorer implementation: `scorer/evaluate.py`
- Harness task JSON: `harness/pv_power_forecasting.json`
- Pre-submission review: `docs/pre_submission_review.md`
- Data audit: `docs/data_audit.md`

## Validation Summary

The 2026-06-06 data refresh removes shifted raw `site_v2/site_v3` variants,
keeps only canonical `site_v1` observations, and fully holds out hidden eval
locations from public train labels. Local validation passes:

- Leakage audit: valid, only variant `1`, no public/eval location overlap, no
  shifted temporal proxy hits.
- Tests: 41 passed.
- Agent-start weak baseline: `weighted_error=211.329112`, score `0.0`.
- Location-agnostic HGB reference: `weighted_error=200.552306`, score `5.0`.
- Observed 30min simple ensemble: `weighted_error=182.502598`, score `14.5`.

The Harness path uses `parser: structured_json`, `selection: score_first`, and
`score_direction: maximize`. Recalibrated Harness acceptance on 2026-06-06:
30min best score `12.757743`; 2h best score `17.009971`; both runs used
structured JSON reports with 14 metric values and no bad reports.

## Release Assets

Refreshed Release:

```text
Tag: v2026.06.06-canonical
Title: PV Power Forecasting SE-Bench Canonical Data Refresh
```

Harness assets to upload to that Release:

```text
pv_work.tar.gz
pv_judge.tar.gz
```

`pv_work.tar.gz` contains only agent-visible files. `pv_judge.tar.gz` contains
the hidden scorer/eval files used by the judge image. Upload both assets to the
same Release used by the task JSON.

After upload, the Harness task JSON downloads:

```text
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.06-canonical/pv_work.tar.gz
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.06-canonical/pv_judge.tar.gz
```

## Cleanliness

This repository should not include SSH credentials, API keys, local submission spreadsheets, personal workflow notes, or VM environment files.
