from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from useq.v2._axes_iterator import AxisIterable, MultiAxisSequence

if TYPE_CHECKING:
    from collections.abc import Iterator

    from useq.v2._axes_iterator import AxesIndex, AxesIndexWithContext


V = TypeVar("V", covariant=True)


def order_axes(
    seq: MultiAxisSequence,
    axis_order: tuple[str, ...] | None = None,
) -> list[AxisIterable]:
    """Returns the axes of a MultiDimSequence in the order specified by seq.axis_order.

    If axis_order is provided, it overrides the sequence's axis_order.
    """
    if axis_order is None:
        axis_order = seq.axis_order
    if axis_order:
        axes_map = {axis.axis_key: axis for axis in seq.axes}
        return [axes_map[key] for key in axis_order if key in axes_map]
    return list(seq.axes)


def iterate_axes_recursive(
    axes: list[AxisIterable],
    prefix: AxesIndex | None = None,
    parent_order: tuple[str, ...] | None = None,
    context: tuple[MultiAxisSequence, ...] = (),
) -> Iterator[AxesIndexWithContext]:
    """Recursively iterate over a list of axes one at a time.

    If an axis yields a nested MultiDimSequence with a non-None value,
    that nested sequence acts as an override for its axis key.
    The parent's remaining axes having matching keys are removed, and the nested
    sequence's axes (ordered by its own axis_order if provided, or else the parent's)
    are appended.

    Before yielding a final combination (when no axes remain), we call should_skip
    on each axis (using the full prefix).
    """
    if prefix is None:
        prefix = {}

    if not axes:
        # Ask each axis in the prefix if the combination should be skipped
        if not any(axis.should_skip(prefix) for *_, axis in prefix.values()):
            yield prefix, context
        return

    current_axis, *remaining_axes = axes

    for idx, item in enumerate(current_axis):
        if isinstance(item, MultiAxisSequence):
            if item.value is None:
                raise NotImplementedError("Nested sequences must have a value.")

            value = item.value
            override_keys = {ax.axis_key for ax in item.axes}
            order = item.axis_order if item.axis_order is not None else parent_order

            # Remove axes from the parent that are overridden by the nested sequence,
            # then append the axes from the nested sequence in the correct order.
            parent_axes_not_overridden = [
                ax for ax in remaining_axes if ax.axis_key not in override_keys
            ]
            nested_axes_in_order = order_axes(item, order)
            updated_axes = parent_axes_not_overridden + nested_axes_in_order

            # Use the nested sequence as the new context
            context = (*context, item)
        else:
            value = item
            updated_axes = remaining_axes

        yield from iterate_axes_recursive(
            updated_axes,
            {**prefix, current_axis.axis_key: (idx, value, current_axis)},
            parent_order=parent_order,
            context=context,
        )


def iterate_multi_dim_sequence(
    seq: MultiAxisSequence, axis_order: tuple[str, ...] | None = None
) -> Iterator[AxesIndexWithContext]:
    """Iterate over a MultiDimSequence.

    Orders the base axes (if an axis_order is provided) and then iterates
    over all index combinations using iterate_axes_recursive.
    The parent's axis_order is passed down to nested sequences.

    Yields
    ------
    AxesIndexWithContext
        A tuple of (AxesIndex, MultiAxisSequence) where AxesIndex is a dictionary
        mapping axis keys to tuples of (index, value, axis), and MultiAxisSequence
        is the context that generated this axes combination.
    """
    ordered_axes = order_axes(seq, axis_order)
    yield from iterate_axes_recursive(
        ordered_axes, parent_order=axis_order, context=(seq,)
    )
