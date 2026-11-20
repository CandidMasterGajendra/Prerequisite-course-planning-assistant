"""Run live GPT wording evaluation; preserve candidates for manual support review.

The cases are the existing development set, not an independent benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .config import load_local_env
from .evaluate_osu import CASES
from .evidence import retriever
from .workflow import run

ROOT = Path(__file__).resolve().parents[1]


def summarize(rows: list[dict]) -> dict:
    attempted = [r for r in rows if "write" in r["workflow_trace"]]
    return {
        "cases_completed": len(rows),
        "decision_matches_existing_labels": sum(r["decision_match"] for r in rows),
        "citation_scope_passed": sum(r["citation_scope_passed"] for r in rows),
        "model_calls_attempted": len(attempted),
        "accepted_model_drafts": sum(r["generation_mode"] == "gpt" for r in rows),
        "model_errors": sum(r["generation_mode"] == "template_after_generation_error" for r in rows),
        "drafts_rejected_by_verifier": sum(r["generation_mode"] == "template_after_verification" for r in rows),
        "manual_support_reviews_pending": sum(r["manual_review"]["supported"] is None for r in attempted),
        "generation_modes": dict(Counter(r["generation_mode"] for r in rows)),
    }


def evaluate(out: Path, model: str, selected: set[str] | None = None) -> dict:
    load_local_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is unset; live GPT evaluation was not run")
    cases = [row for row in CASES if selected is None or row[0] in selected]
    if not cases:
        raise ValueError("No evaluation cases selected")
    by_id = {row["passage_id"]: row for row in retriever().rows}
    report = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "completed": False,
        "model": model,
        "dataset": "27-case development set (25 required-category + 2 plan); labels are not independent",
        "corpus_sha256": hashlib.sha256((ROOT / "data/osu_2026_27.json").read_bytes()).hexdigest(),
        "cases_requested": len(cases),
        "summary": {},
        "rows": [],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    for case_id, question, profile, expected in cases:
        result = run(question, profile, model=model)
        ids = {c["passage_id"] for c in result.get("citations", [])}
        row = {
            "id": case_id,
            "question": question,
            "profile": profile,
            "expected_decision": expected,
            "actual_decision": result["decision"],
            "decision_match": result["decision"] == expected,
            "answer": result["answer"],
            "why": result.get("why", []),
            "plan": result.get("plan", []),
            "citations": result.get("citations", []),
            "cited_passages": [{"passage_id": i, "text": by_id[i]["text"]} for i in sorted(ids) if i in by_id],
            "generation_mode": result["generation_mode"],
            "generation_audit": result.get("generation_audit"),
            "workflow_trace": result["workflow_trace"],
            "citation_scope_passed": result["verification"]["citation_metadata_and_scope"],
            "draft_rejection_reasons": result["verification"]["draft_rejection_reasons"],
            "assistant_audit": {"supported": None, "notes": ""},
            "manual_review": {"supported": None, "issue_category": None, "notes": ""},
        }
        report["rows"].append(row)
        report["summary"] = summarize(report["rows"])
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"{case_id}: {row['generation_mode']}, decision={row['actual_decision']}", flush=True)
    report["completed"] = True
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    load_local_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-5-mini"))
    parser.add_argument("--case", action="append", help="Run only a named case; repeat as needed")
    args = parser.parse_args()
    report = evaluate(args.out, args.model, set(args.case) if args.case else None)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
