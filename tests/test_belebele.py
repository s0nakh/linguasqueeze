from linguasqueeze.belebele import token_span


def test_token_span_covers_passage_tokens_only():
    # "Passage: Hello world\nQ" -> tokens: "Passage", ":", " Hello", " world", "\n", "Q"
    offsets = [(0, 7), (7, 8), (8, 14), (14, 20), (20, 21), (21, 22)]
    passage_start, passage_end = len("Passage: "), len("Passage: Hello world")
    assert token_span(offsets, passage_start, passage_end) == (2, 4)


def test_token_span_runs_to_end_when_passage_is_last():
    offsets = [(0, 7), (7, 8), (8, 14)]
    assert token_span(offsets, 9, 14) == (2, 3)

from linguasqueeze.belebele import PASSAGE_PREFIX, build_example


class EdgeTokenizer:
    """Splits on spaces but glues each space to the NEXT word and each newline to the PREVIOUS word,
    like GPT-style BPE, so the passage edge tokens carry one extra character each."""

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        offsets, start = [], 0
        for i, ch in enumerate(text):
            if ch == " " and i > start:
                offsets.append((start, i)); start = i
            elif ch == "\n":
                offsets.append((start, i + 1)); start = i + 1
        if start < len(text):
            offsets.append((start, len(text)))
        return {"input_ids": list(range(len(offsets))), "offset_mapping": offsets}


def test_span_chars_counts_exactly_the_characters_of_the_scored_tokens():
    row = {"flores_passage": "  Alpha beta gamma ", "question": "Q?", "correct_answer_num": "1",
           **{f"mc_answer{i}": "x" for i in range(1, 5)}}
    ex = build_example(EdgeTokenizer(), row)
    passage = "Alpha beta gamma"
    # first scored token is " Alpha" (space from the prefix), last is " gamma\\n": 2 characters more than the passage
    assert ex["span_chars"] == len(passage) + 2
