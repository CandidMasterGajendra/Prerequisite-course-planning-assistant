"""Write reproducible assessment metrics and the three required transcripts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .evaluate_osu import CASES, evaluate
from .osu_app import respond


def render_list(items: list[str], empty: str = "None") -> str:
    return "\n".join(f"- {item}" for item in items) if items else f"- {empty}"


def render_transcript(title: str, question: str, profile: dict[str, Any], result: dict[str, Any]) -> str:
    plan = ""
    if result.get("plan"):
        plan = "\n" + "\n".join(
            f"- {item['course']} ({item['credits']} credits): {item['why']}"
            for item in result["plan"]
        )
    citations = [f"[{c['section']}]({c['url']}) (`{c['passage_id']}`)" for c in result.get("citations", [])]
    return f"""## {title}

**Student question:** {question}

**Profile:** `{json.dumps(profile, sort_keys=True)}`

**Answer / Plan:** {result['answer']}{plan}

**Why:**

{render_list(result.get('why', []))}

**Citations:**

{render_list(citations, 'No catalog claim was made')}

**Clarifying questions:**

{render_list(result.get('clarifying_questions', []))}

**Assumptions / Not in catalog:**

{render_list(result.get('assumptions_not_in_catalog', []))}

**Next steps:**

{render_list(result.get('next_steps', []))}
"""


def write_reports(results_path: Path, transcripts_path: Path) -> None:
    metrics = evaluate()
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(metrics, indent=2) + "\n")
    by_id = {case_id: (question, profile) for case_id, question, profile, _ in CASES}
    selected = [
        ("Eligibility decision with citations", "direct-03"),
        ("Course plan with justification and citations", "plan-01"),
        ("Safe abstention with guidance", "abstain-02"),
    ]
    parts = ["# Required example transcripts\n"]
    for title, case_id in selected:
        question, profile = by_id[case_id]
        parts.append(render_transcript(title, question, profile, respond(question, profile)))
    transcripts_path.write_text("\n".join(parts))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results/assessment_metrics.json"))
    parser.add_argument("--transcripts", type=Path, default=Path("EXAMPLE_TRANSCRIPTS.md"))
    args = parser.parse_args()
    write_reports(args.results, args.transcripts)
    print(f"Wrote {args.results} and {args.transcripts}")


if __name__ == "__main__":
    main()
