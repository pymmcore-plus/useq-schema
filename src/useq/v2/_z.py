from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Literal, Union

import numpy as np
from annotated_types import Ge
from pydantic import Field
from typing_extensions import deprecated

from useq._base_model import FrozenModel
from useq._enums import Axis
from useq.v2._axes_iterator import AxisIterable
from useq.v2._position import Position

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from useq._mda_event import MDAEvent


class ZPlan(AxisIterable[Position], FrozenModel):
    """Base class for Z-axis plans in v2 MDA sequences.

    All Z plans inherit from MDAAxisIterable and can be used in
    the new v2 MDA sequence framework.
    """

    axis_key: Literal[Axis.Z] = Field(default=Axis.Z, frozen=True, init=False)

    @property
    def is_relative(self) -> bool:
        """Return True if Z positions are relative to current position."""
        return True

    def __iter__(self) -> Iterator[Position]:  # type: ignore[override]
        """Iterate over Z positions."""
        for z in self._z_positions():
            yield Position(z=z, is_relative=self.is_relative)

    def _z_positions(self) -> Iterator[float]:
        start, stop, step = self._start_stop_step()
        if step == 0:
            yield start
            return

        n_steps = round((stop - start) / step)
        z_positions = list(start + step * np.arange(n_steps + 1))
        if not getattr(self, "go_up", True):
            z_positions = z_positions[::-1]

        for z in z_positions:
            yield float(z)

    def _start_stop_step(self) -> tuple[float, float, float]:
        """Return start, stop, and step values for the Z range.

        Must be implemented by subclasses that use range-based positioning.
        """
        raise NotImplementedError

    def __len__(self) -> int:
        """Get the number of Z positions."""
        start, stop, step = self._start_stop_step()
        if step == 0:
            return 1
        nsteps = (stop + step - start) / step
        return math.ceil(round(nsteps, 6))

    def contribute_event_kwargs(
        self, value: Position, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        """Contribute Z position to the MDA event."""
        if value.z is not None:
            if self.is_relative:
                return {"z_pos_rel": value.z}  # type: ignore [typeddict-unknown-key]
            else:
                return {"z_pos": value.z}
        return {}

    @deprecated(
        "num_positions() is deprecated, use len(z_plan) instead.",
        category=UserWarning,
        stacklevel=2,
    )
    def num_positions(self) -> int:
        """Get the number of Z positions."""
        return len(self)


class ZTopBottom(ZPlan):
    """Define Z using absolute top & bottom positions.

    Note that `bottom` will always be visited, regardless of `go_up`, while `top` will
    always be *encompassed* by the range, but may not be precisely visited if the step
    size does not divide evenly into the range.

    Attributes
    ----------
    top : float
        Top position in microns (inclusive).
    bottom : float
        Bottom position in microns (inclusive).
    step : float
        Step size in microns.
    go_up : bool
        If `True`, instructs engine to start at bottom and move towards top. By default,
        `True`.
    """

    top: float
    bottom: float
    step: Annotated[float, Ge(0)]
    go_up: bool = True

    @property
    def is_relative(self) -> bool:
        return False

    def _start_stop_step(self) -> tuple[float, float, float]:
        return self.bottom, self.top, self.step


class ZRangeAround(ZPlan):
    """Define Z as a symmetric range around some reference position.

    Note that `-range / 2` will always be visited, regardless of `go_up`, while
    `+range / 2` will always be *encompassed* by the range, but may not be precisely
    visited if the step size does not divide evenly into the range.

    Attributes
    ----------
    range : float
        Range in microns (inclusive). For example, a range of 4 with a step size
        of 1 would visit [-2, -1, 0, 1, 2].
    step : float
        Step size in microns.
    go_up : bool
        If `True`, instructs engine to start at bottom and move towards top. By default,
        `True`.
    """

    range: float
    step: Annotated[float, Ge(0)]
    go_up: bool = True

    def _start_stop_step(self) -> tuple[float, float, float]:
        return -self.range / 2, self.range / 2, self.step


class ZAboveBelow(ZPlan):
    """Define Z as asymmetric range above and below some reference position.

    Note that `below` will always be visited, regardless of `go_up`, while `above` will
    always be *encompassed* by the range, but may not be precisely visited if the step
    size does not divide evenly into the range.

    Attributes
    ----------
    above : float
        Range above reference position in microns (inclusive).
    below : float
        Range below reference position in microns (inclusive).
    step : float
        Step size in microns.
    go_up : bool
        If `True`, instructs engine to start at bottom and move towards top. By default,
        `True`.
    """

    above: float
    below: float
    step: Annotated[float, Ge(0)]
    go_up: bool = True

    def _start_stop_step(self) -> tuple[float, float, float]:
        return -abs(self.below), +abs(self.above), self.step


class ZRelativePositions(ZPlan):
    """Define Z as a list of positions relative to some reference.

    Typically, the "reference" will be whatever the current Z position is at the start
    of the sequence.

    Attributes
    ----------
    relative : list[float]
        List of relative z positions.
    """

    relative: list[float]

    def _z_positions(self) -> Iterator[float]:
        yield from self.relative

    def __len__(self) -> int:
        return len(self.relative)


class ZAbsolutePositions(ZPlan):
    """Define Z as a list of absolute positions.

    Attributes
    ----------
    absolute : list[float]
        List of absolute z positions.
    """

    absolute: list[float]

    @property
    def is_relative(self) -> bool:
        return False

    def _z_positions(self) -> Iterator[float]:
        yield from self.absolute

    def __len__(self) -> int:
        return len(self.absolute)


# Union type for all Z plan types - order matters for pydantic coercion
# should go from most specific to least specific
AnyZPlan = Union[
    ZTopBottom, ZAboveBelow, ZRangeAround, ZAbsolutePositions, ZRelativePositions
]
