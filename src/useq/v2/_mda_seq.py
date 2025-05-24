from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from pydantic_core import core_schema

from useq._mda_event import MDAEvent
from useq.v2._multidim_seq import AxesIterator, AxisIterable, V

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from typing import TypeAlias

    from pydantic import GetCoreSchemaHandler

    from useq.v2._multidim_seq import AxisKey, Index, Value

    MDAAxesIndex: TypeAlias = dict[AxisKey, tuple[Index, Value, "MDAAxisIterable"]]


EventT = TypeVar("EventT", covariant=True, bound=Any)


class MDAAxisIterable(AxisIterable[V]):
    def contribute_to_mda_event(
        self, value: V, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
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


@runtime_checkable
class EventBuilder(Protocol[EventT]):
    """Callable that builds an event from an AxesIndex."""

    @abstractmethod
    def __call__(self, axes_index: MDAAxesIndex) -> EventT:
        """Transform an AxesIndex into an event object."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Return the schema for the event builder."""
        return core_schema.is_instance_schema(EventBuilder)


# Example concrete event builder for MDAEvent
class MDAEventBuilder(EventBuilder[MDAEvent]):
    """Builds MDAEvent objects from AxesIndex."""

    def __call__(self, axes_index: MDAAxesIndex) -> MDAEvent:
        """Transform AxesIndex into MDAEvent using axis contributions."""
        index: dict[str, int] = {}
        contributions: list[tuple[str, Mapping]] = []

        # Let each axis contribute to the event
        for axis_key, (idx, value, axis) in axes_index.items():
            index[axis_key] = idx
            contribution = axis.contribute_to_mda_event(value, index)
            contributions.append((axis_key, contribution))

        return self._merge_contributions(index, contributions)

    def _merge_contributions(
        self, index: dict[str, int], contributions: list[tuple[str, Mapping]]
    ) -> MDAEvent:
        event_data: dict = {"index": index}
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


class MDASequence(AxesIterator):
    axes: tuple[AxisIterable, ...] = ()
    event_builder: EventBuilder[MDAEvent] = MDAEventBuilder()

    def iter_axes(
        self, axis_order: tuple[str, ...] | None = None
    ) -> Iterator[MDAAxesIndex]:
        return super().iter_axes(axis_order=axis_order)

    def iter_events(
        self, axis_order: tuple[str, ...] | None = None
    ) -> Iterator[MDAEvent]:
        """Iterate over the axes and yield events."""
        if self.event_builder is None:
            raise ValueError("No event builder provided for this sequence.")
        yield from map(self.event_builder, self.iter_axes(axis_order=axis_order))
