import importlib.util


def load():
    spec = importlib.util.spec_from_file_location("solution", "/root/solution.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_single_element_found():
    assert load().bsearch([5], 5) == 0


def test_single_element_missing():
    assert load().bsearch([5], 4) == -1


def test_found_at_end():
    assert load().bsearch([1, 3, 5, 7, 9], 9) == 4


def test_found_at_start():
    assert load().bsearch([1, 3, 5, 7, 9], 1) == 0


def test_two_element_second():
    assert load().bsearch([2, 4], 4) == 1


def test_missing_returns_neg_one():
    assert load().bsearch([1, 3, 5, 7, 9], 6) == -1


def test_empty():
    assert load().bsearch([], 1) == -1
