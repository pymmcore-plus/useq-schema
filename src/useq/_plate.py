from __future__ import annotations

from ast import literal_eval
from contextlib import suppress
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    List,
    Mapping,
    Sequence,
    Tuple,
    Union,
    cast,
    overload,
)

import numpy as np
from pydantic import Field, field_validator, model_validator
from pydantic_core import core_schema
from typing_extensions import Annotated

from useq._base_model import FrozenModel
from useq._grid import GridPosition, GridRowsColumns, RandomPoints, Shape, _PointsPlan
from useq._position import Position

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Required, TypedDict

    class KnownPlateKwargs(TypedDict, total=False):
        rows: Required[int]
        columns: Required[int]
        well_spacing: Required[tuple[float, float] | float]
        well_size: tuple[float, float] | float | None
        circular_wells: bool
        name: str


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


class WellPlate(FrozenModel):
    """A multi-well plate definition.

    Parameters
    ----------
    rows : int
        The number of rows in the plate.
    columns : int
        The number of columns in the plate.
    well_spacing : tuple[float, float] | float
        The spacing between wells in the x and y directions.
        If a single value is provided, it is used for both x and y.
    well_size : tuple[float, float] | float
        The size of each well in the x and y directions.
        If a single value is provided, it is used for both x and y.
    circular_wells : bool
        Whether wells are circular (True) or rectangular (False).
    name : str
        A name for the plate.
    """

    rows: int
    columns: int
    well_spacing: Tuple[float, float]  # (x, y)
    well_size: Tuple[float, float]  # (width, height)
    circular_wells: bool = True
    name: str = ""

    @property
    def size(self) -> int:
        """Return the total number of wells."""
        return self.rows * self.columns

    @property
    def shape(self) -> tuple[int, int]:
        """Return the shape of the plate."""
        return self.rows, self.columns

    @field_validator("well_spacing", "well_size", mode="before")
    def _validate_well_spacing_and_size(cls, value: Any) -> Any:
        return (value, value) if isinstance(value, (int, float)) else value

    @model_validator(mode="before")
    @classmethod
    def validate_plate(cls, value: Any) -> Any:
        if isinstance(value, (int, float)):
            value = f"{int(value)}-well"
        return cls.from_str(value) if isinstance(value, str) else value

    @classmethod
    def from_str(cls, name: str) -> WellPlate:
        """Lookup a plate by registered name.

        Use `useq.register_well_plates` to add new plates to the registry.
        """
        try:
            obj = _KNOWN_PLATES[name]
        except KeyError as e:
            raise ValueError(
                f"Unknown plate name {name!r}. "
                "Use `useq.register_well_plates` to add new plate definitions"
            ) from e
        return WellPlate.model_validate(obj)


Index = Union[int, List[int], Annotated[slice, _SliceType]]
IndexExpression = Union[Tuple[Index, ...], Index]


