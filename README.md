# ÉireWatch Monitor

Independent Python 3.11+ implementation of source-health monitoring, reviewed incident revisions and a local notification outbox. No code copied from The-Eye. No external runtime dependencies.

## Implemented

- Independent source collection, HTTPS host allowlist, blocked redirects, public-address precheck, timeout and response-size limit.
- Transactional SQLite storage; complete-batch validation and repeat-import deduplication.
- Source health: disabled, never checked, healthy, stale or unavailable; last success, failures and capped retry backoff.
- Stable source-scoped incident IDs; immutable revision snapshots and field-level changes.
- Effective lifecycle tracking records expiry without rewriting publisher status or claiming resolution.
- Explainable semantic duplicate candidates remain separate incidents until reviewed; no automatic merge occurs.
- Explicit reviewer approval per revision. Changed records invalidate previous approval. Older revisions are ignored and audited.
- Area/category subscriptions; deduplicated local outbox, superseded alerts and acknowledgement history.
- Active alerts require an official configured source, healthy connection, approval and an unexpired time window. Resolution updates require an earlier subscription event. Disappearing feed entries are not automatically resolved.
- Escaped green-themed HTML operations report with optional browser read-aloud.
- CLI, synthetic fixtures and 36 automated tests, including end-to-end CLI checks.

## Quick start

From this directory:

```sh
python -m unittest discover -s tests -v
mkdir -p runtime
python -m eirewatch --db runtime/demo.sqlite import examples/sources.json examples/incidents.json
python -m eirewatch --db runtime/demo.sqlite health
python -m eirewatch --db runtime/demo.sqlite export runtime/report.html --html
```

Open `runtime/report.html` locally. The example is synthetic and deliberately non-official: it cannot produce official alerts. Dates are fixed fixture dates, not live warnings.

## Review and local notifications

```sh
python -m eirewatch --db runtime/monitor.sqlite subscribe operator --areas Cork --categories road
python -m eirewatch --db runtime/monitor.sqlite export runtime/snapshot.json
python -m eirewatch --db runtime/monitor.sqlite review-queue
python -m eirewatch --db runtime/monitor.sqlite review-detail INCIDENT_ID REVISION
python -m eirewatch --db runtime/monitor.sqlite review INCIDENT_ID REVISION approved --actor REVIEWER --reason "Source and revision checked"
python -m eirewatch --db runtime/monitor.sqlite queue
python -m eirewatch --db runtime/monitor.sqlite inbox operator
python -m eirewatch --db runtime/monitor.sqlite ack NOTIFICATION_ID --subscription operator
```

Replace uppercase placeholders with actual snapshot IDs. The CLI is for a trusted local operator, not an authenticated multi-user API. `--actor` records a name; it does not verify identity. Protect database files with OS permissions.

## Day 4 — local review workflow and access boundaries

Inspect pending records and current revision changes before deciding. CLI decisions require a non-blank reason; decision rows preserve each approval/rejection, actor label, rationale and revision. Legacy Python callers without a reason are explicitly labelled as such. New revisions invalidate approval and stale inspection/decisions fail closed.

Use `duplicates` to inspect candidate IDs, then `review-duplicate FIRST SECOND FIRST_REVISION SECOND_REVISION duplicate --actor REVIEWER --reason "Evidence checked"` (or `distinct`). Assessments never merge or approve incidents. Changed records reopen associated candidates for reassessment; stored heuristic reasons can describe an older match, so inspect both current records. See `docs/ACCESS_BOUNDARIES.md` before considering a hosted service. No authentication, tenant isolation or tamper-proof audit storage is claimed.

## Source integration

`examples/production-sources.json` is empty on purpose. No official live integration has been connected or endorsed. A production adapter must verify source ownership, reuse terms, cadence, record identity, timezones, location precision and cancellation semantics. The normalized JSON envelope is `schema_version: 1` plus an `incidents` array (see fixture). The collector supports this contract only; it is not a generic parser for arbitrary official APIs.

```sh
python -m eirewatch --db runtime/monitor.sqlite collect examples/production-sources.json
```

A successful empty feed is connectivity evidence, not an all-clear. Connection recency and feed publication freshness are separate. A production source requires `publication_max_age_hours` and documented approval evidence. The normalized envelope accepts `published`, a timezone-aware publisher timestamp; missing or stale publication suppresses alerts even after a successful download. Never substitute collection time or the newest incident timestamp for a feed publication timestamp. Future or regressed feed publication timestamps reject the entire batch. See `docs/SOURCE_REGISTRY.md`. No email, push provider, SMS, police submission or background location tracking is connected. Queueing is not delivery. Cross-source duplicates require review; only same-source repeat records are automatically deduplicated.

## Production limits

Enforce network egress restrictions: DNS prechecks alone cannot prevent rebinding. Add authenticated access, review permissions, encrypted backups, retention policy, signed webhooks and provider delivery receipts before serving real users. No media or citizen personal information belongs in Git. Keep source secrets in environment/secret storage. The current static ÉireWatch site is not modified by this package.

## Development

See `docs/WEEK_PLAN.md`, `docs/ARCHITECTURE.md`, `docs/AUDIT.md` and `AGENTS.md`. Proposed features are explicitly separated from implemented features. Public code publication is authorised for this repository. This does not authorise publishing operational databases, personal reports, media, credentials or private project records. No open-source licence has been granted by this package.

## Automated checks and development schedule

GitHub Actions runs the synthetic unit and CLI integration suite on pushes and pull requests, across Python 3.11, 3.12 and 3.13. It has read-only repository permissions, no secrets, no live-feed collection and no deployment steps. CI execution status is available in the repository Actions tab; committing a workflow does not establish a passing remote run.

Days 1–3 (11–13 October): baseline/CI, source freshness, then lifecycle and duplicate-candidate controls. Scheduled development continues through 17 October, around 08:00 Europe/Dublin, working through `docs/WEEK_PLAN.md` and updating code, tests and documentation. This is a bounded development schedule, not continuous operational monitoring. The existing website is not deployed or changed by this repository workflow.

## Day 2 — source readiness and freshness

Source configuration validation now requires production endpoint, reuse and adapter verification evidence. Synthetic fixtures explicitly declare `synthetic: true`; this local test escape hatch is not an authentication boundary and must never be used for a real feed. Legacy approved configurations without evidence fail closed for alert eligibility. Existing databases gain a nullable publication field automatically; back up operational databases before upgrades. HTML and JSON reports show publication status independently of connection status. No real source has been approved or enabled.

## Day 3 — lifecycle and duplicate candidates

The monitor records effective expiry separately from publisher status. An expired active record is suppressed and audited as `expired`; it is not silently rewritten to `resolved`. Feed disappearance remains non-evidence. Explicit resolved or withdrawn revisions require fresh review and are queued only to subscribers who previously received that incident.

Likely duplicates are placed in a review-only candidate table when category and area match, issue times are within 24 hours, and normalized title-token similarity is at least 0.5. The stored reason exposes those factors. The heuristic never deletes, merges, resolves or approves records; false positives and wording variation remain expected until evaluated against representative data.

