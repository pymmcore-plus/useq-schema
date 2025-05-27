"""MultiDimensional Iteration Module.

This module provides a declarative approach to multi-dimensional iteration,
supporting hierarchical (nested) sub-iterations as well as conditional
skipping (filtering) of final combinations.

Key Concepts:
-------------
- **AxisIterable**: An interface (protocol) representing an axis. Each axis
  has a unique `axis_key` and yields values via its iterator. A concrete axis,
  such as `SimpleValueAxis`, yields plain values. To express sub-iterations,
  an axis may yield a nested `MultiAxisSequence` (instead of a plain value).

- **MultiAxisSequence**: Represents a multi-dimensional experiment or sequence.
  It contains a tuple of axes (AxisIterable objects) and an optional `axis_order`
  that controls the order in which axes are processed. When used as a nested override,
  its `value` field is used as the representative value for that branch, and its
  axes override or extend the parent's axes.

- **Nested Overrides**: When an axis yields a nested MultiAxisSequence with a non-None
  `value`, that nested sequence acts as an override for the parent's iteration.
  Specifically, the parent's remaining axes that have keys matching those in the
  nested sequence are removed, and the nested sequence's axes (ordered by its own
  `axis_order`, or inheriting the parent's if not provided) are appended.

- **Prefix and Skip Logic**: As the recursion proceeds, a `prefix` is built up, mapping
  axis keys to a triple: (index, value, axis). Before yielding a final combination,
  each axis is given an opportunity (via the `should_skip` method) to veto that
  combination. By default, `SimpleValueAxis.should_skip` returns False, but you can
  override it in a subclass to implement conditional skipping.

Usage Examples:
---------------
1. Basic Iteration (no nested sequences):

    >>> multi_dim = MultiAxisSequence(
    ...     axes=(
    ...         SimpleValueAxis("t", [0, 1, 2]),
    ...         SimpleValueAxis("c", ["red", "green", "blue"]),
    ...         SimpleValueAxis("z", [0.1, 0.2]),
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
   Here the "t" axis yields a nested MultiAxisSequence that adds an extra "q" axis.

    >>> multi_dim = MultiAxisSequence(
    ...     axes=(
    ...         SimpleValueAxis("t", [
    ...             0,
    ...             MultiAxisSequence(
    ...                 value=1,
    ...                 axes=(SimpleValueAxis("q", ["a", "b"]),),
    ...             ),
    ...             2,
    ...         ]),
    ...         SimpleValueAxis("c", ["red", "green", "blue"]),
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
   Here the "t" axis yields a nested MultiAxisSequence whose axes override the parent's
   "z" axis.

    >>> multi_dim = MultiAxisSequence(
    ...     axes=(
    ...         SimpleValueAxis("t", [
    ...             0,
    ...             MultiAxisSequence(
    ...                 value=1,
    ...                 axes=(
    ...                     SimpleValueAxis("c", ["red", "blue"]),
    ...                     SimpleValueAxis("z", [7, 8, 9]),
    ...                 ),
    ...                 axis_order=("c", "z"),
    ...             ),
    ...             2,
    ...         ]),
    ...         SimpleValueAxis("c", ["red", "green", "blue"]),
    ...         SimpleValueAxis("z", [0.1, 0.2]),
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
   By subclassing SimpleValueAxis to override should_skip, you can filter out
   combinations. For example, suppose we want to skip any combination where "c" equals
   "green" and "z" is not 0.2:

    >>> class FilteredZ(SimpleValueAxis):
    ...     def should_skip(
    ...             self, prefix: dict[str, tuple[int, Any, AxisIterable]]
    ...         ) -> bool:
    ...         c_val = prefix.get("c", (None, None, None))[1]
    ...         z_val = prefix.get("z", (None, None, None))[1]
    ...         if c_val == "green" and z_val != 0.2:
    ...             return True
    ...         return False
    ...
    >>> multi_dim = MultiAxisSequence(
    ...     axes=(
    ...         SimpleValueAxis("t", [0, 1, 2]),
    ...         SimpleValueAxis("c", ["red", "green", "blue"]),
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
  combination) is built by processing one axis at a time. Nested MultiAxisSequence
  objects allow you to either extend the iteration with new axes or override existing
  ones.
- The ordering of axes is controlled via the `axis_order` property, which is inherited
  by nested sequences if not explicitly provided.
- The should_skip mechanism gives each axis an opportunity to veto a final combination.
  By default, SimpleValueAxis does not skip any combination, but you can subclass it to
  implement custom filtering logic.

This module is intended for cases where complex, declarative multidimensional iteration
is required-such as in microscope acquisitions, high-content imaging, or other
experimental designs where the sequence of events must be generated in a flexible,
hierarchical manner.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable, Iterable, Iterator, Mapping, Sized
from functools import cache
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Generic,
    Optional,
    Protocol,
    TypeVar,
    cast,
    runtime_checkable,
)

from pydantic import BaseModel, Field, field_validator

from useq._base_model import MutableModel
from useq.v2._importable_object import ImportableObject

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import TypeAlias

    AxisKey: TypeAlias = str
    Value: TypeAlias = Any
    Index: TypeAlias = int
    AxesIndex: TypeAlias = dict[AxisKey, tuple[Index, Value, "AxisIterable"]]
    AxesIndexWithContext: TypeAlias = tuple[AxesIndex, tuple["MultiAxisSequence", ...]]


V = TypeVar("V", covariant=True, bound=Any)
EventT = TypeVar("EventT", bound=Any)
EventTco = TypeVar("EventTco", covariant=True, bound=Any)


class AxisIterable(BaseModel, Generic[V]):
    axis_key: str
    """A string id representing the axis."""

    @abstractmethod
    def __iter__(self) -> Iterator[V]:  # type: ignore[override]
        """Iterate over the axis.

        If a value needs to declare sub-axes, yield a nested AxesIterator.
        The default iterator pattern will recurse into a nested AxesIterator.
        """

    def should_skip(self, prefix: AxesIndex) -> bool:
        """Return True if this axis wants to skip the combination.

        Default implementation returns False.
        """
        return False

    def contribute_event_kwargs(
        self,
        value: V,  # type: ignore[misc] # covariant cannot be used as parameter
        index: Mapping[str, int],
    ) -> Mapping:
        """Contribute data to the event being built.

        This method allows each axis to contribute its data to the final MDAEvent.
        The default implementation does nothing - subclasses should override
        to add their specific contributions.

        Parameters
        ----------
        value : V
            The value provided by this axis, for this iteration.
        index : Mapping[str, int]
            A mapping of axis keys to their current index in the iteration.
            This can be used to determine the context of the value.

        Returns
        -------
        event_data : dict[str, Any]
            Data to be added to the MDAEvent, it is ultimately up to the
            EventBuilder to decide how to merge possibly conflicting contributions from
            different axes.
        """
        return {}


class SimpleValueAxis(AxisIterable[V]):
    """A basic axis implementation that yields values directly.

    If a value needs to declare sub-axes, yield a nested MultiAxisSequence.
    The default should_skip always returns False.
    """

    values: list[V] = Field(default_factory=list)

    def __iter__(self) -> Iterator[V]:  # type: ignore[override]
        yield from self.values

    def __len__(self) -> int:
        """Return the number of axis values."""
        return len(self.values)


@runtime_checkable
class EventBuilder(Protocol[EventTco]):
    """Callable that builds an event from an AxesIndex."""

    @abstractmethod
    def __call__(
        self, axes_index: AxesIndex, context: tuple[MultiAxisSequence, ...]
    ) -> EventTco:
        """Transform an AxesIndex into an event object."""


@runtime_checkable
class EventTransform(Protocol[EventT]):
    """Callable that can modify, drop, or insert events.

    The transformer receives:

    * **event** - the current (already built) event.
    * **prev_event** - the *previously transformed* event that was just yielded,
      or ``None`` if this is the first call.
    * **make_next_event** - a zero-argument callable that lazily builds the *next*
      raw event (i.e. before any transformers).  Only call it if you really
      need look-ahead so the pipeline stays lazy.

    The transformer must return a list.

    Return **one** event in the list for a 1-to-1 mapping, an empty list to
    drop the original event, or a list with multiple items to insert extras.
    """

    def __call__(
        self,
        event: EventT,
        *,
        prev_event: EventT | None,
        make_next_event: Callable[[], EventT | None],
    ) -> Iterable[EventT]: ...


@runtime_checkable
class AxesIterator(Protocol):
    """Object that iterates over a MultiAxisSequence."""

    @abstractmethod
    def __call__(
        self, seq: MultiAxisSequence, axis_order: tuple[str, ...] | None = None
    ) -> Iterator[AxesIndexWithContext]:
        """Iterate over the axes of a MultiAxisSequence."""
        ...


class MultiAxisSequence(MutableModel, Generic[EventTco]):
    """Represents a multidimensional sequence.

    At the top level the `value` field is ignored.
    When used as a nested override, `value` is the value for that branch and
    its axes are iterated using its own axis_order if provided;
    otherwise, it inherits the parent's axis_order.
    """

    axes: tuple[AxisIterable, ...] = ()
    axis_order: Optional[tuple[str, ...]] = None
    value: Any = None

    # these will rarely be needed, but offer maximum flexibility
    event_builder: Optional[Annotated[EventBuilder[EventTco], ImportableObject()]] = (
        Field(default=None, repr=False)
    )

    # optional post-processing transformer chain
    transforms: tuple[Annotated[EventTransform, ImportableObject()], ...] = Field(
        default_factory=tuple, repr=False
    )

    def is_finite(self) -> bool:
        """Return `True` if the sequence is finite (all axes are Sized)."""
        return all(isinstance(ax, Sized) for ax in self.axes)

    def iter_axes(
        self, axis_order: tuple[str, ...] | None = None
    ) -> Iterator[AxesIndexWithContext]:
        """Iterate over the axes and yield combinations with context.

        Yields
        ------
        AxesIndexWithContext
            A tuple of (AxesIndex, MultiAxisSequence) where AxesIndex is a dictionary
            mapping axis keys to tuples of (index, value, AxisIterable), and
            MultiAxisSequence is the context that generated this axes combination.
            For example, when iterating over an `AxisIterable` with a single axis "t",
            with values of [0.1, .2], the yielded tuples would be:
            - ({'t': (0, 0.1, <AxisIterable>)}, <context>)
            - ({'t': (1, 0.2, <AxisIterable>)}, <context>)
        """
        from useq.v2._iterate import iterate_multi_dim_sequence

        yield from iterate_multi_dim_sequence(self, axis_order=axis_order)

    def iter_events(
        self, axis_order: tuple[str, ...] | None = None
    ) -> Iterator[EventTco]:
        """Iterate over axes, build raw events, then apply transformers."""
        if (event_builder := self.event_builder) is None:
            raise ValueError("No event builder provided for this sequence.")

        axes_iter = self.iter_axes(axis_order=axis_order)

        # Get the first item to see if we have any events
        try:
            next_item: AxesIndexWithContext | None = next(axes_iter)
        except StopIteration:
            return  # empty sequence - nothing to yield

        prev_evt: EventTco | None = None
        while True:
            cur_axes, context = cast("AxesIndexWithContext", next_item)

            try:
                next_item = next(axes_iter)
            except StopIteration:
                next_item = None

            cur_evt = event_builder(cur_axes, context)
            transforms = self.compose_transforms(context)

            if not transforms:
                # simple case - no transforms, just yield the event
                yield cur_evt
                prev_evt = cur_evt
            else:

                @cache
                def _make_next_event(
                    _nxt_item: AxesIndexWithContext | None = next_item,
                    _ctx: Any = context,
                ) -> EventTco | None:
                    if _nxt_item is not None:
                        return event_builder(_nxt_item[0], _ctx)
                    return None

                # run through transformer pipeline
                emitted: Iterable[EventTco] = (cur_evt,)
                pipeline_prev_evt = prev_evt
                for tf in transforms:
                    # Convert to list to materialize the iterable for proper chaining
                    emitted_list = list(emitted)
                    new_emitted = []
                    for e in emitted_list:
                        transformed = list(
                            tf(
                                e,
                                prev_event=pipeline_prev_evt,
                                make_next_event=_make_next_event,
                            )
                        )
                        if transformed:
                            new_emitted.extend(transformed)
                            # Update prev_evt to last event from this transform
                            pipeline_prev_evt = transformed[-1]
                    emitted = new_emitted

                for out_evt in emitted:
                    yield out_evt
                    prev_evt = out_evt

            if next_item is None:
                break

    def compose_transforms(
        self, context: tuple[MultiAxisSequence, ...] = ()
    ) -> tuple[EventTransform, ...]:
        """Compose transforms from the context of nested sequences.

        The base implementation aggregates transforms from outer to inner sequences.
        Only a single instance of each transform type is kept, so if multiple
        sequences in the context have the same transform type, only one will be used,
        and innermost MultiAxisSequence's transform will take precedence.
        """
        merged_transforms = {type(t): t for seq in context for t in seq.transforms}

        # sort by "priority" attribute (if defined) or by order of appearance
        sorted_transforms = sorted(
            merged_transforms.values(),
            key=lambda t: getattr(t, "priority", 0),  # default priority is 0
        )
        return tuple(sorted_transforms)

    # ----------------------- Validation -----------------------

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
    def _validate_axis_order(cls, v: Any) -> Any:
        if v is None:
            return None
        if not isinstance(v, Iterable):
            raise ValueError(f"axis_order must be iterable, got {type(v)}")
        order = tuple(str(x).lower() for x in v)
        if len(set(order)) < len(order):
            raise ValueError(f"Duplicate entries found in acquisition order: {order}")

        return order
