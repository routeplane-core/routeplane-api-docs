"""Narrow README examples guard; no SDK installation or network execution.

Python examples execute against a fake public-shaped client. TypeScript/shell
guards check the documented call shapes, not compilation or live acceptance.
"""
import ast
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def section():
    text = (ROOT / "README.md").read_text()
    return text.split("## Inference → feedback with the official clients\n", 1)[1].split("## Surface at a glance", 1)[0]


def snippet(language):
    matches = re.findall(r"```" + language + r"\n(.*?)\n```", section(), re.S)
    if len(matches) != 1:
        raise AssertionError("Expected one feedback example for each language")
    return matches[0]


class FeedbackExamplesTests(unittest.TestCase):
    def python_example(self, trace, alias):
        calls = []
        metadata = SimpleNamespace(trace_id=trace, request_id=alias)

        class FakeRouteplane:
            def __init__(self, **kwargs):
                calls.append(("init", kwargs))
                self.feedback = SimpleNamespace(create=lambda **args: calls.append(("feedback", args)))

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                calls.append(("close", None))

            def create_with_meta(self, **kwargs):
                calls.append(("inference", kwargs))
                # A provider body ID must never become the feedback target.
                return SimpleNamespace(id="chatcmpl_not_the_gateway_id"), metadata

        module = SimpleNamespace(Routeplane=FakeRouteplane)
        with patch.dict("sys.modules", {"routeplane": module}), patch.dict(os.environ, {
            "ROUTEPLANE_BASE_URL": "https://gateway.example/", "ROUTEPLANE_API_KEY": "synthetic-example-key",
        }, clear=True):
            code = compile(ast.parse(snippet("python")), "README-python-example", "exec")
            try:
                exec(code, {})
            except RuntimeError:
                return calls, False
        return calls, True

    def test_python_completion_metadata_then_feedback_and_cleanup(self):
        for trace, alias in (("req_actual", "req_actual"), ("req_actual", None), (None, "req_actual")):
            with self.subTest(trace=trace, alias=alias):
                calls, passed = self.python_example(trace, alias)
                self.assertTrue(passed)
                self.assertEqual([name for name, _ in calls], ["init", "inference", "feedback", "close"])
                self.assertEqual(calls[0][1]["base_url"], "https://gateway.example/v1")
                self.assertEqual(calls[1][1]["max_tokens"], 32)
                self.assertEqual(calls[2][1], {"request_id": "req_actual", "score": 1})

    def test_python_missing_or_mismatched_id_never_sends_feedback(self):
        for trace, alias in ((None, None), ("", None), (None, ""), ("req_a", "req_b")):
            with self.subTest(trace=trace, alias=alias):
                calls, passed = self.python_example(trace, alias)
                self.assertFalse(passed)
                self.assertNotIn("feedback", [name for name, _ in calls])
                self.assertEqual(calls[-1][0], "close")

    def test_typescript_core_public_api_and_response_headers(self):
        text = snippet("typescript")
        self.assertIn("import { RouteplaneCoreClient } from '@routeplane/sdk/core';", text)
        self.assertIn("await client.postWithMeta('/v1/chat/completions'", text)
        self.assertIn("response.headers.get('x-routeplane-trace-id')", text)
        self.assertIn("response.headers.get('x-routeplane-request-id')", text)
        self.assertIn("traceId !== alias", text)
        self.assertIn("if (!requestId)", text)
        self.assertNotIn(".test(requestId)", text)  # No new request-ID schema pattern.
        self.assertIn("await client.feedback.create({ requestId, score: 1 });", text)
        self.assertNotIn("response.data.id", text)
        self.assertNotIn("comment:", text)

    def test_cli_uses_captured_response_header_not_stream_body_id(self):
        text = snippet("bash")
        for required in ("set -euo pipefail", "curl --disable --fail", "--max-time 30",
                         "%header{x-routeplane-trace-id}", "%header{x-routeplane-request-id}",
                         '"$http_status" == 200', '"$alias" == "$request_id"',
                         'rp feedback --request-id "$request_id" --score 1'):
            self.assertIn(required, text)
        self.assertNotIn("--location", text)
        self.assertNotIn("rp chat", text)
        self.assertNotIn("--api-key", text)  # CLI uses its documented environment variable.
        self.assertIn("does not print the gateway request identifier", section())
        self.assertIn("curl 7.84.0 or newer", section())

    def test_wire_example_matches_both_legacy_schemas(self):
        wire = json.loads(snippet("json"))
        self.assertEqual(set(wire), {"trace_id", "value"})
        self.assertIs(type(wire["value"]), int)
        self.assertEqual(wire["value"], 1)
        self.assertTrue(wire["trace_id"].startswith("req_"))
        for filename in ("openapi.yaml", "openapi.ce.yaml"):
            block = (ROOT / filename).read_text().split("    FeedbackRequest:\n", 1)[1].split("    RequestLogRow:\n", 1)[0]
            self.assertIn("required: [trace_id, value]", block)
            self.assertRegex(block, r"value:\n\s+type: integer\n\s+minimum: -10\n\s+maximum: 10")

    def test_version_and_acknowledgement_boundaries_remain_explicit(self):
        text = section()
        for phrase in ("routeplane==0.2.3", "@routeplane/sdk@0.5.4", "@routeplane/cli@0.5.4",
                       "0.5.4 publication workflow", "bounded installed-package check",
                       "@routeplane/sdk/core", "It did not exercise the\nTypeScript root OpenAI subclass",
                       "the MCP server", "complete API-10/API-11\nSDK suites",
                       "-10 through 10", "no rescaling", "whitespace-only", "before dispatch",
                       "synchronous on both Python clients", "returns `None`", "resolves to `undefined`",
                       "Feedback acknowledged", "proves target existence, durable storage, or retention",
                       "not a new log detail", "`log_...` row ID", "W3C trace ID"):
            self.assertIn(phrase, text)
        for stale in ("release-candidate contract", "not yet been published",
                      "not installed-package acceptance evidence"):
            self.assertNotIn(stale, text)


if __name__ == "__main__":
    unittest.main()
