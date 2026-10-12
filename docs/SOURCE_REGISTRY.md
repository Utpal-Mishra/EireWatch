# Candidate source registry — 12 October 2026

All candidates below are **DISABLED / RESEARCH ONLY**. Runtime `examples/production-sources.json` remains empty. No official adapter is implemented or endorsed. These are public technical research notes, not a representation of integration rights.

| Candidate | Evidence checked on 12 October | Reuse / endpoint assessment | Next gate |
|---|---|---|---|
| Met Éireann weather warnings | Official [Open Data](https://www.met.ie/about-us/specialised-services/open-data) page links its [weather warnings dataset](https://data.gov.ie/dataset/weather-warnings) | General guidance says most datasets use CC BY 4.0 with attribution conditions, while some live forecasts use a custom licence. Dataset page retrieval returned HTTP 429; dataset-specific terms and endpoint/schema not verified | Retrieve dataset-specific licence and attached conditions; verify endpoint, cadence, publisher timestamps, stable IDs, revisions, cancellations and geography; test adapter with labelled synthetic fixtures |
| Met Éireann forecasts | Government catalogue [API notes](https://data.gov.ie/dataset/met-eireann-forecast-api/resource/027da6d5-d819-48d1-9b16-331dba169bd1?inner_span=True) and [API changes](https://data.gov.ie/dataset/met-eireann-forecast-api/resource/911be73d-3d74-451a-ac44-2db4b0005245?inner_span=True) | Catalogue identifies custom licence and best-effort service, with endpoint migration notice. Forecasts are not official incident warnings; no current endpoint response or full licence verified | Do not treat numerical forecasts as issued warnings; separately confirm transport, licence and intended product use before implementation |
| MapAlerter council notices | Attempted [terms page](https://www.mapalerter.ie/terms); retrieval failed | No API endpoint or reuse permission established; failed retrieval does not establish that terms/API do not exist | Locate operator documentation or obtain written permission, council coverage and publication/cancellation semantics |

## Registry approval contract

For an enabled non-synthetic source, `approval` must contain nonempty `publisher`, `endpoint_evidence_url`, `reuse_terms_url`, `reuse_notes`, timezone-aware `reviewed_at`, `reviewer`, and `adapter_test_evidence`; `endpoint_verified`, `reuse_verified` and `adapter_verified` must all be boolean true. Supply a supported adapter, HTTPS endpoint with allowlisted host, and positive finite collection/publication age thresholds. Metadata documents an actual completed review; never fill it merely to pass validation.

The only current adapter is `normalized-json-v1`, a project-owned contract. It accepts `schema_version: 1`, `incidents: [...]` and optional `published`. No candidate above is claimed to serve that format. Future adapters must preserve source evidence and must not mint a publisher timestamp from download time. Unknown timestamps suppress alert eligibility when publication policy is configured.

Synthetic tests can omit production approval evidence with `synthetic: true`. This is a trusted-local development facility; configuration editors already control the application. Do not label production data synthetic to bypass review. A successful configuration check proves structure, not factual accuracy, legal clearance or real authentication.

No live-feed HTTP call was performed by the monitor during this work; research used public documentation. Endpoint live tests, attribution implementation and dataset-specific licence review remain BLOCKED/PENDING. Prefer one approved Cork-relevant warnings source before expanding.
