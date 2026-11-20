"""Retrieve and verify the passage used for each course or program claim."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from .retrieval import Retriever


def normalized_codes(text: str) -> set[str]:
    return {re.sub(r"\s+", "", code) for code in re.findall(r"\b(?:CS|MTH|ECE|ENGR|ST)\s*\d{3}[A-Z]?\b", text.upper())}


@lru_cache(maxsize=1)
def retriever() -> Retriever:
    return Retriever()


def cite(row: dict[str, Any]) -> dict[str, str]:
    return {"url": row["url"], "section": row["section"], "passage_id": row["passage_id"]}


def passage_by_id(passage_id: str) -> dict[str, Any] | None:
    return next((row for row in retriever().rows if row["passage_id"] == passage_id), None)


def passage_containing(doc_id: str, text: str) -> dict[str, Any] | None:
    needle = text.lower()
    return next((row for row in retriever().rows
                 if row["doc_id"] == doc_id and needle in row["text"].lower()), None)


def course_passage(code: str) -> dict[str, Any] | None:
    hits = retriever().search(f"{code} course description prerequisites", k=8)
    return next((hit for hit in hits if hit.get("course_code") == code), None)


def program_passage(code: str) -> dict[str, Any] | None:
    """Find a program passage that actually names the proposed course."""
    hits = retriever().search(f"CS Computer Systems option required courses {code}", k=30)
    return next((hit for hit in hits if hit["doc_id"] in {"cs-major", "systems-option"} and code in normalized_codes(hit["text"])), None)


def course_evidence(code: str, related_codes: set[str] | None = None) -> list[dict[str, str]]:
    """Cite the target rule plus available course pages used in a chain."""
    rows = []
    target = course_passage(code)
    if target:
        rows.append(target)
    for related in sorted((related_codes or set()) - {code}):
        row = course_passage(related)
        if row:
            rows.append(row)
    return [cite(row) for row in {row["passage_id"]: row for row in rows}.values()]


def verify_citations(citations: list[dict[str, str]]) -> bool:
    by_id = {row["passage_id"]: row for row in retriever().rows}
    return all(
        (row := by_id.get(c.get("passage_id"))) is not None
        and row["url"] == c.get("url")
        and row["section"] == c.get("section")
        for c in citations
    )


def verify_course_result(code: str, citations: list[dict[str, str]]) -> bool:
    by_id = {row["passage_id"]: row for row in retriever().rows}
    return verify_citations(citations) and any(by_id[c["passage_id"]].get("course_code") == code for c in citations)


def verify_chain_result(code: str, citations: list[dict[str, str]], minimum_course_pages: int = 2) -> bool:
    by_id = {row["passage_id"]: row for row in retriever().rows}
    course_pages = {by_id[c["passage_id"]].get("course_code") for c in citations
                    if c.get("passage_id") in by_id and by_id[c["passage_id"]].get("course_code")}
    return verify_course_result(code, citations) and len(course_pages) >= minimum_course_pages


def verify_plan(plan: list[dict[str, Any]], limit: int) -> bool:
    if sum(item["credits"] for item in plan) > limit:
        return False
    for item in plan:
        by_id = {row["passage_id"]: row for row in retriever().rows}
        refs = item["citations"]
        if not verify_citations(refs):
            return False
        if not any(by_id[c["passage_id"]].get("course_code") == item["course"] for c in refs):
            return False
        if not any(by_id[c["passage_id"]]["doc_id"] in {"cs-major", "systems-option"} and item["course"] in normalized_codes(by_id[c["passage_id"]]["text"]) for c in refs):
            return False
    return True
