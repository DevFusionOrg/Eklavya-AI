# Awards and follow-up progress

Administrators create an award only for an approved application through
`POST /api/v1/followups/awards`. The payload stores the award amount,
instalments, and optional requirement definitions. When definitions are
omitted, the published scheme version's `rules.followup_requirements` list is
used:

```json
{
  "name": "Semester marksheet",
  "type": "DOCUMENT",
  "due_days": 180,
  "validation_schema": { "required": ["semester"] }
}
```

Applicants use `GET /api/v1/followups/mine` to see award amounts, instalments,
due dates, and requirement status. They submit a response with
`POST /api/v1/followups/{requirement_id}/submissions`. An uploaded application
document may be referenced with `document_id`; it remains subject to the
existing document validation and OCR pipeline.

Officers review pending submissions through `GET /api/v1/followups/review` and
record an audited decision using
`POST /api/v1/followups/submissions/{submission_id}/review`. Rejected
requirements become available for another applicant submission.

The Celery beat task `app.followups.mark_overdue_followups` runs hourly.
Requirements past their due date become `OVERDUE`, and the related award moves
to `ON_HOLD` with an explanatory reason. This state is visible to the
applicant and prevents silent continuation of instalment processing.
