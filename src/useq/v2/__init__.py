"""New MDASequence API."""

from useq.v2._axes_iterator import AxisIterable, MultiAxisSequence, SimpleValueAxis
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
    TIntervalDuration,
    TIntervalLoops,
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

__all__ = [
    "AnyTimePlan",
    "AnyZPlan",
    "AxisIterable",
    "ChannelsPlan",
    "GridFromEdges",
    "GridRowsColumns",
    "GridWidthHeight",
    "MDASequence",
    "MultiAxisSequence",
    "MultiPhaseTimePlan",
    "MultiPointPlan",
    "MultiPositionPlan",
    "Position",
    "RandomPoints",
    "RelativeMultiPointPlan",
    "SimpleValueAxis",
    "SinglePhaseTimePlan",
    "StagePositions",
    "TDurationLoops",
    "TIntervalDuration",
    "TIntervalLoops",
    "ZAboveBelow",
    "ZAbsolutePositions",
    "ZPlan",
    "ZRangeAround",
    "ZRelativePositions",
    "ZTopBottom",
    "iterate_multi_dim_sequence",
]

import pydantic

for item in list(globals().values()):
    if (
        isinstance(item, type)
        and issubclass(item, pydantic.BaseModel)
        and item is not pydantic.BaseModel
    ):
        item.model_rebuild()

del pydantic
