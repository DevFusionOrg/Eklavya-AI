# Officer scrutiny and sign-off

`GET /api/v1/officer/queue` returns a paginated, filterable queue for scrutiny
and verifying officers. Claims use a row lock, so two officers cannot claim the
same assignment concurrently. A verifying officer cannot claim or sign off an
application they scrutinized.

`GET /api/v1/officer/applications/{id}/review` combines form data, documents
with short-lived signed URLs, OCR fields and confidence/bounding boxes,
declarative rules results, and the latest advisory AI recommendation.

Human actions are submitted to
`POST /api/v1/officer/applications/{id}/actions`. `VERIFY` is only accepted
from the verifying role when two-level sign-off is enabled. Schemes can disable
that requirement with `rules.two_level_signoff=false`. Deficiencies and
rejections require reason codes; rejection also requires remarks. Overrides of
AI or rules require remarks and are included in the audit record and
`review_actions` analytics data. AI output never changes application status.
