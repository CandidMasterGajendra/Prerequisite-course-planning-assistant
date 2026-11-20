"""Manually reviewed, source-linked rules for a bounded OSU CS pilot."""

from __future__ import annotations

from typing import Any

def course(code: str, grade: str = "C", concurrent: bool = False) -> dict[str, Any]:
    return {"course": code, "min_grade": grade, "concurrent": concurrent}

def any_of(*children: Any) -> dict[str, Any]:
    return {"any_of": list(children)}

def all_of(*children: Any) -> dict[str, Any]:
    return {"all_of": list(children)}

def placement(kind: str, score: int) -> dict[str, Any]:
    return {"placement": kind, "min_score": score}


def course_leaves(expr: Any) -> set[str]:
    if "course" in expr:
        return {expr["course"]}
    return set().union(*(course_leaves(child) for child in expr.get("all_of", expr.get("any_of", []))))


RULES: dict[str, Any] = {
    "CS161": any_of(course("MTH112", concurrent=True), course("MTH112Z", concurrent=True), placement("math_test", 33), placement("aleks", 61)),
    "CS162": any_of(*(course(c) for c in ["CS161", "ENGR103", "ENGR103H", "DS231"])),
    "CS225": any_of(course("MTH111"), course("MTH111Z"), course("MTH112", concurrent=True), course("MTH112Z", concurrent=True), placement("math_test", 24), placement("aleks", 61)),
    "CS261": all_of(any_of(*(course(c) for c in ["CS162", "CS162H", "CS165"])), any_of(*(course(c) for c in ["CS225", "MTH231", "MTH231H"]))),
    "CS271": any_of(*(course(c) for c in ["CS151", "CS161", "CS165", "ENGR103", "ENGR103H"])),
    "CS274": any_of(course("CS162"), course("CS162H")),
    "CS290": any_of(*(course(c) for c in ["CS162", "CS162H", "CS165"])),
    "CS340": any_of(course("CS261"), course("CS261H")),
    "CS361": any_of(course("CS261"), course("CS261H")),
    "CS362": any_of(course("CS261"), course("CS261H")),
    "CS374": all_of(any_of(course("CS261"), course("CS261H")), course("CS274"), any_of(course("CS271"), course("ECE204"), course("ECE271"))),
    "CS461": all_of(any_of(course("CS325"), course("CS325H")), course("CS361"), any_of(course("CS362"), course("CS362H"))),
    "CS462": all_of(any_of(course("CS362"), course("CS362H")), any_of(course("CS461"), course("CS461H"))),
    "CS463": all_of(any_of(course("CS462"), course("CS462H")), course("ENGR102")),
    "CS162H": any_of(*(course(c) for c in ["CS161", "ENGR103", "ENGR103H", "DS231"])),
    "CS261H": all_of(any_of(*(course(c) for c in ["CS162", "CS162H", "CS165"])), any_of(*(course(c) for c in ["CS225", "MTH231", "MTH231H"]))),
    "CS362H": any_of(course("CS261"), course("CS261H")),
    "CS370": any_of(course("CS344", concurrent=True), course("CS374", concurrent=True)),
    "CS372": all_of(any_of(course("CS261"), course("CS261H")), any_of(course("ECE271"), course("CS271"))),
    "CS461H": all_of(any_of(course("CS325"), course("CS325H")), course("CS361"), any_of(course("CS362"), course("CS362H"))),
    "CS462H": all_of(any_of(course("CS362"), course("CS362H")), any_of(course("CS461"), course("CS461H"))),
    "CS463H": all_of(any_of(course("CS462"), course("CS462H")), course("ENGR102")),
    "CS472": any_of(course("ECE370"), course("ECE370H"), course("ECE375")),
    "CS474": all_of(any_of(course("CS344"), course("CS374")), any_of(course("CS271"), course("ECE375"), course("ECE370"))),
    "CS480": all_of(course("CS381"), any_of(course("CS321"), course("CS321H")), any_of(course("CS344"), course("CS374"))),
    "CS391": all_of(),
    "ENGR330": all_of(),
}

# CS325 grouping is ambiguous in the displayed catalog text. It is deliberately
# excluded from automated decisions pending authoritative interpretation.
UNRESOLVED = {code: "The AND/OR grouping in the prerequisite text is ambiguous." for code in ("CS321", "CS325", "CS325H", "CS381", "CS440")}

