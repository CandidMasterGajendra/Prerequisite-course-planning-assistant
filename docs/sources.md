# Sources and dataset audit

Catalog: Oregon State University, 2026–27. Accessed 20 November 2026. The complete machine-readable manifest is the `sources` array in `data/osu_2026_27.json`; it contains each exact URL, access date, source type, catalog year, and SHA-256 of the downloaded HTML snapshot.

| Source group | Count | Coverage |
|---|---:|---|
| [Individual course pages](https://catalog.oregonstate.edu/search/?P=CS%20261) | 48 | CS major and Computer Systems option sequence, prerequisite alternatives in MTH/ECE/ENGR/ST, honors equivalents. The manifest lists all 48 distinct query URLs. |
| [CS major](https://catalog.oregonstate.edu/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/) | 1 | Major course and credit requirements, alternatives, option requirement. |
| [Computer Systems option](https://catalog.oregonstate.edu/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/computer-systems-option/) | 1 | Required option courses, restricted and approved electives, exclusions. |
| [Academic regulations](https://catalog.oregonstate.edu/regulations/) | 1 | Credit loads, repeats, and academic policy. |
| [Course-description glossary](https://catalog.oregonstate.edu/courses/) | 1 | Meaning of prerequisites, concurrency, corequisites, equivalencies, and registration restrictions. |

Total: **52 distinct official URLs and 52 documents**. This exceeds Assessment 1's minimum of 20 course descriptions, two program pages, one academic policy page, and 25 distinct documents/pages. The selected corpus is **13,473 words**; it does not satisfy the alternative 30,000-word route. Search pages are individual official course entries reached by the catalog's course links, not artificial chunks of one URL. The vector index has 99 passages, but passage count is not used to claim the dataset threshold.

The source blocks were validated against the corresponding department pages. Two legacy math codes (`MTH 111`, `MTH 112`) appear in prerequisites but have no separate 2026–27 course page in the selected catalog; their completion can be supplied by a transcript, but the assistant should not invent a current catalog description for them. The 16 course records outside the 27 reviewed and five unresolved rule records remain evidence-only.

To reproduce a new snapshot, download the parent department and program/policy URLs listed in `src/ingest_osu.py` into the named HTML files, run `python -m src.ingest_osu` to select candidates, run `python -m src.fetch_course_pages` to save official course-specific pages, and rerun ingestion with `--course-pages-dir`. The generated manifest hashes will reveal any changes to the live catalog. Run `python -m src.audit_rules` to check source links and course-code coverage of encoded rules.
