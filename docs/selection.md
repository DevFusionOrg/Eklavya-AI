# Selection and approval

`POST /api/v1/selection/schemes/{scheme_id}/run` evaluates the published
scheme-version selection configuration over `OFFICER_VERIFIED` applications.
Scores include each weight component and the underlying rule results. Ordering
is deterministic: score descending, configured tie-breakers ascending, then
application UUID.

Committee members can inspect and adjust provisional statuses with mandatory
remarks, then freeze the list. A frozen list cannot be rerun or edited.
`POST /api/v1/selection/schemes/{scheme_id}/approve` is restricted to `ADMIN`;
it applies `SELECTED`, `WAITLISTED`, and `NOT_SELECTED` statuses and notifies
applicants. Every generation, adjustment, freeze, and approval is audited.

Exports are available as CSV, XLSX, or PDF from
`GET /api/v1/selection/schemes/{scheme_id}/export?format=...`.
