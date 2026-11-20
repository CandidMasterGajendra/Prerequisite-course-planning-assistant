# Assessment 1: data and system design (planning baseline)

Status: source audit and proposed design, 20 November 2026. The existing demo code and synthetic data do not implement this design and are not submission ready.

Update, 20 November 2026: the focused corpus now uses 48 distinct official course-specific pages, two program pages, and two policy pages (52 URLs total). See `SOURCES.md` and the generated manifest for the verified dataset count. The ten-page table below records the earlier parent-page audit, not the current submitted corpus.

## Product scope

An advisor-style assistant for Oregon State University (OSU) 2026–27 undergraduate Computer Science students. The initial program scope is the CS major plus the Computer Systems option. Questions cover course eligibility, prerequisite chains, corequisites, program requirements, and a proposed next-term plan. The assistant must identify missing student details, cite rule-bearing passages, and avoid claiming schedule availability or approvals absent from sources.

OSU uses Fall, Winter, and Spring terms; the interface should use that vocabulary rather than assuming a two-semester calendar.

## Source audit

The table records downloaded public HTML pages. `main words` counts text under the page's main content element, before cleaning, duplicate removal, and course filtering. `course blocks` counts HTML elements with class `courseblock`; it is not a count of distinct source pages. Local audit copies are in `work/catalog-audit/` (not deliverables).

