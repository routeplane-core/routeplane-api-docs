"""Structural truth guard for the existing FinOps and evaluation APIs.

Dependency-free by design: the docs repository's required validation uses only
Python's standard library. These assertions pin the edition boundary, query
names, provenance wording, and typed schema references most likely to drift.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FULL = (ROOT / "openapi.yaml").read_text()
CE = (ROOT / "openapi.ce.yaml").read_text()

PATHS = (
    "/v1/finops/usage",
    "/v1/finops/timeseries",
    "/v1/finops/cache-savings",
    "/v1/finops/saver-metrics",
    "/v1/finops/usage/daily",
    "/v1/evaluations",
    "/v1/evaluations/score",
    "/v1/evaluations/rubrics",
)


def path_block(text: str, path: str) -> str:
    start = text.index(f"  {path}:\n")
    rest = text[start:]
    next_path = re.search(r"(?m)^  /", rest[len(path) + 4 :])
    return rest if next_path is None else rest[: len(path) + 4 + next_path.start()]


class FinOpsEvaluationsContractTests(unittest.TestCase):
    def test_all_current_routes_are_enterprise_only(self):
        for path in PATHS:
            with self.subTest(path=path):
                block = path_block(FULL, path)
                self.assertEqual(block.count("x-routeplane-edition: enterprise"), 1)
                self.assertEqual(block.count("x-badges: [{name: Enterprise}]"), 1)
                self.assertNotIn(f"  {path}:\n", CE)

    def test_finops_success_responses_are_private_no_store(self):
        for path in PATHS[:5]:
            with self.subTest(path=path):
                block = path_block(FULL, path)
                success = block.split("        '200':", 1)[1].split(
                    "        '401':", 1
                )[0]
                self.assertIn("#/components/headers/PrivateNoStore", success)
                self.assertIn("#/components/headers/FinOpsVary", success)

    def test_timeseries_uses_native_recent_window_query(self):
        block = path_block(FULL, "/v1/finops/timeseries")
        self.assertIn("name: window_mins", block)
        self.assertIn("name: buckets", block)
        self.assertNotRegex(block, r"(?m)^\s+- name: (from|to)$")
        for phrase in ("process-local", "not billed or reconciled", "never an absolute date range"):
            self.assertIn(phrase, block)

    def test_daily_usage_preserves_envelope_and_provenance(self):
        block = path_block(FULL, "/v1/finops/usage/daily")
        self.assertIn("#/components/schemas/FinOpsDailyUsageReport", block)
        schema = FULL.split("    FinOpsDailyUsageReport:\n", 1)[1].split(
            "    EvaluationHistoryRow:\n", 1
        )[0]
        self.assertIn("required: [tenant_id, from, to, days, totals, note]", schema)
        self.assertIn("not a provider invoice or reconciled bill", schema)

    def test_daily_usage_costs_are_nullable_and_pricing_evidence_is_required(self):
        schema = FULL.split("    FinOpsPricingSource:\n", 1)[1].split(
            "    EvaluationHistoryRow:\n", 1
        )[0]
        self.assertIn("FinOpsPricingEvidence:", schema)
        self.assertIn("enum: [live, partial, unavailable]", schema)
        self.assertIn("enum: [available, partial, unavailable]", schema)
        self.assertIn("enum: [known, legacy_unknown, corrupt]", schema)
        self.assertIn("enum: [estimated, unpriced, unavailable]", schema)
        self.assertIn("maximum: 9007199254740991", schema)
        self.assertGreaterEqual(schema.count("type: [integer, 'null']"), 5)
        self.assertIn(
            "required: [provider, model, requests, errors, total_tokens, cost_micro_usd, pricing]",
            schema,
        )
        self.assertIn(
            "required: [requests, errors, prompt_tokens, completion_tokens, total_tokens, cost_micro_usd, input_cost_micro_usd, output_cost_micro_usd, cost_inr_paise, pricing]",
            schema,
        )
        self.assertIn("An available value of 0 is a legitimate fully priced zero", schema)

    def test_saver_metrics_is_tenant_only_and_names_omissions(self):
        block = path_block(FULL, "/v1/finops/saver-metrics")
        self.assertIn("Process-wide replica counters are deliberately not exposed", block)
        schema = FULL.split("    FinOpsSaverMetrics:\n", 1)[1].split(
            "    FinOpsDailyModelUsage:\n", 1
        )[0]
        self.assertIn("not_instrumented", schema)
        self.assertNotRegex(schema, r"(?m)^\s+node:")

    def test_evaluation_surfaces_have_typed_response_schemas(self):
        expected = {
            "/v1/evaluations": "EvaluationsPage",
            "/v1/evaluations/score": "EvaluationScoreResponse",
            "/v1/evaluations/rubrics": "EvaluationRubricCatalog",
        }
        for path, schema in expected.items():
            with self.subTest(path=path):
                self.assertIn(f"#/components/schemas/{schema}", path_block(FULL, path))
                self.assertIn(f"    {schema}:\n", FULL)
        self.assertIn("does not persist the result", path_block(FULL, "/v1/evaluations/score"))
        self.assertIn("summary covers only the returned", path_block(FULL, "/v1/evaluations"))

    def test_new_schema_references_resolve(self):
        for name in re.findall(r"#/components/schemas/([A-Za-z0-9_]+)", FULL):
            with self.subTest(schema=name):
                self.assertIn(f"    {name}:\n", FULL)

    def test_machine_readable_reference_carries_same_truth_boundaries(self):
        text = (ROOT / "llms-full.txt").read_text()
        for heading in (
            "## GET /v1/finops/usage ",
            "## GET /v1/finops/usage/daily ",
            "## GET /v1/evaluations ",
            "## POST /v1/evaluations/score ",
            "## GET /v1/evaluations/rubrics ",
        ):
            self.assertIn(heading, text)
        for phrase in (
            "not durable history, a provider invoice, or a reconciled bill",
            "not a provider invoice or reconciled bill",
            "persists nothing",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
