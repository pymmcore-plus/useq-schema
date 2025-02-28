"""MultiDimensional Iteration Module.

This module provides a declarative approach to multi-dimensional iteration,
supporting hierarchical (nested) sub-iterations as well as conditional
skipping (filtering) of final combinations.

Key Concepts:
-------------
- **AxisIterable**: An interface (protocol) representing an axis. Each axis
  has a unique `axis_key` and yields values via its iterator. A concrete axis,
  such as `SimpleAxis`, yields plain values. To express sub-iterations,
  an axis may yield a nested `MultiDimSequence` (instead of a plain value).

- **MultiDimSequence**: Represents a multi-dimensional experiment or sequence.
  It contains a tuple of axes (AxisIterable objects) and an optional `axis_order`
  that controls the order in which axes are processed. When used as a nested override,
  its `value` field is used as the representative value for that branch, and its
  axes override or extend the parent's axes.

- **Nested Overrides**: When an axis yields a nested MultiDimSequence with a non-None
  `value`, that nested sequence acts as an override for the parent's iteration.
  Specifically, the parent's remaining axes that have keys matching those in the
  nested sequence are removed, and the nested sequence's axes (ordered by its own
  `axis_order`, or inheriting the parent's if not provided) are appended.

- **Prefix and Skip Logic**: As the recursion proceeds, a `prefix` is built up, mapping
  axis keys to a triple: (index, value, axis). Before yielding a final combination,
  each axis is given an opportunity (via the `skip_combination` method) to veto that
  combination. By default, `SimpleAxis.skip_combination` returns False, but you can override
  it in a subclass to implement conditional skipping.

Usage Examples:
---------------
1. Basic Iteration (no nested sequences):

    >>> multi_dim = MultiDimSequence(
    ...     axes=(
    ...         SimpleAxis("t", [0, 1, 2]),
    ...         SimpleAxis("c", ["red", "green", "blue"]),
    ...         SimpleAxis("z", [0.1, 0.2]),
    ...     ),
    ...     axis_order=("t", "c", "z"),
    ... )
    >>> for combo in iterate_multi_dim_sequence(multi_dim):
    ...     # Clean the prefix for display (dropping the axis objects)
    ...     print({k: (idx, val) for k, (idx, val, _) in combo.items()})
    {'t': (0, 0), 'c': (0, 'red'), 'z': (0, 0.1)}
    {'t': (0, 0), 'c': (0, 'red'), 'z': (1, 0.2)}
    ... (and so on for all Cartesian products)

2. Sub-Iteration Adding New Axes:
   Here the "t" axis yields a nested MultiDimSequence that adds an extra "extra" axis.

    >>> multi_dim = MultiDimSequence(
    ...     axes=(
    ...         SimpleAxis("t", [
    ...             0,
    ...             MultiDimSequence(
    ...                 value=1,
    ...                 axes=(SimpleAxis("extra", ["a", "b"]),),
    ...             ),
    ...             2,
    ...         ]),
    ...         SimpleAxis("c", ["red", "green", "blue"]),
    ...     ),
    ...     axis_order=("t", "c"),
    ... )
    >>> for combo in iterate_multi_dim_sequence(multi_dim):
    ...     print({k: (idx, val) for k, (idx, val, _) in combo.items()})
    {'t': (0, 0), 'c': (0, 'red')}
    {'t': (0, 0), 'c': (1, 'green')}
    {'t': (0, 0), 'c': (2, 'blue')}
    {'t': (1, 1), 'c': (0, 'red'), 'extra': (0, 'a')}
    {'t': (1, 1), 'c': (0, 'red'), 'extra': (1, 'b')}
    {'t': (1, 1), 'c': (1, 'green'), 'extra': (0, 'a')}
    ... (and so on)

3. Overriding Parent Axes:
   Here the "t" axis yields a nested MultiDimSequence whose axes override the parent's "z" axis.

    >>> multi_dim = MultiDimSequence(
    ...     axes=(
    ...         SimpleAxis("t", [
    ...             0,
    ...             MultiDimSequence(
    ...                 value=1,
    ...                 axes=(
    ...                     SimpleAxis("c", ["red", "blue"]),
    ...                     SimpleAxis("z", [7, 8, 9]),
    ...                 ),
    ...                 axis_order=("c", "z"),
    ...             ),
    ...             2,
    ...         ]),
    ...         SimpleAxis("c", ["red", "green", "blue"]),
    ...         SimpleAxis("z", [0.1, 0.2]),
    ...     ),
    ...     axis_order=("t", "c", "z"),
    ... )
    >>> for combo in iterate_multi_dim_sequence(multi_dim):
    ...     print({k: (idx, val) for k, (idx, val, _) in combo.items()})
    {'t': (0, 0), 'c': (0, 'red'), 'z': (0, 0.1)}
    ... (normal combinations for t==0 and t==2)
    {'t': (1, 1), 'c': (0, 'red'), 'z': (0, 7)}
    {'t': (1, 1), 'c': (0, 'red'), 'z': (1, 8)}
    {'t': (1, 1), 'c': (0, 'red'), 'z': (2, 9)}
    {'t': (1, 1), 'c': (1, 'blue'), 'z': (0, 7)}
    ... (and so on)

4. Conditional Skipping:
   By subclassing SimpleAxis to override skip_combination, you can filter out combinations.
   For example, suppose we want to skip any combination where "c" equals "green" and "z" is not 0.2:

    >>> class FilteredZ(SimpleAxis):
    ...     def skip_combination(self, prefix: dict[str, tuple[int, Any, AxisIterable]]) -> bool:
    ...         c_val = prefix.get("c", (None, None, None))[1]
    ...         z_val = prefix.get("z", (None, None, None))[1]
    ...         if c_val == "green" and z_val != 0.2:
    ...             return True
    ...         return False
    ...
    >>> multi_dim = MultiDimSequence(
    ...     axes=(
    ...         SimpleAxis("t", [0, 1, 2]),
    ...         SimpleAxis("c", ["red", "green", "blue"]),
    ...         FilteredZ("z", [0.1, 0.2]),
    ...     ),
    ...     axis_order=("t", "c", "z"),
    ... )
    >>> for combo in iterate_multi_dim_sequence(multi_dim):
    ...     print({k: (idx, val) for k, (idx, val, _) in combo.items()})
    (Only those combinations where if c is green then z equals 0.2 are printed.)

Usage Notes:
------------
- The module assumes that each axis is finite and that the final prefix (the combination)
  is built by processing one axis at a time. Nested MultiDimSequence objects allow you to
  either extend the iteration with new axes or override existing ones.
- The ordering of axes is controlled via the `axis_order` property, which is inherited
  by nested sequences if not explicitly provided.
- The skip_combination mechanism gives each axis an opportunity to veto a final combination.
  By default, SimpleAxis does not skip any combination, but you can subclass it to implement
  custom filtering logic.

This module is intended for cases where complex, declarative multidimensional iteration is
required—such as in microscope acquisitions, high-content imaging, or other experimental designs
where the sequence of events must be generated in a flexible, hierarchical manner.
"""

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
        """Iterate over the axis.

        If a value needs to declare sub-axes, yield a nested MultiDimSequence.
        """

    def skip_combination(
        self,
        prefix: dict[str, tuple[int, Any, AxisIterable]],
    ) -> bool:
        """Return True if this axis wants to skip the combination.

        Default implementation returns False.
        """
        return False


