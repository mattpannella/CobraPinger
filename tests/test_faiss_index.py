import numpy as np
from embedding_index import add_embedding, find_similar, build_advisor_prompt, load_index

class DummyDB:
    def __init__(self, rows):
        self._rows = rows
    def get_all_embeddings(self):
        return self._rows


def test_index_build_and_search():
    rows = [
        (1, '[0, 0, 1]'),
        (2, '[0, 1, 0]'),
    ]
    index, ids = load_index(DummyDB(rows))
    res = find_similar(index, ids, [0, 0, 1], k=1)
    assert res[0][0] == 1


def test_build_advisor_prompt():
    txt = 'today'
    sums = ['s1', 's2', 's3']
    prompt = build_advisor_prompt(txt, sums)
    assert 'today' in prompt
    for s in sums:
        assert s in prompt
