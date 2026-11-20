"""Local embedding index with source-linked passages and exact course-code boost."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "osu_2026_27.json"
INDEX = ROOT / "data" / "osu_vectors.npz"
META = ROOT / "data" / "osu_passages.json"
MODEL = "BAAI/bge-small-en-v1.5"


def passages(corpus: dict, size: int = 230, overlap: int = 35) -> list[dict]:
    result = []
    for doc in corpus["documents"]:
        words = doc["text"].split()
        if doc["kind"] == "course":
            parts = [words]
        else:
            step = size - overlap
            parts = [words[start:start + size] for start in range(0, len(words), step) if words[start:start + size]]
        for i, part in enumerate(parts):
            result.append({"passage_id": f"{doc['doc_id']}-{i}", "doc_id": doc["doc_id"], "course_code": doc.get("course_code"), "kind": doc["kind"], "section": doc["heading"] if doc["kind"] == "course" else f"{doc['heading']} / chunk {i+1}", "url": doc["url"], "text": " ".join(part)})
    return result


def build(corpus_path: Path = CORPUS, index_path: Path = INDEX, meta_path: Path = META) -> dict:
    corpus_bytes = corpus_path.read_bytes()
    corpus = json.loads(corpus_bytes)
    rows = passages(corpus)
    model = TextEmbedding(model_name=MODEL)
    vectors = np.asarray(list(model.embed(["passage: " + row["text"] for row in rows])), dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors /= np.maximum(norms, 1e-12)
    np.savez_compressed(index_path, vectors=vectors)
    meta_path.write_text(json.dumps({"model": MODEL, "corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(), "chunk_words": 230, "overlap_words": 35, "rows": rows}, indent=2) + "\n")
    return {"passages": len(rows), "dimension": vectors.shape[1], "model": MODEL, "index": str(index_path)}


class Retriever:
    def __init__(self, index_path: Path = INDEX, meta_path: Path = META) -> None:
        metadata = json.loads(meta_path.read_text())
        if metadata["model"] != MODEL:
            raise ValueError("Embedding model mismatch; rebuild index")
        if metadata["corpus_sha256"] != hashlib.sha256(CORPUS.read_bytes()).hexdigest():
            raise ValueError("Catalog corpus changed; rebuild index")
        self.rows = metadata["rows"]
        self.vectors = np.load(index_path)["vectors"]
        if len(self.rows) != len(self.vectors):
            raise ValueError("Index and passage metadata length mismatch")
        self.model = TextEmbedding(model_name=MODEL)

    def search(self, query: str, k: int = 5) -> list[dict]:
        vector = np.asarray(next(iter(self.model.embed(["query: " + query]))), dtype=np.float32)
        vector /= max(float(np.linalg.norm(vector)), 1e-12)
        # Float64 reduction avoids spurious float32 Accelerate matmul warnings
        # on the supported macOS runtime for this small exact-scan index.
        scores = np.einsum("ij,j->i", self.vectors.astype(np.float64), vector.astype(np.float64))
        if not np.isfinite(scores).all():
            raise ValueError("Non-finite retrieval scores")
        codes = set(re.findall(r"\b(?:CS|MTH|ECE|ENGR|ST)\s*\d{3}[A-Z]?\b", query.upper()))
        codes = {re.sub(r"\s+", "", code) for code in codes}
        # Exact identifiers are authoritative for course lookup. Semantic
        # ranking still orders records for open-ended policy questions.
        for i, row in enumerate(self.rows):
            if row["course_code"] in codes:
                scores[i] += 1.0
            if row["doc_id"] == "cs-major" and re.search(r"\b(major|degree|bachelor)\b", query.lower()):
                scores[i] += 0.25
            if row["doc_id"] == "systems-option" and re.search(r"\b(system|option|restricted elective)\b", query.lower()):
                scores[i] += 0.25
            if row["doc_id"] == "regulations" and re.search(r"\b(register|registration|credit load|repeat)\b", query.lower()):
                scores[i] += 0.15
        best = np.argsort(-scores)[:k]
        return [self.rows[int(i)] | {"score": round(float(scores[i]), 4)} for i in best]


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("build")
    search_parser = sub.add_parser("search")
    search_parser.add_argument("question")
    search_parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    if args.action == "build":
        print(json.dumps(build(), indent=2))
    else:
        print(json.dumps(Retriever().search(args.question, args.k), indent=2))


if __name__ == "__main__":
    main()
