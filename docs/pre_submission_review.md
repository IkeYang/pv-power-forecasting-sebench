# PV Forecasting Pre-Submission Review

Review date: 2026-06-06

## Result

The PV task has been refreshed after the leakage audit. The prepared benchmark
loads only canonical raw `site_v1` observations and excludes shifted
`site_v2/site_v3` variants before any split is generated. This keeps the
forecasting task, scorer, CLI, and metric suite intact, while removing the
train/eval sibling-label path that allowed 21-day or 42-day shifted lookups.
Hidden eval locations are fully held out from public train labels.

The judge uses `structured_json`. It returns the continuous score directly and
preserves `weighted_error`, all 14 metric values, metric weights, normalization
anchors, and runtime fields in `report.json.metrics`.

## Calibration Summary

- Agent-start weak baseline: `weighted_error=211.329112`, score `0.0`.
- Location-agnostic HGB reference: `weighted_error=200.552306`, score `5.0`.
- Observed 30min simple ensemble: `weighted_error=182.502598`, score `14.5`.
- Target 2h improvement band: `weighted_error=158.000000`, score `22.0`.
- Target 2h cap band: `weighted_error=125.000000`, score `30.0`; expert target: `weighted_error=90.000000`, score `100.0`.

Local validation confirms the scorer is deterministic and automatic on the
canonical dataset. The 2026-06-06 leakage audit reports only variant `1` in
public/eval data, no public/eval location overlap, no non-canonical public/eval
locations, and zero shifted temporal proxy hits at `+/-21` or `+/-42` days.

## Harness Acceptance

Recalibrated Harness acceptance completed on 2026-06-06:

- 30min run `pv_agent_recalibrated_30m_20260606_1921`: best score `12.757743`.
- 2h run `pv_agent_recalibrated_2h_20260606_2000`: best score `17.009971`.

Both runs used structured JSON reports with 14 metric values and no bad
reports. The 30min score stayed below 15, and the 2h score improved while
remaining below 30.

Credentials, API keys, SSH details, hidden labels, and raw provenance files are
not included in this public clean repository package.
