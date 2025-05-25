from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Optional,
    Protocol,
    TypeVar,
    get_origin,
    overload,
    runtime_checkable,
)

from pydantic import Field, field_validator
from pydantic_core import core_schema
from typing_extensions import deprecated

from useq._enums import Axis
from useq._hardware_autofocus import AnyAutofocusPlan  # noqa: TC001
from useq._mda_event import MDAEvent
from useq.v2._axes_iterator import AxesIterator, AxisIterable

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from pydantic import GetCoreSchemaHandler

    from useq._channel import Channel
    from useq.v2._axes_iterator import AxesIndex
    from useq.v2._position import Position


EventT = TypeVar("EventT", covariant=True, bound=Any)


@dataclass(frozen=True)
class ImportableObject:
    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Return the schema for the importable object."""

        def import_python_path(value: Any) -> Any:
            """Import a Python object from a string path."""
            if isinstance(value, str):
                # If a string is provided, it should be a path to the class
                # that implements the EventBuilder protocol.
                from importlib import import_module

                parts = value.rsplit(".", 1)
                if len(parts) != 2:
                    raise ValueError(
                        f"Invalid import path: {value!r}. "
                        "Expected format: 'module.submodule.ClassName'"
                    )
                module_name, class_name = parts
                module = import_module(module_name)
                return getattr(module, class_name)
            return value

        def get_python_path(value: Any) -> str:
            """Get a unique identifier for the event builder."""
            val_type = type(value)
            return f"{val_type.__module__}.{val_type.__qualname__}"

        # TODO: check me
        origin = source_type
        try:
            isinstance(None, origin)
        except TypeError:
            origin = get_origin(origin)
            try:
                isinstance(None, origin)
            except TypeError:
                origin = object

        to_pp_ser = core_schema.plain_serializer_function_ser_schema(
            function=get_python_path
        )
        return core_schema.no_info_before_validator_function(
            function=import_python_path,
            schema=core_schema.is_instance_schema(origin),
            serialization=to_pp_ser,
            json_schema_input_schema=core_schema.str_schema(
                pattern=r"^([^\W\d]\w*)(\.[^\W\d]\w*)*$"
            ),
        )


@runtime_checkable
class EventBuilder(Protocol[EventT]):
    """Callable that builds an event from an AxesIndex."""

    @abstractmethod
    def __call__(self, axes_index: AxesIndex) -> EventT:
        """Transform an AxesIndex into an event object."""


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
    event_builder: Annotated[EventBuilder[MDAEvent], ImportableObject()] = Field(
        default_factory=MDAEventBuilder, repr=False
    )

    # legacy __init__ signature
    @overload
    def __init__(
        self: MDASequence,
        *,
        axis_order: tuple[str, ...] | None = ...,
        value: Any = ...,
        time_plan: AxisIterable[float] | None = ...,
        z_plan: AxisIterable[Position] | None = ...,
        channels: AxisIterable[Channel] | list | None = ...,
        stage_positions: AxisIterable[Position] | list | None = ...,
        grid_plan: AxisIterable[Position] | None = ...,
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
        if axes := _extract_legacy_axes(kwargs):
            if "axes" in kwargs:
                raise ValueError(
                    "Cannot provide both 'axes' and legacy axis parameters."
                )
            kwargs["axes"] = axes
        super().__init__(**kwargs)

    def iter_events(
        self, axis_order: tuple[str, ...] | None = None
    ) -> Iterator[MDAEvent]:
        """Iterate over the axes and yield events."""
        if self.event_builder is None:
            raise ValueError("No event builder provided for this sequence.")
        yield from map(self.event_builder, self.iter_axes(axis_order=axis_order))

    def __iter__(self) -> Iterator[MDAEvent]:  # type: ignore[override]
        yield from self.iter_events()

    @field_validator("keep_shutter_open_across", mode="before")
    def _validate_keep_shutter_open_across(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        try:
            v = tuple(v)
        except (TypeError, ValueError):  # pragma: no cover
            raise ValueError(
                f"keep_shutter_open_across must be string or a sequence of strings, "
                f"got {type(v)}"
            ) from None
        return v

    # ------------------------- Old API -------------------------

    @property
    @deprecated(
        "The shape of an MDASequence is ill-defined. "
        "This API will be removed in a future version.",
        category=FutureWarning,
        stacklevel=2,
    )
    def shape(self) -> tuple[int, ...]:
        """Return the shape of this sequence.

        !!! note
            This doesn't account for jagged arrays, like channels that exclude z
            stacks or skip timepoints.
        """
        return tuple(s for s in self.sizes.values() if s)

    @property
    @deprecated(
        "The sizes of an MDASequence is ill-defined. "
        "This API will be removed in a future version.",
        category=FutureWarning,
        stacklevel=2,
    )
    def sizes(self) -> Mapping[str, int]:
        """Mapping of axis name to size of that axis."""
        if not self.is_finite():
            raise ValueError("Cannot get sizes of infinite sequence.")

        return {axis.axis_key: len(axis) for axis in self._ordered_axes()}  # type: ignore[arg-type]

    def _ordered_axes(self) -> tuple[AxisIterable, ...]:
        """Return the axes in the order specified by axis_order."""
        if (order := self.axis_order) is None:
            return self.axes

        axes_map = {axis.axis_key: axis for axis in self.axes}
        return tuple(axes_map[key] for key in order if key in axes_map)

    @property
    def used_axes(self) -> tuple[str, ...]:
        """Return keys of the axes whose length is not 0."""
        out = []
        for ax in self._ordered_axes():
            with suppress(TypeError, ValueError):
                if not len(ax):  # type: ignore[arg-type]
                    continue
            out.append(ax.axis_key)
        return tuple(out)

    @property
    def time_plan(self) -> Optional[AxisIterable[float]]:
        """Return the time plan."""
        return next((axis for axis in self.axes if axis.axis_key == Axis.TIME), None)

    @property
    def z_plan(self) -> Optional[AxisIterable[Position]]:
        """Return the z plan."""
        return next((axis for axis in self.axes if axis.axis_key == Axis.Z), None)

    @property
    def channels(self) -> Sequence[Channel]:
        """Return the channels."""
        for axis in self.axes:
            if axis.axis_key == Axis.CHANNEL:
                return tuple(axis)  # type: ignore[arg-type]
        # If no channel axis is found, return an empty tuple
        return ()

    @property
    def stage_positions(self) -> Sequence[Position]:
        """Return the stage positions."""
        for axis in self.axes:
            if axis.axis_key == Axis.POSITION:
                return tuple(axis)  # type: ignore[arg-type]
        return ()

    @property
    def grid_plan(self) -> Optional[AxisIterable[Position]]:
        """Return the grid plan."""
        return next((axis for axis in self.axes if axis.axis_key == Axis.GRID), None)


def _extract_legacy_axes(kwargs: dict[str, Any]) -> tuple[AxisIterable, ...]:
    """Extract legacy axes from kwargs."""
    from pydantic import TypeAdapter

    from useq import v2

    axes: list[AxisIterable] = []

    # process kwargs in order of insertion
    for key in list(kwargs):
        match key:
            case "channels":
                val = kwargs.pop(key)
                if not isinstance(val, AxisIterable):
                    val = v2.ChannelsPlan.model_validate(val)
            case "z_plan":
                val = kwargs.pop(key)
                if not isinstance(val, AxisIterable):
                    val = TypeAdapter(v2.AnyZPlan).validate_python(val)
            case "time_plan":
                val = kwargs.pop(key)
                if not isinstance(val, AxisIterable):
                    val = TypeAdapter(v2.AnyTimePlan).validate_python(val)
            case "grid_plan":
                val = kwargs.pop(key)
                if not isinstance(val, AxisIterable):
                    val = TypeAdapter(v2.MultiPointPlan).validate_python(val)
            case "stage_positions":
                val = kwargs.pop(key)
                if not isinstance(val, AxisIterable):
                    val = v2.StagePositions.model_validate(val)
            case _:
                continue  # Ignore any other keys
        axes.append(val)

    return tuple(axes)
