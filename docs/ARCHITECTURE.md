# Architecture

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
