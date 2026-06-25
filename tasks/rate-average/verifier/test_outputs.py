import os


def test_answer_correct():
    path = "/root/answer.txt"
    assert os.path.exists(path), "answer.txt not found"
    with open(path) as f:
        raw = f.read().strip().replace("$", "").replace(",", "")
    val = float(raw)
    assert abs(val - 48.0) < 0.01, f"expected 48, got {val}"
