# API-docs bundle — reviewer summary (vs the current public spec)

Reviewer-facing changelog for the rebuilt `routeplane-api-docs` content. Every
documented behavior below was verified against the gateway source at
`routeplane` v0.1.32 (`crates/routeplane/src/` route wiring, handler modules,
`crates/types/src/lib.rs`) on 2026-07-02. Items I could not fully verify are
listed under **Not verified / TODO** at the end. This file is for the review
PR only — do not publish it.

## openapi.yaml

### Corrected (was actively wrong)

- `GET /metrics` — was documented as JSON `{shed_total}`. Now documented as
  **Prometheus text exposition** (`text/plain; version=0.0.4`) with the real
  `rp_*` families (`rp_requests_total{provider,outcome}`,
  `rp_request_duration_ms`, `rp_tokens_total`, `rp_cost_micro_usd_total`,
  `rp_cache_events_total{type,result}`, `rp_provider_errors_total{provider}`,
  `rp_hedged_wins_total`, `rp_shed_total`) plus the deprecated unprefixed
  `shed_total` alias. Verified in `metrics.rs` (render) + `main.rs`
  (`metrics_handler`, content type).
- `info.version` `0.1.15` → `0.1.32`.
- Provider roster prose ("OpenAI, Anthropic, Google Gemini, Azure OpenAI") →
  the 15 integrations actually registered (`proxy.rs`
  `build_provider_registry()`: openai, anthropic, gemini, azure_openai,
  mistral, cohere, bedrock, groq, deepseek, together, fireworks, xai,
  openrouter, self_hosted) plus the built-in `local` moderation source.
- Embeddings description ("OpenAI, Azure OpenAI, and Gemini") → the providers
  with first-party embeddings (adds Mistral, Cohere, Together, Fireworks —
  all carry embedding models in the `/v1/models` catalog).
- `401 Unauthorized` — was documented as `text/plain`; the gateway returns the
  OpenAI envelope with `code: invalid_api_key` (verified in `auth.rs` tests).
- `x-routeplane-cache` header enum — added the fifth value `semantic-hit`
  (header form; the event/log form is `semantic_hit`), verified in
  `crates/cache` `CacheStatus`.

### Added — authentication

- `BearerAuth` security scheme (`Authorization: Bearer rp_…`, RFC-6750 style)
  alongside `x-routeplane-api-key`, with the non-`rp_`-token rejection and
  no-provider-key-passthrough posture documented (verified `auth.rs`
  `bearer_gateway_candidate`). Root `security` now offers both.

### Added — paths (all verified against `main.rs` route wiring + handlers)

Community (the CE Bundle A surface):

- `POST /v1/messages` — native Anthropic surface incl. the documented
  `stream:true` → 400 and missing-`max_tokens` → 400 (Anthropic error shape),
  the `anthropic` default provider, and the pipeline-error passthrough
  (verified `messages_api.rs`).
- `GET /v1/models` + `GET /v1/models/{id}` — OpenAI list/object shapes, the
  additive `routeplane` metadata extension (cost/modalities/capabilities/
  context_window/compliance_restrictions), env-discovered deployments, combos
  with `owned_by: "routeplane"`, 404 `model_not_found` (verified
  `models_api.rs`).
- `POST /v1/moderations` — incl. the `local`/`routeplane` built-in source and
  the documented raw-input (no-masking) deviation (verified
  `moderations_api.rs`).
- `POST /v1/rerank` — Cohere-shaped request/response, `cohere` default,
  empty-`documents` 422, `search_units` usage (verified `rerank_api.rs`,
  `crates/types`).
- `POST /v1/images/generations` — OpenAI shape with verbatim passthrough of
  unmodeled fields (verified `images_api.rs`, `crates/types`).
- `POST /v1/audio/speech` — JSON in, binary audio out, format-driven
  Content-Type (verified `audio_api.rs`, `SpeechRequest`).
