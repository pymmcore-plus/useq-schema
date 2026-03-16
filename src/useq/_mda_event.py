# don't add __future__.annotations here
# pydantic2 isn't rebuilding the model correctly

from collections import UserDict
from typing import TYPE_CHECKING, Any, NamedTuple, Optional, TypedDict

import numpy as np
import numpy.typing as npt
from pydantic import (
    Field,
    GetCoreSchemaHandler,
    NonNegativeInt,
    field_validator,
    model_validator,
)
from pydantic_core import core_schema

from useq._actions import AcquireImage, AnyAction
from useq._base_model import UseqModel

try:
    from pydantic import field_serializer
except ImportError:
    field_serializer = None  # type: ignore

try:
    from pydantic import model_serializer
except ImportError:
    model_serializer = None  # type: ignore

if TYPE_CHECKING:
    from collections.abc import Sequence

    from useq._mda_sequence import MDASequence

    ReprArgs = Sequence[tuple[str | None, Any]]


class Channel(UseqModel):
    """Channel in a MDA event.

    Attributes
    ----------
    config : str
        Name of the configuration to use for this channel, (e.g. `"488nm"`, `"DAPI"`,
        `"FITC"`).
    group : str
        Optional name of the group to which this channel belongs. By default,
        `"Channel"`.
    """

    config: str
    group: str = "Channel"

    def __eq__(self, _value: object) -> bool:
        if isinstance(_value, str):
            return self.config == _value
        return super().__eq__(_value)

    if TYPE_CHECKING:

        class Kwargs(TypedDict, total=False):
            """Type for the kwargs passed to the channel."""

            config: str
            group: str


class SLMImage(UseqModel):
    """SLM Image in a MDA event.

    This object can be cast to a numpy.array using `np.asarray` or `np.array`.

    Attributes
    ----------
    data: npt.ArrayLike
        Image data. Anything that can be cast to a numpy array. For pydantic simplicity,
        we mark this as Any, but in practice it should be numpy.typing.ArrayLike (which
        is anything that can be cast to a numpy array using `np.asarray`).
    device: Optional[str]
        Optional name of the SLM device to use. If not provided, the "default" SLM
        device should be used. (It is left to the backend to determine what device that
        is). By default, `None`.
    exposure: Optional[float]
        Exposure time for the SLM specifically (if different from the detector), in
        milliseconds. If not provided, the exposure on the owning MDAEvent should be
        used. By default, `None`.
    """

    data: Any = Field(..., repr=False)
    device: str | None = None
    exposure: float | None = Field(default=None, gt=0.0)

    @model_validator(mode="before")
    def _cast_data(cls, v: Any) -> Any:
        """Can single, non-dict values to be the data."""
        if not isinstance(v, dict):
            v = {"data": v}
        return v

    def __array__(self, *args: Any, **kwargs: Any) -> npt.NDArray:
        """Cast the image data to a numpy array."""
        return np.asarray(self.data, *args, **kwargs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SLMImage):
            return False
        return (
            self.device == other.device
            and self.exposure == other.exposure
            and np.array_equal(self.data, other.data)
        )

    if TYPE_CHECKING:

        class Kwargs(TypedDict, total=False):
            """Type for the kwargs passed to the SLM image."""

            data: npt.ArrayLike
            device: str | None
            exposure: float | None


class CameraROI(UseqModel):
    """Camera region of interest.

    May be initialized with a ``(offset_x, offset_y, width, height)`` tuple.

    Attributes
    ----------
    offset_x : int
        X offset of the ROI in pixels. Must be >= 0.
    offset_y : int
        Y offset of the ROI in pixels. Must be >= 0.
    width : int
        Width of the ROI in pixels. Must be >= 0.
    height : int
        Height of the ROI in pixels. Must be >= 0.
    """

    offset_x: NonNegativeInt
    offset_y: NonNegativeInt
    width: NonNegativeInt
    height: NonNegativeInt

    @model_validator(mode="before")
    def _cast_tuple(cls, v: Any) -> Any:
        """Cast bare tuples/lists to CameraROI fields."""
        if isinstance(v, (tuple, list)) and len(v) == 4:
            return {
                "offset_x": v[0],
                "offset_y": v[1],
                "width": v[2],
                "height": v[3],
            }
        return v

    if TYPE_CHECKING:

        class Kwargs(TypedDict, total=False):
            """Type for the kwargs passed to the CameraROI."""

            offset_x: int
            offset_y: int
            width: int
            height: int


