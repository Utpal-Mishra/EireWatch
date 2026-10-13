# Audit — 10 October 2026

Status vocabulary: IMPLEMENTED, TESTED, PROPOSED, BLOCKED. No government endorsement or live feed implied.

- Business learning: IMPLEMENTED foundation targets verifiable changes and traceable handling; commercial value and customer demand remain unvalidated.
- System: IMPLEMENTED local collector/reviewer/outbox/report; no hosted daemon or official feed connected.
- Architecture: IMPLEMENTED Python standard library and SQLite with transactional ingestion and stable source-scoped identities.
- Automation: SCHEDULED seven daily development runs 11–17 October 2026, approximately 08:00 Europe/Dublin (flexible window), confirmed by scheduler on 10 October. Each run must check repository privacy before writes. Production polling is not activated.
- Recommendation: PROPOSED source-specific adapters and freshness policy, genuine auth, delivery receipts and cross-source review before production.
- Experiment: TESTED 14 synthetic-data tests; no real-world false-positive estimate or browser visual verification.
- External evidence: The-Eye README and source inspected via GitHub; Linux local-network checks do not provide geographic public safety data. No code reused.
- Risk & assumption: IMPLEMENTED stale/failed-source suppression, review gating, expiry, deduplication and HTML escaping. Remaining risks include DNS rebinding without egress policy, trusted-local CLI identity, no multi-tenant isolation and no external delivery guarantee.
- Data & integration: IMPLEMENTED normalized JSON adapter and non-official synthetic fixture; production source list empty pending validation.
- Product/feature: IMPLEMENTED revision history, scoped subscriptions, acknowledgement and optional read-aloud. PROPOSED quiet hours, digest, provider adapters and UI integration.
- Merchant & fulfilment: Not applicable.
- Expansion: PROPOSED pilot one approved source and bounded geographic scope before wider coverage.
- Decision: Independent implementation; preserve green theme. BLOCKED GitHub push: repository public, standing privacy preference private. No files sent to repository.

## EW-20261011-01 — Day 1 baseline and CI

Date: 11 October 2026. Owner: project maintainer. Version: 0.1.1.
Context: baseline existed as a saved package; repository contained only a starter README. Scope: publish original monitor code and establish repeatable checks.

| Log | Status and evidence | Decision / mitigation / follow-up |
|---|---|---|
| Business Learning | IMPLEMENTED repeatable engineering baseline; demand remains unvalidated | Pilot outcomes still required before commercial claims |
| System | IMPLEMENTED original collector, SQLite store, review CLI and local outbox in repository package | No hosted operation or official submission |
| Architecture | IMPLEMENTED CI/runtime separation; read-only CI permissions | Runtime data never uploaded as CI artifacts |
| Automation | SCHEDULED remaining six runs, 12–17 October, approximately 08:00 Europe/Dublin | Public code authorisation recorded; schedule ends after 17 October |
| Recommendation | PROPOSED next package: approved-source registry and publication freshness | Unknown endpoints and reuse terms keep sources disabled |
| Experiment | TESTED 16 tests on Python 3.12.14 and package compilation | Includes demo replay/export and empty production configuration; no live-network experiment |
| External Evidence | VERIFIED current repository head before integration; restored package inspected | No new official-data evidence asserted |
| Risk & Assumption | Public Git can expose runtime information; high impact | Ignore databases, environment files and runtime directories; stage source files only; no secrets or personal evidence included |
| Data & Integration | IMPLEMENTED unchanged synthetic fixtures; production configuration empty | No new source activation |
| Product / Feature | IMPLEMENTED CI and CLI smoke coverage | Remote Actions outcome must be checked separately; local success is not remote success |
| Merchant & Fulfilment | NOT APPLICABLE | No commerce workflow |
| Expansion | PROPOSED single-source pilot remains pending | Do not expand coverage without source validation |
| Decision | APPROVED public code publication; earlier publication blocker resolved | Permission limited to project code and technical documentation; no visibility change |
| Validation / QA | TESTED original 14 core tests plus 2 subprocess CLI tests | CI matrix covers 3.11–3.13; other interpreters not locally verified |
| Change / Release | IMPLEMENTED 0.1.1 documentation and workflow | Preserve remote starter history; no force-push; no website deployment |

Next: Day 2 on 12 October — source registry, publication freshness and official adapter research. Production monitoring, browser testing and external delivery remain unverified/unconnected.

## EW-20261012-01 — Day 2 source registry and publication freshness

Date: 12 October 2026. Owner: project maintainer. Version: 0.1.2.
Context: collection success alone could label old publications healthy. Decision: model publisher freshness independently and require production approval evidence. Evidence: `tests/test_sources.py`, `docs/SOURCE_REGISTRY.md`; local suite 24 passing tests.

