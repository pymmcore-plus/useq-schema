from __future__ import annotations

import math
from typing import Iterator, NamedTuple, Optional, Union

import numpy as np
from pydantic_compat import Field

from useq._base_model import FrozenModel


class Point(NamedTuple):
    x: float
    y: float


class RandomArea(NamedTuple):
    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> Point:
        return Point(self.x + (self.width / 2), self.y + (self.height / 2))


class RandomPoints(FrozenModel):
    circular: bool
    nFOV: int
    area: RandomArea
    random_seed: Optional[Union[int, None]] = Field(None)

    def iterate_random_points(self) -> Iterator[Point]:
        """Generate a list of random points in a circle or in a rectangle."""
        for fov in range(self.nFOV):
            # increase seed every time we yield a new point so it is reproducible
            # if we start from the same seed
            seed = self.random_seed + fov if self.random_seed is not None else None

            yield (
                self._random_point_in_circle(self.area, seed)
                if self.circular
                else self._random_point_in_rectangle(self.area, seed)
            )

    def _random_point_in_circle(self, area: RandomArea, seed: int | None) -> Point:
        """Generate a random point around the center of a circle."""
        radius = area.width / 2
        np.random.seed(seed)
        angle = np.random.uniform(0, 2 * math.pi)
        np.random.seed(seed + 1 if seed is not None else None)
        x = area.center.x + (np.random.uniform(0, radius) * math.cos(angle))
        np.random.seed(seed + 2 if seed is not None else None)
        y = area.center.y + (np.random.uniform(0, radius) * math.sin(angle))
        return Point(x, y)

    def _random_point_in_rectangle(self, area: RandomArea, seed: int | None) -> Point:
        """Generate a random point around the center of a rectangle."""
        np.random.seed(seed + 1 if seed is not None else None)
        x = np.random.uniform(
            area.center.x - (area.width / 2), area.center.x + (area.width / 2)
        )
        np.random.seed(seed + 2 if seed is not None else None)
        y = np.random.uniform(
            area.center.y - (area.height / 2), area.center.y + (area.height / 2)
        )
        return Point(x, y)

    def __iter__(self) -> Iterator[Point]:  # type: ignore
        yield from self.iterate_random_points()
