from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Annotated

from annotated_types import Ge

from useq.v2._axes_iterator import AxisIterable
from useq.v2._position import Position

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from matplotlib.axes import Axes

    from useq._mda_event import MDAEvent


class MultiPositionPlan(AxisIterable[Position]):
    """Base class for all multi-position plans."""

    fov_width: Annotated[float, Ge(0)] | None = None
    fov_height: Annotated[float, Ge(0)] | None = None

    @property
    def is_relative(self) -> bool:
        return True

    @abstractmethod
    def __iter__(self) -> Iterator[Position]: ...  # type: ignore[override]

    def contribute_to_mda_event(
        self, value: Position, index: Mapping[str, int]
    ) -> MDAEvent.KwargsContribution:
        out: MDAEvent.KwargsContribution = {}
        if value.x is not None:
            out["x_pos"] = value.x
        if value.y is not None:
            out["y_pos"] = value.y
        if value.z is not None:
            out["z_pos"] = value.z
        # Note: pos_name is intentionally NOT included here for grid plans.
        # In v1, pos_name comes from stage positions, not grid positions.
        if out:
            out["is_relative"] = value.is_relative
        return out

    def plot(self, *, show: bool = True) -> Axes:
        """Plot the positions in the plan."""
        from useq._plot import plot_points

        rect = None
        if self.fov_width is not None and self.fov_height is not None:
            rect = (self.fov_width, self.fov_height)

        return plot_points(self, rect_size=rect, show=show)  # type: ignore[arg-type]
