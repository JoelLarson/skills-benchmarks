import os


def test_answer_correct():
    path = "/root/answer.txt"
    assert os.path.exists(path), "answer.txt not found"
    with open(path) as f:
        raw = f.read().strip().replace("$", "").replace(",", "")
    val = float(raw)
    expected = 267.83
    assert abs(val - expected) < 0.005, f"expected {expected}, got {val}"
