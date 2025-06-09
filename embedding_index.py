import json
from typing import List, Tuple

import faiss
import numpy as np


def load_index(db) -> Tuple[faiss.IndexFlatL2, List[int]]:
    """Load all embeddings from SQLite into a FAISS index."""
    rows = db.get_all_embeddings()
    if not rows:
        return faiss.IndexFlatL2(0), []

    first_emb = json.loads(rows[0][1])
    dim = len(first_emb)
    index = faiss.IndexFlatL2(dim)
    vectors = np.array([json.loads(r[1]) for r in rows], dtype="float32")
    index.add(vectors)
    ids = [r[0] for r in rows]
    return index, ids


def add_embedding(index: faiss.IndexFlatL2, id_list: List[int], video_id: int, embedding: List[float]):
    vec = np.array(embedding, dtype="float32").reshape(1, -1)
    if index.d == 0:
        index = faiss.IndexFlatL2(vec.shape[1])
    index.add(vec)
    id_list.append(video_id)
    return index


def find_similar(index: faiss.IndexFlatL2, id_list: List[int], query_vec: List[float], k: int = 3) -> List[Tuple[int, float]]:
    if index.ntotal == 0:
        return []
    q = np.array(query_vec, dtype="float32").reshape(1, -1)
    D, I = index.search(q, k)
    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx < len(id_list):
            results.append((id_list[idx], float(dist)))
    return results


def build_advisor_prompt(transcript: str, summaries: List[str]) -> str:
    summary_lines = [f"{i+1}. \"{s}\"" for i, s in enumerate(summaries)]
    joined = "\n".join(summary_lines)
    return (
        f"Here\u2019s today\u2019s transcript:\n\"\"\"{transcript}\"\"\"\n\n"
        f"Here are summaries of three similar past videos:\n{joined}\n\n"
        "Based on both today\u2019s transcript and these past contexts, what do you think?"
    )

