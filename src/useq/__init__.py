"""Implementation agnostic schema for multi-dimensional microscopy experiments."""

from typing import Any

from useq._actions import AcquireImage, Action, HardwareAutofocus
from useq._channel import Channel
from useq._grid import (
    AnyGridPlan,
    GridFromEdges,
    GridRowsColumns,
    GridWidthHeight,
    RandomPoints,
)
from useq._hardware_autofocus import AnyAutofocusPlan, AutoFocusPlan, AxesBasedAF
from useq._mda_event import MDAEvent, PropertyTuple
from useq._mda_sequence import MDASequence
from useq._position import AbsolutePosition, Position, RelativePosition
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
    "AbsolutePosition",
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
    "RandomPoints",
    "RelativePosition",
    "TDurationLoops",
    "TIntervalDuration",
    "TIntervalLoops",
    "ZAboveBelow",
    "ZAbsolutePositions",
    "ZRangeAround",
    "ZRelativePositions",
    "ZTopBottom",
]


MDAEvent.model_rebuild()
Position.model_rebuild()


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
