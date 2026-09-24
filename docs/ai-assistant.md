# Explainable AI verification assistant

The officer-only `POST /api/v1/applications/{id}/ai-recommendation` endpoint
creates an advisory recommendation only when the application is
`UNDER_SCRUTINY`. It never changes application status or creates a selection,
approval, or rejection.

`AI_PROVIDER` supports `mock`, `local`, `openai`, and `anthropic`. The default
mock provider is deterministic and produces a rules-only summary, so local
development and tests do not require an external model. All providers receive
temperature `0` and must return the strict Pydantic recommendation schema.

Prompts contain field names, lengths, confidence, and last-four metadata rather
than raw applicant values. Every citation is checked against persisted
`extracted_fields` and its document before storage. Invalid output is retried,
then rejected. Prompt and response SHA-256 hashes are stored in
`ai_recommendations` for reproducibility and auditability.

The evaluation harness contains 30 labelled cases:

```powershell
python evals\run.py
```

It reports agreement with the human labels without making an automated
decision about any real application.
