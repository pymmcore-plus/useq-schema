"""Implementation agnostic schema for multi-dimensional microscopy experiments."""

import warnings
from typing import Any

from useq._actions import AcquireImage, Action, HardwareAutofocus
from useq._channel import Channel
from useq._grid import (
    GridFromEdges,
    GridRowsColumns,
    GridWidthHeight,
    MultiPointPlan,
    RandomPoints,
    RelativeMultiPointPlan,
    Shape,
)
from useq._hardware_autofocus import AnyAutofocusPlan, AutoFocusPlan, AxesBasedAF
from useq._mda_event import MDAEvent, PropertyTuple
from useq._mda_sequence import MDASequence
from useq._plate import WellPlate, WellPlatePlan
from useq._plate_registry import register_well_plates, registered_well_plate_keys
from useq._point_visiting import OrderMode, TraversalOrder
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
    "MultiPointPlan",
    "OrderMode",
    "Position",  # alias for AbsolutePosition
    "PropertyTuple",
    "RandomPoints",
    "register_well_plates",
    "registered_well_plate_keys",
    "RelativeMultiPointPlan",
    "RelativePosition",
    "Shape",
    "TDurationLoops",
    "TIntervalDuration",
    "TIntervalLoops",
    "TraversalOrder",
    "WellPlate",
    "WellPlatePlan",
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
    if name == "AnyGridPlan":  # pragma: no cover
        warnings.warn(
            "useq.AnyGridPlan has been renamed to useq.MultiPointPlan",
            DeprecationWarning,
            stacklevel=2,
        )
        return MultiPointPlan
    raise AttributeError(f"module {__name__} has no attribute {name}")
