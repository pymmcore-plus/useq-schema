from functools import cached_property
from typing import Iterable, Sequence, Union, overload

import numpy as np
from pydantic import BaseModel, Field

from useq import Position
from useq._grid import GridRowsColumns, RandomPoints


class Plate(BaseModel):
    rows: int
    columns: int
    well_spacing: tuple[float, float]  # (x, y)
    well_size: tuple[float, float]  # (x, y)
    circular: bool = False
    name: str = ""


class Well(BaseModel):
    row: int
    column: int
    name: str = ""


class PlatePlan(BaseModel, Sequence[Position]):
    plate: Plate
    a1_center_xy: tuple[float, float]
    rotation_matrix: tuple[float, float, float, float] | None = None
    # the stage coordinates of the top-left corner of the plate
    selected_wells: list[Well] = Field(default_factory=list)
    well_points_plan: Union[GridRowsColumns | RandomPoints | Position] = Field(
        default_factory=lambda: Position(x=0, y=0)
    )

    def __iter__(self) -> Iterable[Position]:  # type: ignore
        yield from self._selected_well_centers

    def __len__(self) -> int:
        """Return the total number of points (stage positions) to be acquired."""
        return len(self.selected_wells) * self.points_per_well

    @overload
    def __getitem__(self, index: int) -> Position:
        ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[Position]:
        ...

    def __getitem__(self, index: int | slice) -> Position | Sequence[Position]:
        return self._selected_well_centers[index]

    @property
    def points_per_well(self) -> int:
        """Return the number of points per well."""
        if isinstance(self.well_points_plan, Position):
            return 1
        else:
            return self.well_points_plan.num_positions()

    @cached_property
    def _selected_well_centers(self) -> tuple[Position, ...]:
        """Return coordinate array (N x 2) and well names."""
        well_centers = self._well_centers_stage_coords()

        row_indices, col_indices, names = zip(
            *((w.row, w.column, w.name) for w in self.selected_wells)
        )
        selected_centers = well_centers[row_indices, col_indices]
        return tuple(
            Position(x=x, y=y, name=name)
            for (x, y), name in zip(selected_centers, names)
        )

    def _well_centers_stage_coords(self) -> np.ndarray:
        # first establish a meshgrid of well in well coordinate (row, column)
        Y, X = np.meshgrid(
            np.arange(self.plate.rows), np.arange(self.plate.columns), indexing="ij"
        )
        # create homogenous coordinates
        coords = np.column_stack((X.ravel(), Y.ravel(), np.ones(X.size)))

        # transform well coordinates to stage coordinates using
        # a1_center_xy and rotation_matrix
        T = np.eye(3)
        T[:2, 2] = self.a1_center_xy
        if self.rotation_matrix is not None:
            R = np.array(self.rotation_matrix).reshape(2, 2)
            T[:2, :2] = R

        # transform well coordinates to stage coordinates
        well_centers = T @ coords.T
        # get rid of the homogenous coordinate
        return (well_centers[:2].T).reshape(self.plate.rows, self.plate.columns, 2)

    def plot(self) -> None:
        import matplotlib.pyplot as plt

        _, ax = plt.subplots()

        for well in self._selected_well_centers:
            plt.plot(well.x, -well.y, "mo")
            # draw name next to spot
            ax.text(well.x, -well.y, well.name, fontsize=8, color="black")
            # sh = patches.Circle((well.x, well.y), radius=self.plate.well_size[0])
            # ax.add_patch(sh)

        ax.axis("equal")
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        plt.show()


from itertools import product

import matplotlib.pyplot as plt

wells = [
    Well(row=r, column=c, name=f"r{r}c{c}")
    for r, c in product(range(1, 3), range(0, 4))
] + [Well(row=0, column=0, name="origin")]

self = PlatePlan(
    plate=Plate(rows=3, columns=4, well_spacing=(26, 26), well_size=(22, 22)),
    a1_center_xy=(100, 200),
    selected_wells=wells,
    rotation_matrix=(0.99, 0.0948, -0.09, 0.99),
)

self.plot()
plt.show()