- `POST /v1/audio/transcriptions` + `POST /v1/audio/translations` — multipart
  contract (`file` + `model` required; translations has no `language`), the
  26 MiB audio-specific body cap (`RP_AUDIO_MAX_BODY_BYTES`, verified
  `config.rs`), the binary-audio residency caveat, 422
  `transcription_not_supported` / `translation_not_supported`.
- `POST /v1/responses` — documented as the intentional typed **501**
  `endpoint_not_supported` (verified `main.rs` + `api_error.rs`).
- `POST /v1/feedback` — Portkey-shaped contract, validation bounds
  (value −10..=10, weight 0.0..=1.0, trace_id ≤256, metadata ≤16 flat keys /
  ≤256 chars), `{"status":"recorded","trace_id":…}` ack (verified
  `feedback_api.rs`).
- `GET /v1/logs` — `{"events":[…]}` of sanitized rows, newest-first, cap 200,
  key-ownership tenant isolation (verified `logs_api.rs`, `LogRow`).
- `GET /analytics/latency` — nearest-rank p50/p95/p99/max overall +
  per-provider (verified `observability.rs` `LatencyReport`).
- `GET /status` — unauthenticated snapshot: circuits, latency EWMA, cache
  stats, shed count, usage aggregate (verified `status.rs`).

Also updated `/analytics` prose: it is now tenant-scoped by key ownership
(verified `analytics_api.rs`) — the old spec implied a global read.

### Added — schemas / headers

- `ChatCompletionRequest`: `tools` / `tool_choice` / `parallel_tool_calls`,
  `response_format`, `seed`, `logprobs` / `top_logprobs`, `logit_bias`,
  `service_tier`, `reasoning_effort`, string-or-array `stop`; combo-as-model-id
  note on `model`. `Message`: string OR content-part array OR null content,
  `tool` role, `cache_control` passthrough, `tool_calls` / `tool_call_id`.
  Response side: `system_fingerprint`, `service_tier`, per-choice `logprobs`,
  `Usage.cached_tokens` / `cache_creation_tokens`. All verified against
  `crates/types/src/lib.rs`.
- Request headers: `x-routeplane-use-case`, `-currency`, `-timeout-ms`
  (narrow-only MIN-fold), `-pii-mode` (tokenize, degrade-to-mask),
  `-output-mask` (annotation semantics — see TODO), `-cache-control`
  (`no-store`), `-idempotency-key` (+ standard `Idempotency-Key`
  precedence), `-cohort` (prompts completions only). Verified in `proxy.rs` /
  `prompts_api.rs`.
- Response headers: `x-routeplane-trace-id` + `-request-id` (identical value,
  verified alias), `-hedged`, `-compliance-warning`, `-idempotent-replayed`,
  `-budget-warning`, `-limit-{type,scope,policy}` (on 402/429),
  `-guardrails: deny` (on 446), `-shed: capacity` (on 503).
- New response on chat: **403** `model_compliance_excluded` (the
  model-catalog compliance gate; Enterprise capability, `warn` mode emits the
  header instead — verified `api_error.rs` + `models_api.rs`).

### Edition markers + scrubs

- Every operation now carries `x-routeplane-edition: community | enterprise`
  (26 ops: 20 community, 6 enterprise). The 6 enterprise ops (3 prompts, 3
  MCP) also carry Redoc `x-badges: [{name: Enterprise}]`.
- Scrubbed from public prose: internal ADR numbers (ADR-025 on `/metrics`,
  ADR-017 on `/v1/mcp/run/step`), internal tier names ("Standard+" →
  "Enterprise"), and the "Azure Container App FQDN" hosting hint in `servers`.
- Added `info.license` (Apache-2.0) and an **Editions** section to
  `info.description`; the inline `x-routeplane-config` envelope is marked as
  an Enterprise capability with named combos as the Community path (per the
  packaging decision).
- A header comment in the yaml records the two invariants `community.html`
  relies on (one operation per path; the verbatim edition-marker line).

### Deliberately NOT added (kept out of scope per the work order)

