# Routeplane AI Gateway — API Documentation

The public API reference for [Routeplane](https://routeplane.ai), the
open-source, OpenAI-compatible AI gateway. Maintained by the Routeplane team.

**Rendered reference:**

- Full reference (Community + Enterprise, badged):
  [docs.routeplane.ai](https://docs.routeplane.ai/)
- Community Edition view (only what ships in the open-source gateway):
  [docs.routeplane.ai/community.html](https://docs.routeplane.ai/community.html)

The source of truth is [`openapi.yaml`](openapi.yaml) (OpenAPI 3.1), rendered
with a pinned, integrity-checked Redoc bundle via GitHub Pages. The Community
view renders the checked-in [`openapi.ce.yaml`](openapi.ce.yaml), a deliberately
maintained mirror of the Community operations.

**AI agents / LLMs:** see [`llms.txt`](llms.txt) for a machine-readable API
overview (auth, base URLs, endpoints, headers, SDKs, examples), and
[`llms-full.txt`](llms-full.txt) for the long-form per-endpoint reference —
both published at [docs.routeplane.ai/llms.txt](https://docs.routeplane.ai/llms.txt)
and [/llms-full.txt](https://docs.routeplane.ai/llms-full.txt).

## Versioning

`info.version` in `openapi.yaml` records the most recent tagged release baseline
(currently **v0.1.32**). Additive contract changes may merge after their gateway
implementation and before the next release tag; each such PR links its shipped
implementation evidence. If the spec disagrees with the corresponding gateway
commit or later release, please report it.

## Editions

Routeplane serves one API surface in two editions. Every operation in the spec
carries the vendor extension `x-routeplane-edition: community | enterprise`:

- **Community** (open source, Apache-2.0) — the OpenAI-compatible inference
  surface (chat, messages, embeddings, models, moderations, rerank, images,
  audio), routing with fallback/retries/hedging, the exact-match response
  cache, rate/spend limits, baseline PII masking, and the observability reads.
- **Enterprise** (commercial) — sovereign data-residency enforcement with the
  signed audit ledger, the agentic-security (MCP) gateway, advanced
  guardrails, evaluation-gated semantic-cache machinery, the prompt registry,
  FinOps export, and the multi-tenant control plane. Semantic answer serving is
  not implied by entitlement: it remains dark until the production verifier is
  provisioned and the ADR-105 held-out and production-shadow bars pass.

## Quickstart

Point any OpenAI SDK at your Routeplane deployment — only the base URL and the
key change. Both auth forms are equivalent:

```bash
# Stock OpenAI SDK form (Authorization: Bearer)
curl https://<gateway-host>/v1/chat/completions \
  -H "content-type: application/json" \
  -H "authorization: Bearer $RP_KEY" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"Hello"}]}'
```

```bash
# Branded header form, with a provider fallback chain
curl https://<gateway-host>/v1/chat/completions \
  -H "content-type: application/json" \
  -H "x-routeplane-api-key: rp_..." \
  -H "x-routeplane-provider: openai,anthropic" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"Hello"}]}'
```

Named combos — send an operator-defined routing chain's id straight through
the `model` field (combos are listed by `GET /v1/models` with
`owned_by: "routeplane"`):

```bash
curl https://<gateway-host>/v1/chat/completions \
  -H "content-type: application/json" \
  -H "authorization: Bearer $RP_KEY" \
  -d '{"model":"fast-fallback","messages":[{"role":"user","content":"Hello"}]}'
```

## Surface at a glance

| Endpoint | What it does | Edition |
|---|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible chat (buffered + SSE), full pipeline | Community |
| `POST /v1/messages` | Native Anthropic Messages surface (same pipeline) | Community |
| `POST /v1/embeddings` | OpenAI-compatible embeddings | Community |
| `GET /v1/models` + `/{id}` | Model discovery — curated catalog + combos | Community |
| `POST /v1/moderations` | OpenAI-compatible moderation (incl. built-in `local` source) | Community |
| `POST /v1/rerank` | Cohere/LiteLLM-compatible reranking | Community |
| `POST /v1/images/generations` | OpenAI-compatible image generation | Community |
| `POST /v1/audio/speech` | Text-to-speech (binary audio out) | Community |
| `POST /v1/audio/transcriptions` | Speech-to-text (multipart upload) | Community |
| `POST /v1/audio/translations` | Audio → English text (multipart upload) | Community |
| `POST /v1/responses` | Intentionally unsupported — typed 501 pointing to chat | Community |
| `POST /v1/feedback` | Attach a quality score to a request trace | Community |
| `POST /v1/cache/purge` | Purge this authenticated tenant's exact-cache namespace(s) | Community |
| `GET /v1/logs` | Recent request logs (your keys only) | Community |
| `GET /analytics` + `/analytics/latency` | Recent usage events + latency percentiles | Community |
| `GET /status` | Fixed liveness in managed Enterprise; operational snapshot in CE | Community |
| `GET /metrics` | Dedicated operator credential in managed Enterprise; unauthenticated in CE | Community |
| `GET /healthz` | Liveness (no auth) | Community |
| `GET /v1/prompts/{ref}` (+ `/render`, `/completions`) | Versioned prompt registry | Enterprise |
| `POST /v1/mcp/tool-result/inspect` | Agentic security — inspect a tool result | Enterprise |
| `POST /v1/mcp/tool-call/authorize` | Agentic security — default-deny tool-call authorization | Enterprise |
| `POST /v1/mcp/run/step` | Agentic security — account an agent-run iteration | Enterprise |

All `4xx`/`5xx` bodies use the OpenAI error envelope, extended with
Routeplane-branded codes (`routeplane_rate_limit_exceeded`,
`routeplane_guardrails_denied`, `endpoint_not_supported`, …) and, on guardrail
denials (HTTP 446), per-check results under `x_routeplane.check_results`.

## Contributing

Issues and PRs are welcome. The contract rule: the spec documents **verified,
shipped behavior only** — a spec change that adds or alters an endpoint must
point at the gateway release that shipped it. For anything else, open an
issue first.

- General contact: <maintainers@routeplane.ai>
- Security reports: <security@routeplane.ai> (do not open public issues for
  vulnerabilities)

## License

The OpenAPI specification and the pages in this repository are licensed under
[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0).
