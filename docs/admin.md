# Administration

The `/admin` portal is restricted to `ADMIN` users by both the frontend route
middleware and backend role dependencies. Scheme configuration is versioned:
published versions cannot be edited, while a new draft can be created and
published after review.

The builder stores JSON Schema form definitions and rule DSL data without
embedding scheme-specific logic in application code. The dry-run panel sends
sample context to the backend rules engine. Publishing retires the previous
published version and is recorded by the append-only audit chain.

The audit panel shows recent audit entries and can verify the complete hash
chain. Officer accounts are limited to scrutiny and verifying roles and are
listed with their active state.
