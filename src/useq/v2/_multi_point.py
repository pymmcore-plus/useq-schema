from abc import abstractmethod
from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Annotated

from annotated_types import Ge

from useq.v2._axes_iterator import AxisIterable
from useq.v2._position import Position

if TYPE_CHECKING:
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
    ) -> "MDAEvent.Kwargs":
        out: dict = {}
        rel = "_rel" if self.is_relative else ""
        if value.x is not None:
            out[f"x_pos{rel}"] = value.x
        if value.y is not None:
            out[f"y_pos{rel}"] = value.y
        if value.z is not None:
            out[f"z_pos{rel}"] = value.z
        # if value.name is not None:
        # out["pos_name"] = value.name

        # TODO: deal with the _rel suffix hack
        return out  # type: ignore[return-value]

    def plot(self, *, show: bool = True) -> "Axes":
        """Plot the positions in the plan."""
        from useq._plot import plot_points

        rect = None
        if self.fov_width is not None and self.fov_height is not None:
            rect = (self.fov_width, self.fov_height)

        return plot_points(self, rect_size=rect, show=show)  # type: ignore[arg-type]
