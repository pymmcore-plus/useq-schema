from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from useq.new._multidim_seq import AxisIterable, MultiDimSequence

if TYPE_CHECKING:
    from collections.abc import Iterator

    from useq.new._multidim_seq import AxesIndex


V = TypeVar("V", covariant=True)


def order_axes(
    seq: MultiDimSequence,
    parent_order: tuple[str, ...] | None = None,
) -> list[AxisIterable]:
    """Returns the axes of a MultiDimSequence in the order specified by seq.axis_order.

    If not provided, order by the parent's order (if given), or in the declared order.
    """
    if order := seq.axis_order if seq.axis_order is not None else parent_order:
        axes_map = {axis.axis_key: axis for axis in seq.axes}
        return [axes_map[key] for key in order if key in axes_map]
    return list(seq.axes)


def iterate_axes_recursive(
    axes: list[AxisIterable],
    prefix: AxesIndex | None = None,
    parent_order: tuple[str, ...] | None = None,
) -> Iterator[AxesIndex]:
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
            yield prefix
        return

    current_axis, *remaining_axes = axes

    for idx, item in enumerate(current_axis.iter()):
        if isinstance(item, MultiDimSequence) and item.value is not None:
            value = item.value
            override_keys = {ax.axis_key for ax in item.axes}
            updated_axes = [
                ax for ax in remaining_axes if ax.axis_key not in override_keys
            ] + order_axes(item, parent_order=parent_order)
        else:
            value = item
            updated_axes = remaining_axes

        yield from iterate_axes_recursive(
            updated_axes,
            {**prefix, current_axis.axis_key: (idx, value, current_axis)},
            parent_order=parent_order,
        )


def iterate_multi_dim_sequence(
    seq: MultiDimSequence, axis_order: tuple[str, ...] | None = None
) -> Iterator[AxesIndex]:
    """Iterate over a MultiDimSequence.

    Orders the base axes (if an axis_order is provided) and then iterates
    over all index combinations using iterate_axes_recursive.
    The parent's axis_order is passed down to nested sequences.

    Yields
    ------
    AxesIndex
        A dictionary mapping axis keys to tuples of (index, value, axis).
        The index is the position in the axis, the value is the corresponding
        value at that index, and the axis is the AxisIterable object itself.
    """
    if axis_order is None:
        axis_order = seq.axis_order
    ordered_axes = order_axes(seq, axis_order)
    yield from iterate_axes_recursive(ordered_axes, parent_order=axis_order)
