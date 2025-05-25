from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Protocol,
    TypeVar,
    overload,
    runtime_checkable,
)

from pydantic import Field
from pydantic_core import core_schema

from useq._enums import Axis
from useq._hardware_autofocus import AnyAutofocusPlan  # noqa: TC001
from useq._mda_event import MDAEvent
from useq.v2._axes_iterator import AxesIterator, AxisIterable

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from pydantic import GetCoreSchemaHandler

    from useq._channel import Channel
    from useq.v2._axes_iterator import AxesIndex
    from useq.v2._position import Position


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

        def get_python_path(value: AxesIndex) -> str:
            """Get a unique identifier for the event builder."""
            val_type = type(value)
            return f"{val_type.__module__}.{val_type.__qualname__}"

        def validate_event_builder(value: Any) -> EventBuilder[EventT]:
            """Validate the event builder."""
            if isinstance(value, str):
                # If a string is provided, it should be a path to the class
                # that implements the EventBuilder protocol.
                from importlib import import_module

                module_name, class_name = value.rsplit(".", 1)
                module = import_module(module_name)
                value = getattr(module, class_name)

            if not isinstance(value, EventBuilder):
                raise TypeError(f"Expected an EventBuilder, got {type(value).__name__}")
            return value

        return core_schema.no_info_plain_validator_function(
            function=validate_event_builder,
            serialization=core_schema.plain_serializer_function_ser_schema(
                function=get_python_path
            ),
        )


# Example concrete event builder for MDAEvent
class MDAEventBuilder(EventBuilder[MDAEvent]):
    """Builds MDAEvent objects from AxesIndex."""

    def __call__(self, axes_index: AxesIndex) -> MDAEvent:
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
    autofocus_plan: Optional[AnyAutofocusPlan] = None
    keep_shutter_open_across: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)
    event_builder: EventBuilder[MDAEvent] = Field(default_factory=MDAEventBuilder)

    # legacy __init__ signature
    @overload
    def __init__(
        self: MDASequence,
        *,
        axis_order: tuple[str, ...] | None = ...,
        value: Any = ...,
        time_plan: AxisIterable[float] | None = ...,
        z_plan: AxisIterable[Position] | None = ...,
        channels: AxisIterable[Channel] | None = ...,
        stage_positions: AxisIterable[Position] | None = ...,
        grid_plan: AxisIterable[Position] | None,
        autofocus_plan: AnyAutofocusPlan | None = ...,
        keep_shutter_open_across: tuple[str, ...] = ...,
        metadata: dict[str, Any] = ...,
        event_builder: EventBuilder[MDAEvent] = ...,
    ) -> None: ...
    # new pattern
    @overload
    def __init__(
        self,
        *,
        axes: tuple[AxisIterable, ...] = ...,
        axis_order: tuple[str, ...] | None = ...,
        value: Any = ...,
        autofocus_plan: AnyAutofocusPlan | None = ...,
        keep_shutter_open_across: tuple[str, ...] = ...,
        metadata: dict[str, Any] = ...,
        event_builder: EventBuilder[MDAEvent] = ...,
    ) -> None: ...
    def __init__(self, **kwargs: Any) -> None:
        """Initialize MDASequence with provided axes and parameters."""
        axes = list(kwargs.setdefault("axes", ()))
        legacy_fields = (
            "time_plan",
            "z_plan",
            "channels",
            "stage_positions",
            "grid_plan",
        )
        axes.extend([kwargs.pop(field) for field in legacy_fields if field in kwargs])

        kwargs["axes"] = tuple(axes)
        super().__init__(**kwargs)

    def iter_axes(
        self, axis_order: tuple[str, ...] | None = None
    ) -> Iterator[AxesIndex]:
        return super().iter_axes(axis_order=axis_order)

    def iter_events(
        self, axis_order: tuple[str, ...] | None = None
    ) -> Iterator[MDAEvent]:
        """Iterate over the axes and yield events."""
        if self.event_builder is None:
            raise ValueError("No event builder provided for this sequence.")
        yield from map(self.event_builder, self.iter_axes(axis_order=axis_order))

    @property
    def time_plan(self) -> Optional[AxisIterable[float]]:
        """Return the time plan."""
        return next((axis for axis in self.axes if axis.axis_key == Axis.TIME), None)

    @property
    def z_plan(self) -> Optional[AxisIterable[Position]]:
        """Return the z plan."""
        return next((axis for axis in self.axes if axis.axis_key == Axis.Z), None)

    @property
    def channels(self) -> Iterable[Channel]:
        """Return the channels."""
        channel_plan = next(
            (axis for axis in self.axes if axis.axis_key == Axis.CHANNEL), None
        )
        return channel_plan or ()  # type: ignore

    @property
    def stage_positions(self) -> Optional[AxisIterable[Position]]:
        """Return the stage positions."""
        return next(
            (axis for axis in self.axes if axis.axis_key == Axis.POSITION), None
        )

    @property
    def grid_plan(self) -> Optional[AxisIterable[Position]]:
        """Return the grid plan."""
        return next((axis for axis in self.axes if axis.axis_key == Axis.GRID), None)
