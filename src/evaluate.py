"""Small deterministic evaluation harness matching the assessment categories."""

from __future__ import annotations

import json
from .course_planner import answer

TESTS = [
    *[(f"prereq-{i}", q, p, "eligibility") for i, (q, p) in enumerate([
        ("Can I take CS301?", {"completed_courses": ["CS201", "MATH120"]}),
        ("Can I take CS302?", {"completed_courses": ["CS201", "MATH120"]}),
        ("Can I take CS303?", {"completed_courses": ["CS202", "STAT201"]}),
        ("Can I take CS304?", {"completed_courses": ["CS201", "CS202"]}),
        ("Can I take DS301?", {"completed_courses": ["CS201", "STAT201"]}),
        ("Can I take DS302?", {"completed_courses": ["DS301"]}),
        ("Can I take MATH220?", {"completed_courses": ["MATH120"]}),
        ("Can I take CS401?", {"completed_courses": ["CS301", "CS302"]}),
        ("Can I take DS401?", {"completed_courses": ["DS301", "DS302"]}),
        ("Can I take CS305?", {"completed_courses": ["CS201", "MATH120"]}),
    ], 1)],
    *[(f"chain-{i}", q, p, "chain") for i, (q, p) in enumerate([
        ("Can I take CS401 after CS301 and CS302?", {"completed_courses": ["CS301", "CS302"]}),
        ("Can I take DS401 after DS301 and DS302?", {"completed_courses": ["DS301", "DS302"]}),
        ("Can I take AI410 after CS401?", {"completed_courses": ["CS401", "MATH220"]}),
        ("Can I take ML420 after DS301 and STAT201?", {"completed_courses": ["DS301", "STAT201"]}),
        ("Can I take CS305 with CS201?", {"completed_courses": ["CS201"]}),
    ], 1)],
    *[(f"program-{i}", q, p, "program") for i, (q, p) in enumerate([
        ("What courses should I plan next term for Data Science?", {"completed_courses": ["CS201", "STAT201"], "target_program": "Data Science", "target_term": "Fall", "max_credits": 9}),
        ("Plan my next term for Computer Science.", {"completed_courses": ["CS201", "MATH120"], "target_program": "Computer Science", "target_term": "Fall", "max_credits": 12}),
        ("Which electives count for the DS major?", {"target_program": "Data Science", "target_term": "Fall", "max_credits": 9}),
        ("Schedule courses for my major.", {}),
        ("What are the residency requirements?", {"target_program": "Computer Science", "target_term": "Fall", "max_credits": 12}),
    ], 1)],
    *[(f"abstain-{i}", q, {}, "abstention") for i, q in enumerate([
        "Who will teach CS301 next semester?", "Is CS301 offered online?", "What room is CS301 in?", "Can my advisor waive this prerequisite?", "What is the textbook for CS301?",
    ], 1)],
]


def main() -> None:
    rows = []
    for name, question, profile, category in TESTS:
        result = answer(question, profile)
        rows.append({"id": name, "category": category, "question": question, "decision": result["decision"], "citation_count": len(result.get("citations", [])), "output": result})
    cited = sum(row["citation_count"] > 0 for row in rows)
    print(json.dumps({"total": len(rows), "citation_coverage": round(cited / len(rows), 3), "results": rows}, indent=2))


if __name__ == "__main__":
    main()

