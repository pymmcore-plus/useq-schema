from typing import Annotated

from annotated_types import Ge

from useq.v2._axes_iterator import AxisIterable
from useq.v2._position import Position


class MultiPositionPlan(AxisIterable[Position]):
    """Base class for all multi-position plans."""

    fov_width: Annotated[float, Ge(0)] | None = None
    fov_height: Annotated[float, Ge(0)] | None = None

    @property
    def is_relative(self) -> bool:
        return True
