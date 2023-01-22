from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    NamedTuple,
    NoReturn,
    Optional,
    Sequence,
    Tuple,
)

from pydantic import Field, validator
from pydantic.types import PositiveFloat

from ._base_model import UseqModel
from ._utils import ReadOnlyDict

if TYPE_CHECKING:
    from ._mda_sequence import MDASequence

    ReprArgs = Sequence[Tuple[Optional[str], Any]]


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


def _readonly(self: object, *_: Any, **__: Any) -> NoReturn:
    raise RuntimeError(f"Cannot modify {type(self).__name__}")


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
    exposure : PositiveFloat | None
        Exposure time in seconds. If not provided, implies use current exposure time.
        By default, `None`.
    min_start_time : float | None
        Minimum start time of this event, in seconds.  If provided, the engine will
        pause until this time has elapsed (relative to the start of the sequence)
        before starting this event. By default, `None`.
    x_pos : float | None
        X position in microns. If not provided, implies use current position. By
        default, `None`.
    y_pos : float | None
        Y position in microns. If not provided, implies use current position. By
        default, `None`.
    z_pos : float | None
        Z position in microns. If not provided, implies use current position. By
        default, `None`.
    properties : Sequence[PropertyTuple] | None
        List of [`useq.PropertyTuple`][] to set before starting this event. Where each
        item in the list is a 3-member named tuple of `(device_name, property_name,
        property_value)`.  This is inspired by micro-manager's Device Adapter API, but
        could be used to set arbitrary properties in any backend that supports the
        concept of devices that have properties with values. By default, `None`.
    sequence : MDASequence | None
        A reference to the [`useq.MDASequence`][] this event belongs to. This is a
        read-only attribute. By default, `None`.
    global_index : int
        The global index of this event in the sequence. For example, in an
        `MDASequence` with 2 channels and 5 time points, the global index of each
        event will be an integer from 0 to 9.  By default, `0`.
    metadata : dict
        Optional metadata to be associated with this event.
    """

    index: ReadOnlyDict[str, int] = Field(default_factory=ReadOnlyDict)
    channel: Optional[Channel] = None
    exposure: Optional[PositiveFloat] = None
    min_start_time: Optional[float] = None  # time in sec
    pos_name: Optional[str] = None
    x_pos: Optional[float] = None
    y_pos: Optional[float] = None
    z_pos: Optional[float] = None
    properties: Optional[List[PropertyTuple]] = None
    sequence: Optional[MDASequence] = Field(default=None, repr=False)
    global_index: int = Field(default=0, repr=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # action
    # keep shutter open between channels/steps

    @validator("index", pre=True)
    def validate_index(cls, v: dict) -> ReadOnlyDict[str, int]:
        return ReadOnlyDict(v)

    def __repr_args__(self) -> ReprArgs:
        d = self.__dict__.copy()
        d.pop("sequence")
        return list(d.items())

    def to_pycromanager(self) -> dict:
        """Convenience method to convert this event to a pycro-manager events.

        See: <https://pycro-manager.readthedocs.io/en/latest/apis.html>
        """
        d: Dict[str, Any] = {
            "exposure": self.exposure,
            "axes": {},
            "z": self.z_pos,
            "x": self.x_pos,
            "y": self.y_pos,
            "min_start_time": self.min_start_time,
            "channel": self.channel and self.channel.dict(),
        }
        if "p" in self.index:
            d["axes"]["position"] = self.index["p"]
        if "t" in self.index:
            d["axes"]["time"] = self.index["t"]
        if "z" in self.index:
            d["axes"]["z"] = self.index["z"]
        if self.properties:
            d["properties"] = [list(p) for p in self.properties]

        for key, value in list(d.items()):
            if value is None:
                d.pop(key)
        return d