MAJOR_CORE = {"ENGR102", "ENGR103", "MTH231", "MTH251Z", "MTH252Z", "CS162", "CS261", "CS325", "CS340", "CS361", "CS362", "ENGR330"}
MAJOR_ALTERNATIVES = {"ethics": {"CS391", "PHL330"}, "transitions": {"ENGR110+ENGR115", "ENGR310"}, "communication": {"COMM114", "COMM111Z"}, "advanced_writing": {"WR314", "WR323"}}
SYSTEMS_REQUIRED = {"AI230", "CS274", "CS321", "CS370", "CS372", "CS374", "CS381", "CS461", "CS462", "CS463", "CS472", "CS474", "CS480", "ECE204", "ECE370", "MTH254", "MTH264", "MTH265", "ST314"}
SYSTEMS_ELECTIVES = {"restricted_credits": 8, "approved_credits": 7, "restricted_level": {300, 400}, "restricted_grade_mode": "A-F", "advisor_approval_for_outside_engineering": True, "approved_electives_outside": {"CS", "ECE"}, "cs401_cs406_combined_credit_cap": 6, "excluded_restricted_numbers": {402, 403, 404, 405, 407, 408, 409, 410}}
GRADE_RANK = {"F": 0, "D-": 1, "D": 2, "D+": 3, "C-": 4, "C": 5, "C+": 6, "B-": 7, "B": 8, "B+": 9, "A-": 10, "A": 11, "A+": 12}


def evaluate(expr: Any, profile: dict[str, Any]) -> tuple[str, list[str]]:
    """Three-valued logic: satisfied, unsatisfied, unknown, with trace."""
    if "all_of" in expr:
        children = [evaluate(x, profile) for x in expr["all_of"]]
        state = "unsatisfied" if any(s == "unsatisfied" for s, _ in children) else "unknown" if any(s == "unknown" for s, _ in children) else "satisfied"
        return state, [item for _, trace in children for item in trace]
    if "any_of" in expr:
        children = [evaluate(x, profile) for x in expr["any_of"]]
        state = "satisfied" if any(s == "satisfied" for s, _ in children) else "unknown" if any(s == "unknown" for s, _ in children) else "unsatisfied"
        return state, [item for _, trace in children for item in trace]
    if "placement" in expr:
        score = (profile.get("placement_scores") or {}).get(expr["placement"])
        if score is None:
            return "unknown", [f"{expr['placement']} score not provided"]
        ok = score >= expr["min_score"]
        return ("satisfied" if ok else "unsatisfied"), [f"{expr['placement']} score {score}; minimum {expr['min_score']}"]
    code = expr["course"]
    completed = profile.get("completed_courses") or {}
    if isinstance(completed, list):
        completed = {c: None for c in completed}
    if code in completed:
        grade = completed[code]
        if grade is None:
            return "unknown", [f"{code}: grade missing"]
        if grade not in GRADE_RANK:
            return "unknown", [f"{code}: unrecognized grade {grade}"]
        ok = GRADE_RANK[grade] >= GRADE_RANK[expr["min_grade"]]
        return ("satisfied" if ok else "unsatisfied"), [f"{code}: {grade}; minimum {expr['min_grade']}"]
    if expr["concurrent"] and code in (profile.get("in_progress_courses") or []):
        return "unknown", [f"{code} is concurrent; final grade remains unknown"]
    if not profile.get("transcript_complete", False):
        return "unknown", [f"{code}: completion status not confirmed"]
    return "unsatisfied", [f"{code}: not completed"]


def check(code: str, profile: dict[str, Any], corpus: dict[str, Any]) -> dict[str, Any]:
    document = next((d for d in corpus["documents"] if d.get("course_code") == code), None)
    if not document:
        return {"course": code, "decision": "needs_more_info", "reason": "Course not in reviewed corpus", "citations": []}
    citation = {"url": document["url"], "section": document["heading"], "passage_id": document["doc_id"]}
    if code.endswith("H") and not profile.get("honors_eligibility_confirmed"):
        return {"course": code, "decision": "needs_more_info", "reason": "Honors eligibility has not been confirmed", "citations": [citation]}
    if code in UNRESOLVED:
        return {"course": code, "decision": "needs_more_info", "reason": UNRESOLVED[code], "citations": [citation]}
    if code not in RULES:
        return {"course": code, "decision": "needs_more_info", "reason": "Prerequisite rule has not been manually reviewed", "citations": [citation]}
    state, trace = evaluate(RULES[code], profile)
    return {"course": code, "decision": {"satisfied": "eligible", "unsatisfied": "not_eligible", "unknown": "needs_more_info"}[state], "evidence_trace": trace, "citations": [citation]}
