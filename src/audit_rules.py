"""Audit source provenance and course-code coverage of reviewed rules."""

from __future__ import annotations

import json
import re
from .osu_app import CORPUS
from .osu_rules import MAJOR_ALTERNATIVES, MAJOR_CORE, RULES, SYSTEMS_ELECTIVES, SYSTEMS_REQUIRED, UNRESOLVED

COURSE = re.compile(r"\b[A-Z]{2,5}\s*\d{3}[A-Z]?\b")


def codes(text: str) -> set[str]:
    return {re.sub(r"\s+", "", s) for s in COURSE.findall(text)}


def leaves(expr: dict) -> set[str]:
    if "course" in expr:
        return {expr["course"]}
    return set().union(*(leaves(child) for child in expr.get("all_of", expr.get("any_of", []))))


def audit() -> dict:
    corpus = json.loads(CORPUS.read_text())
    docs = {d["course_code"]: d for d in corpus["documents"] if d.get("course_code")}
    sources = corpus["sources"]
    issues = []
    for code, expr in RULES.items():
        if code not in docs:
            issues.append(f"{code}: source document missing")
            continue
        text = docs[code]["text"]
        match = re.search(r"Prerequisite:\s*(.*?)(?= Equivalent to:| Corequisites:| Recommended:| Available via| Attributes:|$)", text)
        expected = codes(match.group(1)) if match else set()
        actual = leaves(expr)
        if expected != actual:
            issues.append(f"{code}: source references {sorted(expected)}, rule references {sorted(actual)}")
    for code in UNRESOLVED:
        if code not in docs:
            issues.append(f"{code}: unresolved source missing")
    program_docs = {d["doc_id"]: d for d in corpus["documents"] if d["kind"] == "program"}
    for doc_id, required in (("cs-major", MAJOR_CORE), ("systems-option", SYSTEMS_REQUIRED)):
        if doc_id not in program_docs:
            issues.append(f"{doc_id}: program source missing")
        else:
            absent = required - codes(program_docs[doc_id]["text"])
            if absent:
                issues.append(f"{doc_id}: required codes absent from source {sorted(absent)}")
    major_text = program_docs["cs-major"]["text"]
    for category, alternatives in MAJOR_ALTERNATIVES.items():
        for alternative in alternatives:
            for code in alternative.split("+"):
                if code not in codes(major_text):
                    issues.append(f"major {category}: {code} absent from source")
    option_text = program_docs["systems-option"]["text"]
    for snippet in (f"Restricted Electives 1, 2 {SYSTEMS_ELECTIVES['restricted_credits']}", f"Approved Electives 3 {SYSTEMS_ELECTIVES['approved_credits']}", "A-F letter grade", "advisor approval"):
        if snippet not in option_text:
            issues.append(f"systems option: policy evidence absent for {snippet}")
    urls = [s["url"] for s in sources]
    if len(urls) != len(set(urls)):
        issues.append("Duplicate source URLs")
    for doc in corpus["documents"]:
        if doc["source_id"] not in {s["source_id"] for s in sources}:
            issues.append(f"{doc['doc_id']}: source ID missing")
    return {"source_urls": len(urls), "course_descriptions": len(docs), "reviewed_rules": len(RULES), "unresolved_rules": len(UNRESOLVED), "issues": issues}


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
