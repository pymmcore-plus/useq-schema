from __future__ import annotations

import warnings
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    NamedTuple,
    NoReturn,
    Optional,
    Sequence,
    Tuple,
)

from pydantic import Field

from useq._actions import AcquireImage, AnyAction
from useq._base_model import UseqModel

if TYPE_CHECKING:
    from useq._mda_sequence import MDASequence
    from useq.pycromanager import PycroManagerEvent

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

    def __eq__(self, _value: object) -> bool:
        if isinstance(_value, str):
            return self.config == _value
        return super().__eq__(_value)


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
    exposure : float | None
        Exposure time in milliseconds. If not provided, implies use current exposure
        time. By default, `None`.
    min_start_time : float | None
        Minimum start time of this event, in seconds.  If provided, the engine will
        pause until this time has elapsed (relative to the start of the sequence)
        before starting this event. By default, `None`.
    pos_name : str | None
        The name assigned to the position. By default, `None`.
    x_pos : float | None
        X position in microns. If not provided, implies use current position. By
        default, `None`.
    y_pos : float | None
        Y position in microns. If not provided, implies use current position. By
        default, `None`.
    z_pos : float | None
        Z position in microns. If not provided, implies use current position. By
        default, `None`.
    sequence : MDASequence | None
        A reference to the [`useq.MDASequence`][] this event belongs to. This is a
        read-only attribute. By default, `None`.
    properties : Sequence[PropertyTuple] | None
        List of [`useq.PropertyTuple`][] to set before starting this event. Where each
        item in the list is a 3-member named tuple of `(device_name, property_name,
        property_value)`.  This is inspired by micro-manager's Device Adapter API, but
        could be used to set arbitrary properties in any backend that supports the
        concept of devices that have properties with values. By default, `None`.
    metadata : dict
        Optional metadata to be associated with this event.
    action : Action
        The action to perform for this event.  By default, [`useq.AcquireImage`][].
        Example of another action is [`useq.HardwareAutofocus`][] which could be used
        to perform a hardware autofocus.
    keep_shutter_open : bool
        If True, the illumination shutter should be left open after the event has
        been executed, otherwise it should be closed. By default, `False`."
        This is useful when the sequence of events being executed use the same
        illumination scheme (such as a z-stack in a single channel), and closing and
        opening the shutter between events would be slow.
    """

    # MappingProxyType is not subscriptable on Python 3.8
    index: Mapping[str, int] = Field(default_factory=lambda: MappingProxyType({}))
    channel: Optional[Channel] = None
    exposure: Optional[float] = Field(default=None, gt=0.0)
    min_start_time: Optional[float] = None  # time in sec
    pos_name: Optional[str] = None
    x_pos: Optional[float] = None
    y_pos: Optional[float] = None
    z_pos: Optional[float] = None
    sequence: Optional[MDASequence] = Field(default=None, repr=False)
    properties: Optional[List[PropertyTuple]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    action: AnyAction = Field(default_factory=AcquireImage)
    keep_shutter_open: bool = False

    # action
    # keep shutter open between channels/steps
    @property
    def global_index(self) -> int:
        warnings.warn(
            "global_index is no longer functional.  Use `enumerate()` "
            "on an iterable of events instead.",
            stacklevel=2,
        )
        return 0

    def __repr_args__(self) -> ReprArgs:
        d = self.__dict__.copy()
        d.pop("sequence")
        return list(d.items())

    def to_pycromanager(self) -> PycroManagerEvent:
        from useq.pycromanager import to_pycromanager

        warnings.warn(
            "useq.MDAEvent.to_pycromanager() is deprecated and will be removed in a "
            "future version. Useq useq.pycromanager.to_pycromanager(event) instead.",
            FutureWarning,
            stacklevel=2,
        )

        return to_pycromanager(self)
