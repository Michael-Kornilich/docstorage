from docstorage.utility import freeze


def test_freeze():
    li = [1, 2, 3]
    out = freeze(li)
    assert out == tuple(li)


def test_nested_freeze():
    li = [1, 2, [3, 4], 5, (6, 7)]
    out = freeze(li)
    assert out == (1, 2, (3, 4), 5, (6, 7))
