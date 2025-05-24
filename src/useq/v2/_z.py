from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Literal, Union

import numpy as np
from annotated_types import Ge
from pydantic import Field

from useq._base_model import FrozenModel
from useq._utils import Axis
from useq.v2._mda_seq import MDAAxisIterable
from useq.v2._position import Position

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from useq._mda_event import MDAEvent


class ZPlan(MDAAxisIterable[Position], FrozenModel):
    """Base class for Z-axis plans in v2 MDA sequences.

    All Z plans inherit from MDAAxisIterable and can be used in
    the new v2 MDA sequence framework.
    """

    axis_key: Literal[Axis.Z] = Field(default=Axis.Z, frozen=True, init=False)

    def iter(self) -> Iterator[Position]:
        """Iterate over Z positions."""
        for z in self._z_positions():
            yield Position(z=z, is_relative=self.is_relative)

    def _z_positions(self) -> Iterator[float]:
        start, stop, step = self._start_stop_step()
        if step == 0:
            yield start
            return

        z_positions = list(np.arange(start, stop + step, step))
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

    @property
    def is_relative(self) -> bool:
        """Return True if Z positions are relative to current position."""
        return True

    def contribute_to_mda_event(
        self, value: Position, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        """Contribute Z position to the MDA event."""
        return {"z_pos": value.z}


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

    def _start_stop_step(self) -> tuple[float, float, float]:
        return self.bottom, self.top, self.step

    @property
    def is_relative(self) -> bool:
        return False


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

    def _z_positions(self) -> Iterator[float]:
        yield from self.absolute

    def __len__(self) -> int:
        return len(self.absolute)

    @property
    def is_relative(self) -> bool:
        return False


# Union type for all Z plan types - order matters for pydantic coercion
# should go from most specific to least specific
AnyZPlan = Union[
    ZTopBottom, ZAboveBelow, ZRangeAround, ZAbsolutePositions, ZRelativePositions
]
