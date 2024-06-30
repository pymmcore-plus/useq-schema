from ast import literal_eval
from contextlib import suppress
from functools import cached_property
from typing import (
    Annotated,
    Any,
    Callable,
    ClassVar,
    Iterable,
    Sequence,
    Union,
    overload,
)

import numpy as np
from pydantic import Field, field_validator, model_validator
from pydantic_core import core_schema

from useq._base_model import FrozenModel
from useq._grid import GridRowsColumns, RandomPoints
from useq._position import Position


class _SliceType:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        def _to_slice(value: Any) -> slice:
            if isinstance(value, slice):
                return value
            if isinstance(value, str):
                if value.startswith("slice(") and value.endswith(")"):
                    with suppress(Exception):
                        return slice(*literal_eval(value.replace("slice", "")))
            raise ValueError(f"Invalid slice expression {value}")

        return core_schema.no_info_before_validator_function(
            _to_slice,
            schema=core_schema.any_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                repr,
                return_schema=core_schema.str_schema(),
            ),
        )


Index = int | list[int] | Annotated[slice, _SliceType]
IndexExpression = tuple[Index, ...] | Index


class Plate(FrozenModel):
    """A multi-well plate definition."""

    rows: int
    columns: int
    well_spacing: tuple[float, float]  # (x, y)
    well_size: tuple[float, float] | None = None  # (x, y)
    circular_wells: bool = True
    name: str = ""

    @property
    def size(self) -> int:
        """Return the total number of wells."""
        return self.rows * self.columns

    @field_validator("well_spacing", "well_size", mode="before")
    def _validate_well_spacing_and_size(cls, value: Any) -> Any:
        if isinstance(value, (int, float)):
            return value, value
        return value

    @model_validator(mode="before")
    @classmethod
    def validate_plate(cls, value: Any) -> Any:
        if isinstance(value, int):
            value = f"{value}-well"
        if isinstance(value, str):
            try:
                return cls.lookup(value)
            except KeyError as e:  # pragma: no cover
                raise ValueError(f"Unknown plate name {value!r}") from e
        return value

    @classmethod
    def lookup(cls, name: str) -> "Plate":
        """Lookup a plate by name."""
        return Plate(**cls._PLATES[name])

    _PLATES: ClassVar[dict[str, dict]] = {
        "12-well": {"rows": 3, "columns": 4, "well_spacing": 26, "well_size": 22},
        "24-well": {"rows": 4, "columns": 6, "well_spacing": 19, "well_size": 15.6},
        "48-well": {"rows": 6, "columns": 8, "well_spacing": 13, "well_size": 11.1},
        "96-well": {"rows": 8, "columns": 12, "well_spacing": 9, "well_size": 6.4},
        "384-well": {"rows": 16, "columns": 24, "well_spacing": 4.5, "well_size": 3.4},
        "1536-well": {
            "rows": 32,
            "columns": 48,
            "well_spacing": 2.25,
            "well_size": 1.7,
            "circular_wells": False,
        },
    }