class PropertyTuple(NamedTuple):
    """Three-tuple capturing a device, property, and value.

    Attributes
    ----------
    device_name : str
        Name of a device.
    property_name : str
        Name of a property recognized by the device.
    value : Any
        Value for the property.
    """

    device_name: str
    property_name: str
    property_value: Any


def _float_or_none(v: Any) -> float | None:
    return float(v) if v is not None else v


class ReadOnlyDict(UserDict[str, int]):
    """A read-only dictionary."""

    _initialized: bool = False
    if not TYPE_CHECKING:

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._initialized = True

    def __setitem__(self, key: str, value: int) -> None:
        if self._initialized:
            raise TypeError("Read-only dictionary")
        super().__setitem__(key, value)

    def __repr__(self) -> str:
        return repr({str(x): v for x, v in self.data.items()})

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.dict_schema(
            keys_schema=core_schema.str_schema(), values_schema=core_schema.int_schema()
        )


class StagePosition(UseqModel):
    """A position for a single stage axis.

    Attributes
    ----------
    pos : float
        Position value.
    stage : str | None
        Device name. Optional for spatial axes (x, y, z), where it overrides
        the default device. For other stages, this is the device name.
    """

    pos: float
    stage: str | None = None

    if TYPE_CHECKING:

        class Kwargs(TypedDict, total=False):
            pos: float
            stage: str


