# PV Power Forecasting SE-Bench Task

Clean repository package for `pv_power_forecasting`.

## Repository Structure

- `agent-start/`: Agent-visible starter project and public train/dev data.
- `scorer/`: Hidden evaluation data, deterministic scorer, and scoring anchors.
- `harness/pv_power_forecasting.json`: SE-Bench Harness task definition.
- `harness/README.md`: Harness asset/build/run instructions.
- `docs/`: Data audit, pre-submission review, and real Agent acceptance evidence.
- `baseline/`: Baseline/reference submissions and score logs.
- `task.yaml`: Task specification.
- `split_manifest.json`: Deterministic data split manifest.

## Key Files

- Agent prompt/readme: `agent-start/README.md`
- Scorer entrypoint: `scorer/score.sh`
- Scorer implementation: `scorer/evaluate.py`
- Scoring anchors: `scorer/eval-data/baseline_metrics.json`
- Harness task JSON: `harness/pv_power_forecasting.json`
- Acceptance evidence: `docs/agent_acceptance_runs_20260523.md`
- Pre-submission review: `docs/pre_submission_review.md`
- Data audit: `docs/data_audit.md`

## Validation Summary

Real SE-Bench Harness Agent validations:

- 30min run `pv_agent_30m_20260523_0331`: `runtime_seconds=1800.1332714557648`, `best_score=3.4332`.
- 2h run `pv_agent_2h_newkey_20260523_1226`: `runtime_seconds=7200.029923439026`, `total_rounds=81`, `agent_submissions=57`, `final best_score=14.887849`, highest report score `14.938906`, `weighted_error=129.841525`.

The 2h run improves over 30min but stays below the 30-point ceiling, leaving a continuing improvement runway.

## Cleanliness

This repository should not include SSH credentials, API keys, local submission spreadsheets, personal workflow notes, or VM environment files.
