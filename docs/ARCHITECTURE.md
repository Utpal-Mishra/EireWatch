# Architecture

Source configuration → bounded collector → validated normalized records → SQLite transaction → revision history → human review → eligible local outbox → acknowledgement.

Each source has independent health and retry state. An invalid batch commits no incidents. A source failure retains last-known records without converting them into current warnings. IDs combine source ID and external ID; revisions fingerprint complete normalized records. Changes require fresh review and supersede pending older notifications.

Reports are generated local files, not a deployed service. Optional speech is user initiated. The outbox records pending/acknowledged/superseded states and does not imply network delivery. SQLite suits a single-host pilot; multi-worker claims/leases and authenticated service boundaries are deferred.

Recommended production boundaries: collector has restricted outbound network access; reviewer API enforces organisation roles; notification workers use provider idempotency keys and receipts; citizen uploads live in separate controlled storage. Cross-source merging, subscriber quiet hours/digests, secure web push and authenticated reviewer UI are planned.

## Development boundary (Day 1)

CI checks synthetic data and isolated temporary SQLite databases on push/PR. It uses read-only GitHub permissions and performs no collection, delivery or deployment. Scheduled development is a separate, bounded task ending 17 October 2026; it advances the plan only after inspecting the current branch and validating changes. Runtime files are excluded from Git.
