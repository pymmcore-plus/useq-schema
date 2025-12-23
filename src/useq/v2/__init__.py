"""New MDASequence API."""

from typing import Any

import pydantic
from typing_extensions import deprecated

from useq._actions import AcquireImage, Action, CustomAction, HardwareAutofocus
from useq._channel import Channel
from useq._enums import Axis, RelativeTo, Shape
from useq._hardware_autofocus import AnyAutofocusPlan, AutoFocusPlan, AxesBasedAF
from useq._mda_event import Channel as EventChannel
from useq._mda_event import MDAEvent, PropertyTuple, SLMImage
from useq._plate import WellPlate, WellPlatePlan
from useq._plate_registry import register_well_plates, registered_well_plate_keys
from useq._point_visiting import OrderMode, TraversalOrder
from useq.v2._axes_iterator import (
    AxisIterable,
    EventBuilder,
    EventTransform,
    MultiAxisSequence,
    SimpleValueAxis,
)
from useq.v2._channels import ChannelsPlan
from useq.v2._grid import (
    GridFromEdges,
    GridRowsColumns,
    GridWidthHeight,
    MultiPointPlan,
    RandomPoints,
    RelativeMultiPointPlan,
)
from useq.v2._iterate import iterate_multi_dim_sequence
from useq.v2._mda_sequence import MDASequence
from useq.v2._multi_point import MultiPositionPlan
from useq.v2._position import Position
from useq.v2._stage_positions import StagePositions
from useq.v2._time import (
    AnyTimePlan,
    MultiPhaseTimePlan,
    SinglePhaseTimePlan,
    TDurationLoops,
    TimePlan,
    TIntervalDuration,
    TIntervalLoops,
)
from useq.v2._transformers import (
    AutoFocusTransform,
    KeepShutterOpenTransform,
    ResetEventTimerTransform,
)
from useq.v2._z import (
    AnyZPlan,
    ZAboveBelow,
    ZAbsolutePositions,
    ZPlan,
    ZRangeAround,
    ZRelativePositions,
    ZTopBottom,
)

AbsolutePosition = Position


@deprecated(
    "The RelativePosition class is deprecated. "
    "Use Position with is_relative=True instead.",
    category=DeprecationWarning,
    stacklevel=2,
)
def RelativePosition(**kwargs: Any) -> Position:
    """Create a relative position."""
    return Position(**kwargs, is_relative=True)


__all__ = [
    "AbsolutePosition",
    "AcquireImage",
    "Action",
    "AnyAutofocusPlan",
    "AnyTimePlan",
    "AnyZPlan",
    "AutoFocusPlan",
    "AutoFocusTransform",
    "AxesBasedAF",
    "Axis",
    "AxisIterable",
    "Channel",
    "ChannelsPlan",
    "CustomAction",
    "EventBuilder",
    "EventChannel",
    "EventTransform",
    "GridFromEdges",
    "GridRowsColumns",
    "GridWidthHeight",
    "HardwareAutofocus",
    "KeepShutterOpenTransform",
    "MDAEvent",
    "MDASequence",
    "MultiAxisSequence",
    "MultiPhaseTimePlan",
    "MultiPointPlan",
    "MultiPositionPlan",
    "OrderMode",
    "Position",  # alias for AbsolutePosition
    "PropertyTuple",
    "RandomPoints",
    "RelativeMultiPointPlan",
    "RelativePosition",
    "RelativeTo",
    "ResetEventTimerTransform",
    "SLMImage",
    "Shape",
    "SimpleValueAxis",
    "SinglePhaseTimePlan",
    "StagePositions",
    "TDurationLoops",
    "TIntervalDuration",
    "TIntervalLoops",
    "TimePlan",
    "TraversalOrder",
    "WellPlate",
    "WellPlatePlan",
    "ZAboveBelow",
    "ZAbsolutePositions",
    "ZPlan",
    "ZRangeAround",
    "ZRelativePositions",
    "ZTopBottom",
    "iterate_multi_dim_sequence",
    "register_well_plates",
    "registered_well_plate_keys",
]

MDASequence.model_rebuild()

for item in list(globals().values()):
    if (
        isinstance(item, type)
        and issubclass(item, pydantic.BaseModel)
        and item is not pydantic.BaseModel
    ):
        item.model_rebuild()

del pydantic
