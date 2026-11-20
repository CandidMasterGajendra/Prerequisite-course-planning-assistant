"""Offline graph routing and generation-guard checks; no model-quality claim."""

import unittest
import os
from unittest.mock import patch

from src.workflow import run


PROFILE = {
    "catalog_year": "2026-2027", "target_program": "CS Computer Systems",
    "target_term": "Fall", "max_credits": 12, "transcript_complete": True,
    "completed_courses": {"CS162": "C", "CS225": "B", "CS261": "B"},
}


class Writer:
    def __init__(self, summary, citation_ids):
        self.summary = summary
        self.citation_ids = citation_ids
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return {"summary": self.summary, "citation_ids": self.citation_ids}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        # Keep offline guard tests offline even when a developer has a local key.
        self.env_patch = patch.dict(os.environ, {"OPENAI_API_KEY": ""})
        self.loader_patch = patch("src.workflow.load_local_env")
        self.env_patch.start()
        self.loader_patch.start()
        self.addCleanup(self.loader_patch.stop)
        self.addCleanup(self.env_patch.stop)

    def test_course_template_has_verified_citation(self):
        result = run("Can I take CS261?", PROFILE)
        self.assertEqual(result["decision"], "eligible")
        self.assertTrue(result["verification"]["citation_metadata_and_scope"])
        self.assertEqual(result["generation_mode"], "template")
        self.assertEqual(result["workflow_trace"], ["intake", "retrieve", "rules", "write_template", "verify"])

    def test_uncertain_rule_bypasses_writer(self):
        writer = Writer("CS325 is eligible.", ["bogus"])
        result = run("Can I take CS325?", PROFILE, writer=writer)
        self.assertEqual(result["decision"], "needs_more_info")
        self.assertEqual(writer.calls, 0)
        self.assertEqual(result["workflow_trace"], ["intake", "retrieve", "rules", "verify"])

    def test_bad_generated_citation_falls_back(self):
        result = run("Can I take CS261?", PROFILE,
                     writer=Writer("CS261 is eligible.", ["fabricated-id"]))
        self.assertEqual(result["answer"], "CS261: eligible.")
        self.assertEqual(result["generation_mode"], "template_after_verification")

    def test_valid_structured_draft_is_used(self):
        baseline = run("Can I take CS261?", PROFILE)
        citation_id = baseline["citations"][0]["passage_id"]
        writer = Writer("CS261 is eligible based on the reviewed prerequisites.", [citation_id])
        result = run("Can I take CS261?", PROFILE, writer=writer)
        self.assertEqual(writer.calls, 1)
        self.assertEqual(result["generation_mode"], "gpt")
        self.assertEqual(result["answer"], writer.summary)

    def test_prerequisites_named_in_cited_course_are_allowed(self):
        baseline = run("Can I take CS261?", PROFILE)
        citation_id = baseline["citations"][0]["passage_id"]
        summary = "CS261 is eligible because CS162 and CS225 satisfy its prerequisite branches."
        result = run("Can I take CS261?", PROFILE, writer=Writer(summary, [citation_id]))
        self.assertEqual(result["generation_mode"], "gpt")
        self.assertEqual(result["answer"], summary)

    def test_extra_course_in_draft_falls_back(self):
        result = run("Can I take CS261?", PROFILE,
                     writer=Writer("CS261 and CS999 are eligible.", ["cs261-0"]))
        self.assertEqual(result["generation_mode"], "template_after_verification")

    def test_unverified_offering_claim_falls_back(self):
        baseline = run("Can I take CS261?", PROFILE)
        citation_id = baseline["citations"][0]["passage_id"]
        result = run("Can I take CS261?", PROFILE,
                     writer=Writer("CS261 is offered in Fall.", [citation_id]))
        self.assertEqual(result["generation_mode"], "template_after_verification")
        self.assertIn("unverified_offering_claim", result["verification"]["draft_rejection_reasons"])

    def test_plan_preserves_credit_check(self):
        result = run("Plan my next term", PROFILE)
        self.assertEqual(result["decision"], "plan_proposed")
        self.assertTrue(result["verification"]["citation_metadata_and_scope"])
        self.assertLessEqual(sum(x["credits"] for x in result["plan"]), 12)


if __name__ == "__main__":
    unittest.main()
