"""Build a provenance-preserving OSU catalog corpus from saved HTML snapshots.

Use --snapshot-dir for the audited catalog pages. The generated corpus contains
course descriptions as independent documents, each linked to its original URL.
No network request is performed by this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

BASE = "https://catalog.oregonstate.edu"
PAGES = {
    "cs": ("/courses/cs/", "course"),
    "mth": ("/courses/mth/", "course"),
    "ece": ("/courses/ece/", "course"),
    "engr": ("/courses/engr/", "course"),
    "st": ("/courses/st/", "course"),
    "cs-major": ("/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/", "program"),
    "systems-option": ("/college-departments/engineering/school-electrical-engineering-computer-science/computer-science-ba-bs-hba-hbs/computer-systems-option/", "program"),
    "regulations": ("/regulations/", "policy"),
    "course-guide": ("/courses/", "policy"),
}

# A connected set of core, option, and directly relevant prerequisite courses.
SELECTED = {
    "CS161", "CS162", "CS162H", "CS225", "CS261", "CS261H", "CS271", "CS274",
    "CS290", "CS321", "CS325", "CS325H", "CS331", "CS340", "CS361", "CS362",
    "CS362H", "CS370", "CS372", "CS374", "CS381", "CS391", "CS420", "CS440",
    "CS461", "CS461H", "CS462", "CS462H", "CS463", "CS463H", "CS472", "CS474",
    "CS480", "MTH111", "MTH111Z", "MTH112", "MTH112Z", "MTH231", "MTH231H",
    "MTH254", "MTH264", "MTH265", "ECE204", "ECE271", "ECE370", "ST314",
    "ENGR102", "ENGR103", "ENGR103H", "ENGR330",
}


class CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.main_depth = 0
        self.block_depth = 0
        self.main: list[str] = []
        self.block: list[str] = []
        self.blocks: list[str] = []
        self.ignored = 0
        self.glossary_depth = 0
        self.glossary: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored += 1
        attrs_dict = dict(attrs)
        is_void = tag in {"br", "hr", "img", "input", "meta", "link"}
        if tag == "div" and attrs_dict.get("id") == "content" and not self.main_depth:
            self.main_depth = 1
        elif self.main_depth and not is_void:
            self.main_depth += 1
        if tag == "div" and attrs_dict.get("id") == "glossarytextcontainer" and not self.glossary_depth:
            self.glossary_depth = 1
        elif self.glossary_depth and not is_void:
            self.glossary_depth += 1
        if tag == "div" and "courseblock" in (attrs_dict.get("class") or "").split() and not self.block_depth:
            self.block_depth = 1
            self.block = []
        elif self.block_depth and not is_void:
            self.block_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.block_depth:
            self.block_depth -= 1
            if not self.block_depth:
                self.blocks.append(" ".join(" ".join(self.block).split()))
        if self.main_depth:
            self.main_depth -= 1
        if self.glossary_depth:
            self.glossary_depth -= 1
        if tag in {"script", "style"}:
            self.ignored -= 1

    def handle_data(self, data: str) -> None:
        if self.main_depth and not self.ignored:
            self.main.append(data)
        if self.glossary_depth and not self.ignored:
            self.glossary.append(data)
        if self.block_depth and not self.ignored:
            self.block.append(data)


def build(snapshot_dir: Path, output: Path, course_pages_dir: Path | None = None) -> dict:
    docs = []
    sources = []
    for name, (url_path, kind) in PAGES.items():
        path = snapshot_dir / f"{name}.html"
        raw = path.read_bytes()
        parser = CatalogParser()
        parser.feed(raw.decode("utf-8"))
        source = {
            "source_id": name,
            "url": BASE + url_path,
            "catalog_year": "2026-2027",
            "accessed": str(date.today()),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_type": kind,
        }
        if kind != "course" or course_pages_dir is None:
            sources.append(source)
        if kind == "course":
            for block in parser.blocks:
                match = re.match(r"([A-Z]+)\s*(\d{3}[A-Z]?)\s*,", block)
                if not match:
                    continue
                code = "".join(match.groups())
                if code in SELECTED:
                    course_source = source
                    if course_pages_dir is not None:
                        course_raw = (course_pages_dir / f"{code.lower()}.html").read_bytes()
                        individual = CatalogParser()
                        individual.feed(course_raw.decode("utf-8"))
                        main_text = " ".join(" ".join(individual.main).split())
                        expected_body = block.split(" Credits", 1)[1].strip()
                        if not re.search(rf"\b{match.group(1)}\s*{match.group(2)}\s*,", main_text) or expected_body not in individual.blocks:
                            raise ValueError(f"Individual catalog page differs from department page: {code}")
                        course_source = {
                            "source_id": f"course-{code.lower()}",
                            "url": BASE + "/search/?P=" + quote(f"{match.group(1)} {match.group(2)}", safe=""),
                            "catalog_year": "2026-2027",
                            "accessed": str(date.today()),
                            "sha256": hashlib.sha256(course_raw).hexdigest(),
                            "source_type": "course",
                        }
                        sources.append(course_source)
                    docs.append({
                        "doc_id": f"{name}-{code.lower()}",
                        "kind": "course",
                        "course_code": code,
                        "heading": block.split(" Credits", 1)[0] + " Credits",
                        "text": block,
                        "source_id": course_source["source_id"],
                        "url": course_source["url"],
                    })
        else:
            text = " ".join(" ".join(parser.glossary if name == "course-guide" else parser.main).split())
            docs.append({"doc_id": name, "kind": kind, "heading": name.replace("-", " ").title(), "text": text, "source_id": name, "url": source["url"]})
    payload = {"sources": sources, "documents": docs}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return {
        "source_pages": len(sources),
        "documents": len(docs),
        "course_descriptions": sum(d["kind"] == "course" for d in docs),
        "document_words": sum(len(d["text"].split()) for d in docs),
        "missing_selected_codes": sorted(SELECTED - {d.get("course_code") for d in docs}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--course-pages-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.snapshot_dir, args.output, args.course_pages_dir), indent=2))


if __name__ == "__main__":
    main()
