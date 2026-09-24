# Eklavya.AI RBAC matrix

All protected endpoints require a valid, non-revoked access token. A role mismatch returns `403`.

| Capability | APPLICANT | SCRUTINY_OFFICER | VERIFYING_OFFICER | COMMITTEE_MEMBER | ADMIN |
|---|---:|---:|---:|---:|---:|
| Register account | Yes (self, applicant only) | No | No | No | No |
| Login / refresh / logout | Yes | Yes | Yes | Yes | Yes |
| Create officer account | No | No | No | No | Yes |
| Submit own application | Yes | No | No | No | No |
| Scrutinize applications | No | Yes | No | No | Yes |
| Verify applications | No | No | Yes | No | Yes |
| Record selections | No | No | No | Yes | Yes |
| Manage schemes and users | No | No | No | No | Yes |

Role grants are implemented with the reusable `require_roles(*roles)` dependency. Officer
accounts cannot be self-registered; they are provisioned by an authenticated administrator.
