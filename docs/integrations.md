# Government integration adapters

Commit 20 defines provider-neutral contracts under `backend/app/integrations/`:

- `StatusSync` normalizes DBT payment/disbursement status.
- `BeneficiaryExport` validates and submits PFMS beneficiary batches.
- `DocumentFetch` retrieves a consented DigiLocker document.

The included DBT, PFMS, and DigiLocker implementations are **offline mocks**.
They make no network calls and must not be described as live integrations in
the product UI, demo, or operational documentation. Their responses include
offline wording where a status or receipt could otherwise be mistaken for a
government-provider response.

## Production onboarding requirements

A production connector needs a separately approved adapter and deployment
configuration, including:

1. Written onboarding and data-sharing approval from the relevant DBT/PFMS/
   DigiLocker programme owners.
2. Provider-issued client credentials, certificates or signing keys, endpoint
   allowlists, environment separation, and secret rotation.
3. For DigiLocker, OAuth redirect/callback handling, user consent records,
   token encryption and rotation, document-URI validation, and consent
   revocation handling.
4. For DBT/PFMS, schema/version negotiation, request signing or mTLS where
   required, idempotency keys, reconciliation jobs, retry/backoff rules,
   provider error mapping, and an audit trail for every exchange.
5. Security, privacy, retention, and operational approval before enabling any
   real connector.

No provider credentials are present in this repository. Application workflows
should treat adapter results as external facts requiring normal validation and
audit logging; an adapter must never approve an application or award funds.
