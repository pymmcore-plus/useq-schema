from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol, Union, runtime_checkable

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator


@runtime_checkable
class AxisIterable(Protocol):
    @property
    def axis_key(self) -> str:
        """A string id representing the axis."""

    def __iter__(self) -> Iterator[Union[Any, MultiDimSequence]]:
        """Iterate over the axis, yielding either plain values or a nested MultiDimSequence."""


class SimpleAxis:
    """A basic axis implementation that yields values directly.

    If a value needs to declare sub-axes, yield a nested MultiDimSequence.
    """

    def __init__(self, axis_key: str, values: list[Any]) -> None:
        self._axis_key = axis_key
        self.values = values

    @property
    def axis_key(self) -> str:
        return self._axis_key

    def __iter__(self) -> Iterator[Union[Any, MultiDimSequence]]:
        yield from self.values


class MultiDimSequence(BaseModel):
    """
    Represents a multidimensional sequence.

    At the top level the `value` field is ignored.
    When used as a nested override, `value` is the value for that branch and
    its axes are iterated using its own axis_order if provided;
    otherwise, it inherits the parent's axis_order.
    """

    value: Any = None
    axes: tuple[AxisIterable, ...] = ()
    axis_order: tuple[str, ...] | None = None

    model_config = {"arbitrary_types_allowed": True}


def order_axes(
    seq: MultiDimSequence,
    parent_order: Optional[tuple[str, ...]] = None,
) -> list[AxisIterable]:
    """Returns the axes of a MultiDimSequence in the order specified by seq.axis_order.

    or if not provided, by the parent's order (if given), or in the declared order.
    """
    if order := seq.axis_order if seq.axis_order is not None else parent_order:
        axes_map = {axis.axis_key: axis for axis in seq.axes}
        return [axes_map[key] for key in order if key in axes_map]
    return list(seq.axes)


def iterate_axes_recursive(
    axes: list[AxisIterable],
    prefix: dict[str, tuple[int, Any]] | None = None,
    parent_order: Optional[tuple[str, ...]] = None,
) -> Iterator[dict[str, tuple[int, Any]]]:
    """Recursively iterate over a list of axes one at a time.

    If an axis yields a nested MultiDimSequence with a non-None value,
    that nested sequence acts as an override for its axis key.
    The parent's remaining axes having matching keys are removed, and the nested
    sequence's axes (ordered by its own axis_order if provided, or else the parent's)
    are appended.
    """
    if prefix is None:
        prefix = {}

    if not axes:
        yield prefix
        return

    current_axis, *remaining_axes = axes

    for idx, item in enumerate(current_axis):
        new_prefix = prefix.copy()
        if isinstance(item, MultiDimSequence) and item.value is not None:
            new_prefix[current_axis.axis_key] = (idx, item.value)
            # Determine override keys from the nested sequence's axes.
            override_keys = {ax.axis_key for ax in item.axes}
            # Remove from the remaining axes any axis whose key is overridden.
            filtered_remaining = [
                ax for ax in remaining_axes if ax.axis_key not in override_keys
            ]
            # Get the nested sequence's axes, using the parent's order if none is provided.
            new_axes = filtered_remaining + order_axes(item, parent_order=parent_order)
            yield from iterate_axes_recursive(
                new_axes,
                new_prefix,
                parent_order=parent_order,
            )
        else:
            new_prefix[current_axis.axis_key] = (idx, item)
            yield from iterate_axes_recursive(
                remaining_axes,
                new_prefix,
                parent_order=parent_order,
            )


def iterate_multi_dim_sequence(
    seq: MultiDimSequence,
) -> Iterator[dict[str, tuple[int, Any]]]:
    """
    Orders the base axes (if an axis_order is provided) and then iterates
    over all index combinations using iterate_axes_recursive.
    The parent's axis_order is passed down to nested sequences.
    """
    ordered_axes = order_axes(seq, seq.axis_order)
    yield from iterate_axes_recursive(ordered_axes, parent_order=seq.axis_order)


# Example usage:
if __name__ == "__main__":
    # In this example, the "t" axis yields a nested MultiDimSequence for the value 1.
    # That nested sequence (with its own axis_order) provides a new definition for "z",
    # effectively overriding the outer "z" axis when t==1.
    multi_dim = MultiDimSequence(
        axes=(
            SimpleAxis(
                "t",
                [
                    0,
                    MultiDimSequence(
                        value=1,
                        axes=[
                            SimpleAxis("c", ["red", "blue"]),
                            SimpleAxis("z", [7, 8, 9]),
                        ],
                    ),
                    2,
                ],
            ),
            SimpleAxis("c", ["red", "green", "blue"]),
            SimpleAxis("z", [0.1, 0.2]),
        ),
        axis_order=("t", "c", "z"),
    )

    for indices in iterate_multi_dim_sequence(multi_dim):
        print(indices)
