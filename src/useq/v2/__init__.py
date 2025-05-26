"""New MDASequence API."""

from typing import TYPE_CHECKING

from useq.v2._axes_iterator import AxesIterator, AxisIterable, SimpleValueAxis
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

if TYPE_CHECKING:
    from useq.v2._position import Position
else:
    from useq.v2 import _position

    def Position(**kwargs) -> "_position.Position":
        """Converter for legacy Position class."""
        if "sequence" in kwargs:
            seq = kwargs.pop("sequence")
            seq = MDASequence.model_validate(seq)
            return seq.model_copy(
                update={"value": _position.Position.model_validate(kwargs)}
            )
        return _position.Position(**kwargs)


__all__ = [
    "AnyTimePlan",
    "AnyZPlan",
    "AxesIterator",
    "AxisIterable",
    "ChannelsPlan",
    "GridFromEdges",
    "GridRowsColumns",
    "GridWidthHeight",
    "MDASequence",
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
