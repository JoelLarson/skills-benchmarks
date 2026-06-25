import os


def test_answer_correct():
    path = "/root/answer.txt"
    assert os.path.exists(path), "answer.txt not found"
    with open(path) as f:
        raw = f.read().strip().replace("$", "").replace(",", "")
    val = int(raw)
    assert val == 17, f"expected 17, got {val}"
