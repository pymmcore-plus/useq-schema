from __future__ import annotations

import math
from typing import Callable, Iterator, List, Sequence, Union

import numpy as np
from pydantic import field_validator

from useq._base_model import FrozenModel


def _list_cast(field: str) -> Callable:
    v = field_validator(field, mode="before", check_fields=False)
    return v(list)


class ZPlan(FrozenModel):
    go_up: bool = True

    def __iter__(self) -> Iterator[float]:  # type: ignore
        positions = self.positions()
        if not self.go_up:
            positions = positions[::-1]
        yield from positions

    def _start_stop_step(self) -> tuple[float, float, float]:
        raise NotImplementedError

    def positions(self) -> Sequence[float]:
        start, stop, step = self._start_stop_step()
        if step == 0:
            return [start]
        stop += step / 2  # make sure we include the last point
        return list(np.arange(start, stop, step))

    def num_positions(self) -> int:
        start, stop, step = self._start_stop_step()
        if step == 0:
            return 1
        nsteps = (stop + step - start) / step
        return math.ceil(round(nsteps, 6))

    @property
    def is_relative(self) -> bool:
        return True


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
    step: float

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
    step: float

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
    step: float

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
    go_up : bool
        If `True` (the default), visits points in the order provided, otherwise in
        reverse.
    """

    relative: List[float]

    _normrel = _list_cast("relative")

    def positions(self) -> Sequence[float]:
        return self.relative

    def num_positions(self) -> int:
        return len(self.relative)


class ZAbsolutePositions(ZPlan):
    """Define Z as a list of absolute positions.

    Attributes
    ----------
    relative : list[float]
        List of relative z positions.
    go_up : bool
        If `True` (the default), visits points in the order provided, otherwise in
        reverse.
    """

    absolute: List[float]

    _normabs = _list_cast("absolute")

    def positions(self) -> Sequence[float]:
        return self.absolute

    def num_positions(self) -> int:
        return len(self.absolute)

    @property
    def is_relative(self) -> bool:
        return False


# order matters... this is the order in which pydantic will try to coerce input.
# should go from most specific to least specific
AnyZPlan = Union[
    ZTopBottom, ZAboveBelow, ZRangeAround, ZAbsolutePositions, ZRelativePositions
]
