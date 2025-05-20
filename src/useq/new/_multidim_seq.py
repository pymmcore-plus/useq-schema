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
  each axis is given an opportunity (via the `should_skip` method) to veto that
  combination. By default, `SimpleAxis.should_skip` returns False, but you can override
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
   Here the "t" axis yields a nested MultiDimSequence that adds an extra "q" axis.

    >>> multi_dim = MultiDimSequence(
    ...     axes=(
    ...         SimpleAxis("t", [
    ...             0,
    ...             MultiDimSequence(
    ...                 value=1,
    ...                 axes=(SimpleAxis("q", ["a", "b"]),),
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
    {'t': (1, 1), 'c': (0, 'red'), 'q': (0, 'a')}
    {'t': (1, 1), 'c': (0, 'red'), 'q': (1, 'b')}
    {'t': (1, 1), 'c': (1, 'green'), 'q': (0, 'a')}
    ... (and so on)

3. Overriding Parent Axes:
   Here the "t" axis yields a nested MultiDimSequence whose axes override the parent's
   "z" axis.

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
   By subclassing SimpleAxis to override should_skip, you can filter out combinations.
   For example, suppose we want to skip any combination where "c" equals "green" and "z" is not 0.2:

    >>> class FilteredZ(SimpleAxis):
    ...     def should_skip(self, prefix: dict[str, tuple[int, Any, AxisIterable]]) -> bool:
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
- The should_skip mechanism gives each axis an opportunity to veto a final combination.
  By default, SimpleAxis does not skip any combination, but you can subclass it to implement
  custom filtering logic.

This module is intended for cases where complex, declarative multidimensional iteration is
required—such as in microscope acquisitions, high-content imaging, or other experimental designs
where the sequence of events must be generated in a flexible, hierarchical manner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from useq.new._axis_iterable import AxisIterable, V

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


class SimpleAxis(AxisIterable[V]):
    """A basic axis implementation that yields values directly.

    If a value needs to declare sub-axes, yield a nested MultiDimSequence.
    The default should_skip always returns False.
    """

    def __init__(self, axis_key: str, values: Iterable[V]) -> None:
        self._axis_key = axis_key
        self.values = values

    @property
    def axis_key(self) -> str:
        return self._axis_key

    def __iter__(self) -> Iterator[V | MultiDimSequence]:
        yield from self.values

    def should_skip(self, prefix: dict[str, tuple[int, Any, AxisIterable]]) -> bool:
        return False


class MultiDimSequence(BaseModel):
    """Represents a multidimensional sequence.

    At the top level the `value` field is ignored.
    When used as a nested override, `value` is the value for that branch and
    its axes are iterated using its own axis_order if provided;
    otherwise, it inherits the parent's axis_order.
    """

    axes: tuple[AxisIterable, ...] = ()
    axis_order: tuple[str, ...] | None = None
    value: Any = None

    model_config = {"arbitrary_types_allowed": True}
