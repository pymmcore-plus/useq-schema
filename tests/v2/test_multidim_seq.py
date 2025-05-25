from __future__ import annotations

from itertools import count
from typing import TYPE_CHECKING, Any

from pydantic import Field

from useq._enums import Axis
from useq.v2 import AxesIterator, AxisIterable, SimpleValueAxis

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from useq.v2._axes_iterator import AxesIndex


def _index_and_values(
    multi_dim: AxesIterator,
    axis_order: tuple[str, ...] | None = None,
    max_iters: int | None = None,
) -> list[dict[str, tuple[int, Any]]]:
    """Return a list of indices and values for each axis in the MultiDimSequence."""
    result = []
    for i, indices in enumerate(multi_dim.iter_axes(axis_order=axis_order)):
        if max_iters is not None and i >= max_iters:
            break
        # cleaned version that drops the axis objects.
        result.append({k: (idx, val) for k, (idx, val, _) in indices.items()})
    return result


def test_new_multidim_simple_seq() -> None:
    multi_dim = AxesIterator(
        axes=(
            SimpleValueAxis(axis_key=Axis.TIME, values=[0, 1]),
            SimpleValueAxis(axis_key=Axis.CHANNEL, values=["red", "green", "blue"]),
            SimpleValueAxis(axis_key=Axis.Z, values=[0.1, 0.3]),
        )
    )
    assert multi_dim.is_finite()

    result = _index_and_values(multi_dim)
    assert result == [
        {"t": (0, 0), "c": (0, "red"), "z": (0, 0.1)},
        {"t": (0, 0), "c": (0, "red"), "z": (1, 0.3)},
        {"t": (0, 0), "c": (1, "green"), "z": (0, 0.1)},
        {"t": (0, 0), "c": (1, "green"), "z": (1, 0.3)},
        {"t": (0, 0), "c": (2, "blue"), "z": (0, 0.1)},
        {"t": (0, 0), "c": (2, "blue"), "z": (1, 0.3)},
        {"t": (1, 1), "c": (0, "red"), "z": (0, 0.1)},
        {"t": (1, 1), "c": (0, "red"), "z": (1, 0.3)},
        {"t": (1, 1), "c": (1, "green"), "z": (0, 0.1)},
        {"t": (1, 1), "c": (1, "green"), "z": (1, 0.3)},
        {"t": (1, 1), "c": (2, "blue"), "z": (0, 0.1)},
        {"t": (1, 1), "c": (2, "blue"), "z": (1, 0.3)},
    ]


class InfiniteAxis(AxisIterable[int]):
    axis_key: str = "i"

    def model_post_init(self, _ctx: Any) -> None:
        self._counter = count()

    def __iter__(self) -> Iterator[int]:
        yield from self._counter


def test_multidim_nested_seq() -> None:
    inner_seq = AxesIterator(
        value=1, axes=(SimpleValueAxis(axis_key="q", values=["a", "b"]),)
    )
    outer_seq = AxesIterator(
        axes=(
            SimpleValueAxis(axis_key="t", values=[0, inner_seq, 2]),
            SimpleValueAxis(axis_key="c", values=["red", "green", "blue"]),
        )
    )

    assert outer_seq.is_finite()

    result = _index_and_values(outer_seq)
    assert result == [
        {"t": (0, 0), "c": (0, "red")},
        {"t": (0, 0), "c": (1, "green")},
        {"t": (0, 0), "c": (2, "blue")},
        {"t": (1, 1), "c": (0, "red"), "q": (0, "a")},
        {"t": (1, 1), "c": (0, "red"), "q": (1, "b")},
        {"t": (1, 1), "c": (1, "green"), "q": (0, "a")},
        {"t": (1, 1), "c": (1, "green"), "q": (1, "b")},
        {"t": (1, 1), "c": (2, "blue"), "q": (0, "a")},
        {"t": (1, 1), "c": (2, "blue"), "q": (1, "b")},
        {"t": (2, 2), "c": (0, "red")},
        {"t": (2, 2), "c": (1, "green")},
        {"t": (2, 2), "c": (2, "blue")},
    ]

    result = _index_and_values(outer_seq, axis_order=("t", "c"))
    assert result == [
        {"t": (0, 0), "c": (0, "red")},
        {"t": (0, 0), "c": (1, "green")},
        {"t": (0, 0), "c": (2, "blue")},
        {"t": (1, 1), "c": (0, "red")},
        {"t": (1, 1), "c": (1, "green")},
        {"t": (1, 1), "c": (2, "blue")},
        {"t": (2, 2), "c": (0, "red")},
        {"t": (2, 2), "c": (1, "green")},
        {"t": (2, 2), "c": (2, "blue")},
    ]


