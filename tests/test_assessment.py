"""Checks tied directly to Assessment 1's required categories and output contract."""

import unittest

from src.evaluate_osu import BASE, CASES, evaluate, student
from src.evidence import verify_chain_result
from src.osu_app import respond


REQUIRED_FIELDS = {
    "answer", "why", "citations", "clarifying_questions",
    "assumptions_not_in_catalog", "next_steps", "decision",
}


class AssessmentContractTests(unittest.TestCase):
    def test_required_case_mix(self):
        counts = {prefix: sum(case[0].startswith(prefix) for case in CASES)
                  for prefix in ("direct", "chain", "program", "abstain", "plan")}
        self.assertEqual(counts, {"direct": 10, "chain": 5, "program": 5,
                                  "abstain": 5, "plan": 2})

    def test_chain_answers_use_multiple_course_pages(self):
        for case_id, question, profile, _ in CASES:
            if case_id.startswith("chain"):
                result = respond(question, profile)
                code = "CS" + question.split("CS", 1)[1].split("?", 1)[0]
                self.assertTrue(verify_chain_result(code, result["citations"]), case_id)

    def test_program_rules_are_cited(self):
        for case_id, question, profile, _ in CASES:
            if case_id.startswith("program"):
                result = respond(question, profile)
                self.assertEqual(result["decision"], "answered", case_id)
                self.assertTrue(result["citations"], case_id)

    def test_course_name_and_corequisite_definition(self):
        course = respond("What do I need before enrolling in Database Systems?", student())
        self.assertEqual(course["decision"], "not_eligible")
        self.assertEqual(course["citations"][0]["passage_id"], "cs-cs340-0")
        coreq = respond("What does corequisite mean?", student())
        self.assertEqual(coreq["decision"], "answered")
        self.assertEqual(coreq["citations"][0]["passage_id"], "course-guide-2")

    def test_policy_answers_and_overload_are_cited(self):
        questions = [
            "What is the maximum undergraduate credit load per term?",
            "How does repeating a course affect GPA?",
            "Do transfer grades count in the OSU GPA?",
            "What is the academic residency requirement?",
        ]
        for question in questions:
            result = respond(question, student())
            self.assertEqual(result["decision"], "answered", question)
            self.assertTrue(result["citations"], question)
        overload = respond("Plan my next term", student(CS261="C") | {"max_credits": 20})
        self.assertEqual(overload["decision"], "needs_more_info")
        self.assertTrue(overload["citations"])

    def test_every_case_has_structured_output_and_next_step(self):
        for case_id, question, profile, _ in CASES:
            result = respond(question, profile)
            self.assertTrue(REQUIRED_FIELDS <= result.keys(), case_id)
            self.assertTrue(result["next_steps"], case_id)

    def test_reported_metrics(self):
        metrics = evaluate()
        self.assertEqual(metrics["eligibility_accuracy"], 1.0)
        self.assertEqual(metrics["abstention_accuracy"], 1.0)
        self.assertEqual(metrics["citation_coverage_catalog_claims"], 1.0)
        self.assertEqual(metrics["chain_evidence_validity"], 1.0)
        self.assertEqual(metrics["plan_credit_validity"], 1.0)


if __name__ == "__main__":
    unittest.main()
