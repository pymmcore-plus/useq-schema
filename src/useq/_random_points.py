from __future__ import annotations

import math
from typing import Iterator, NamedTuple, Optional, Union

import numpy as np
from pydantic_compat import Field

from useq._base_model import FrozenModel


class Point(NamedTuple):
    x: float
    y: float


class RandomPoints(FrozenModel):
    circular: bool
    nFOV: int
    area_width: float
    area_height: float
    random_seed: Optional[Union[int, None]] = Field(None)

    def iterate_random_points(self) -> Iterator[Point]:
        """Generate a list of random points in a circle or in a rectangle."""
        for fov in range(self.nFOV):
            # increase seed every time we yield a new point so it is reproducible
            # if we start from the same seed
            seed = self.random_seed + fov if self.random_seed is not None else None

            yield (
                self._random_point_in_circle(seed)
                if self.circular
                else self._random_point_in_rectangle(seed)
            )

    def _random_point_in_circle(self, seed: int | None) -> Point:
        """Generate a random point around a circle with center (0, 0).

        The point is within the bounding box (-radius, -radius, radius, radius)
        """
        radius = self.area_width / 2
        np.random.seed(seed)
        angle = np.random.uniform(0, 2 * math.pi)
        np.random.seed(seed + 1 if seed is not None else None)
        r = math.sqrt(np.random.uniform(0, 1)) * radius
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        return Point(x, y)

    def _random_point_in_rectangle(self, seed: int | None) -> Point:
        """Generate a random point around a rectangle with center (0, 0).

        The point is within the bounding box (-width/2, -height/2, width/2, height/2)
        """
        np.random.seed(seed)
        x = np.random.uniform(-self.area_width / 2, self.area_width / 2)
        np.random.seed(seed + 1 if seed is not None else None)
        y = np.random.uniform(-self.area_height / 2, self.area_height / 2)
        return Point(x, y)

    def __iter__(self) -> Iterator[Point]:  # type: ignore
        yield from self.iterate_random_points()
