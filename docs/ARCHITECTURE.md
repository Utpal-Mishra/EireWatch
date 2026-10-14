# Architecture

## Local review boundary (Day 4)

Pending inspection and revision detail precede a decision. Review mutations compare the supplied revision inside the SQLite transaction, add a decision-history row and audit entry atomically, and preserve rejection suppression. Duplicate assessments compare both revisions and only change candidate state; a changed record reopens associated candidates even if the old heuristic no longer matches. Audit reasons and current records must be considered together. Existing databases gain an additive review table; old audit rows are not backfilled as new decisions.

This is genuine local operator workflow, not genuine remote authentication. Database writers can bypass or alter every check and audit. `docs/ACCESS_BOUNDARIES.md` defines proposed production separation; no user-supplied role or actor is accepted as proof of authenticated authority.

Source configuration → bounded collector → validated normalized records → SQLite transaction → revision history → human review → eligible local outbox → acknowledgement.

Each source has independent health and retry state. An invalid batch commits no incidents. A source failure retains last-known records without converting them into current warnings. IDs combine source ID and external ID; revisions fingerprint complete normalized records. Changes require fresh review and supersede pending older notifications.

Reports are generated local files, not a deployed service. Optional speech is user initiated. The outbox records pending/acknowledged/superseded states and does not imply network delivery. SQLite suits a single-host pilot; multi-worker claims/leases and authenticated service boundaries are deferred.

Recommended production boundaries: collector has restricted outbound network access; reviewer API enforces organisation roles; notification workers use provider idempotency keys and receipts; citizen uploads live in separate controlled storage. Cross-source merging, subscriber quiet hours/digests, secure web push and authenticated reviewer UI are planned.

## Development boundary (Day 1)

CI checks synthetic data and isolated temporary SQLite databases on push/PR. It uses read-only GitHub permissions and performs no collection, delivery or deployment. Scheduled development is a separate, bounded task ending 17 October 2026; it advances the plan only after inspecting the current branch and validating changes. Runtime files are excluded from Git.

## Source policy and publication health (Day 2)

`registry.validate_config` gates registration and ingestion. Approved non-synthetic configurations require named publisher, reviewer/date, endpoint and reuse evidence URLs, reuse notes, adapter test evidence and explicit verification flags. These are operator assertions, not independent certification or access control. Runtime network safeguards still apply. Legacy configurations are also checked when evaluating health, preventing old rows from silently bypassing new gates.

The normalized envelope's optional `published` field refers to the feed's publisher timestamp, including a publisher-confirmed empty feed. Production policy requires `publication_max_age_hours`; no timestamp means unknown, not fresh. Collection updates `checked` and `succeeded` independently. Missing publication replaces previous publication with unknown. Publication regression or future timestamps reject the transaction. No inferred timestamp is taken from incident maxima or HTTP retrieval time. Publisher clock skew and timestamp reset require source-specific investigation; strict rejection is intentional for this version.

A nullable `sources.published` column is added once on open. Old incident and history data are preserved. Combined source eligibility is healthy only if required publication freshness also passes; queue and inbox reuse this gate. No source is resolved merely because its feed is empty. Event-driven feeds without a periodic publisher timestamp need a researched policy/adapter before approval; an old warning is not necessarily invalid, so source-specific thresholds remain required.

## Effective lifecycle and duplicate candidates (Day 3)

Publisher status remains immutable inside each revision. A separate `lifecycle` projection records the current effective state. When an active record reaches its declared expiry, the projection becomes `expired` and an audit entry is written once; the source record remains `active`. This suppresses continued delivery without inventing a publisher-confirmed resolution. An empty feed or missing record never advances lifecycle state.

Explicit `resolved` and `withdrawn` revisions follow the normal revision/review path. They can enter the outbox only for subscriptions with an earlier notification for the same incident, avoiding cancellation broadcasts to unrelated subscribers.

`duplicate_candidates` is a review queue, not an identity resolver. Candidate pairs require equal category, an overlapping area, issue timestamps within 24 hours and title-token Jaccard similarity of at least 0.5. Detection stores an explainable reason and never merges incidents or changes review/outbox state. Source-specific evaluation is required before changing thresholds.

