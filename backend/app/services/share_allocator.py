"""Pure share-distribution logic for offers inside a stream.

Rules (invariants the editor relies on):
* active offers' integer shares always sum to exactly 100;
* a pinned offer keeps the share the user typed;
* the rest (100 − pinned) is split evenly between unpinned offers;
  the remainder goes to the first ones: 100 / 3 → 34, 33, 33;
* every active offer gets at least 1 %.
"""

from collections.abc import Hashable, Sequence
from dataclasses import dataclass

TOTAL = 100


class AllocationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Slot:
    key: Hashable
    pinned_share: int | None = None  # None → share is calculated automatically


def allocate(slots: Sequence[Slot]) -> dict[Hashable, int]:
    if not slots:
        return {}

    pinned = [s for s in slots if s.pinned_share is not None]
    auto = [s for s in slots if s.pinned_share is None]

    for s in pinned:
        if not 1 <= s.pinned_share <= TOTAL:  # type: ignore[operator]
            raise AllocationError(f"Share must be between 1 and {TOTAL}, got {s.pinned_share}")

    pinned_total = sum(s.pinned_share for s in pinned)  # type: ignore[misc]
    if pinned_total > TOTAL:
        raise AllocationError(f"Pinned shares sum to {pinned_total}% — more than {TOTAL}%")

    result: dict[Hashable, int] = {s.key: s.pinned_share for s in pinned}  # type: ignore[misc]

    if not auto:
        if pinned_total != TOTAL:
            raise AllocationError(f"All offers are pinned but they sum to {pinned_total}%, not {TOTAL}%")
        return result

    remaining = TOTAL - pinned_total
    if remaining < len(auto):
        raise AllocationError(
            f"Only {remaining}% left for {len(auto)} unpinned offer(s) — each needs at least 1%"
        )

    base, extra = divmod(remaining, len(auto))
    for index, s in enumerate(auto):
        result[s.key] = base + (1 if index < extra else 0)
    return result
