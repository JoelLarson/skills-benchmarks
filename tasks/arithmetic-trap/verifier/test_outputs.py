import os


def test_answer_correct():
    path = "/root/answer.txt"
    assert os.path.exists(path), "answer.txt not found"
    with open(path) as f:
        raw = f.read().strip().replace("$", "").replace(",", "")
    val = float(raw)
    assert abs(val - 353.33) < 0.005, f"expected 353.33, got {val}"
