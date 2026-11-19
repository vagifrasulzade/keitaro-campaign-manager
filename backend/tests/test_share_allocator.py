import pytest

from app.services.share_allocator import AllocationError, Slot, allocate


def test_equal_split_with_remainder_goes_first():
    assert list(allocate([Slot(1), Slot(2), Slot(3)]).values()) == [34, 33, 33]


@pytest.mark.parametrize("n", range(1, 30))
def test_always_sums_to_100(n):
    result = allocate([Slot(i) for i in range(n)])
    assert sum(result.values()) == 100
    assert max(result.values()) - min(result.values()) <= 1


def test_pinned_keeps_value_rest_is_split():
    assert allocate([Slot("a", 70), Slot("b"), Slot("c")]) == {"a": 70, "b": 15, "c": 15}


def test_all_pinned_must_sum_to_100():
    assert allocate([Slot("a", 60), Slot("b", 40)]) == {"a": 60, "b": 40}
    with pytest.raises(AllocationError):
        allocate([Slot("a", 60), Slot("b", 30)])


def test_pinned_over_100_fails():
    with pytest.raises(AllocationError):
        allocate([Slot("a", 80), Slot("b", 30), Slot("c")])


def test_each_unpinned_needs_at_least_one_percent():
    with pytest.raises(AllocationError):
        allocate([Slot("a", 99), Slot("b"), Slot("c")])
    assert allocate([Slot("a", 98), Slot("b"), Slot("c")]) == {"a": 98, "b": 1, "c": 1}


def test_empty():
    assert allocate([]) == {}
