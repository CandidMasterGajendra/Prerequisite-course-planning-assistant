# Assessment evaluation results

Run date: 20 November 2026. The reproducible case-level output is `results/assessment_metrics.json`.

The set contains the PDF's required 25-query mix: 10 direct prerequisite checks, five prerequisite-chain checks, five program-requirement questions, and five not-in-catalog or trick questions. Two additional planning cases bring the total to 27. Chain cases require valid evidence from the target course and at least one related course page.

| Measure | Result | Scope |
|---|---:|---|
| Eligibility correctness | 15/15 (100%) | 10 direct + 5 chain decisions |
| Abstention accuracy | 5/5 (100%) | Not-in-catalog and unresolved-rule cases |
| Citation coverage on catalog-claim responses | 22/22 (100%) | Direct, chain, program, and plan responses |
| Citation coverage on all responses | 23/27 (85.2%) | Includes four abstentions that deliberately make no catalog claim |
| Citation metadata verification | 23/23 (100%) | All responses containing citations |
| Multi-course chain evidence | 5/5 (100%) | Target + at least one related course page |
| Plan credit validity | 2/2 (100%) | Plans stay within the requested credit limit |
| Next-step coverage | 27/27 (100%) | Every response provides a practical next action |

## Grading rubric

- **Eligibility correct:** the three-valued decision matches the manually encoded, source-reviewed prerequisite expression for the supplied grades and profile.
- **Correct abstention:** the assistant does not invent unavailable scheduling, instructor, room, or textbook facts, and unresolved prerequisite wording remains `needs_more_info`.
- **Citation covered:** a response making a catalog rule, prerequisite, requirement, or plan-membership claim contains at least one citation.
- **Citation valid:** every passage ID exists and its URL and section match the indexed metadata. Course decisions must cite the target course; chain cases must cite at least two distinct course pages; plan items must cite both the course and a program page that names it.
- **Plan valid:** total selected credits do not exceed the requested limit and every proposed course passes the reviewed prerequisite and program-membership checks.

These are deterministic development regression results. They demonstrate that the implementation follows the encoded rules; they do not establish independent real-world accuracy or prove every manual transcription correct.

## Live GPT wording run

An earlier 25-case development run used `gpt-5-mini`: 17 supported decisions or plans invoked GPT, all 17 drafts passed the structural verifier, eight uncertain cases bypassed GPT, and no API error occurred. That report predates the corrected PDF category mix, so it is retained as engineering evidence rather than the final assessment metric. A manual, independent review is still required before claiming a GPT citation-support percentage.

## Failure found and corrected

The first live smoke run rejected a valid CS 261 explanation because the verifier treated prerequisite codes named in the cited CS 261 passage as unrelated course claims. The verifier now permits prerequisite codes present in the cited passage while still rejecting unrelated courses, and a regression test covers this behavior.
