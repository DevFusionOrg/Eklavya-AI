# Security hardening and ASVS L2 checklist

This document records the security posture delivered by Commit 21. Items
marked **open** require deployment-specific controls or a production
integration review; they are not claims that the demo environment is
production-ready.

## Implemented controls

- **Done — V2 authentication:** password policy, Argon2 password hashing,
  bearer access/refresh tokens, refresh-token revocation, login throttling,
  account lockout, and role checks.
- **Done — V3 session management:** access and refresh lifetimes are
  configurable; bearer tokens are sent in the Authorization header.
- **Done — V4 access control:** backend role dependencies remain the security
  boundary; frontend route checks are only a UX layer.
- **Done — V5 validation:** Pydantic validation, document MIME/size checks,
  and a global request body limit are applied.
- **Done — V7 error handling and logging:** JSON logs redact sensitive keys and
  12-digit Aadhaar-like values; regression tests cover redaction.
- **Done — V8 data protection:** applicant phone, email, and Aadhaar last four
  fields use AES-GCM application-level encryption. The key is supplied through
  `FIELD_ENCRYPTION_KEY`; rotate it using a planned re-encryption procedure.
- **Done — V9 communications:** explicit CORS origins, constrained methods and
  headers, security response headers, CSP, and HSTS outside development.
- **Done — V12 files:** documents use random object keys, MIME sniffing,
  checksums, size limits, antivirus hook support, and short-lived downloads.
- **Done — V14 configuration:** dependency audits and Gitleaks run in CI;
  example configuration contains placeholders only.
- **Open — dependency remediation:** the current pinned frontend tree reports
  six npm advisories (including Next.js and PostCSS) that require a planned
  breaking-version upgrade; CI intentionally fails on high-severity findings
  until that upgrade is reviewed and tested.

## CSRF boundary

The API currently authenticates with `Authorization: Bearer`, not cookies, so
CSRF does not apply to API authorization. The frontend `eklavya_role` cookie
only drives route presentation and is not accepted by the backend as identity.
If cookie-based API authentication is introduced, it must use an
`eklavya_session` cookie and the existing middleware requires
`X-CSRF-Token` on unsafe requests. Set `Secure`, `HttpOnly`, and `SameSite`
attributes before enabling such a cookie.

## Operational checklist

- **Open — ASVS V1 architecture:** complete a deployment threat model and
  independent security review.
- **Open — ASVS V6 cryptography:** production key management, rotation,
  re-encryption, and key escrow are not provided by local `.env` files.
- **Open — ASVS V10 malicious code:** enable ClamAV or an equivalent managed
  scanner; the default antivirus hook is a no-op.
- **Open — ASVS V11 business logic:** execute load, abuse, and concurrency
  testing against production-like PostgreSQL/Redis/MinIO.
- **Open — ASVS V13 API security:** configure an API gateway/WAF, rate limits
  beyond authentication, and provider-specific mTLS where required.
- **Open — ASVS V15 configuration:** use a secret manager, rotate all default
  credentials, and disable debug access in deployed environments.
- **Open — ASVS V16 threat monitoring:** centralize immutable logs, alerts,
  retention, and incident response.

## Backup and restore notes

Back up PostgreSQL with encrypted, access-controlled snapshots and test
point-in-time recovery at least quarterly. Back up MinIO documents and
metadata together, preserving object versioning and server-side encryption
configuration. Redis is treated as rebuildable cache/job state unless the
deployment explicitly enables durable task persistence. Restore into an
isolated environment, run Alembic migrations, verify the audit hash chain,
check object checksums, and record the recovery point and operator.

Never place database dumps, MinIO credentials, encryption keys, or restored
PII in the repository, CI artifacts, issue comments, or application logs.