def test_override_parent_axes() -> None:
    inner_seq = AxesIterator(
        value=1,
        axes=(
            SimpleValueAxis(axis_key="c", values=["red", "blue"]),
            SimpleValueAxis(axis_key="z", values=[7, 8, 9]),
        ),
    )
    multi_dim = AxesIterator(
        axes=(
            SimpleValueAxis(axis_key="t", values=[0, inner_seq, 2]),
            SimpleValueAxis(axis_key="c", values=["red", "green", "blue"]),
            SimpleValueAxis(axis_key="z", values=[0.1, 0.2]),
        ),
        axis_order=("t", "c", "z"),
    )

    assert multi_dim.is_finite()
    result = _index_and_values(multi_dim)
    assert result == [
        {"t": (0, 0), "c": (0, "red"), "z": (0, 0.1)},
        {"t": (0, 0), "c": (0, "red"), "z": (1, 0.2)},
        {"t": (0, 0), "c": (1, "green"), "z": (0, 0.1)},
        {"t": (0, 0), "c": (1, "green"), "z": (1, 0.2)},
        {"t": (0, 0), "c": (2, "blue"), "z": (0, 0.1)},
        {"t": (0, 0), "c": (2, "blue"), "z": (1, 0.2)},
        {"t": (1, 1), "c": (0, "red"), "z": (0, 7)},
        {"t": (1, 1), "c": (0, "red"), "z": (1, 8)},
        {"t": (1, 1), "c": (0, "red"), "z": (2, 9)},
        {"t": (1, 1), "c": (1, "blue"), "z": (0, 7)},
        {"t": (1, 1), "c": (1, "blue"), "z": (1, 8)},
        {"t": (1, 1), "c": (1, "blue"), "z": (2, 9)},
        {"t": (2, 2), "c": (0, "red"), "z": (0, 0.1)},
        {"t": (2, 2), "c": (0, "red"), "z": (1, 0.2)},
        {"t": (2, 2), "c": (1, "green"), "z": (0, 0.1)},
        {"t": (2, 2), "c": (1, "green"), "z": (1, 0.2)},
        {"t": (2, 2), "c": (2, "blue"), "z": (0, 0.1)},
        {"t": (2, 2), "c": (2, "blue"), "z": (1, 0.2)},
    ]


class FilteredZ(SimpleValueAxis):
    def __init__(self, values: Iterable) -> None:
        super().__init__(axis_key=Axis.Z, values=values)

    def should_skip(self, prefix: AxesIndex) -> bool:
        # If c is green, then only allow combinations where z equals 0.2.
        c_val = prefix.get(Axis.CHANNEL, (None, None))[1]
        z_val = prefix.get(Axis.Z, (None, None))[1]
        return bool(c_val == "green" and z_val != 0.2)


