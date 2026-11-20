# Assessment 1: selected course rule review

Reviewed 20 November 2026 against the Oregon State University 2026–27 catalog. This is a data specification, not an implemented rule engine. Course descriptions are on the [CS catalog page](https://catalog.oregonstate.edu/courses/cs/) and [MTH catalog page](https://catalog.oregonstate.edu/courses/mth/). Each course heading is the citation section. Rules below paraphrase the catalog; preserve the exact source block and snapshot hash during ingestion.

Current audit: 27 encoded reviewed course rules, five explicitly unresolved rules, and 16 evidence-only course descriptions. `python -m src.audit_rules` checks that encoded course-code references match the prerequisite text and that all 52 source URLs are distinct. This structural audit does not resolve precedence, grade-policy interpretation, or honors restrictions.

Notation: `&` means all groups, `|` means any alternative, `>=C` is a completed course with at least C, and `concurrent(X)` means X may be completed or taken in the target term when the catalog expressly allows it. Unknown grades, transfer equivalencies, placement scores, or approvals yield `needs_more_info`, not a negative decision.

| Target | Reviewed prerequisite expression | Notes |
|---|---|---|
| CS 161 | `concurrent(MTH 112 >=C) | concurrent(MTH 112Z >=C) | placement_test >=33 | ALEKS >=61` | Placement evidence must be in the student profile. |
| CS 162 | `CS 161 >=C | ENGR 103 >=C | ENGR 103H >=C | DS 231 >=C` | CS 162H is listed as equivalent; confirm how equivalence is applied to degree credit separately. |
| CS 225 | `MTH 111 >=C | MTH 111Z >=C | concurrent(MTH 112 >=C) | concurrent(MTH 112Z >=C) | placement_test >=24 | ALEKS >=61` | Distinct score threshold from CS 161. |
| CS 261 | `(CS 162 >=C | CS 162H >=C | CS 165 >=C) & (CS 225 >=C | MTH 231 >=C | MTH 231H >=C)` | The explicit parentheses make this a good reference case for AND/OR logic. |
| CS 271 | `CS 151 >=C | CS 161 >=C | CS 165 >=C | ENGR 103 >=C | ENGR 103H >=C` | Include every branch in the source-backed schema even if the first demo profile uses CS 161. |
| CS 290 | `CS 162 >=C | CS 162H >=C | CS 165 >=C` | Useful independent eligible-course candidate. |
| CS 325 | `CS 261 >=C | CS 261H >=C and (CS 225 >=C | MTH 231 >=C | MTH 231H >=C)` | **Ambiguous grouping in the displayed text.** Do not assume whether the math group applies to both CS 261 branches or only CS 261H. Seek an authoritative interpretation or mark uncertain profiles for advisor review. |
| CS 340 | `CS 261 >=C | CS 261H >=C` | Database course; direct prerequisite check. |
| CS 361 | `CS 261 >=C | CS 261H >=C` | First software engineering course. |
| CS 362 | `CS 261 >=C | CS 261H >=C` | CS 361 appears in **recommended experience**, not in the prerequisite rule. Do not block enrollment solely because CS 361 is absent. |
| CS 374 | `(CS 261 >=C | CS 261H >=C) & CS 274 >=C & (CS 271 >=C | ECE 204 >=C | ECE 271 >=C)` | Three mandatory groups; ECE branches need their own source blocks if planning them. |
| CS 461 | `(CS 325 >=C | CS 325H >=C) & CS 361 >=C & (CS 362 >=C | CS 362H >=C)` | Start of capstone chain. |
| CS 462 | `(CS 362 >=C | CS 362H >=C) & (CS 461 >=C | CS 461H >=C)` | CS 461 can be an honors equivalent. |
| CS 463 | `(CS 462 >=C | CS 462H >=C) & ENGR 102 >=C` | Include ENGR 102 in prerequisite closure. |
| MTH 231 | alternatives include completed MTH 111/111Z `>=C-`, several MTH courses allowed concurrently `>=C-`, or ALEKS `>=60` | The full rule has many alternatives; transcribe and review the entire expression before enabling automated decisions. |

## Program and policy checks

The [CS major page](https://catalog.oregonstate.edu/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/) lists CS 162, 261, 325, 340, 361, and 362 among core courses and requires an option. It lists a 180-credit degree total. The [Computer Systems option](https://catalog.oregonstate.edu/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/computer-systems-option/) is an 80-credit option with required and elective groups. Restricted electives have grade-mode, level, credit, and double-count constraints; model these as program rules, not course prerequisites.

The full major requirement table also includes ENGR 102 and 103, MTH 231, 251Z, and 252Z; it has alternatives for transitions, communication, writing, and ethics courses. The current planner covers only the reviewed CS subset, so it is **not a degree audit**. The Computer Systems option table includes AI 230; CS 274, 321, 370, 372, 374, 381, 461–463, 472, 474, and 480; ECE 204 and 370; MTH 254, 264, and 265; ST 314; eight restricted-elective credits and seven approved-elective credits. Its restrictions require A–F grading for restricted electives, prevent double counting with other major requirements, limit CS 401/406 credits, exclude several independent-study/internship numbers, and require advisor approval for specified outside courses. The existing planner does not yet enforce these elective constraints.

The [academic regulations](https://catalog.oregonstate.edu/regulations/) state a usual undergraduate registration maximum of 19 credits and describe conditions for an extension. Repeated courses have special credit/grade treatment. A student-requested max below 19 is an additional planning constraint; a request above 19 requires the specific policy conditions and student information before recommending that load.

## Decision cases to label before coding

1. CS 261 with CS 162 grade C and MTH 231 grade C: eligible, cite CS 261.
2. CS 261 with CS 162 grade C- and MTH 231 grade C: not eligible, cite CS 261.
3. CS 261 with CS 162 grade unknown and MTH 231 grade C: needs more info.
4. CS 225 with MTH 112 in progress: distinguish concurrent permission from an already earned grade; confirm how the catalog applies the grade threshold to concurrent enrollment.
5. CS 362 with CS 261 grade C but no CS 361: prerequisite satisfied; mention CS 361 only as a recommendation if relevant.
6. CS 374 with CS 261 and CS 274 but no architecture alternative: not eligible.
7. CS 461 with CS 325, CS 361, and CS 362 at C or better: eligible, with three evidence branches.
8. CS 463 with CS 462 but missing ENGR 102: not eligible.
9. CS 325 with a profile whose outcome depends on AND/OR grouping: needs authoritative resolution, not an arbitrary parse.
10. A plan that reaches 20 credits: do not present as ordinarily permissible; check extension conditions or reduce the plan.

These are rule-level gold cases. The full evaluation set still needs at least 25 queries in the assessment's required category mix, plus citation and abstention labels.

## Corrections to the initial design

The shorthand `CS 361 -> CS 362` is not a prerequisite chain in the catalog. The verified capstone chain is CS 461 -> CS 462 -> CS 463, with CS 362 contributing to CS 461 and CS 462. Course availability by term remains outside the present sources unless an authoritative schedule is added.

## Additional course review for scoped option

The following are direct transcriptions of the prerequisite structure shown in the saved 2026–27 catalog; each is tied to the course heading on the [CS catalog page](https://catalog.oregonstate.edu/courses/cs/). They expand the reviewed option graph without resolving ambiguous text by guesswork.

| Course(s) | Rule status |
|---|---|
| CS 162H, 261H, 362H, 461H, 462H, 463H | Same prerequisite expression as the corresponding non-honors course in this snapshot. Honors eligibility itself may impose further restrictions outside this corpus. |
| CS 370 | CS 344 or CS 374, with concurrent enrollment expressly allowed; grade threshold C. |
| CS 372 | `(CS 261 or CS 261H) and (ECE 271 or CS 271)`, each at least C. |
| CS 472 | ECE 370, 370H, or 375 at least C. |
| CS 474 | `(CS 344 or CS 374) and (CS 271 or ECE 375 or ECE 370)`, each at least C. |
| CS 480 | CS 381 and `(CS 321 or CS 321H)` and `(CS 344 or CS 374)`, each at least C. |
| CS 321, 325, 325H, 381, 440 | **Unresolved:** displayed `or`/`and` grouping is not explicit enough to encode safely. Ask for authoritative interpretation or abstain on profiles where grouping affects the result. |

Course records outside this reviewed set remain evidence-only until their prerequisite and exception logic is transcribed and checked. This distinction must remain visible in code and evaluation.