The gateway also serves `GET /v1/finops/{usage,timeseries,cache-savings}`,
`GET /v1/residency/{summary,ledger}`, `GET /v1/guardrails/outcomes`,
`POST /v1/cache/purge`, and 10 further `/v1/mcp/*` routes (sampling, HITL,
receipts, anomaly, security events). These are enterprise-side or
out-of-Bundle-A surfaces; the instruction was to keep the existing
prompts/MCP set as-is and not expand it. They remain undocumented in the
public spec — flagging so the reviewer makes that call consciously.

## index.html

- Kept the audited shell (pinned Redoc v2.1.5 + SRI, dark theme, brand mark).
- Removed the two generated styled-components hash selectors (`.sc-dAlyuH`,
  `.sc-cWSHoV`) — replaced with stable selectors (`.api-content h5`,
  `.api-content h5 > span`, `caption`); added a comment forbidding `.sc-*`
  selectors so a future Redoc bump can't silently break the styling.
- Added a topbar edition switcher (Full reference ↔ Community Edition).

## community.html (new)

- Same shell rendering the CE-filtered view. An inline script fetches
  `openapi.yaml`, drops every path chunk containing
  `x-routeplane-edition: enterprise` plus the Prompts / Agentic-security tag
  entries, and hands the filtered YAML to `Redoc.init` via a **Blob URL**
  (Redoc parses YAML itself — no extra CDN dependency, no build step).
  Note: the work order said "hands the object to Redoc.init"; a Blob URL is
  used instead of a parsed object because the pinned Redoc bundle does not
  expose its YAML parser — same effect, zero added dependencies.
- Enterprise surfaces are **absent** (not greyed), matching the gateway's
  404-when-not-entitled posture. Unreferenced components left in the spec are
  not rendered by Redoc.
- The filter was validated offline against the shipped spec (a Python replica
  of the JS produces a spec that parses, has exactly the 20 community paths,
  drops both tags, and has no dangling `$ref`s).

## README.md

- Rewritten: view URLs (docs.routeplane.ai + community.html), the
  spec-tracks-gateway-version contract, the editions table, Bearer-first
  quickstart, combo example, contribution rule (verified-shipped-behavior
  only), contacts (maintainers@ / security@routeplane.ai), Apache-2.0 note.
  No personal names, handles, or emails anywhere in the bundle.

## CODEOWNERS (new)

- `* @routeplane-core/maintainers` only.

## Not verified / TODO for the reviewer

1. **`x-routeplane-output-mask` semantics** — code shows it is an *annotation*
   (recorded on the usage event; baseline masking runs regardless, values
   `pii|secrets|all|true`, ignored under tokenize). The spec says exactly
   that, but if a future pass makes it behavioral the wording must change.
2. **Non-JSON transcription formats** — `response_format: text|srt|vtt` are
   accepted fields; I did not trace whether the gateway returns them as
   plain text or re-wraps them. The spec documents the `json` contract and
   says richer/other formats pass through verbatim (looser-but-true).
   TODO: verify with a live call and tighten.
3. **`x-routeplane-timeout-ms` on non-chat routes** — verified on the chat
   pipeline; documented only there. The grep shows it referenced in several
   modules, so it may also apply to embeddings/rerank — TODO: verify and add
   the parameter to those operations if so.
4. **`/v1/audio/speech` capability-gap error code** — transcriptions/
   translations use `transcription_not_supported`/`translation_not_supported`
   (verified); the exact speech/TTS code string was not read in code, so the
   spec says "a typed capability error" without naming it. TODO: pin it down.
5. **`x-routeplane-limit-{type,scope,policy}` value vocabularies** — headers
   verified present on 402/429; the exact value sets were not enumerated, so
   descriptions stay generic.
6. **Rendering** — the Redoc render of both pages was not visually checked in
   a browser in this pass (CSP-free static host needed); the YAML + filter
   logic were machine-validated. TODO: eyeball both pages after the Pages
   deploy, especially the badge color and the switcher on mobile.