class PlatePlan(FrozenModel, Sequence[Position]):
    """A plan for acquiring images from a multi-well plate."""

    # if expressed as a string, it is assumed to be a key in _PLATES
    plate: Plate
    # stage coordinates of the center of well A1
    a1_center_xy: tuple[float, float]
    # if expressed as a single number, it is assumed to be the angle in degrees
    # with anti-clockwise rotation
    # if expressed as a string, rad/deg is inferred from the string
    # if expressed as a tuple, it is assumed to be a 2x2 rotation matrix or a 4-tuple
    rotation: float | None = None
    # Any 2-dimensional index expression, where None means all wells
    # and slice(0, 0) means no wells
    selected_wells: IndexExpression | None = None
    well_points_plan: Union[GridRowsColumns | RandomPoints | Position] = Field(
        default_factory=lambda: Position(x=0, y=0)
    )

    @field_validator("plate", mode="before")
    @classmethod
    def _validate_plate(cls, value: Any) -> Any:
        return Plate.validate_plate(value)  # type: ignore [operator]

    @field_validator("rotation", mode="before")
    @classmethod
    def _validate_rotation(cls, value: Any) -> Any:
        if isinstance(value, str):
            # assume string representation of an angle
            # infer deg or radians from the string
            if "rad" in value:
                value = value.replace("rad", "").strip()
                # convert to degrees
                return np.degrees(float(value))
            if "°" in value or "˚" in value or "deg" in value:
                value = value.replace("°", "").replace("˚", "").replace("deg", "")
                return float(value.strip())
        if isinstance(value, (tuple, list)):
            ary = np.array(value).flatten()
            if len(ary) not in (2, 4):
                raise ValueError("Rotation matrix must have 2 or 4 elements")
            return -np.degrees(np.arctan2(ary[1], ary[0]))
        return value

    @property
    def rotation_matrix(self) -> np.ndarray:
        """Convert self.rotation (which is in degrees) to a rotation matrix."""
        if self.rotation is None:
            return np.eye(2)
        rads = np.radians(self.rotation)
        return np.array([[np.cos(rads), -np.sin(rads)], [np.sin(rads), np.cos(rads)]])

    def __iter__(self) -> Iterable[Position]:  # type: ignore
        """Iterate over the selected positions."""
        yield from self.selected_positions

    def __len__(self) -> int:
        """Return the total number of points (stage positions) to be acquired."""
        dummy = np.empty((self.plate.rows, self.plate.columns))
        indexed = dummy[self.selected_wells]
        return indexed.size * self.points_per_well  # type: ignore

    @overload
    def __getitem__(self, index: int) -> Position: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[Position]: ...

    def __getitem__(self, index: int | slice) -> Position | Sequence[Position]:
        """Return the selected position(s) at the given index."""
        return self.selected_positions[index]

    @property
    def points_per_well(self) -> int:
        """Return the number of points per well."""
        if isinstance(self.well_points_plan, Position):
            return 1
        else:
            return self.well_points_plan.num_positions()

    @property
    def all_well_indices(self) -> np.ndarray:
        """Return the indices of all wells as array with shape (Rows, Cols, 2)."""
        Y, X = np.meshgrid(
            np.arange(self.plate.rows), np.arange(self.plate.columns), indexing="ij"
        )
        return np.stack([Y, X], axis=-1)

    @property
    def selected_well_indices(self) -> np.ndarray:
        """Return the indices of selected wells as array with shape (N, 2)."""
        return self.all_well_indices[self.selected_wells].reshape(-1, 2)

    @cached_property
    def all_well_coordinates(self) -> np.ndarray:
        """Return the stage coordinates of all wells as array with shape (N, 2)."""
        return self._transorm_coords(self.all_well_indices.reshape(-1, 2))

    @cached_property
    def selected_well_coordinates(self) -> np.ndarray:
        """Return the stage coordinates of selected wells as array with shape (N, 2)."""
        return self._transorm_coords(self.selected_well_indices)

    @property
    def all_well_names(self) -> np.ndarray:
        """Return the names of all wells as array of strings with shape (Rows, Cols)."""
        return np.array(
            [
                [f"{_index_to_row_name(r)}{c+1}" for c in range(self.plate.columns)]
                for r in range(self.plate.rows)
            ]
        )

    @property
    def selected_well_names(self) -> list[str]:
        """Return the names of selected wells."""
        return list(self.all_well_names[self.selected_wells].reshape(-1))

    def _transorm_coords(self, coords: np.ndarray) -> np.ndarray:
        """Transform coordinates to the plate coordinate system."""
        # create homogenous coordinates
        h_coords = np.column_stack((coords, np.ones(coords.shape[0])))
        # transform
        transformed = self.affine_transform @ h_coords.T
        # strip homogenous coordinate
        return (transformed[:2].T).reshape(coords.shape)

    @property
    def all_positions(self) -> Sequence[Position]:
        """Return all well positions as Position objects."""
        return [
            Position(x=x, y=y, name=name)
            for (y, x), name in zip(
                self.all_well_coordinates, self.all_well_names.reshape(-1)
            )
        ]

    @cached_property
    def selected_positions(self) -> Sequence[Position]:
        """Return selected wells as Position objects."""
        return [
            Position(x=x, y=y, name=name)
            for (y, x), name in zip(
                self.selected_well_coordinates, self.selected_well_names
            )
        ]

    @property
    def affine_transform(self) -> np.ndarray:
        """Return transformation matrix.

        This includes:
        1. scaling by plate.well_spacing
        2. rotation by rotation_matrix
        3. translation to a1_center_xy
        """
        translation = np.eye(3)
        translation[:2, 2] = self.a1_center_xy[::-1]

        rotation = np.eye(3)
        rotation[:2, :2] = self.rotation_matrix

        scaling = np.eye(3)
        scaling[:2, :2] = np.diag(self.plate.well_spacing)

        return translation @ rotation @ scaling

    def plot(self) -> None:
        """Plot the selected positions on the plate."""
        import matplotlib.pyplot as plt
        from matplotlib import patches

        _, ax = plt.subplots()

        # draw outline of all wells
        if self.plate.well_size is None:
            height, width = self.plate.well_spacing
        else:
            height, width = self.plate.well_size

        kwargs = {}
        offset_x, offset_y = 0.0, 0.0
        if self.plate.circular_wells:
            patch_type: Callable = patches.Ellipse
        else:
            patch_type = patches.Rectangle
            offset_x, offset_y = -width / 2, -height / 2
            kwargs["rotation_point"] = "center"

        for well in self.all_positions:
            sh = patch_type(
                (well.x + offset_x, -well.y + offset_y),  # type: ignore[operator]
                width=width,
                height=height,
                angle=self.rotation or 0,
                facecolor="none",
                edgecolor="gray",
                linewidth=0.5,
                linestyle="--",
                **kwargs,
            )
            ax.add_patch(sh)

        for well in self.selected_positions:
            x, y = float(well.x), -float(well.y)  # type: ignore[arg-type]
            plt.plot(x, y, "mo")
            # draw name next to spot
            txt = f"{well.name}\n({x:.1f}, {y:.1f})"
            ax.text(x - 2, y + 2, txt, fontsize=7)

        ax.axis("equal")
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        plt.show()


def _index_to_row_name(index: int) -> str:
    """Convert a zero-based column index to row name (A, B, ..., Z, AA, AB, ...)."""
    name = ""
    while index >= 0:
        name = chr(index % 26 + 65) + name
        index = index // 26 - 1
    return name
