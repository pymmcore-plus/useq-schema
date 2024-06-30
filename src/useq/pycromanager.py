from __future__ import annotations

from typing import TYPE_CHECKING, overload

from useq import MDAEvent, MDASequence
from useq._utils import Axis

if TYPE_CHECKING:
    from typing_extensions import Literal, Required, TypedDict

    class PycroManagerAxes(TypedDict, total=False):
        """Axes dict used by pycro-manager."""

        time: int
        position: int
        z: int
        channel: str
        row: int
        column: int

    class PycroManagerEvent(TypedDict, total=False):
        """Dict in the format expected by pycro-manager."""

        axes: Required[PycroManagerAxes]
        x: float
        y: float
        z: float
        min_start_time: float
        config_group: list[str]  # [group, config]
        exposure: float
        properties: list[list[str]]  # [[device, property, value], ...]
        keep_shutter_open: bool

    PycroAxis = Literal["time", "position", "z", "channel", "row", "column"]
    PycroKey = Literal["x", "y", "z", "exposure", "min_start_time", "keep_shutter_open"]


@overload
def to_pycromanager(obj: MDAEvent) -> PycroManagerEvent: ...


@overload
def to_pycromanager(obj: MDASequence) -> list[PycroManagerEvent]: ...


def to_pycromanager(
    obj: MDAEvent | MDASequence,
) -> PycroManagerEvent | list[PycroManagerEvent]:
    """Convert a [`useq.MDAEvent`][] or [`useq.MDASequence`][] to pycro-manager form.

    Parameters
    ----------
    obj : MDAEvent | MDASequence
        The event or sequence to convert.

    Returns
    -------
    PycroManagerEvent | list[PycroManagerEvent]
        If `obj` is an [`useq.MDAEvent`][], returns a single pycro-manager event dict.
        Otherwise, returns a list of pycro-manager event dicts.
    """
    if isinstance(obj, MDAEvent):
        return _event_to_pycromanager(obj)
    elif isinstance(obj, MDASequence):
        return [_event_to_pycromanager(event) for event in obj]
    raise TypeError(  # pragma: no cover
        f"invalid argument: {obj!r}. Must be MDAEvent or MDASequence."
    )


_USEQ_AXIS_TO_PYCRO: dict[str, PycroAxis] = {
    Axis.TIME: "time",
    Axis.POSITION: "position",
    Axis.Z: "z",
    Axis.CHANNEL: "channel",
}
_USEQ_KEY_TO_PYCRO: dict[str, PycroKey] = {
    "exposure": "exposure",
    "x_pos": "x",
    "y_pos": "y",
    "z_pos": "z",
    "min_start_time": "min_start_time",
    "keep_shutter_open": "keep_shutter_open",
}


def _event_to_pycromanager(event: MDAEvent) -> PycroManagerEvent:
    """Convenience method to convert this event to a pycro-manager events.

    See: <https://pycro-manager.readthedocs.io/en/latest/apis.html>
    """
    pycro: PycroManagerEvent = {"axes": {}}

    for axis in event.index.keys():
        if axis in _USEQ_AXIS_TO_PYCRO:
            pycro["axes"][_USEQ_AXIS_TO_PYCRO[axis]] = event.index[axis]

    for useq_name, pycro_name in _USEQ_KEY_TO_PYCRO.items():
        if (val := getattr(event, useq_name)) is not None:
            pycro[pycro_name] = val

    if event.channel:
        pycro["config_group"] = [event.channel.group, event.channel.config]

    if event.properties:
        pycro["properties"] = [list(p) for p in event.properties]

    return pycro
