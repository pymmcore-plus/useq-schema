from __future__ import annotations

import itertools
import math
from typing import Any, Iterator, Literal, Union

from useq._base_model import FrozenModel


class Coordinate(FrozenModel):
    """Defines a position in 2D space.

    Attributes
    ----------
    x : float
        X position in microns.
    y : float
        Y position in microns.
    """

    x: float
    y: float


class _TilePlan(FrozenModel):
    """Base class for all tile plans.

    Attributes
    ----------
    overlap : float | tuple[float, float]
        Overlap between tiles in percent. If a single value is provided, it is
        used for both x and y. If a tuple is provided, the first value is used
        for x and the second for y.
    snake_order : bool
        If `True`, tiles are arranged in a snake order (i.e. back and forth).
        If `False`, tiles are arranged in a row-wise order.
    """

    overlap: float | tuple[float, float] = 0.0
    snake_order: bool = True

    def iter_tiles(self, fov_width: float, fov_height: float) -> Iterator[dict]:
        """Iterate over all tiles, given a field of view size."""
        raise NotImplementedError()

    def __len__(self) -> int:
        return len(list(self.iter_tiles(1, 1)))


class TileFromCorners(_TilePlan):
    """Define tile positions from two corners.

    Attributes
    ----------
    corner1 : Coordinate
        First bounding coordinate (e.g. "top left").
    corner2 : Coordinate
        Second bounding coordinate (e.g. "bottom right").
    

    Yields
    ------
    dict
        "is_relative": False
        "x": float
        "y": float
    """

    corner1: Coordinate
    corner2: Coordinate

    def iter_tiles(self, fov_width: float, fov_height: float) -> Iterator[dict[str, Any]]:
        """Yield absolute tile positions to visit.

        `fov_width` and `fov_height` should be in physical units (not pixels).
        """
        over = (self.overlap,) * 2 if isinstance(self.overlap, float) else self.overlap
        overlap_x, overlap_y = over

        cam_width_minus_overlap = fov_width - (fov_width * overlap_x) / 100
        cam_height_minus_overlap = fov_height - (fov_height * overlap_y) / 100

        total_width = abs(self.corner1.x + self.corner2.x)
        total_height = abs(self.corner1.y + self.corner2.y)

        rows = math.ceil(total_width / cam_width_minus_overlap)
        cols = math.ceil(total_height / cam_height_minus_overlap)

        increment_x = cam_width_minus_overlap if overlap_x > 0 else fov_width
        increment_y = cam_height_minus_overlap if overlap_y > 0 else fov_height

        # TODO: find which coord is the top left
        top_left = self.corner1

        yield from self._yield_grid_info(
            False, top_left, increment_x, increment_y, rows, cols, self.snake_order
        )
    
    def _yield_grid_info(
        self, 
        is_relative: bool,
        top_left: Coordinate,
        increment_x: float,
        increment_y: float,
        rows: int,
        cols: int,
        snake_order: bool,
    ) -> Iterator[dict[str, Any]]:
        for r, c in itertools.product(range(rows), range(cols)):
            y_pos = top_left.y - (r * increment_y)
            if snake_order and r % 2 == 1:
                x_pos = top_left.x + ((cols - c - 1) * increment_x)
            else:
                x_pos = top_left.x + (c * increment_x)
            yield {
                "is_relative": is_relative,
                "x": x_pos,
                "y": y_pos,
            }


class TileRelative(_TilePlan):
    """Yield relative delta increments to build a tile acquisition.

    Attributes
    ----------
    rows: int
        Number of rows.
    cols: int
        Number of columns.
    relative_to: Literal["center", "top_left"]:
        Define if the position list will be generated using a
        specified position as a central grid position (`center`) or
        as the first top_left grid position (`top_left`).


    Yields
    ------
    dict
        "is_relative": True
        "dx": float
        "dy": float
    """

    rows: int
    cols: int
    relative_to: Literal["center", "top_left"] = "center"

    def iter_tiles(self, fov_width: float, fov_height: float) -> Iterator[str, Any]:
        """Yield deltas relative to some position.

        `fov_width` and `fov_height` should be in physical units (not pixels).
        """
        over = (self.overlap,) * 2 if isinstance(self.overlap, float) else self.overlap
        overlap_x, overlap_y = over

        x_pos, y_pos = (0.0, 0.0)
        cam_width_minus_overlap = fov_width - (fov_width * overlap_x) / 100
        cam_height_minus_overlap = fov_height - (fov_height * overlap_y) / 100

        if self.relative_to == "center":
            # move to top left corner
            move_x = (fov_width / 2) * (self.cols - 1) - cam_width_minus_overlap
            move_y = (fov_height / 2) * (self.rows - 1) - cam_height_minus_overlap
            x_pos -= move_x + fov_width
            y_pos += move_y + fov_height

        increment_x = cam_width_minus_overlap if overlap_x > 0 else fov_width
        increment_y = cam_height_minus_overlap if overlap_y > 0 else fov_height

        yield from self._yield_grid_info(
            True,
            increment_x,
            increment_y,
            self.rows,
            self.cols,
            self.snake_order,
        )
    
    def _yield_grid_info(
        self,
        is_relative: bool,
        increment_x: float,
        increment_y: float,
        rows: int,
        cols: int,
        snake_order: bool
    ) -> Iterator[dict[str, Any]]:
        for r, c in itertools.product(range(rows), range(cols)):
            inc_y = - (r * increment_y)
            if snake_order and r % 2 == 1:
                inc_x = ((cols - c - 1) * increment_x)
            else:
                inc_x = (c * increment_x)
            yield {
                "is_relative": is_relative,
                "dx": inc_x,
                "dy": inc_y
            }


class NoTile(_TilePlan):
    def iter_tiles(self, fov_width: float, fov_height: float) -> Iterator[str, Any]:
        return iter([])


AnyTilePlan = Union[TileFromCorners, TileRelative, NoTile]
