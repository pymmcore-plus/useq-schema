from typing import Iterator, List, Sequence, Union

import numpy as np

from useq._base_model import FrozenModel
from useq._utils import list_cast


class ZPlan(FrozenModel):
    go_up: bool

    def __iter__(self) -> Iterator[float]:  # type: ignore
        positions = self.positions()
        if not self.go_up:
            positions = positions[::-1]
        yield from positions

    def positions(self) -> Sequence[float]:
        raise NotImplementedError()

    def __len__(self) -> int:
        return len(self.positions())

    @property
    def is_relative(self) -> bool:
        return True


class ZTopBottom(ZPlan):
    """Define Z using absolute top & bottom positions.

    Attributes
    ----------
    top : float
        Top position.
    bottom : float
        Bottom position.
    step : float
        Step size in microns.
    go_up : bool
        If `True`, instructs engine to start at bottom and move towards top. By default,
        `True`.
    """

    top: float
    bottom: float
    step: float
    go_up: bool = True

    def positions(self) -> Sequence[float]:
        return np.arange(self.bottom, self.top + self.step, self.step)  # type: ignore

    @property
    def is_relative(self) -> bool:
        return False


# ZTopBottom()


class ZRangeAround(ZPlan):
    """Define Z as a symmetric range around some reference position.

    Attributes
    ----------
    range : float
        Range in microns.
    step : float
        Step size in microns.
    go_up : bool
        If `True`, instructs engine to start at bottom and move towards top. By default,
        `True`.
    """

    range: float
    step: float
    go_up: bool = True

    def positions(self) -> Sequence[float]:
        return np.arange(  # type: ignore
            -self.range / 2, self.range / 2 + self.step, self.step
        )


class ZAboveBelow(ZPlan):
    """Define Z as asymmetric range above and below some reference position.

    Attributes
    ----------
    above : float
        Range above reference position in microns.
    below : float
        Range below reference position in microns.
    step : float
        Step size in microns.
    go_up : bool
        If `True`, instructs engine to start at bottom and move towards top. By default,
        `True`.
    """

    above: float
    below: float
    step: float
    go_up: bool = True

    def positions(self) -> Sequence[float]:
        return np.arange(  # type: ignore
            -abs(self.below), +abs(self.above) + self.step, self.step
        )


class ZRelativePositions(ZPlan):
    """Define Z as a list of positions relative to some reference.

    Attributes
    ----------
    relative : list[float]
        List of relative z positions.
    go_up : bool
        If `True` (the default), visits points in the order provided, otherwise in
        reverse.
    """

    relative: List[float]
    go_up: bool = True

    _normrel = list_cast("relative")

    def positions(self) -> Sequence[float]:
        return self.relative


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
    go_up: bool = True

    _normabs = list_cast("absolute")

    def positions(self) -> Sequence[float]:
        return self.absolute

    @property
    def is_relative(self) -> bool:
        return False


# order matters... this is the order in which pydantic will try to coerce input.
# should go from most specific to least specific
AnyZPlan = Union[
    ZTopBottom, ZAboveBelow, ZRangeAround, ZAbsolutePositions, ZRelativePositions
]
