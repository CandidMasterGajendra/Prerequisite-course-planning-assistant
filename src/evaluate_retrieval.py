"""Small labeled retrieval benchmark; separate from eligibility evaluation."""

from __future__ import annotations

import json
from .retrieval import Retriever

CASES = [
    ("r01", "What do I need before CS 261 Data Structures?", "cs-cs261-0"),
    ("r02", "Can CS 162 be taken after engineering programming?", "cs-cs162-0"),
    ("r03", "What are the prerequisites for CS 374 Operating Systems?", "cs-cs374-0"),
    ("r04", "Does CS 362 require software engineering one?", "cs-cs362-0"),
    ("r05", "What grade is needed for CS 461 capstone project one?", "cs-cs461-0"),
    ("r06", "What comes before CS 462 capstone project two?", "cs-cs462-0"),
    ("r07", "Can MTH 231 discrete mathematics use an ALEKS score?", "mth-mth231-0"),
    ("r08", "What is the prerequisite for CS 340 databases?", "cs-cs340-0"),
    ("r09", "How many credits can an undergraduate register for in a term?", "regulations-7"),
    ("r10", "Which courses are required for the Computer Systems option?", "systems-option-0"),
    ("r11", "Which courses are in the computer science undergraduate major?", "cs-major-2"),
    ("r12", "What is the prerequisite for CS 225 discrete structures?", "cs-cs225-0"),
]


def evaluate(k: int = 5) -> dict:
    retriever = Retriever()
    rows = []
    for case_id, query, gold in CASES:
        hits = retriever.search(query, k)
        rank = next((i + 1 for i, hit in enumerate(hits) if hit["passage_id"] == gold), None)
        rows.append({"id": case_id, "gold": gold, "rank": rank, "hits": [h["passage_id"] for h in hits]})
    return {"cases": len(rows), "k": k, "recall_at_k": sum(r["rank"] is not None for r in rows) / len(rows), "mrr_at_k": sum(1 / r["rank"] for r in rows if r["rank"]) / len(rows), "rows": rows}


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
