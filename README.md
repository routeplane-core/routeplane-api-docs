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
  not implied by entitlement: production currently has no provisioned verifier,
  so candidates fail closed. Separately, release policy prohibits arming until
  the ADR-105 held-out and production-shadow bars pass.

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

## Inference → feedback with the official clients

The Python example targets `routeplane==0.2.3`. The TypeScript
`@routeplane/sdk@0.5.4` and `@routeplane/cli@0.5.4` examples use the published
npm packages from the successful
[0.5.4 publication workflow](https://github.com/routeplane-core/routeplane-devtools/actions/runs/34699128126).
A bounded installed-package check on 2026-09-12 used a deterministic synthetic
upstream through the exact Community Edition v0.4.2 artifact and a separately
pinned internal build. It exercised Python sync and async owner modes, the
TypeScript `@routeplane/sdk/core` client, and the CLI. It did not exercise the
TypeScript root OpenAI subclass, the MCP server, or the complete API-10/API-11
SDK suites. Set
`ROUTEPLANE_BASE_URL` to your gateway origin (for example,
`https://<gateway-host>`, without `/v1`) and `ROUTEPLANE_API_KEY` to your
gateway key. Replace `your-enabled-model` with a model enabled on that gateway.
The Python client takes a `/v1` base URL; the TypeScript core client and CLI
take the origin and append their endpoint paths.

Use the **gateway-generated response** `x-routeplane-trace-id` (or its
`x-routeplane-request-id` alias), not the completion body's `id`, an existing
`log_...` row ID, a caller-supplied correlation value, or a W3C trace ID.
When both response aliases are present they must agree. If no usable request
identifier was returned, stop instead of inventing one.

### Python

The official client's `create_with_meta` returns the completion and its response
metadata. The feedback helper is synchronous and returns `None` on success.

```python
import os
from routeplane import Routeplane

with Routeplane(
    api_key=os.environ["ROUTEPLANE_API_KEY"],
    base_url=os.environ["ROUTEPLANE_BASE_URL"].rstrip("/") + "/v1",
) as client:
    completion, meta = client.create_with_meta(
        model="your-enabled-model",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=32,
    )
    request_id = meta.trace_id or meta.request_id
    if not request_id:
        raise RuntimeError("No gateway request identifier; feedback not sent")
    if meta.trace_id and meta.request_id and meta.trace_id != meta.request_id:
        raise RuntimeError("Gateway request identifier aliases disagree")
    client.feedback.create(request_id=request_id, score=1)
```

With `AsyncRouteplane`, await `create_with_meta`, but **do not await
`feedback.create`**: that helper is synchronous on both Python clients in 0.2.3.

### TypeScript

Use the official dependency-free core export; `postWithMeta` exposes the
completion response headers. `feedback.create` resolves to `undefined`.

```typescript
import { RouteplaneCoreClient } from '@routeplane/sdk/core';

const apiKey = process.env.ROUTEPLANE_API_KEY;
const baseUrl = process.env.ROUTEPLANE_BASE_URL;
if (!apiKey || !baseUrl) throw new Error('Set gateway URL and key');
const client = new RouteplaneCoreClient({ apiKey, baseUrl, timeout: 30_000 });
const response = await client.postWithMeta('/v1/chat/completions', {
  model: 'your-enabled-model',
  messages: [{ role: 'user', content: 'Hello' }],
  max_tokens: 32,
});
const traceId = response.headers.get('x-routeplane-trace-id');
const alias = response.headers.get('x-routeplane-request-id');
const requestId = traceId ?? alias;
if (!requestId) {
  throw new Error('No gateway request identifier; feedback not sent');
}
if (traceId && alias && traceId !== alias) throw new Error('Gateway request identifier aliases disagree');
await client.feedback.create({ requestId, score: 1 });
```

### CLI

`rp chat` in 0.5.4 does not print the gateway request identifier; `--json`
prints SSE chunk bodies, whose `id` is not a substitute. For a self-contained
CLI feedback example, capture the completion response header with curl, then
submit that identifier with the official `rp feedback` command. An identifier
captured by either SDK above can also be supplied to `--request-id`.

This Bash example requires curl 7.84.0 or newer for
[`%header{...}`](https://curl.se/docs/manpage.html#-w). It discards the completion
body, requires HTTP 200, and does not follow redirects.

```bash
set -euo pipefail
: "${ROUTEPLANE_BASE_URL:?Set your gateway origin}"
: "${ROUTEPLANE_API_KEY:?Set your gateway key}"
response_meta="$(curl --disable --fail --silent --show-error --max-time 30 \
  "${ROUTEPLANE_BASE_URL%/}/v1/chat/completions" \
  --header "x-routeplane-api-key: $ROUTEPLANE_API_KEY" \
  --header 'content-type: application/json' \
  --data '{"model":"your-enabled-model","messages":[{"role":"user","content":"Hello"}],"max_tokens":32}' \
  --output /dev/null \
  --write-out '%{http_code}|%header{x-routeplane-trace-id}|%header{x-routeplane-request-id}')"
IFS='|' read -r http_status request_id alias <<< "$response_meta"
request_id="${request_id:-$alias}"
[[ "$http_status" == 200 && -n "$request_id" ]] || {
  echo 'No successful completion with a gateway request identifier; feedback not sent' >&2
  exit 1
}
[[ -z "$alias" || "$alias" == "$request_id" ]] || {
  echo 'Gateway request identifier aliases disagree' >&2
  exit 1
}
rp feedback --request-id "$request_id" --score 1
```

### Shared feedback contract

The ergonomic Python `request_id` / TypeScript `requestId` / CLI `--request-id`
and `score` / `--score` arguments serialize to exactly this legacy request body:

```json
{"trace_id":"req_0123456789abcdef0123456789abcdef","value":1}
```

Scores are integers from **-10 through 10**, with no rescaling. Integral floats
such as Python `1.0` and CLI `--score 1.0` are accepted and sent as JSON integers.
Fractional, out-of-range, nonfinite, boolean, and nonnumeric SDK scores are
rejected before dispatch. CLI scores are text: numeric `1` is valid, while
empty, whitespace-only, fractional, nonfinite, and out-of-range values fail.

Comments are unsupported. Omitted, `None` / `null`, or empty-string comments
are omitted from the wire; every nonempty comment, including whitespace-only
text, is rejected before dispatch. The CLI has no null-typed argument: omit
`--comment`, or pass `--comment ''`. The helpers do not send `request_id`,
`requestId`, `score`, or `comment` as wire fields.

Successful calls acknowledge acceptance: Python returns `None`, TypeScript
resolves to `undefined`, and the CLI reports **“Feedback acknowledged”** with
exit status 0. Neither that acknowledgement nor a raw `{"status":"recorded"}`
response proves target existence, durable storage, or retention. The optional
`request_id` on log/usage rows is a correlation field, not a new log detail
endpoint or a guarantee that the request remains in history.

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

The optional `request_id` on `RequestLogRow` and `UsageEvent` matches the
gateway-generated response request identifier. It is distinct from a log row's
existing `id`; multiple retained attempts may share one request identifier.
Legacy or uncorrelated events omit the field. This does not add a log detail
endpoint or change bounded in-memory history, retention, or durability.

Run the focused full/Community schema guard with Python's standard library:

```sh
python3 -B -m unittest discover -s tests -v
```

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
