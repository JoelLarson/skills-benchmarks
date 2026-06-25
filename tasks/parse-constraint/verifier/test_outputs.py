import os


def test_answer_is_carol():
    path = "/root/answer.txt"
    assert os.path.exists(path), "answer.txt not found"
    with open(path) as f:
        answer = f.read().strip()
    assert answer == "Carol", f"expected 'Carol', got {answer!r}"
