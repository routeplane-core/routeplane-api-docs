"""Dependency-free structural guard for the two public request-ID properties.

This checks the deliberately stable YAML schema blocks, not arbitrary YAML or
full OpenAPI validity. The public full and Community mirrors must stay aligned.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROPERTY = """        request_id:
          type: string
          example: req_0123456789abcdef0123456789abcdef
          description: >-
            Gateway-generated request identifier matching the x-routeplane-request-id
            and x-routeplane-trace-id response headers. Shared by retained attempts
            for the same request; distinct from the log row id and caller, upstream,
            or W3C trace identifiers. Omitted for legacy or uncorrelated events.
"""


def schema_block(text, name):
    start = text.index(f"    {name}:\n")
    rest = text[start:]
    next_schema = re.search(r"(?m)^    [A-Za-z][A-Za-z0-9_]*:\n", rest[len(name) + 6:])
    if next_schema is None:
        raise AssertionError("expected a following schema block")
    return rest[:len(name) + 6 + next_schema.start()]


class RequestIdentityTests(unittest.TestCase):
    def test_optional_string_and_description_in_both_mirrors(self):
        for filename in ("openapi.yaml", "openapi.ce.yaml"):
            text = (ROOT / filename).read_text()
            for name in ("RequestLogRow", "UsageEvent"):
                with self.subTest(file=filename, schema=name):
                    block = schema_block(text, name)
                    self.assertEqual(block.count(PROPERTY), 1)
                    self.assertEqual(block.count("        request_id:\n"), 1)
                    # These two historically permissive schemas have no required
                    # fields: legacy rows must remain valid without request_id.
                    self.assertNotRegex(block, r"(?m)^      required:")
                    self.assertNotIn("nullable:", PROPERTY)
                    self.assertNotIn("pattern:", PROPERTY)

    def test_existing_log_row_id_is_not_replaced(self):
        for filename in ("openapi.yaml", "openapi.ce.yaml"):
            block = schema_block((ROOT / filename).read_text(), "RequestLogRow")
            self.assertIn("        id:\n          type: string\n          example: log_a41f9c02\n", block)
            self.assertIn("Synthesized stable id within a snapshot read.", block)

    def test_no_invented_log_detail_endpoint(self):
        for filename in ("openapi.yaml", "openapi.ce.yaml"):
            self.assertNotRegex((ROOT / filename).read_text(), r"(?m)^  /v1/logs/\{")


if __name__ == "__main__":
    unittest.main()
