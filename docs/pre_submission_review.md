# PV Forecasting Pre-Submission Review

Review date: 2026-05-23

## Result

The task has a runnable technical closed loop after the difficulty pass. The
hidden evaluation tail is long enough to measure short/mid/long-horizon
behavior, and the scorer reports ramp, extreme-ramp, sunlight-transition,
station-bias, daily-energy, and horizon metrics. Ordinary single-model
references do not receive high scores.

The 2026-06-02 review-feedback pass moved Harness evaluation from `score_sum`
pseudo cases to `structured_json`. The judge now returns the continuous score
directly and preserves `weighted_error`, all 14 metric values, metric weights,
normalization anchors, and runtime fields in `report.json.metrics`.

## Calibration Summary

- Malformed or blank submission: `0.0`.
- Agent-start weak baseline: `0.0`.
- Ordinary HistGradientBoosting reference: `2.0`.
- Capacity-normalized strong reference: `5.0`.
- Observed 16min Agent HGB ensemble: `8.0`.
- Observed structured 2h Agent run: `24.0`.
- Observed stronger historical Agent run: `30.0`.
- Strong solution band: `50.0`.
- Expert target: `100.0`.

This confirms the scorer is deterministic, automatic, and has a non-saturating
improvement range. A real 30min Agent run should stay low, and a real 2h run
should show visible progress but remain well below the strong-solution band.
Full score remains reserved for deeper feature discovery, model ensembling,
ramp-event specialization, daily-energy calibration, station-bias control, and
long-horizon calibration.

## Harness Evidence

Real Harness runs were used to validate the task:

- 30min run `pv_agent_30m_20260523_0331`: timed out naturally after about
  1800 seconds, completed 7 rounds, and reached best score `3.4332`.
- Structured smoke run `pv_agent_smoke_structured3_20260602_172440`: timed out
  naturally after about 900 seconds and reached best score `14.206642`; the
  best report includes `total_score`, `weighted_error`, and all 14 metric
  values.
- Structured 2h run `pv_agent_2h_structured_20260602_194356`: timed out
  naturally after about 7200 seconds, produced 62 valid structured reports, and
  reached `weighted_error=135.446758`; calibrated rescore is about `23.998468`.
- Calibrated 8h run `pv_agent_8h_calibrated_20260602_222150`: timed out
  naturally after about 28800 seconds, produced 152 valid structured reports,
  and reached `score=41.982139` with `weighted_error=119.098354`.

This satisfies the intended difficulty shape: the 2h Agent run improves over
30min, the 8h run improves over 2h, neither approaches full score, and the score
continues to have room for stronger long-horizon, ramp-event, station-bias, and
ensemble work.

The private evidence bundle contains run IDs, summaries, and selected logs.
Credentials, API keys, SSH details, hidden labels, and raw provenance files are
not included in this public clean package.
