# Access boundaries — 14 October 2026

IMPLEMENTED: trusted-local CLI and transactional revision checks. NOT IMPLEMENTED: authenticated API, organisation membership, roles, tenant isolation or tamper-resistant audit. Actor labels are attribution supplied by the operator, not verified identities. Do not expose CLI commands or SQLite directly over HTTP.

## Current operating boundary

One trusted OS account controls the database and reports. Restrict directory/database/export access using OS permissions; exports contain full incident records and operator labels and are not public artifacts. No citizen evidence should be imported into this prototype. SQLite backups and retention require an operator policy before real data. Decision rows are append-only through the provided workflow, not protected against direct SQL manipulation. Legacy decisions remain in audit; the new table does not invent past reasons.

## Proposed hosted boundary (not deployed)

| Component | Allowed responsibility | Required enforcement |
|---|---|---|
| Collector worker | Approved-source ingestion | Separate service identity; no reviewer permission; constrained network egress |
| Reviewer API | Inspect/decide current records for own organisation | Verified session, server-derived actor/membership, deny-by-default permission checks on every read/write |
| Notification worker | Claim eligible outbox entries | Separate credentials, idempotency/receipts; no incident approval |
| Subscriber API | Own preferences/inbox/acknowledgement | Authenticated ownership, not a supplied subscription ID |
| Public report | Sanitized approved information only | Explicit projection excluding raw evidence, subscriber IDs and reviewer labels |
| Audit storage | Preserve attributable changes | Restricted append path, retention and independent backup; avoid sensitive free-text reasons |

Before any hosted pilot: add organisation-scoped schemas and queries, negative cross-tenant tests, session expiry/revocation, CSRF protection where applicable, permission-change tests, secret handling, encrypted backup/restore tests and retention/deletion policy. Concurrency checks must remain transactional. Human review does not certify an official source or eliminate stale-source gates. No security certification or readiness for customer evidence is asserted.
