from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    NamedTuple,
    Protocol,
    Union,
    runtime_checkable,
)

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


@runtime_checkable
class AxisIterable(Protocol):
    @property
    def axis_key(self) -> str:
        """A string id representing the axis."""

    def __iter__(self) -> Iterator[Union[Any, AxisValue]]:
        """Iterate over the axis, yielding either plain values or AxisValue instances."""


class AxisValue(NamedTuple):
    """
    Wraps a value and optionally declares sub-axes that should be iterated
    when this value is yielded.
    """

    value: Any
    sub_axes: Iterable[AxisIterable] | None = None


class SimpleAxis:
    """
    A basic axis implementation that yields values directly.
    If a value needs to declare sub-axes, it should be wrapped in an AxisValue.
    """

    def __init__(self, axis_key: str, values: list[Any]) -> None:
        self._axis_key = axis_key
        self.values = values

    @property
    def axis_key(self) -> str:
        return self._axis_key

    def __iter__(self) -> Iterator[Union[Any, AxisValue]]:
        yield from self.values

    def __len__(self) -> int:
        return len(self.values)


class MultiDimSequence(BaseModel):
    axes: tuple[AxisIterable, ...] = ()
    axis_order: tuple[str, ...] | None = None

    model_config = {"arbitrary_types_allowed": True}


def iterate_axes_recursive(
    axes: list[AxisIterable], prefix: dict[str, tuple[int, Any]] | None = None
) -> Iterator[dict[str, tuple[int, Any]]]:
    """
    Recursively iterate over the list of axes one at a time.

    If the current axis yields an AxisValue with sub-axes, then override any
    remaining outer axes whose keys match those sub-axes. The sub-axes are then
    appended after the filtered outer axes so that the global ordering is preserved.
    """
    if prefix is None:
        prefix = {}

    if not axes:
        yield prefix
        return

    current_axis = axes[0]
    remaining_axes = axes[1:]

    for idx, item in enumerate(current_axis):
        new_prefix = prefix.copy()
        if isinstance(item, AxisValue) and item.sub_axes:
            new_prefix[current_axis.axis_key] = (idx, item.value)
            # Compute the override keys from the sub-axes.
            override_keys = {ax.axis_key for ax in item.sub_axes}
            # Remove from the remaining axes any axis whose key is overridden.
            filtered_remaining = [
                ax for ax in remaining_axes if ax.axis_key not in override_keys
            ]
            # Append the sub-axes *after* the filtered remaining axes.
            new_axes = filtered_remaining + list(item.sub_axes)
            yield from iterate_axes_recursive(new_axes, new_prefix)
        else:
            new_prefix[current_axis.axis_key] = (idx, item)
            yield from iterate_axes_recursive(remaining_axes, new_prefix)


def iterate_multi_dim_sequence(
    seq: MultiDimSequence,
) -> Iterator[dict[str, tuple[int, Any]]]:
    """
    Orders the base axes (if an axis_order is provided) and then iterates
    over all index combinations using iterate_axes_recursive.
    """
    if seq.axis_order:
        axes_map = {axis.axis_key: axis for axis in seq.axes}
        ordered_axes = [axes_map[key] for key in seq.axis_order if key in axes_map]
    else:
        ordered_axes = list(seq.axes)
    yield from iterate_axes_recursive(ordered_axes)


# Example usage:
if __name__ == "__main__":
    # In this example, the "t" axis yields an AxisValue for 1 that provides sub-axes
    # overriding the outer "z" axis. The expected behavior is that for t == 1,
    # the outer "z" axis is replaced by the sub-axis "z" (yielding [7, 8, 9]),
    # while for t == 0 and t == 2 the outer "z" ([0, 1]) is used.
    multi_dim = MultiDimSequence(
        axes=(
            SimpleAxis(
                "t",
                [
                    0,
                    AxisValue(
                        1,
                        sub_axes=[
                            SimpleAxis("g", ["a1", "a2"]),
                            SimpleAxis("z", [7, 8, 9]),
                        ],
                    ),
                    2,
                ],
            ),
            SimpleAxis("c", ["red", "green", "blue"]),
            SimpleAxis("z", [0.1, 0.2]),
        ),
        axis_order=("z", "t", "c"),
    )

    for indices in iterate_multi_dim_sequence(multi_dim):
        print(indices)
