from __future__ import annotations

import warnings
from collections.abc import Iterable, Iterator
from contextlib import suppress
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Optional,
    overload,
)

from pydantic import Field, TypeAdapter, field_validator, model_validator
from typing_extensions import deprecated

from useq import v2
from useq._enums import AXES, Axis
from useq._hardware_autofocus import AnyAutofocusPlan, AxesBasedAF
from useq._mda_event import MDAEvent
from useq._mda_sequence import MDASequence as MDASequenceV1
from useq.v2 import _position
from useq.v2._axes_iterator import (
    AxisIterable,
    EventBuilder,
    EventTransform,
    MultiAxisSequence,
)
from useq.v2._importable_object import ImportableObject
from useq.v2._transformers import (
    AutoFocusTransform,
    KeepShutterOpenTransform,
    ResetEventTimerTransform,
    reset_global_timer_state,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from useq._channel import Channel
    from useq.v2._axes_iterator import AxesIndex
    from useq.v2._position import Position


# Example concrete event builder for MDAEvent
class MDAEventBuilder(EventBuilder[MDAEvent]):
    """Builds MDAEvent objects from AxesIndex."""

    def __call__(
        self, axes_index: AxesIndex, context: tuple[MultiAxisSequence, ...]
    ) -> MDAEvent:
        """Transform AxesIndex into MDAEvent using axis contributions."""
        index: dict[str, int] = {}
        contributions: list[tuple[str, Mapping]] = []

        # Let each axis contribute to the event
        for axis_key, (idx, value, axis) in axes_index.items():
            index[axis_key] = idx
            contribution = axis.contribute_to_mda_event(value, index)
            contributions.append((axis_key, contribution))

        event = self._merge_contributions(index, contributions)
        event.sequence = context[-1] if context else None
        return event

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
                        warnings.warn(
                            f"Conflicting absolute position from {axis_key}: "
                            f"existing {key}={abs_pos[key]}, new {key}={val}",
                            UserWarning,
                            stacklevel=3,
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


def _default_transforms(data: dict) -> tuple[EventTransform[MDAEvent], ...]:
    if any(ax.axis_key == Axis.TIME for ax in data.get("axes", ())):
        return (ResetEventTimerTransform(),)
    return ()


class MDASequence(MultiAxisSequence[MDAEvent]):
    autofocus_plan: Optional[AnyAutofocusPlan] = None
    keep_shutter_open_across: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)
    event_builder: Optional[Annotated[EventBuilder[MDAEvent], ImportableObject()]] = (
        Field(default_factory=MDAEventBuilder, repr=False)
    )

    transforms: tuple[Annotated[EventTransform[MDAEvent], ImportableObject()], ...] = (
        Field(
            default_factory=_default_transforms,
            repr=False,
        )
    )

    if TYPE_CHECKING:
        # legacy __init__ signature
        @overload
        def __init__(
            self: MDASequence,
            *,
            axis_order: tuple[str, ...] | str | None = ...,
            value: Any = ...,
            time_plan: AxisIterable[float] | list | dict | None = ...,
            z_plan: AxisIterable[Position] | None = ...,
            channels: AxisIterable[Channel] | list | None = ...,
            stage_positions: AxisIterable[Position] | list | None = ...,
            grid_plan: AxisIterable[Position] | None = ...,
            autofocus_plan: AnyAutofocusPlan | None = ...,
            keep_shutter_open_across: str | tuple[str, ...] = ...,
            metadata: dict[str, Any] = ...,
            event_builder: EventBuilder[MDAEvent] = ...,
            transforms: tuple[EventTransform[MDAEvent], ...] = ...,
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
            transforms: tuple[EventTransform[MDAEvent], ...] = ...,
        ) -> None: ...
        def __init__(self, **kwargs: Any) -> None: ...

    def __iter__(self) -> Iterator[MDAEvent]:  # type: ignore[override]
        # Reset global timer state at the beginning of each sequence (like v1)
        reset_global_timer_state()
        yield from self.iter_events()

    @model_validator(mode="before")
    @classmethod
    def _cast_legacy_kwargs(cls, data: Any) -> Any:
        """Cast legacy kwargs to the new pattern."""
        if isinstance(data, MDASequenceV1):
            data = data.model_dump(exclude_unset=True)
        if isinstance(data, dict) and (axes := _extract_legacy_axes(data)):
            if "axes" in data:
                raise ValueError(
                    "Cannot provide both 'axes' and legacy MDASequence parameters."
                )
            data["axes"] = axes
        return data

    @model_validator(mode="after")
    def _compose_transforms(self) -> MDASequence:
        """Compose transforms after initialization."""
        # add autofocus transform if applicable
        if isinstance(self.autofocus_plan, AxesBasedAF) and not any(
            isinstance(ax, AutoFocusTransform) for ax in self.transforms
        ):
            self.transforms += (AutoFocusTransform(self.autofocus_plan),)
        if self.keep_shutter_open_across and not any(
            isinstance(ax, KeepShutterOpenTransform) for ax in self.transforms
        ):
            self.transforms += (
                KeepShutterOpenTransform(self.keep_shutter_open_across),
            )
        return self

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
                return tuple(axis)
        # If no channel axis is found, return an empty tuple
        return ()

    @property
    def stage_positions(self) -> Sequence[Position]:
        """Return the stage positions."""
        for axis in self.axes:
            if axis.axis_key == Axis.POSITION:
                return tuple(axis)
        return ()

    @property
    def grid_plan(self) -> Optional[AxisIterable[Position]]:
        """Return the grid plan."""
        return next((axis for axis in self.axes if axis.axis_key == Axis.GRID), None)


def _extract_legacy_axes(kwargs: dict[str, Any]) -> tuple[AxisIterable, ...]:
    """Extract legacy axes from kwargs."""

    def _cast_stage_position(val: Any) -> v2.StagePositions:
        if not isinstance(val, Iterable):  # pragma: no cover
            raise ValueError(
                f"Cannot convert 'stage_position' to AxisIterable: "
                f"Expected a sequence, got {type(val)}"
            )
        new_val: list[v2.Position] = []
        for item in val:
            if isinstance(item, dict):
                item = v2.Position(**item)
            elif isinstance(item, MultiAxisSequence):
                if item.value is None:
                    item = item.model_copy(update={"value": _position.Position()})
            else:
                item = _position.Position.model_validate(item)
            new_val.append(item)
        return v2.StagePositions.model_validate(new_val)

    def _cast_legacy_to_axis_iterable(key: str) -> AxisIterable | None:
        validator: dict[str, Callable[[Any], AxisIterable]] = {
            "channels": v2.ChannelsPlan.model_validate,
            "z_plan": TypeAdapter(v2.AnyZPlan).validate_python,
            "time_plan": TypeAdapter(v2.AnyTimePlan).validate_python,
            "grid_plan": TypeAdapter(v2.MultiPointPlan).validate_python,
            "stage_positions": _cast_stage_position,
        }
        if (val := kwargs.pop(key)) not in (None, [], (), {}):
            if not isinstance(val, AxisIterable):
                try:
                    val = validator[key](val)
                except Exception as e:  # pragma: no cover
                    raise ValueError(
                        f"Failed to process legacy axis '{key}': {e}"
                    ) from e
            return val  # type: ignore[no-any-return]
        return None

    axes = [
        val
        for key in list(kwargs)
        if key in {"channels", "z_plan", "time_plan", "grid_plan", "stage_positions"}
        and (val := _cast_legacy_to_axis_iterable(key)) is not None
    ]

    if "axis_order" not in kwargs:
        # sort axes by AXES
        axes.sort(
            key=lambda ax: AXES.index(ax.axis_key) if ax.axis_key in AXES else len(AXES)
        )

    return tuple(axes)
