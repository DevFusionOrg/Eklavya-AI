# Deficiency correction loop

System deficiencies remain in the database as history. An open deficiency is
reused when it recurs; when its condition is corrected, it is marked `RESOLVED`
with `resolved_at`. This preserves reopened history without inflating cycle
counts.

While an application is `DEFICIENT`, applicants may edit only fields referenced
by open deficiencies and may replace only referenced documents (or upload a
missing required document). `POST /applications/{id}/resubmit` increments the
correction round and re-runs validation. The maximum round count and deadline
are scheme validation settings, falling back to `MAX_CORRECTION_ROUNDS` and
`CORRECTION_DEADLINE_DAYS`.

`GET /applications/{id}/deficiencies` exposes `repeat_deficiency_cycles`,
currently defined as the number of correction rounds, alongside the complete
open/resolved deficiency history. Celery beat runs the deadline expiry task
hourly; expired applications transition to `CLOSED` and receive an audit entry.
