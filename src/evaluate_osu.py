"""Labeled rule-level evaluation for the OSU pilot (not an LLM benchmark)."""

from __future__ import annotations

import json
from .evidence import verify_chain_result, verify_citations, verify_course_result, verify_plan
from .osu_app import respond

BASE = {"catalog_year": "2026-2027", "target_program": "CS Computer Systems", "target_term": "Fall", "max_credits": 12, "transcript_complete": True}

def student(**grades: str) -> dict:
    return BASE | {"completed_courses": grades}

CASES = [
    # 10 direct prerequisite checks
    ("direct-01", "Can I take CS162?", student(CS161="C"), "eligible"),
    ("direct-02", "Can I take CS162?", student(CS161="C-"), "not_eligible"),
    ("direct-03", "Can I take CS261?", student(CS162="C", CS225="C"), "eligible"),
    ("direct-04", "Can I take CS261?", student(CS162="C-", CS225="C"), "not_eligible"),
    ("direct-05", "Can I take CS261?", student(CS162="C", MTH231="C"), "eligible"),
    ("direct-06", "Can I take CS340?", student(CS261="C"), "eligible"),
    ("direct-07", "Can I take CS340?", student(CS261="D"), "not_eligible"),
    ("direct-08", "Can I take CS361?", student(CS261="C"), "eligible"),
    ("direct-09", "Can I take CS362?", student(CS261="C"), "eligible"),
    ("direct-10", "Can I take CS290?", student(CS162H="B"), "eligible"),
    # 5 chain checks; every result must cite the target plus 1+ related course pages
    ("chain-01", "Can I take CS374? Show the prerequisite-chain evidence.", student(CS261="C", CS274="C", CS271="C"), "eligible"),
    ("chain-02", "Can I take CS374? Show the prerequisite-chain evidence.", student(CS261="C", CS274="C"), "not_eligible"),
    ("chain-03", "Can I take CS461? Show the prerequisite-chain evidence.", student(CS325="C", CS361="C", CS362="C"), "eligible"),
    ("chain-04", "Can I take CS462? Show the prerequisite-chain evidence.", student(CS362="C", CS461="C"), "eligible"),
    ("chain-05", "Can I take CS463? Show the prerequisite-chain evidence.", student(CS462="C", ENGR102="C-"), "not_eligible"),
    # 5 program requirement questions: credits, categories, and elective constraints
    ("program-01", "How many total credits are required for the CS major?", student(), "answered"),
    ("program-02", "How many total credits are required for the Computer Systems option?", student(), "answered"),
    ("program-03", "How many restricted elective credits does the Computer Systems option require?", student(), "answered"),
    ("program-04", "How many approved elective credits does the Computer Systems option require?", student(), "answered"),
    ("program-05", "Can CS 402 count as a restricted elective?", student(), "answered"),
    # 5 out-of-scope or uncertain-policy checks
    ("abstain-01", "Who teaches CS340?", student(), "needs_more_info"),
    ("abstain-02", "Is CS340 offered in Fall?", student(), "needs_more_info"),
    ("abstain-03", "What room is CS340 in?", student(), "needs_more_info"),
    ("abstain-04", "What textbook does CS340 use?", student(), "needs_more_info"),
    ("abstain-05", "Can I take CS325?", student(CS261="C", CS225="C"), "needs_more_info"),
    # Extra planning checks beyond the required 25-query category mix
    ("plan-01", "Plan my next term", student(CS162="C", CS225="C", CS261="C"), "plan_proposed"),
    ("plan-02", "Plan my next term", student(CS162="C", CS225="C", CS261="C") | {"max_credits": 4}, "plan_proposed"),
]

def evaluate() -> dict:
    rows = []
    for case_id, question, profile, expected in CASES:
        result = respond(question, profile)
        citations = result.get("citations", [])
        citations_valid = verify_citations(citations)
        if result["decision"] in {"eligible", "not_eligible"}:
            code = question.split("CS")[-1].split("?")[0].strip()
            code = "CS" + code
            citations_valid = citations_valid and verify_course_result(code, citations)
            if case_id.startswith("chain"):
                citations_valid = citations_valid and verify_chain_result(code, citations)
        plan = result.get("plan", [])
        plan_within_limit = sum(p["credits"] for p in plan) <= profile.get("max_credits", 19)
        if result["decision"] == "plan_proposed":
            citations_valid = citations_valid and verify_plan(plan, profile["max_credits"])
        rows.append({"id": case_id, "expected": expected, "actual": result["decision"], "correct": result["decision"] == expected, "citations": len(citations), "citation_ids_valid": citations_valid, "plan_within_limit": plan_within_limit, "plan": [p["course"] for p in plan], "has_next_step": bool(result.get("next_steps"))})
    direct = [r for r in rows if r["id"].startswith(("direct", "chain"))]
    abstain = [r for r in rows if r["id"].startswith("abstain")]
    claim_rows = [r for r in rows if not r["id"].startswith("abstain")]
    cited = [r for r in rows if r["citations"]]
    return {"cases": len(rows), "required_category_cases": 25,
            "decision_accuracy": sum(r["correct"] for r in rows) / len(rows),
            "eligibility_accuracy": sum(r["correct"] for r in direct) / len(direct),
            "abstention_accuracy": sum(r["correct"] for r in abstain) / len(abstain),
            "citation_coverage_all_responses": sum(bool(r["citations"]) for r in rows) / len(rows),
            "citation_coverage_catalog_claims": sum(bool(r["citations"]) for r in claim_rows) / len(claim_rows),
            "citation_verification_on_cited": sum(r["citation_ids_valid"] for r in cited) / len(cited),
            "chain_evidence_validity": sum(r["citation_ids_valid"] for r in rows if r["id"].startswith("chain")) / 5,
            "plan_credit_validity": sum(r["plan_within_limit"] for r in rows if r["id"].startswith("plan")) / 2,
            "next_step_coverage": sum(r["has_next_step"] for r in rows) / len(rows), "rows": rows}

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
