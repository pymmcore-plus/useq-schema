from typing import Any

from useq._actions import AcquireImage, Action, HardwareAutofocus
from useq._channel import Channel
from useq._grid import AnyGridPlan, GridFromEdges, GridRowsColumns, GridWidthHeight
from useq._hardware_autofocus import AnyAutofocusPlan, AutoFocusPlan, AxesBasedAF
from useq._mda_event import MDAEvent, PropertyTuple
from useq._mda_sequence import MDASequence
from useq._position import Position
from useq._time import (
    AnyTimePlan,
    MultiPhaseTimePlan,
    TDurationLoops,
    TIntervalDuration,
    TIntervalLoops,
)
from useq._z import (
    AnyZPlan,
    ZAboveBelow,
    ZAbsolutePositions,
    ZRangeAround,
    ZRelativePositions,
    ZTopBottom,
)

__all__ = [
    "AcquireImage",
    "Action",
    "AnyAutofocusPlan",
    "AnyGridPlan",
    "AnyTimePlan",
    "AnyZPlan",
    "AutoFocusPlan",
    "AxesBasedAF",
    "Channel",
    "GridFromEdges",
    "GridRelative",
    "GridRowsColumns",
    "GridWidthHeight",
    "HardwareAutofocus",
    "MDAEvent",
    "MDASequence",
    "MultiPhaseTimePlan",
    "Position",
    "PropertyTuple",
    "TDurationLoops",
    "TIntervalDuration",
    "TIntervalLoops",
    "ZAboveBelow",
    "ZAbsolutePositions",
    "ZRangeAround",
    "ZRelativePositions",
    "ZTopBottom",
]


# type ignores because pydantic-compat consumes the kwargs
MDAEvent.model_rebuild(MDASequence=MDASequence)  # type: ignore  [call-arg]
Position.model_rebuild(MDASequence=MDASequence)  # type: ignore  [call-arg]


def __getattr__(name: str) -> Any:
    if name == "GridRelative":
        from useq._grid import GridRowsColumns

        # warnings.warn(
        #     "useq.GridRelative has been renamed to useq.GridFromEdges",
        #     DeprecationWarning,
        #     stacklevel=2,
        # )

        return GridRowsColumns
    raise AttributeError(f"module {__name__} has no attribute {name}")