def test_multidim_with_should_skip() -> None:
    multi_dim = AxesIterator(
        axes=(
            SimpleValueAxis(axis_key=Axis.TIME, values=[0, 1, 2]),
            SimpleValueAxis(axis_key=Axis.CHANNEL, values=["red", "green", "blue"]),
            FilteredZ([0.1, 0.2, 0.3]),
        ),
        axis_order=(Axis.TIME, Axis.CHANNEL, Axis.Z),
    )

    assert multi_dim.is_finite()
    result = _index_and_values(multi_dim)

    # If c is green, then only allow combinations where z equals 0.2.
    assert not any(
        item["c"][1] == "green" and item["z"][1] != 0.2 for item in result
    ), "FilteredZ should have filtered out green z!=0.2 combinations"

    assert result == [
        {"t": (0, 0), "c": (0, "red"), "z": (0, 0.1)},
        {"t": (0, 0), "c": (0, "red"), "z": (1, 0.2)},
        {"t": (0, 0), "c": (0, "red"), "z": (2, 0.3)},
        {"t": (0, 0), "c": (1, "green"), "z": (1, 0.2)},
        {"t": (0, 0), "c": (2, "blue"), "z": (0, 0.1)},
        {"t": (0, 0), "c": (2, "blue"), "z": (1, 0.2)},
        {"t": (0, 0), "c": (2, "blue"), "z": (2, 0.3)},
        {"t": (1, 1), "c": (0, "red"), "z": (0, 0.1)},
        {"t": (1, 1), "c": (0, "red"), "z": (1, 0.2)},
        {"t": (1, 1), "c": (0, "red"), "z": (2, 0.3)},
        {"t": (1, 1), "c": (1, "green"), "z": (1, 0.2)},
        {"t": (1, 1), "c": (2, "blue"), "z": (0, 0.1)},
        {"t": (1, 1), "c": (2, "blue"), "z": (1, 0.2)},
        {"t": (1, 1), "c": (2, "blue"), "z": (2, 0.3)},
        {"t": (2, 2), "c": (0, "red"), "z": (0, 0.1)},
        {"t": (2, 2), "c": (0, "red"), "z": (1, 0.2)},
        {"t": (2, 2), "c": (0, "red"), "z": (2, 0.3)},
        {"t": (2, 2), "c": (1, "green"), "z": (1, 0.2)},
        {"t": (2, 2), "c": (2, "blue"), "z": (0, 0.1)},
        {"t": (2, 2), "c": (2, "blue"), "z": (1, 0.2)},
        {"t": (2, 2), "c": (2, "blue"), "z": (2, 0.3)},
    ]


def test_all_together() -> None:
    t1_overrides = AxesIterator(
        value=1,
        axes=(
            SimpleValueAxis(axis_key="c", values=["red", "blue"]),
            SimpleValueAxis(axis_key="z", values=[7, 8, 9]),
        ),
    )
    c_blue_subseq = AxesIterator(
        value="blue",
        axes=(SimpleValueAxis(axis_key="q", values=["a", "b"]),),
    )
    multi_dim = AxesIterator(
        axes=(
            SimpleValueAxis(axis_key="t", values=[0, t1_overrides, 2]),
            SimpleValueAxis(axis_key="c", values=["red", "green", c_blue_subseq]),
            FilteredZ([0.1, 0.2, 0.3]),
        ),
    )

    assert multi_dim.is_finite()
    result = _index_and_values(multi_dim)
    assert result == [
        {"t": (0, 0), "c": (0, "red"), "z": (0, 0.1)},
        {"t": (0, 0), "c": (0, "red"), "z": (1, 0.2)},
        {"t": (0, 0), "c": (0, "red"), "z": (2, 0.3)},
        {"t": (0, 0), "c": (1, "green"), "z": (1, 0.2)},
        {"t": (0, 0), "c": (2, "blue"), "z": (0, 0.1), "q": (0, "a")},
        {"t": (0, 0), "c": (2, "blue"), "z": (0, 0.1), "q": (1, "b")},
        {"t": (0, 0), "c": (2, "blue"), "z": (1, 0.2), "q": (0, "a")},
        {"t": (0, 0), "c": (2, "blue"), "z": (1, 0.2), "q": (1, "b")},
        {"t": (0, 0), "c": (2, "blue"), "z": (2, 0.3), "q": (0, "a")},
        {"t": (0, 0), "c": (2, "blue"), "z": (2, 0.3), "q": (1, "b")},
        {"t": (1, 1), "c": (0, "red"), "z": (0, 7)},
        {"t": (1, 1), "c": (0, "red"), "z": (1, 8)},
        {"t": (1, 1), "c": (0, "red"), "z": (2, 9)},
        {"t": (1, 1), "c": (1, "blue"), "z": (0, 7)},
        {"t": (1, 1), "c": (1, "blue"), "z": (1, 8)},
        {"t": (1, 1), "c": (1, "blue"), "z": (2, 9)},
        {"t": (2, 2), "c": (0, "red"), "z": (0, 0.1)},
        {"t": (2, 2), "c": (0, "red"), "z": (1, 0.2)},
        {"t": (2, 2), "c": (0, "red"), "z": (2, 0.3)},
        {"t": (2, 2), "c": (1, "green"), "z": (1, 0.2)},
        {"t": (2, 2), "c": (2, "blue"), "z": (0, 0.1), "q": (0, "a")},
        {"t": (2, 2), "c": (2, "blue"), "z": (0, 0.1), "q": (1, "b")},
        {"t": (2, 2), "c": (2, "blue"), "z": (1, 0.2), "q": (0, "a")},
        {"t": (2, 2), "c": (2, "blue"), "z": (1, 0.2), "q": (1, "b")},
        {"t": (2, 2), "c": (2, "blue"), "z": (2, 0.3), "q": (0, "a")},
        {"t": (2, 2), "c": (2, "blue"), "z": (2, 0.3), "q": (1, "b")},
    ]