| Source | Role | Main words | Course blocks |
|---|---|---:|---:|
| [CS courses](https://catalog.oregonstate.edu/courses/cs/) | CS course rules | 7,701 | 145 |
| [MTH courses](https://catalog.oregonstate.edu/courses/mth/) | math dependencies and alternatives | 8,778 | 163 |
| [ECE courses](https://catalog.oregonstate.edu/courses/ece/) | option electives and corequisites | 6,388 | 148 |
| [ENGR courses](https://catalog.oregonstate.edu/courses/engr/) | engineering dependencies | 2,510 | 44 |
| [ST courses](https://catalog.oregonstate.edu/courses/st/) | statistics dependencies | 3,545 | 77 |
| [CS major](https://catalog.oregonstate.edu/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/) | program requirement page 1 | 1,050 | 0 |
| [Computer Systems option](https://catalog.oregonstate.edu/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/computer-systems-option/) | program requirement page 2 | 547 | 0 |
| [Cybersecurity option](https://catalog.oregonstate.edu/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/cybersecurity-option/) | comparison/optional expansion | 569 | 0 |
| [Academic regulations](https://catalog.oregonstate.edu/regulations/) | academic policy | 8,145 | 0 |
| [Course description guide](https://catalog.oregonstate.edu/courses/) | notation and exception policy | 1,483 | 0 |

Total: 10 actual pages, 40,716 main-content words before cleaning. This is not yet a certified 30,000-word *usable corpus*. Many MTH/ECE/ST blocks are outside the target program. Do not count chunks from the same page as separate source pages. Before development, decide whether the cleaned, relevant corpus clears 30,000 words or whether the curated course descriptions count as 25 distinct documents under the assessment's alternative threshold. Prefer satisfying both with additional relevant program/policy pages if feasible, without padding with unrelated text.

The first release should select a prerequisite-closed set of 40–60 courses: the CS major's required sequence, Computer Systems option courses, and every directly referenced MTH/ECE/ENGR/ST alternative needed to reason about those courses. The final source inventory will list each selected course, source URL, catalog year, retrieval timestamp, source heading, prerequisite coverage, and review status.

### Curation finding

The CS source page has 145 `courseblock` elements, but a focused undergraduate set is much smaller, and each course block is only about 40–110 words. The full 40,716-word count therefore relies heavily on unrelated mathematics, ECE, and statistics courses and on general regulations. We must not use that raw count as proof that a focused dataset meets the 30,000-word route. The safer dataset route is to preserve at least 25 distinct, source-backed course/program/policy *documents* (the assessment explicitly allows course descriptions), while transparently reporting that several descriptions come from the same original catalog URL. If a reviewer interprets “distinct documents/pages” as distinct URLs, expand the evidence set with relevant official degree, option, and policy pages and verify the count again.

Initial course chain for manual rule review: `CS 161 -> CS 162 -> CS 261`, with `CS 225` or `MTH 231` as discrete-math alternatives; `CS 340`, `CS 361`, `CS 362`, `CS 374`, and `CS 461 -> CS 462 -> CS 463` provide plan and multi-hop cases. CS 361 is recommended for CS 362, not required; the wording of CS 325's prerequisite has ambiguous AND/OR grouping. See `RULE_REVIEW.md` before encoding either rule. Add option courses only after checking the option's exact required/elective table.

## Rule cases evidenced by catalog

- CS 261 combines an OR group of CS preparation courses with an AND group of discrete-math alternatives; each alternative has a minimum grade.
- MTH 231 includes multiple alternatives, including courses that may be taken concurrently and a placement-score path.
- ECE course records include explicit corequisites.
- The Computer Systems option defines restricted-elective eligibility and exclusions.
- Academic regulations include undergraduate credit-load and repeat rules.

These examples are candidates for labeled tests. Exact logic must be transcribed and manually checked against the saved catalog text before use. If source wording is ambiguous, represent the rule as unresolved and ask for advisor/department confirmation.

## Data model

`Source`: source_id, URL, accessed_at, catalog_year, institution, title, source_type, content_hash, license/usage note.

`Passage`: passage_id, source_id, heading, exact source excerpt, normalized text, start/end location, course code if present. Prefer one course block per passage and heading-aware sections for programs/policy; avoid arbitrary overlap across unrelated courses.

`Course`: code, title, credits, campus/mode where expressly stated, prerequisite expression, corequisite expression, equivalencies, repeatability, evidence passage IDs, review status.

`Requirement`: program/option, category, required courses or credit bounds, exclusions and double-count rules, evidence passage IDs, review status.

`StudentProfile`: catalog year, program and option, completed courses with grades, in-progress courses, transfer/equivalent courses with approval status, target term, credit limit. Unknown is distinct from false or failed.

Prerequisites should use a small expression tree: `all_of`, `any_of`, `course(min_grade, concurrent_allowed)`, `placement(min_score)`, `approval_required`, and `unknown`. Preserve the exact source phrase alongside every parsed expression. Never silently coerce an unsupported exception into eligibility.

## System design

1. Ingest pinned public HTML/PDF snapshots. Extract main content, course blocks, program tables, and policy headings; hash sources and record provenance.
2. Build two indexes: a vector index for passage search, and a structured course/program rule graph. Keep a lexical course-code lookup for exact identifiers.
3. Parse user intent and student profile. Ask up to five focused clarification questions when missing information changes the decision.
4. Retrieve relevant passages with metadata filters for institution, catalog year, program, and course code. Report retrieval scores and passage IDs internally.
5. Evaluate prerequisite expressions and program constraints deterministically. Return `eligible`, `not_eligible`, or `needs_more_info`, with an evidence trace for each branch.
6. For planning, rank courses that advance unmet requirements, then enforce prerequisites, corequisites, grade thresholds, credit limits, repeats, and known exclusions. Treat term offering as unknown unless an authoritative schedule source is added.
7. Use a GPT model only to interpret phrasing and explain the computed result. Require a structured response with answer/plan, why, citations, clarification questions, and assumptions/not-in-catalog.
8. Validate every citation against retrieved passage IDs and block unsupported policy claims. Escalate conflicting or ambiguous rules.

## Evaluation contract

Build a labeled set of at least 25 cases, with no overlap between tuning examples and final reporting: at least 10 direct eligibility checks, 5 multi-hop chains, 5 program/plan cases, and 5 not-in-docs or trick cases. Include grade boundary, OR branch, concurrent course, corequisite, equivalent/approval uncertainty, option elective, over-credit, repeat, and unknown offering cases. Each case includes the student profile, expected decision or acceptable plan constraints, and gold evidence passage IDs.

Report separately:

- Eligibility accuracy = correct decisions / labeled eligibility cases.
- Citation support = policy and requirement claims whose cited passage actually supports them / all such claims (manual audit sample and automated ID validation).
- Citation coverage = applicable answers with at least one valid citation / applicable answers; clarification-only and abstention-only outputs should be reported separately.
- Abstention accuracy = correct abstentions / cases where sources cannot justify an answer.
- Plan validity = plans with no prerequisite, credit, or program-rule violations / evaluated plans.

Publish the case-level results, three transcripts (eligible with citations, plan with justifications, correct abstention), a failure analysis, and the exact evaluation version. Do not quote a metric from the current synthetic demo as a real-system result.

## Documentation and delivery

The repository should eventually contain: source manifest and access dates, ingestion instructions, architecture/rule schema, retrieval and chunking rationale, model/prompt settings, deterministic verification design, README with reproducible commands, 25+ labeled cases and results, one-page write-up, and a short demo. Resume bullets are written after the evaluation and should name measured performance and concrete engineering contributions.

## Gates before implementation

- Confirm selected courses form a useful prerequisite-closed graph and meet dataset size requirements after cleaning.
- Manually validate a sample of complex rules and all rules used in gold evaluation cases.
- Freeze the program/catalog-year scope and expected input/output schema.
- Record the evaluation labels before tuning retrieval or prompts.