class WellPlatePlan(FrozenModel, Sequence[Position]):
    """A plan for acquiring images from a multi-well plate.

    Parameters
    ----------
    plate : WellPlate | str | int
        The well-plate definition. Minimally including rows, columns, and well spacing.
        If expressed as a string, it is assumed to be a key in `WellPlate.KNOWN_PLATES`.
    a1_center_xy : tuple[float, float]
        The stage coordinates of the center of well A1 (top-left corner).
    rotation : float | None
        The rotation angle in degrees (anti-clockwise) of the plate.
        If None, no rotation is applied.
        If expressed as a string, it is assumed to be an angle with units (e.g., "5°",
        "4 rad", "4.5deg").
        If expressed as an arraylike, it is assumed to be a 2x2 rotation matrix
        `[[cos, -sin], [sin, cos]]`, or a 4-tuple `(cos, -sin, sin, cos)`.
    selected_wells : IndexExpression | None
        Any <=2-dimensional index expression for selecting wells.
        for example:
        -   None -> all wells are selected.
        -   0 -> Selects the first row.
        -   [0, 1, 2] -> Selects the first three rows.
        -   slice(1, 5) -> selects wells from row 1 to row 4.
        -   (2, slice(1, 4)) -> select wells in the second row and only columns 1 to 3.
        -   ([1, 2], [3, 4]) -> select wells in (row, column): (1, 3) and (2, 4)
    well_points_plan : GridRowsColumns | RandomPoints | Position
        A plan for acquiring images within each well. This can be a single position
        (for a single image per well), a GridRowsColumns (for a grid of images),
        or RandomPoints (for random points within each well).
    """

    plate: WellPlate
    a1_center_xy: Tuple[float, float]
    rotation: Union[float, None] = None
    selected_wells: Union[IndexExpression, None] = None
    well_points_plan: Union[GridRowsColumns, RandomPoints, Position] = Field(
        default_factory=lambda: Position(x=0, y=0)
    )

    @field_validator("plate", mode="before")
    @classmethod
    def _validate_plate(cls, value: Any) -> Any:
        return WellPlate.validate_plate(value)  # type: ignore [operator]

    @field_validator("well_points_plan", mode="wrap")
    @classmethod
    def _validate_well_points_plan(
        cls,
        value: Any,
        handler: core_schema.ValidatorFunctionWrapHandler,
        info: core_schema.ValidationInfo,
    ) -> Any:
        value = handler(value)
        if plate := info.data.get("plate"):
            if isinstance(value, RandomPoints) and (
                value.max_width == np.inf or value.max_height == np.inf
            ):
                plate = cast(WellPlate, plate)
                # use the well size and shape to bound the random points
                kwargs = value.model_dump(mode="python")
                kwargs["max_width"] = plate.well_size[0] - (value.fov_width or 0.1)
                kwargs["max_height"] = plate.well_size[1] - (value.fov_height or 0.1)
                kwargs["shape"] = (
                    Shape.ELLIPSE if plate.circular_wells else Shape.RECTANGLE
                )
                value = RandomPoints(**kwargs)
        return value

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
            if len(ary) != 4:  # pragma: no cover
                raise ValueError("Rotation matrix must have 4 elements")
            # convert (cos, -sin, sin, cos) to angle in degrees, anti-clockwise
            return np.degrees(np.arctan2(ary[2], ary[0]))
        return value

    @model_validator(mode="after")
    def _validate_self(self) -> WellPlatePlan:
        try:
            # make sure we can index an array of shape (Rows, Cols)
            # with the selected_wells expression
            self._dummy_indexed()
        except Exception as e:
            raise ValueError(
                f"Invalid well selection {self.selected_wells!r} for plate of "
                f"shape {self.plate.shape}: {e}"
            ) from e
        return self

    @property
    def rotation_matrix(self) -> np.ndarray:
        """Convert self.rotation (which is in degrees) to a rotation matrix."""
        if self.rotation is None:
            return np.eye(2)
        rads = np.radians(self.rotation)
        return np.array([[np.cos(rads), -np.sin(rads)], [np.sin(rads), np.cos(rads)]])

    def __iter__(self) -> Iterable[Position]:  # type: ignore
        """Iterate over the selected positions."""
        yield from self.image_positions

    def __len__(self) -> int:
        """Return the total number of points (stage positions) to be acquired."""
        return self._dummy_indexed().size * self.num_points_per_well

    def _dummy_indexed(self) -> np.ndarray:
        dummy = np.empty((self.plate.rows, self.plate.columns))
        return dummy[self.selected_wells]

    @overload
    def __getitem__(self, index: int) -> Position: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[Position]: ...

    def __getitem__(self, index: int | slice) -> Position | Sequence[Position]:
        """Return the selected position(s) at the given index."""
        return self.image_positions[index]

    @property
    def num_points_per_well(self) -> int:
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
        return (transformed[:2].T).reshape(coords.shape)  # type: ignore[no-any-return]

    @property
    def all_well_positions(self) -> Sequence[Position]:
        """Return all wells (centers) as Position objects."""
        return [
            Position(x=x, y=y, name=name)
            for (y, x), name in zip(
                self.all_well_coordinates, self.all_well_names.reshape(-1)
            )
        ]

    @cached_property
    def selected_well_positions(self) -> Sequence[Position]:
        """Return selected wells (centers) as Position objects."""
        return [
            Position(x=x, y=y, name=name)
            for (y, x), name in zip(
                self.selected_well_coordinates, self.selected_well_names
            )
        ]

    @cached_property
    def image_positions(self) -> Sequence[Position]:
        """All image positions.

        This includes *both* selected wells and the image positions within each well
        based on the `well_points_plan`.  This is the primary property that gets used
        when iterating over the plan.
        """
        wpp = self.well_points_plan
        offsets: Iterable[Position | GridPosition] = (
            [wpp] if isinstance(wpp, Position) else wpp
        )
        # TODO: note that all positions within the same well will currently have the
        # same name.  This could be improved by modifying `Position.__add__` and
        # adding a `name` to GridPosition.
        return [
            well + offset for well in self.selected_well_positions for offset in offsets
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

        # hide axes
        ax.axis("off")

        # ################ draw outline of all wells ################
        height, width = self.plate.well_size

        kwargs = {}
        offset_x, offset_y = 0.0, 0.0
        if self.plate.circular_wells:
            patch_type: Callable = patches.Ellipse
        else:
            patch_type = patches.Rectangle
            offset_x, offset_y = -width / 2, -height / 2
            kwargs["rotation_point"] = "center"

        for well in self.all_well_positions:
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

        # ################ plot image positions ################
        w = h = None
        if isinstance(self.well_points_plan, _PointsPlan):
            w, h = self.well_points_plan.fov_width, self.well_points_plan.fov_height

        for img_point in self.image_positions:
            x, y = float(img_point.x), -float(img_point.y)  # type: ignore[arg-type]
            if w and h:
                ax.add_patch(
                    patches.Rectangle(
                        (x - w / 2, y - h / 2),
                        width=w,
                        height=h,
                        facecolor="magenta",
                        edgecolor="gray",
                        linewidth=0.5,
                        alpha=0.5,
                    )
                )
            else:
                plt.plot(x, y, "mo", markersize=3, alpha=0.5)

        # ################ draw names on used wells ################
        offset_x, offset_y = -width / 2, -height / 2
        for well in self.selected_well_positions:
            x, y = float(well.x), -float(well.y)  # type: ignore[arg-type]
            # draw name next to spot
            ax.text(x + offset_x, y - offset_y, well.name, fontsize=7)

        ax.axis("equal")
        plt.show()


def _index_to_row_name(index: int) -> str:
    """Convert a zero-based column index to row name (A, B, ..., Z, AA, AB, ...)."""
    name = ""
    while index >= 0:
        name = chr(index % 26 + 65) + name
        index = index // 26 - 1
    return name


# ---------------------------- Known Plates ----------------------------

PlateOrKwargs = Union["KnownPlateKwargs", WellPlate]
_KNOWN_PLATES: dict[str, PlateOrKwargs] = {
    "6-well": {"rows": 2, "columns": 3, "well_spacing": 39.12, "well_size": 34.8},
    "12-well": {"rows": 3, "columns": 4, "well_spacing": 26, "well_size": 22},
    "24-well": {"rows": 4, "columns": 6, "well_spacing": 19, "well_size": 15.6},
    "48-well": {"rows": 6, "columns": 8, "well_spacing": 13, "well_size": 11.1},
    "96-well": {"rows": 8, "columns": 12, "well_spacing": 9, "well_size": 6.4},
    "384-well": {
        "rows": 16,
        "columns": 24,
        "well_spacing": 4.5,
        "well_size": 3.4,
        "circular_wells": False,
    },
    "1536-well": {
        "rows": 32,
        "columns": 48,
        "well_spacing": 2.25,
        "well_size": 1.7,
        "circular_wells": False,
    },
}


@overload
def register_well_plates(
    plates: Mapping[str, PlateOrKwargs],
    /,
    **kwargs: PlateOrKwargs,
) -> None: ...
@overload
def register_well_plates(
    plates: Iterable[tuple[str, PlateOrKwargs]],
    /,
    **kwargs: PlateOrKwargs,
) -> None: ...
@overload
def register_well_plates(**kwargs: PlateOrKwargs) -> None: ...
def register_well_plates(
    plates: Mapping[str, PlateOrKwargs] | Iterable[tuple[str, PlateOrKwargs]] = (),
    /,
    **kwargs: PlateOrKwargs,
) -> None:
    """Register well-plate definitions to allow lookup by key.

    Added keys will override existing keys if they already exist.

    Values may either be WellPlate instances, or dictionaries with the following keys:
        - rows: Required[int]
        - columns: Required[int]
        - well_spacing: Required[tuple[float, float]]
        - well_size: tuple[float, float] | None
        - circular_wells: bool
        - name: str

    Examples
    --------
    >>> import useq
    >>> useq.register_well_plates(
    ...     {
    ...         "custom-square-plate": {
    ...             "rows": 8, "columns": 8, "well_spacing": 9.3, "well_size": 7.1
    ...         },
    ...         "silly-plate": {"rows": 1, "columns": 1, "well_spacing": 100}
    ...     }
    ... )
    """
    _KNOWN_PLATES.update(plates, **kwargs)


def known_well_plate_keys() -> set[str]:
    """Return a set of all registered well-plate keys.

    These keys may be used as an argument to `WellPlatePlan.plate` to select a plate
    definition.
    """
    return set(_KNOWN_PLATES)