def test_new_multidim_with_infinite_axis() -> None:
    # note... we never progress to t=1
    multi_dim = AxesIterator(
        axes=(
            SimpleValueAxis(axis_key=Axis.TIME, values=[0, 1]),
            InfiniteAxis(),
            SimpleValueAxis(axis_key=Axis.Z, values=[0.1, 0.3]),
        )
    )

    assert not multi_dim.is_finite()
    result = _index_and_values(multi_dim, max_iters=10)
    assert result == [
        {"t": (0, 0), "i": (0, 0), "z": (0, 0.1)},
        {"t": (0, 0), "i": (0, 0), "z": (1, 0.3)},
        {"t": (0, 0), "i": (1, 1), "z": (0, 0.1)},
        {"t": (0, 0), "i": (1, 1), "z": (1, 0.3)},
        {"t": (0, 0), "i": (2, 2), "z": (0, 0.1)},
        {"t": (0, 0), "i": (2, 2), "z": (1, 0.3)},
        {"t": (0, 0), "i": (3, 3), "z": (0, 0.1)},
        {"t": (0, 0), "i": (3, 3), "z": (1, 0.3)},
        {"t": (0, 0), "i": (4, 4), "z": (0, 0.1)},
        {"t": (0, 0), "i": (4, 4), "z": (1, 0.3)},
    ]


class DynamicROIAxis(SimpleValueAxis[str]):
    axis_key: str = "r"
    values: list[str] = Field(default_factory=lambda: ["cell0", "cell1"])

    # we add a new roi at each time step
    def __iter__(self) -> Iterator[str]:
        yield from self.values
        self.values.append(f"cell{len(self.values)}")


def test_dynamic_roi_addition() -> None:
    multi_dim = AxesIterator(axes=(InfiniteAxis(), DynamicROIAxis()))

    assert not multi_dim.is_finite()
    result = _index_and_values(multi_dim, max_iters=16)
    assert result == [
        {"i": (0, 0), "r": (0, "cell0")},
        {"i": (0, 0), "r": (1, "cell1")},
        {"i": (1, 1), "r": (0, "cell0")},
        {"i": (1, 1), "r": (1, "cell1")},
        {"i": (1, 1), "r": (2, "cell2")},
        {"i": (2, 2), "r": (0, "cell0")},
        {"i": (2, 2), "r": (1, "cell1")},
        {"i": (2, 2), "r": (2, "cell2")},
        {"i": (2, 2), "r": (3, "cell3")},
        {"i": (3, 3), "r": (0, "cell0")},
        {"i": (3, 3), "r": (1, "cell1")},
        {"i": (3, 3), "r": (2, "cell2")},
        {"i": (3, 3), "r": (3, "cell3")},
        {"i": (3, 3), "r": (4, "cell4")},
        {"i": (4, 4), "r": (0, "cell0")},
        {"i": (4, 4), "r": (1, "cell1")},
    ]
