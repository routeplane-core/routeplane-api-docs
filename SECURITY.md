# Security Policy

This repository publishes the Routeplane API reference (OpenAPI 3.1 + Redoc). It ships
documentation rather than a running service, but documentation for a security product is
load-bearing: an example that teaches an unsafe pattern, or a spec that describes a control
we do not actually enforce, is a real defect and we want to hear about it.

## Reporting a vulnerability

Email **security@routeplane.ai**.

You can also use GitHub's private vulnerability reporting on this repository. Please do **not**
open a public issue for anything you believe is a vulnerability.

**Never include a real gateway key, provider API key, or customer data in a report** — including
in a screenshot. Redact it.

## What to expect (coordinated disclosure)

- **Acknowledgement within 72 hours** of your report reaching us.
- An initial assessment (accepted / needs-more-info / not-a-vulnerability) within 7 days.
- Where a report concerns the gateway rather than the docs, we ask for a standard **90-day
  coordinated disclosure window** and will agree a date with you, crediting you in the release
  notes (or keeping you anonymous — your choice).
- Documentation corrections are usually shipped immediately rather than held to a window.

## Scope

**In scope:** the published specification and site in this repository. We are particularly
interested in:

- **A documented control that does not match what the gateway enforces** — the spec claiming a
  check, default, or guarantee the implementation does not make. A reader who builds on a
  control that is not there is exposed by our documentation.
- **Examples that teach an unsafe pattern** — embedding credentials in a URL or query string,
  disabling TLS verification, logging a key, or an auth flow weaker than what we support.
- **Leaked material** — a real key, internal hostname, or customer identifier in an example,
  fixture, or committed file.
- Injection or supply-chain issues in the published site or its build.

**Out of scope:** the Routeplane gateway implementation itself (report those to the same
address — they are handled outside this repo's process), third-party LLM providers, and
cosmetic or editorial issues, which are welcome as ordinary public issues or pull requests.

## Bug bounty

We do **not** run a paid bug bounty program. We are a small team and we would rather say so
plainly than promise rewards we cannot pay consistently. We credit reporters, and we fix
confirmed reports fast.
