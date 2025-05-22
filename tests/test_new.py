from __future__ import annotations

from typing import TYPE_CHECKING, Any

from useq import Axis
from useq.new import MultiDimSequence, SimpleAxis, iterate_multi_dim_sequence

if TYPE_CHECKING:
    from collections.abc import Iterable

    from useq.new._iterate import AxesIndex


def index_and_values(
    multi_dim: MultiDimSequence, axis_order: tuple[str, ...] | None = None
) -> list[dict[str, tuple[int, Any]]]:
    """Return a list of indices and values for each axis in the MultiDimSequence."""
    # cleaned version that drops the axis objects.
    return [
        {k: (idx, val) for k, (idx, val, _) in indices.items()}
        for indices in iterate_multi_dim_sequence(multi_dim, axis_order=axis_order)
    ]


def test_new_multidim_simple_seq() -> None:
    multi_dim = MultiDimSequence(
        axes=(
            SimpleAxis(axis_key=Axis.TIME, values=[0, 1]),
            SimpleAxis(axis_key=Axis.CHANNEL, values=["red", "green", "blue"]),
            SimpleAxis(axis_key=Axis.Z, values=[0.1, 0.3]),
        )
    )

    result = index_and_values(multi_dim)
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


def test_multidim_nested_seq() -> None:
    inner_seq = MultiDimSequence(
        value=1, axes=(SimpleAxis(axis_key="q", values=["a", "b"]),)
    )
    outer_seq = MultiDimSequence(
        axes=(
            SimpleAxis(axis_key="t", values=[0, inner_seq, 2]),
            SimpleAxis(axis_key="c", values=["red", "green", "blue"]),
        )
    )

    result = index_and_values(outer_seq)
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

    result = index_and_values(outer_seq, axis_order=("t", "c"))
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
    inner_seq = MultiDimSequence(
        value=1,
        axes=(
            SimpleAxis(axis_key="c", values=["red", "blue"]),
            SimpleAxis(axis_key="z", values=[7, 8, 9]),
        ),
    )
    multi_dim = MultiDimSequence(
        axes=(
            SimpleAxis(axis_key="t", values=[0, inner_seq, 2]),
            SimpleAxis(axis_key="c", values=["red", "green", "blue"]),
            SimpleAxis(axis_key="z", values=[0.1, 0.2]),
        ),
        axis_order=("t", "c", "z"),
    )

    result = index_and_values(multi_dim)
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


class FilteredZ(SimpleAxis):
    def __init__(self, values: Iterable) -> None:
        super().__init__(axis_key=Axis.Z, values=values)

    def should_skip(self, prefix: AxesIndex) -> bool:
        # If c is green, then only allow combinations where z equals 0.2.
        c_val = prefix.get(Axis.CHANNEL, (None, None))[1]
        z_val = prefix.get(Axis.Z, (None, None))[1]
        return bool(c_val == "green" and z_val != 0.2)


def test_multidim_with_should_skip() -> None:
    multi_dim = MultiDimSequence(
        axes=(
            SimpleAxis(Axis.TIME, [0, 1, 2]),
            SimpleAxis(Axis.CHANNEL, ["red", "green", "blue"]),
            FilteredZ([0.1, 0.2, 0.3]),
        ),
        axis_order=(Axis.TIME, Axis.CHANNEL, Axis.Z),
    )

    result = index_and_values(multi_dim)

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
    t1_overrides = MultiDimSequence(
        value=1,
        axes=(
            SimpleAxis(axis_key="c", values=["red", "blue"]),
            SimpleAxis(axis_key="z", values=[7, 8, 9]),
        ),
    )
    c_blue_subseq = MultiDimSequence(
        value="blue",
        axes=(SimpleAxis(axis_key="q", values=["a", "b"]),),
    )
    multi_dim = MultiDimSequence(
        axes=(
            SimpleAxis(axis_key="t", values=[0, t1_overrides, 2]),
            SimpleAxis(axis_key="c", values=["red", "green", c_blue_subseq]),
            FilteredZ([0.1, 0.2, 0.3]),
        ),
    )

    result = index_and_values(multi_dim)
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
