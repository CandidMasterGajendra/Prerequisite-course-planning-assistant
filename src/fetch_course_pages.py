"""Download exact OSU course search pages for the selected corpus.

The search endpoint is the same official course link used in OSU program tables.
Each response must contain a course block for the requested code.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from .ingest_osu import CatalogParser


def fetch(code: str, output_dir: Path) -> tuple[str, str]:
    subject, number = re.match(r"^([A-Z]+)(\d{3}[A-Z]?)$", code).groups()
    url = "https://catalog.oregonstate.edu/search/?P=" + quote(f"{subject} {number}", safe="")
    request = Request(url, headers={"User-Agent": "CoursePlanningResearch/0.1 (personal academic catalog audit)"})
    with urlopen(request, timeout=25) as response:
        raw = response.read()
    parser = CatalogParser()
    parser.feed(raw.decode("utf-8"))
    main_text = " ".join(" ".join(parser.main).split())
    found = bool(re.search(rf"\b{subject}\s*{number}\s*,", main_text)) and bool(parser.blocks)
    if not found:
        raise ValueError(f"Exact course block missing from {url}")
    (output_dir / f"{code.lower()}.html").write_bytes(raw)
    return code, url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    codes = sorted({d["course_code"] for d in json.loads(args.corpus.read_text())["documents"] if d.get("course_code")})
    results = []
    for code in codes:
        results.append(fetch(code, args.output_dir))
        time.sleep(0.15)
    print(json.dumps({"verified_course_pages": len(results), "first": results[:3], "last": results[-3:]}, indent=2))


if __name__ == "__main__":
    main()
