# Analytics metric definitions

All dashboard values are calculated from persisted application, status-history,
deficiency, review-action, extracted-field, scheme, and form-data records at
request time.

| Metric | Definition |
| --- | --- |
| Funnel by stage | Current application count grouped by lifecycle status. |
| Average time per stage | Mean elapsed days between consecutive status-history events for each entered stage; applications still in that stage are excluded. |
| Deficiency causes | Count of deficiency records grouped by deficiency code, including resolved records. |
| Repeat-deficiency rate | Applications with `correction_round > 0` divided by all applications. |
| Override rate | Review actions whose `override_source` is `AI` or `RULES`, divided by all review actions. |
| OCR confidence distribution | Extracted-field confidence buckets: LOW `< 0.75`, MEDIUM `0.75–<0.90`, HIGH `>= 0.90`. |
| Scheme performance | Application counts grouped by scheme code and current lifecycle status. |
| State-wise distribution | `form_data.state`, then `form_data.address.state`; missing values are `UNKNOWN`. |

The backend exposes `GET /api/v1/analytics/summary` and
`GET /api/v1/analytics/export?format=csv|pdf`. Analytics is restricted to
administrators and officer roles.
