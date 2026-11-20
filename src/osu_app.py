"""Grounded CLI for the reviewed Oregon State course-planning pilot."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .evidence import (cite, course_evidence as course_citations, course_passage, passage_containing,
                       program_passage, verify_course_result, verify_plan)
from .osu_rules import (MAJOR_CORE, SYSTEMS_REQUIRED, RULES, SYSTEMS_ELECTIVES,
                        check, course_leaves)

CORPUS = Path(__file__).resolve().parents[1] / "data" / "osu_2026_27.json"


def _program_response(question: str) -> dict[str, Any] | None:
    q = question.lower()
    policy_facts = [
        (bool(re.search(r"\b(maximum|max|credit limit|how many credits)\b", q)) and
         bool(re.search(r"\b(term|register|registration|load)\b", q)),
         "The normal undergraduate registration maximum is 19 credits per term; extensions require the conditions or approvals described in AR 7.",
         "regulations", "maximum is 19"),
        (bool(re.search(r"\b(repeat|repeated|repeating|retake)\b", q)),
         "For a repeated OSU course, every attempt remains on the academic record, but ordinarily only the second attempt counts toward institutional credits, requirements, and GPA.",
         "regulations", "only the second attempt will count"),
        ("transfer" in q and ("gpa" in q or "grade" in q),
         "Transfer credits and grades are not used in calculating the OSU GPA.",
         "regulations", "Transfer credits and grades are not used"),
        ("residency" in q or "academic residence" in q,
         "The baccalaureate academic-residence rule requires at least 45 of the last 75 credits, or 150 total credits, in OSU academic residence; at least 15 upper-division credits used for that rule must be taken in each major.",
         "regulations", "A minimum of 45 of the last 75 credits"),
    ]
    for applies, answer, doc_id, needle in policy_facts:
        if applies:
            row = passage_containing(doc_id, needle)
            if not row:
                return None
            return {"answer": answer, "decision": "answered", "why": [answer],
                    "citations": [cite(row)], "clarifying_questions": [],
                    "assumptions_not_in_catalog": [],
                    "next_steps": ["Apply this policy to the student's documented academic record, or ask the Registrar when an exception may apply."]}
    facts = [
        (("total credits" in q or "credits to graduate" in q) and "option" not in q,
         "The scoped CS major requires 180 total credits.", "cs-major", "Total Credits 180"),
        ("option" in q and "total" in q and "credit" in q,
         "The Computer Systems option totals 80 credits.", "systems-option", "Total Credits 80"),
        ("restricted elective" in q and ("how many" in q or "credit" in q),
         "The Computer Systems option requires 8 restricted-elective credits.", "systems-option", "Restricted Electives 1, 2 8"),
        ("approved elective" in q and ("how many" in q or "credit" in q),
         "The Computer Systems option requires 7 approved-elective credits.", "systems-option", "Approved Electives 3 7"),
        ("a-f" in q and "restricted elective" in q,
         "Restricted electives must use A-F letter grading.", "systems-option", "A-F letter grade"),
        (bool(re.search(r"\bCS\s*40[2345789]\b", question.upper())) and "restricted elective" in q,
         "That course number is excluded from the option's restricted electives.", "systems-option", "402, 403, 404, 405, 407, 408, 409, 410"),
        (("outside" in q or "advisor approval" in q) and "elective" in q,
         "Approved electives consist of coursework outside CS and ECE, should align with the student's interests, and require advisor approval.",
         "systems-option", "Approved electives consists of coursework outside of CS and ECE"),
    ]
    for applies, answer, doc_id, needle in facts:
        if applies:
            row = passage_containing(doc_id, needle)
            if not row:
                return None
            return {"answer": answer, "decision": "answered", "why": [answer],
                    "citations": [cite(row)], "clarifying_questions": [],
                    "assumptions_not_in_catalog": [],
                    "next_steps": ["Use this rule when checking the remaining program requirements."]}
    if "corequisite" in q or "co-requisite" in q:
        row = passage_containing("course-guide", "Corequisites – Courses you must enroll in at the same time")
        if row:
            answer = "A corequisite must be taken at the same time as the associated course."
            return {"answer": answer, "decision": "answered", "why": [answer],
                    "citations": [cite(row)], "clarifying_questions": [],
                    "assumptions_not_in_catalog": [],
                    "next_steps": ["Name the course if you want its specific corequisite checked."]}
    if "concurrent" in q and ("prerequisite" in q or "same time" in q):
        row = passage_containing("course-guide", "Concurrency will be indicated")
        if row:
            answer = "A prerequisite may be taken concurrently only when the course description explicitly allows it."
            return {"answer": answer, "decision": "answered", "why": [answer],
                    "citations": [cite(row)], "clarifying_questions": [],
                    "assumptions_not_in_catalog": [],
                    "next_steps": ["Check the target course description for an explicit concurrent-enrollment statement."]}
    return None


def _resolve_course(question: str, corpus: dict[str, Any]) -> str | None:
    match = re.search(r"\b(?:CS|MTH|ECE|ENGR|ST)\s*\d{3}[A-Z]?\b", question.upper())
    if match:
        return re.sub(r"\s+", "", match.group())
    aliases = {"database systems": "CS340", "introduction to databases": "CS340",
               "data structures": "CS261", "software engineering i": "CS361",
               "software engineering ii": "CS362", "operating systems i": "CS374"}
    q = question.lower()
    for name, code in aliases.items():
        if name in q:
            return code
    for doc in corpus["documents"]:
        if not doc.get("course_code"):
            continue
        match = re.match(r"[A-Z]+\s+\d+[A-Z]?,\s*(.*?),\s*\d+ Credits", doc["heading"])
        if match and match.group(1).lower() in q:
            return doc["course_code"]
    return None


def respond(question: str, profile: dict[str, Any], corpus: dict[str, Any] | None = None,
            course_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    corpus = corpus or json.loads(CORPUS.read_text())
    q = question.lower()
    output: dict[str, Any] = {"answer": "", "decision": "needs_more_info", "why": [], "citations": [], "clarifying_questions": [], "assumptions_not_in_catalog": [], "next_steps": []}
    if re.search(r"\b(teach|teaches|teaching|instructor|professor|room|textbook|offered|available|online|schedule of classes)\b", q):
        output["answer"] = "The provided catalog does not establish that fact. Check the current Schedule of Classes or department."
        output["assumptions_not_in_catalog"] = ["No course offering, instructor, room, or textbook is inferred from catalog descriptions."]
        output["next_steps"] = ["Check the current Schedule of Classes or contact the department."]
        return output
    program = _program_response(question)
    if program:
        return program
    code = _resolve_course(question, corpus)
    wants_plan = bool(re.search(r"\b(plan|recommend|next term|courses should|schedule)\b", q))
    if wants_plan:
        missing = [name for name in ("catalog_year", "target_program", "target_term", "max_credits", "completed_courses") if name not in profile]
        if missing:
            output["answer"] = "I need more information before planning."
            output["clarifying_questions"] = [f"What is your {name.replace('_', ' ')}?" for name in missing[:5]]
            output["next_steps"] = ["Provide the requested profile fields, then run the planner again."]
            return output
        if profile["catalog_year"] != "2026-2027" or profile["target_program"] != "CS Computer Systems":
            output["answer"] = "This pilot supports only the 2026–27 CS Computer Systems program."
            output["next_steps"] = ["Use the supported catalog year and program, or add sources and rules for the requested program."]
            return output
        if not profile.get("transcript_complete", False):
            output["answer"] = "Please confirm that your completed-course list is complete, including grades and transfer approvals."
            output["clarifying_questions"] = ["Is your transcript complete, with grades for each completed prerequisite?"]
            output["next_steps"] = ["Confirm the transcript and transfer approvals before requesting a plan."]
            return output
        limit = profile["max_credits"]
        if not isinstance(limit, int) or limit <= 0 or limit > 19:
            output["answer"] = "The requested credit limit needs review against the undergraduate load policy."
            output["clarifying_questions"] = ["What credit limit at or below 19 should I use, or do you have an approved overload?"]
            output["next_steps"] = ["Choose a limit at or below 19 credits or provide evidence of an approved overload."]
            policy = passage_containing("regulations", "maximum is 19")
            if policy:
                output["citations"] = [cite(policy)]
                output["why"] = ["AR 7 sets the normal undergraduate maximum at 19 credits and defines extension conditions."]
            return output
        completed = profile["completed_courses"]
        required = MAJOR_CORE | SYSTEMS_REQUIRED
        candidates = []
        for code in sorted(required & RULES.keys()):
            if code in completed:
                continue
            result = check(code, profile, corpus)
            if result["decision"] == "eligible":
                passage = course_passage(code)
                program = program_passage(code)
                if not passage or not program:
                    continue
                doc = next(d for d in corpus["documents"] if d.get("course_code") == code)
                credits_match = re.search(r"(\d+) Credits", doc["heading"])
                if credits_match:
                    candidates.append((code, int(credits_match.group(1)), result, [cite(passage), cite(program)]))
        plan, used = [], 0
        for code, credits, result, citations in candidates:
            if used + credits <= limit:
                plan.append({"course": code, "credits": credits, "why": "Required in the scoped program and prerequisite check passed", "evidence_trace": result["evidence_trace"], "citations": citations})
                used += credits
        if not plan or not verify_plan(plan, limit):
            output["answer"] = "I cannot verify a complete plan from the reviewed catalog evidence."
            output["clarifying_questions"] = ["Would you like an advisor to review the remaining program requirements or course options?"]
            output["next_steps"] = ["Ask an advisor to review courses that are unresolved or outside the encoded rule set."]
            return output
        output.update({"answer": "Candidate next-term plan; confirm actual offering and advisor approval.", "decision": "plan_proposed", "plan": plan, "why": [f"{used} of {limit} requested credits selected from reviewed required courses."], "citations": list({c["passage_id"]: c for item in plan for c in item["citations"]}.values()), "assumptions_not_in_catalog": ["Term offering, seat availability, timetable conflicts, and transfer approvals are not verified."], "next_steps": ["Check the current Schedule of Classes and review the candidate plan with an advisor."]})
        return output
    if code:
        result = check(code, profile, corpus)
        passage = (course_evidence if course_evidence and course_evidence.get("course_code") == code
                   else course_passage(code))
        related = course_leaves(RULES[code]) if code in RULES else set()
        citations = course_citations(code, related)
        if not passage or not verify_course_result(code, citations):
            output["answer"] = f"I cannot verify catalog evidence for {code}."
            return output
        next_step = ("You may include this course in a candidate plan, subject to actual offering and advisor review."
                     if result["decision"] == "eligible" else
                     "Complete a missing prerequisite with the required grade, or ask an advisor to review an unresolved rule."
                     if result["decision"] == "not_eligible" else
                     "Provide the missing grade, placement result, or authoritative rule interpretation.")
        output.update({"answer": f"{code}: {result['decision'].replace('_', ' ')}.", "decision": result["decision"], "why": result.get("evidence_trace", [result.get("reason", "")]), "citations": citations, "retrieved_evidence": passage["text"], "next_steps": [next_step]})
        if result["decision"] == "needs_more_info":
            output["clarifying_questions"] = ["Can you provide the missing grades, placement result, or official rule interpretation noted above?"]
        return output
    output["answer"] = "Please name a course or request a plan within the supported CS Computer Systems scope."
    output["clarifying_questions"] = ["Which course or program requirement do you mean?"]
    output["next_steps"] = ["Provide a course code, course name, or a specific program-requirement question."]
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--profile", type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text()) if args.profile else {}
    print(json.dumps(respond(args.question, profile), indent=2))


if __name__ == "__main__":
    main()