class MDAEvent(UseqModel):
    """Define a single event in a [`MDASequence`][useq.MDASequence].

    Usually, this object will be generator by iterating over a
    [`MDASequence`][useq.MDASequence] (see [`useq.MDASequence.iter_events`][]).

    Attributes
    ----------
    index : dict[str, int]
        Index of this event in the sequence. This is a mapping of axis name
        to index.  For example: `{'t': 4, 'c': 0, 'z': 5},`
    channel : Channel | None
        Channel to use for this event. If `None`, implies use current channel.
        By default, `None`.  `Channel` is a simple pydantic object with two attributes:
        `config` and `group`.  `config` is the name of the configuration to use for this
        channel, (e.g. `"488nm"`, `"DAPI"`, `"FITC"`).  `group` is the name of the group
        to which this channel belongs. By default, `"Channel"`.
    exposure : float | None
        Exposure time in milliseconds. If not provided, implies use current exposure
        time. By default, `None`.
    min_start_time : float | None
        Minimum start time of this event, in seconds.  If provided, the engine will
        pause until this time has elapsed before starting this event. Times are
        relative to the start of the sequence, or the last event with
        `reset_event_timer` set to `True`.
    pos_name : str | None
        The name assigned to the position. By default, `None`.
    position : dict[str, StagePosition]
        A mapping of axis name to StagePosition. For spatial axes ("x", "y", "z"),
        the stage device name is optional and overrides the default device. For
        backward compatibility, x_pos, y_pos, and z_pos can still be used as
        constructor arguments and are available as properties.
    slm_image : SLMImage | None
        Image data to display on an SLM device. `SLMImage` is a simple pydantic object
        with two attributes: `data` and `device`. `data` is the image data (anything
        that can be cast to a numpy array), `device` is the name of the SLM device to
        use. If not provided, the "default" SLM device should be used. By default,
        `None`.
    sequence : MDASequence | None
        A reference to the [`useq.MDASequence`][] this event belongs to. This is a
        read-only attribute. By default, `None`.
    properties : Sequence[PropertyTuple] | None
        List of [`useq.PropertyTuple`][] to set before starting this event. Where each
        item in the list is a 3-member named tuple of `(device_name, property_name,
        property_value)`.  This is inspired by micro-manager's Device Adapter API, but
        could be used to set arbitrary properties in any backend that supports the
        concept of devices that have properties with values. By default, `None`.
    roi : CameraROI | None
        Camera region of interest. Accepts a `CameraROI` object or a bare tuple of
        `(offset_x, offset_y, width, height)` which will be automatically converted.
        By default, `None`.
    metadata : dict
        Optional metadata to be associated with this event.
    action : Action
        The action to perform for this event.  By default, [`useq.AcquireImage`][].
        Example of another action is [`useq.HardwareAutofocus`][] which could be used
        to perform a hardware autofocus.  For backwards compatibility, an `action` of
        `None` implies `AcquireImage`.  You may use `CustomAction` to indicate any
        custom action, with the `data` attribute containing any data required to
        perform the custom action.
    keep_shutter_open : bool
        If `True`, the illumination shutter should be left open after the event has
        been executed, otherwise it should be closed. By default, `False`."
        This is useful when the sequence of events being executed use the same
        illumination scheme (such as a z-stack in a single channel), and closing and
        opening the shutter between events would be slow.
    reset_event_timer : bool
        If `True`, the engine should reset the event timer to the time of this event,
        and future `min_start_time` values will be relative to this event. By default,
        `False`.
    """

    index: ReadOnlyDict = Field(default_factory=ReadOnlyDict)
    channel: Channel | None = None
    exposure: float | None = Field(default=None, gt=0.0)
    min_start_time: float | None = None  # time in sec
    pos_name: str | None = None
    position: dict[str, StagePosition] = Field(default_factory=dict)
    slm_image: SLMImage | None = None
    sequence: Optional["MDASequence"] = Field(default=None, repr=False)
    properties: list[PropertyTuple] | None = None
    roi: CameraROI | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    action: AnyAction = Field(default_factory=AcquireImage, discriminator="type")
    keep_shutter_open: bool = False
    reset_event_timer: bool = False

    @property
    def x_pos(self) -> float | None:
        sp = self.position.get("x")
        return sp.pos if sp else None

    @property
    def y_pos(self) -> float | None:
        sp = self.position.get("y")
        return sp.pos if sp else None

    @property
    def z_pos(self) -> float | None:
        sp = self.position.get("z")
        return sp.pos if sp else None

    @model_validator(mode="before")
    @classmethod
    def _validate_positions(cls, values: Any) -> Any:
        if isinstance(values, dict):
            position = dict(values.pop("position", {}))
            for axis in ("x", "y", "z"):
                key = f"{axis}_pos"
                if key in values:
                    val = values.pop(key)
                    if val is not None:
                        if isinstance(val, (int, float)):
                            position[axis] = {"pos": float(val)}
                        else:
                            position[axis] = val
            if position:
                values["position"] = position
        return values

    @model_validator(mode="after")
    def _validate_xy_stage(self) -> "MDAEvent":
        x = self.position.get("x")
        y = self.position.get("y")
        if x and y and x.stage != y.stage:
            raise ValueError("x and y positions must use the same XY stage device")
        return self

    @field_validator("channel", mode="before")
    def _validate_channel(cls, val: Any) -> Any:
        return Channel(config=val) if isinstance(val, str) else val

    if field_serializer is not None:
        _si = field_serializer("index", mode="plain")(lambda v: dict(v))

        @field_serializer("position", mode="plain")
        @classmethod
        def _serialize_positions(
            cls, v: dict[str, StagePosition]
        ) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, sp in v.items():
                if sp.stage is None:
                    result[key] = {"pos": float(sp.pos)}
                else:
                    result[key] = {"pos": float(sp.pos), "stage": sp.stage}
            return result

    if model_serializer is not None:

        @model_serializer(mode="wrap")
        def _serialize_model(self, handler):  # type: ignore
            data = handler(self)
            # Convert position to legacy format if possible
            position = data.pop("position", {})
            _SPATIAL = {"x", "y", "z"}
            all_spatial_no_stage = all(
                k in _SPATIAL
                and (not isinstance(v, dict) or v.get("stage") is None)
                for k, v in position.items()
            )
            if all_spatial_no_stage:
                for axis in ("x", "y", "z"):
                    if axis in position:
                        val = position[axis]
                        data[f"{axis}_pos"] = (
                            float(val["pos"])
                            if isinstance(val, dict)
                            else float(val.pos)
                        )
            elif position:
                data["position"] = position
            return data

    if TYPE_CHECKING:

        class Kwargs(TypedDict, total=False):
            """Type for the kwargs passed to the MDA event."""

            index: dict[str, int]
            channel: "Channel | Channel.Kwargs"
            exposure: float
            min_start_time: float
            pos_name: str
            x_pos: float
            y_pos: float
            z_pos: float
            position: "dict[str, StagePosition | StagePosition.Kwargs]"
            slm_image: "SLMImage | SLMImage.Kwargs | npt.ArrayLike"
            sequence: "MDASequence | dict"
            properties: list[tuple[str, str, Any]]
            roi: "CameraROI | CameraROI.Kwargs | tuple[int, int, int, int]"
            metadata: dict
            action: AnyAction
            keep_shutter_open: bool
            reset_event_timer: bool

        class KwargsContribution(Kwargs, total=False):
            is_relative: bool
