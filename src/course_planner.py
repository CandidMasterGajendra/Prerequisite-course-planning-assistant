"""Citation-aware course prerequisite and planning assistant.

The demo is intentionally deterministic and local. Replace the retriever with
embeddings/vector search and add an LLM response layer only after preserving
the evidence and abstention checks in this module.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "demo_catalog.json"


def load_catalog() -> list[dict[str, Any]]:
    return json.loads(CATALOG_PATH.read_text())


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class Retriever:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self.docs = docs
        self.tokens = [tokenize(d["text"]) for d in docs]
        df = Counter(t for row in self.tokens for t in set(row))
        self.idf = {t: math.log((1 + len(docs)) / (1 + n)) + 1 for t, n in df.items()}

    def search(self, query: str, k: int = 6) -> list[dict[str, Any]]:
        q = Counter(tokenize(query))
        scored = []
        for doc, row in zip(self.docs, self.tokens):
            tf = Counter(row)
            score = sum((1 + math.log(freq)) * self.idf.get(term, 1) for term, freq in q.items() if term in tf)
            score /= max(1.0, math.sqrt(len(row)))
            if score:
                scored.append((score, doc))
        return [doc | {"score": round(score, 4)} for score, doc in sorted(scored, reverse=True, key=lambda x: x[0])[:k]]


def citation(doc: dict[str, Any]) -> dict[str, str]:
    return {"title": doc["title"], "source_url": doc["source_url"], "section": doc["section"], "chunk_id": doc["doc_id"]}


def course_map(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {d["course_code"]: d for d in docs if d.get("course_code")}


def missing_profile(profile: dict[str, Any] | None, needs_plan: bool) -> list[str]:
    if not needs_plan:
        return []
    profile = profile or {}
    required = []
    if not profile.get("completed_courses"):
        required.append("completed courses, including grades if available")
    if not profile.get("target_program"):
        required.append("target program or major")
    if not profile.get("target_term"):
        required.append("target term")
    if not profile.get("max_credits"):
        required.append("maximum credits or courses")
    return required


def extract_course_codes(text: str) -> list[str]:
    return re.findall(r"\b[A-Z]{2,5}\d{3}\b", text.upper())


def eligibility(target: str, completed: set[str], courses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    doc = courses.get(target)
    if not doc:
        return {"course": target, "decision": "Need more info", "reasons": ["Course is not in the catalog corpus."], "citations": []}
    prereqs = doc.get("prerequisites", [])
    satisfied = []
    missing = []
    for group in prereqs:
        options = group if isinstance(group, list) else [group]
        if any(option in completed for option in options):
            satisfied.append(options)
        else:
            missing.append(options)
    decision = "Eligible" if not missing else "Not eligible"
    return {"course": target, "decision": decision, "satisfied": satisfied, "missing": missing, "citations": [citation(doc)]}


def answer(question: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    docs = load_catalog()
    retriever = Retriever(docs)
    hits = retriever.search(question)
    codes = extract_course_codes(question)
    plan_intent = bool(re.search(r"\b(plan|next term|schedule|enroll|courses should)\b", question.lower()))
    unsupported_intent = bool(re.search(r"\b(who|teach|instructor|room|textbook|online|offered|delivery|available|availability)\b", question.lower()))
    missing = missing_profile(profile, plan_intent)
    if plan_intent and missing:
        return {
            "answer": "I need a few details before I can produce a safe course plan.",
            "decision": "Need more info",
            "clarifying_questions": [f"What is your {item}?" for item in missing[:5]],
            "citations": [],
            "assumptions": [],
        }
    if not hits:
        return {
            "answer": "I don't have that information in the provided catalog/policies.",
            "decision": "Need more info",
            "clarifying_questions": [],
            "citations": [],
            "assumptions": ["Check the current department catalog, schedule, or academic advisor."],
        }
    courses = course_map(docs)
    if unsupported_intent and not plan_intent:
        return {
            "answer": "I don't have that information in the provided catalog/policies.",
            "decision": "Need more info",
            "clarifying_questions": [],
            "citations": [citation(h) for h in hits if h.get("section") in {"Academic Policies", "Program Requirements"}],
            "assumptions": ["Check the department schedule or academic advisor for current offering details."],
        }
    if codes:
        # In "Can I take CS401 after CS301 and CS302?", the first code is
        # the requested target; later codes are evidence supplied by the user.
        target = codes[0]
        result = eligibility(target, set((profile or {}).get("completed_courses", [])), courses)
        if result["decision"] == "Eligible":
            text = f"{target} appears eligible based on the completed courses provided."
        else:
            text = f"{target} is not currently eligible because at least one prerequisite group is unsatisfied."
        return {"answer": text, "decision": result["decision"], "evidence": result, "clarifying_questions": [], "citations": result["citations"], "assumptions": []}
    if plan_intent:
        completed = set((profile or {}).get("completed_courses", []))
        max_credits = int((profile or {}).get("max_credits", 12))
        candidates = []
        for code, doc in courses.items():
            if code in completed or doc.get("credits", 3) > max_credits:
                continue
            check = eligibility(code, completed, courses)
            if check["decision"] == "Eligible":
                candidates.append((code, doc, check))
        chosen, credits = [], 0
        for code, doc, check in candidates:
            if credits + doc.get("credits", 3) <= max_credits:
                chosen.append({"course": code, "title": doc["title"], "credits": doc.get("credits", 3), "why": "Prerequisites are satisfied and the course fits the credit limit.", "citations": check["citations"]})
                credits += doc.get("credits", 3)
        return {"answer": "Suggested next-term courses are listed below.", "decision": "Plan generated", "plan": chosen, "clarifying_questions": [], "citations": [citation(h) for h in hits], "assumptions": ["Course availability by semester is not stated in the demo catalog; verify the schedule before enrolling."]}
    return {"answer": "The retrieved catalog evidence does not support a confident answer to this question.", "decision": "Need more info", "clarifying_questions": ["Which course, program, and catalog year should I use?"], "citations": [citation(h) for h in hits], "assumptions": []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--profile", type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text()) if args.profile else None
    print(json.dumps(answer(args.question, profile), indent=2))


if __name__ == "__main__":
    main()

