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

Real SE-Bench Harness Agent validations:

- 30min run `pv_agent_30m_20260523_0331`: `runtime_seconds=1800.1332714557648`, `best_score=3.4332`.
- Structured smoke run `pv_agent_smoke_structured3_20260602_172440`: `runtime_seconds=900.3348398208618`, `total_rounds=12`, `agent_submissions=5`, `auto_submissions=7`, `best_score=14.206642`; best report includes `total_score`, `weighted_error`, and all 14 metric values.
- Structured 2h run `pv_agent_2h_structured_20260602_194356`: `runtime_seconds=7200.03037571907`, `total_rounds=63`, `agent_submissions=39`, `auto_submissions=24`, `report_count=62`, `bad_report_count=0`, best `agent-39`, `weighted_error=135.446758`, old-curve score `12.405539`, calibrated rescore about `23.998468`.
- Calibrated 8h run `pv_agent_8h_calibrated_20260602_222150`: `runtime_seconds=28800.041011810303`, `total_rounds=151`, `agent_submissions=56`, `auto_submissions=95`, `report_count=152`, `bad_report_count=0`, best `auto-93`, `score=41.982139`, `weighted_error=119.098354`.

The current Harness path uses `parser: structured_json`, `selection: score_first`, and `score_direction: maximize`. Reports do not contain synthetic 1000-case output; they expose the continuous score plus `weighted_error`, 14 named metric values, metric weights, and score anchors. The 8h run improves over the 2h run but remains below the strong-solution band, leaving a continuing improvement runway.

## Release Assets

Final Release:

```text
Tag: v2026.06.03-final
Title: PV Power Forecasting SE-Bench Final Submission
```

Harness assets to upload to that Release:

```text
pv_work.tar.gz
pv_judge.tar.gz
```

After upload, the Harness task JSON downloads:

```text
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.03-final/pv_work.tar.gz
https://github.com/IkeYang/pv-power-forecasting-sebench/releases/download/v2026.06.03-final/pv_judge.tar.gz
```

## Cleanliness

This repository should not include SSH credentials, API keys, local submission spreadsheets, personal workflow notes, or VM environment files.
