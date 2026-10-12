# One-week development plan

Baseline: 10 October 2026. Scheduled follow-ups: 11–17 October 2026 inclusive, one bounded run daily. Automated development is distinct from a continuously running monitoring service. No production feed polling is currently deployed.

| Work package | Deliverable | Acceptance |
|---|---|---|
| Baseline — complete | SQLite core, collectors, CLI, report, examples | 14 tests pass |
| Day 1 — implemented, 11 October | Publish baseline, add repository CI and CLI integration checks | 16 local tests pass; remote CI result tracked separately |
| Day 2 — implemented, 12 October | Source registry, publication freshness and official adapter research | 24 local tests pass; source evidence and unresolved reuse/adapter checks documented; production list remains empty |
| Day 3 | Lifecycle edge cases, expiry transitions and semantic duplicate candidates | Replay/cancellation tests; never resolve by disappearance |
| Day 4 | Review workflow and access-boundary design | No simulated authentication represented as real access control |
| Day 5 | Outbox delivery interface, retries and receipts | Fake-provider tests; no external send without explicit destination authorisation |
| Day 6 | Operations report usability, filters and accessibility | Keyboard checks where supported; source degradation is visible |
| Day 7 | Regression review, packaging, operational runbook and handover | README accurately distinguishes working, unconnected and deferred features |

At each run: check publication authorisation and latest changes, select the next incomplete package, implement a bounded change, run meaningful tests, update audit/docs, then commit/push under the recorded public-code authorisation. Do not defer an available baseline merely because a later run exists. If blocked, record the blocker privately and report it. Do not overwrite concurrent work or claim unverified results. A schedule is not a guarantee that every dependency will be available.

Remaining dates: Day 2 = 12 October; Day 3 = 13 October; Day 4 = 14 October; Day 5 = 15 October; Day 6 = 16 October; Day 7 = 17 October. Stop after Day 7.
