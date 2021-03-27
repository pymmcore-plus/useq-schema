from typing import Iterator, List, Sequence, Union

import numpy as np
from pydantic import BaseModel


class ZPlan(BaseModel):
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
    """Define absolute top & bottom positions."""

    top: float
    bottom: float
    step: float
    go_up: bool = True

    def positions(self) -> Sequence[float]:
        return np.arange(self.bottom, self.top + self.step, self.step)

    @property
    def is_relative(self) -> bool:
        return False


# ZTopBottom()


class ZRangeAround(ZPlan):
    """Range symmetrically around some reference position."""

    range: float
    step: float
    go_up: bool = True

    def positions(self) -> Sequence[float]:
        return np.arange(-self.range / 2, self.range / 2 + self.step, self.step)


class ZAboveBelow(ZPlan):
    """Range asymmetrically above and below some reference position."""

    above: float
    below: float
    step: float
    go_up: bool = True

    def positions(self) -> Sequence[float]:
        return np.arange(-abs(self.below), +abs(self.above) + self.step, self.step)


class ZRelativePositions(ZPlan):
    """Direct list of relative z positions."""

    relative: List[float]
    go_up: bool = True

    def positions(self) -> Sequence[float]:
        return self.relative


class ZAbsolutePositions(ZPlan):
    """Direct list of absolute z positions."""

    absolute: List[float]
    go_up: bool = True

    def positions(self) -> Sequence[float]:
        return self.absolute

    @property
    def is_relative(self) -> bool:
        return False


class NoZ(ZPlan):
    """Don't acquire Z."""

    go_up: bool = True

    def positions(self) -> Sequence[float]:
        return []

    def __bool__(self) -> bool:
        return False


AnyZPlan = Union[
    ZTopBottom, ZRangeAround, ZAboveBelow, ZRelativePositions, ZAbsolutePositions, NoZ
]
