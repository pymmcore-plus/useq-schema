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
   For example, suppose we want to skip any combination where "c" equals "green" and "z"
   is not 0.2:

    >>> class FilteredZ(SimpleAxis):
    ...     def should_skip(
    ...             self, prefix: dict[str, tuple[int, Any, AxisIterable]]
    ...         ) -> bool:
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
- The module assumes that each axis is finite and that the final prefix (the
  combination) is built by processing one axis at a time. Nested MultiDimSequence
  objects allow you to either extend the iteration with new axes or override existing
  ones.
- The ordering of axes is controlled via the `axis_order` property, which is inherited
  by nested sequences if not explicitly provided.
- The should_skip mechanism gives each axis an opportunity to veto a final combination.
  By default, SimpleAxis does not skip any combination, but you can subclass it to
  implement custom filtering logic.

This module is intended for cases where complex, declarative multidimensional iteration
is required—such as in microscope acquisitions, high-content imaging, or other
experimental designs where the sequence of events must be generated in a flexible,
hierarchical manner.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, GetCoreSchemaHandler, field_validator
from pydantic_core import core_schema

from useq._mda_event import MDAEvent

if TYPE_CHECKING:
    from typing import TypeAlias

    AxisKey: TypeAlias = str
    Value: TypeAlias = Any
    Index: TypeAlias = int
    AxesIndex: TypeAlias = dict[AxisKey, tuple[Index, Value, "AxisIterable"]]

    from collections.abc import Iterator

V = TypeVar("V")
EventT = TypeVar("EventT", covariant=True, bound=Any)


@runtime_checkable
class EventBuilder(Protocol[EventT]):
    """Callable that builds an event from an AxesIndex."""

    @abstractmethod
    def __call__(self, axes_index: AxesIndex) -> EventT:
        """Transform an AxesIndex into an event object."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Return the schema for the event builder."""
        return core_schema.is_instance_schema(EventBuilder)


class AxisIterable(BaseModel, Generic[V]):
    axis_key: str
    """A string id representing the axis."""

    @abstractmethod
    def iter(self) -> Iterator[V | MultiDimSequence]:
        """Iterate over the axis.

        If a value needs to declare sub-axes, yield a nested MultiDimSequence.
        """

    @abstractmethod
    def length(self) -> int:
        """Return the number of axis values.

        If the axis is infinite, return -1.
        """

    def should_skip(self, prefix: AxesIndex) -> bool:
        """Return True if this axis wants to skip the combination.

        Default implementation returns False.
        """
        return False

    @property
    def is_infinite(self) -> bool:
        """Return `True` if the sequence is infinite."""
        return self.length() == -1

    def contribute_to_mda_event(
        self, value: V, index: Mapping[str, int]
    ) -> dict[str, Any]:
        """Contribute data to the event being built.

        This method allows each axis to contribute its data to the final MDAEvent.
        The default implementation does nothing - subclasses should override
        to add their specific contributions.

        Parameters
        ----------
        value : V
            The value provided by this axis, for this iteration.

        Returns
        -------
        event_data : dict[str, Any]
            Data to be added to the MDAEvent, it is ultimately up to the
            EventBuilder to decide how to merge possibly conflicting contributions from
            different axes.
        """
        return {}


class SimpleAxis(AxisIterable[V]):
    """A basic axis implementation that yields values directly.

    If a value needs to declare sub-axes, yield a nested MultiDimSequence.
    The default should_skip always returns False.
    """

    values: list[V]

    def iter(self) -> Iterator[V | MultiDimSequence]:
        yield from self.values

    def length(self) -> int:
        """Return the number of axis values."""
        return len(self.values)


# Example concrete event builder for MDAEvent
class MDAEventBuilder(EventBuilder[MDAEvent]):
    """Builds MDAEvent objects from AxesIndex."""

    def __call__(self, axes_index: AxesIndex) -> Any:
        """Transform AxesIndex into MDAEvent using axis contributions."""
        index: dict[str, int] = {}
        contributions: list[tuple[str, dict[str, Any]]] = []

        # Let each axis contribute to the event
        for axis_key, (idx, value, axis) in axes_index.items():
            index[axis_key] = idx
            contribution = axis.contribute_to_mda_event(value, index)
            contributions.append((axis_key, contribution))

        return self._merge_contributions(index, contributions)

    def _merge_contributions(
        self, index: dict[str, int], contributions: list[tuple[str, dict[str, Any]]]
    ) -> MDAEvent:
        event_data: dict[str, Any] = {}
        abs_pos: dict[str, float] = {}

        # First pass: collect all contributions and detect conflicts
        for axis_key, contrib in contributions:
            for key, val in contrib.items():
                if key.endswith("_pos") and val is not None:
                    if key in abs_pos and abs_pos[key] != val:
                        raise ValueError(
                            f"Conflicting absolute position from {axis_key}: "
                            f"existing {key}={abs_pos[key]}, new {key}={val}"
                        )
                    abs_pos[key] = val
                elif key in event_data and event_data[key] != val:
                    # Could implement different strategies here
                    raise ValueError(f"Conflicting values for {key} from {axis_key}")
                else:
                    event_data[key] = val

        # Second pass: handle relative positions
        for _, contrib in contributions:
            for key, val in contrib.items():
                if key.endswith("_pos_rel") and val is not None:
                    abs_key = key.replace("_rel", "")
                    abs_pos.setdefault(abs_key, 0.0)
                    abs_pos[abs_key] += val

        # Merge final positions
        event_data.update(abs_pos)
        return MDAEvent(**event_data)


class _MultiDimSequence(BaseModel, Generic[EventT]):
    """Represents a multidimensional sequence.

    At the top level the `value` field is ignored.
    When used as a nested override, `value` is the value for that branch and
    its axes are iterated using its own axis_order if provided;
    otherwise, it inherits the parent's axis_order.
    """

    axes: tuple[AxisIterable, ...] = ()
    axis_order: tuple[str, ...] | None = None
    value: Any = None
    event_builder: EventBuilder[EventT]

    @field_validator("axes", mode="after")
    def _validate_axes(cls, v: tuple[AxisIterable, ...]) -> tuple[AxisIterable, ...]:
        keys = [x.axis_key for x in v]
        if dupes := {k for k in keys if keys.count(k) > 1}:
            raise ValueError(
                f"The following axis keys appeared more than once: {dupes}"
            )
        return v

    @field_validator("axis_order", mode="before")
    @classmethod
    def _validate_axis_order(cls, v: Any) -> tuple[str, ...]:
        if not isinstance(v, Iterable):
            raise ValueError(f"axis_order must be iterable, got {type(v)}")
        order = tuple(str(x).lower() for x in v)
        if len(set(order)) < len(order):
            raise ValueError(f"Duplicate entries found in acquisition order: {order}")

        return order

    @property
    def is_infinite(self) -> bool:
        """Return `True` if the sequence is infinite."""
        return any(ax.is_infinite for ax in self.axes)


class MultiDimSequence(_MultiDimSequence[MDAEvent]):
    event_builder: EventBuilder[MDAEvent] = MDAEventBuilder()