| Log | Status / evidence | Rationale, mitigation and next action |
|---|---|---|
| Business Learning | IMPLEMENTED evidence-based readiness indicators; commercial benefit PROPOSED | Fresh connection is insufficient evidence of useful current information; validate with a future bounded pilot |
| System | IMPLEMENTED nullable publication column and idempotent upgrade | Preserve existing incidents/history; back up real databases before migration |
| Architecture | IMPLEMENTED independent connection/publication statuses and combined alert gate | Missing publication is unknown; no timestamp inferred from retrieval or incident maxima |
| Automation | IMPLEMENTED next bounded package; no production polling activated | Continue lifecycle package next; existing development end remains 17 October |
| Recommendation | PROPOSED one verified weather-warning source first | Event-driven publication policy and cancellation mapping must be reviewed before enabling |
| Experiment | TESTED 24 unit/CLI tests including 8 new source tests | Stale/missing/future/regressed publication, exact threshold/timezone, legacy migration, approval gates and no-fetch disabled source |
| External Evidence | RESEARCHED official Met Éireann open-data guidance and government API catalogue | Dataset terms retrieval rate-limited; MapAlerter terms retrieval failed; no permissions inferred; links in source registry |
| Risk & Assumption | IMPLEMENTED fail-closed publication gate; risk of clock skew/reset and over-strict cadence remains | High impact if stale content alerts; strict rejection pending source-specific policy. Operator flags are not authentication or legal certification |
| Data & Integration | IMPLEMENTED normalized envelope publication timestamp and approval schema | Production source list remains empty; official adapter and dataset-specific verification PENDING |
| Product / Feature | IMPLEMENTED publication status/time in HTML and JSON | No live website integration or browser visual verification claimed |
| Merchant & Fulfilment | NOT APPLICABLE | No commerce or external delivery |
| Expansion | PROPOSED single-source bounded pilot | No geographic coverage increase claimed |
| Decision | IMPLEMENTED original code only; no source activation | Keep candidate research separate from enabled configuration; preserve public repository history |
| Validation / QA | TESTED local suite and additive legacy-source migration | Remote CI is separate from local results; no live-network test |
| Change / Release | IMPLEMENTED 0.1.2 code, README, architecture, registry, changelog and plan | Next incomplete package: Day 3 lifecycle/duplicate candidates |

## EW-20261013-01 — Day 3 lifecycle and duplicate candidates

Date: 13 October 2026. Owner: project maintainer. Version: 0.1.3.
Context: expiry was enforced at queue time but was not retained as an effective lifecycle transition, and cross-record duplicates had no explicit review queue. Evidence: `tests/test_monitor.py`; local suite 29 passing tests.

| Log | Status / evidence | Rationale, mitigation and next action |
|---|---|---|
| Business Learning | IMPLEMENTED traceable expiry and duplicate-review signals; operational value remains PROPOSED | Validate review workload and false-positive rate in a bounded pilot |
| System | IMPLEMENTED lifecycle projection and duplicate-candidate tables | Publisher records remain unchanged; additive tables preserve incident/history data |
| Architecture | IMPLEMENTED audit-on-transition and non-destructive candidate pairing | Expiry and heuristic similarity cannot masquerade as publisher truth |
| Automation | IMPLEMENTED Day 3 bounded package; no operational polling activated | Continue genuine review/access boundaries next; development ends 17 October |
| Recommendation | PROPOSED source-specific duplicate thresholds and manual candidate disposition | Measure precision/recall before tuning or adding merge operations |
| Experiment | TESTED 29 tests, including replay idempotence, expiry, withdrawal audience, and positive/negative duplicate boundaries | Synthetic coverage only; no representative cross-source corpus |
| External Evidence | NOT REQUIRED for this original internal algorithm | No official endpoint, third-party code or licensing claim introduced |
| Risk & Assumption | IMPLEMENTED no auto-merge/no false resolution; token similarity can over- or under-match | Candidate state only, stored reasons, 24-hour/category/area gates; human review remains next |
| Data & Integration | IMPLEMENTED additive lifecycle/candidate SQLite records | Production source list remains empty; no personal data or database published |
| Product / Feature | IMPLEMENTED lifecycle in snapshots and duplicate-candidate accessor | Operations-report presentation deferred to Day 6 |
| Merchant & Fulfilment | NOT APPLICABLE | No commerce workflow |
| Expansion | PROPOSED evaluate candidates on one approved source pair before wider coverage | No geographic or source expansion |
| Decision | IMPLEMENTED expiry as effective `expired`, never `resolved`; cancellations notify prior audiences only | Preserve source truth and avoid unrelated cancellation notifications |
| Validation / QA | TESTED full local suite on Python 3.12 | Remote CI checked separately after push; browser and multi-process behaviour unverified |
| Change / Release | IMPLEMENTED 0.1.3 code, tests and documentation | Next incomplete package: Day 4 review workflow and access-boundary design |