class SimpleAxis:
    """A basic axis implementation that yields values directly.

    If a value needs to declare sub-axes, yield a nested MultiDimSequence.
    The default skip_combination always returns False.
    """

    def __init__(self, axis_key: str, values: list[Any]) -> None:
        self._axis_key = axis_key
        self.values = values

    @property
    def axis_key(self) -> str:
        return self._axis_key

    def __iter__(self) -> Iterator[Union[Any, MultiDimSequence]]:
        yield from self.values

    def skip_combination(
        self, prefix: dict[str, tuple[int, Any, AxisIterable]]
    ) -> bool:
        return False


class MultiDimSequence(BaseModel):
    """Represents a multidimensional sequence.

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

    If not provided, order by the parent's order (if given), or in the declared order.
    """
    if order := seq.axis_order if seq.axis_order is not None else parent_order:
        axes_map = {axis.axis_key: axis for axis in seq.axes}
        return [axes_map[key] for key in order if key in axes_map]
    return list(seq.axes)


def iterate_axes_recursive(
    axes: list[AxisIterable],
    prefix: dict[str, tuple[int, Any, AxisIterable]] | None = None,
    parent_order: Optional[tuple[str, ...]] = None,
) -> Iterator[dict[str, tuple[int, Any, AxisIterable]]]:
    """Recursively iterate over a list of axes one at a time.

    If an axis yields a nested MultiDimSequence with a non-None value,
    that nested sequence acts as an override for its axis key.
    The parent's remaining axes having matching keys are removed, and the nested
    sequence's axes (ordered by its own axis_order if provided, or else the parent's)
    are appended.

    Before yielding a final combination (when no axes remain), we call skip_combination
    on each axis (using the full prefix).
    """
    if prefix is None:
        prefix = {}
    if not axes:
        # Ask each axis in the prefix if the combination should be skipped
        if not any(axis.skip_combination(prefix) for *_, axis in prefix.values()):
            yield prefix
        return

    current_axis, *remaining_axes = axes

    for idx, item in enumerate(current_axis):
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
    seq: MultiDimSequence,
) -> Iterator[dict[str, tuple[int, Any, AxisIterable]]]:
    """Iterate over a MultiDimSequence.

    Orders the base axes (if an axis_order is provided) and then iterates
    over all index combinations using iterate_axes_recursive.
    The parent's axis_order is passed down to nested sequences.
    """
    ordered_axes = order_axes(seq, seq.axis_order)
    yield from iterate_axes_recursive(ordered_axes, parent_order=seq.axis_order)


# Example usage:
if __name__ == "__main__":
    # A simple test: no overrides, just yield combinations.
    multi_dim = MultiDimSequence(
        axes=(
            SimpleAxis("t", [0, 1, 2]),
            SimpleAxis("c", ["red", "green", "blue"]),
            SimpleAxis("z", [0.1, 0.2, 0.3]),
        ),
        axis_order=("t", "c", "z"),
    )

    for indices in iterate_multi_dim_sequence(multi_dim):
        # Print a cleaned version that drops the axis objects.
        clean = {k: v[:2] for k, v in indices.items()}
        print(clean)
    print("-------------")

    # As an example, we override skip_combination for the "z" axis:
    class FilteredZ(SimpleAxis):
        def skip_combination(self, prefix: dict[str, tuple[int, Any]]) -> bool:
            # If c is green, then only allow combinations where z equals 0.2.
            # Get the c value from the prefix:
            c_val = prefix.get("c", (None, None))[1]
            z_val = prefix.get("z", (None, None))[1]
            return bool(c_val == "green" and z_val != 0.2)

    multi_dim = MultiDimSequence(
        axes=(
            SimpleAxis("t", [0, 1, 2]),
            SimpleAxis("c", ["red", "green", "blue"]),
            FilteredZ("z", [0.1, 0.2, 0.3]),
        ),
        axis_order=("t", "c", "z"),
    )
    for indices in iterate_multi_dim_sequence(multi_dim):
        # Print a cleaned version that drops the axis objects.
        clean = {k: v[:2] for k, v in indices.items()}
        print(clean)
