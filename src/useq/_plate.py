from __future__ import annotations

from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Iterator,
    List,
    Sequence,
    Tuple,
    Union,
    cast,
    overload,
)

import numpy as np
from annotated_types import Gt  # noqa: TCH002
from pydantic import (
    Field,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated

from useq._base_model import FrozenModel, UseqModel
from useq._grid import RandomPoints, RelativeMultiPointPlan, Shape
from useq._plate_registry import _PLATE_REGISTRY
from useq._position import Position, PositionBase, RelativePosition

if TYPE_CHECKING:
    from pydantic_core import core_schema

    Index = Union[int, List[int], slice]
    IndexExpression = Union[Tuple[Index, ...], Index]


class WellPlate(FrozenModel):
    """A multi-well plate definition.

    Parameters
    ----------
    rows : int
        The number of rows in the plate. Must be > 0.
    columns : int
        The number of columns in the plate. Must be > 0.
    well_spacing : tuple[float, float] | float
        The center-to-center distance in mm (pitch) between wells in the x and y
        directions. If a single value is provided, it is used for both x and y.
    well_size : tuple[float, float] | float
        The size in mm of each well in the x and y directions. If the well is squared or
        rectangular, this is the width and height of the well. If the well is circular,
        this is the diameter. If a single value is provided, it is used for both x and
        y.
    circular_wells : bool
        Whether wells are circular (True) or squared/rectangular (False).
    name : str
        A name for the plate.
    """

    rows: Annotated[int, Gt(0)]
    columns: Annotated[int, Gt(0)]
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

    @property
    def all_well_indices(self) -> np.ndarray:
        """Return the indices of all wells as array with shape (Rows, Cols, 2)."""
        Y, X = np.meshgrid(np.arange(self.rows), np.arange(self.columns), indexing="ij")
        return np.stack([Y, X], axis=-1)

    def indices(self, expr: IndexExpression) -> np.ndarray:
        """Return the indices for any index expression as array with shape (N, 2)."""
        return self.all_well_indices[expr].reshape(-1, 2).T

    @property
    def all_well_names(self) -> np.ndarray:
        """Return the names of all wells as array of strings with shape (Rows, Cols)."""
        return np.array(
            [
                [f"{_index_to_row_name(r)}{c+1}" for c in range(self.columns)]
                for r in range(self.rows)
            ]
        )

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
            obj = _PLATE_REGISTRY[name]
        except KeyError as e:
            raise ValueError(
                f"Unknown plate name {name!r}. "
                "Use `useq.register_well_plates` to add new plate definitions"
            ) from e
        if isinstance(obj, dict) and "name" not in obj:
            obj = {**obj, "name": name}
        return WellPlate.model_validate(obj)


class WellPlatePlan(UseqModel, Sequence[Position]):
    """A plan for acquiring images from a multi-well plate.

    Parameters
    ----------
    plate : WellPlate | str | int
        The well-plate definition. Minimally including rows, columns, and well spacing.
        If expressed as a string, it is assumed to be a key in
        `useq.registered_well_plate_keys`.
    a1_center_xy : tuple[float, float]
        The stage coordinates in µm of the center of well A1 (top-left corner).
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
        -   None -> No wells are selected.
        -   slice(0) -> (also) select no wells.
        -   slice(None) -> Selects all wells.
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
    selected_wells: Union[Tuple[Tuple[int, ...], Tuple[int, ...]], None] = None
    well_points_plan: RelativeMultiPointPlan = Field(
        default_factory=RelativePosition, union_mode="left_to_right"
    )

    def __repr_args__(self) -> Iterable[Tuple[str | None, Any]]:
        for item in super().__repr_args__():
            if item[0] == "selected_wells":
                # improve repr for selected_wells
                yield "selected_wells", _expression_repr(item[1])
            else:
                yield item

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
            if isinstance(value, RandomPoints):
                plate = cast(WellPlate, plate)
                kwargs = value.model_dump(mode="python")
                if value.max_width == np.inf:
                    well_size_x = plate.well_size[0] * 1000  # convert to µm
                    kwargs["max_width"] = well_size_x - (value.fov_width or 0.1)
                if value.max_height == np.inf:
                    well_size_y = plate.well_size[1] * 1000  # convert to µm
                    kwargs["max_height"] = well_size_y - (value.fov_height or 0.1)
                if "shape" not in value.__pydantic_fields_set__:
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

    @field_validator("selected_wells", mode="wrap")
    @classmethod
    def _validate_selected_wells(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
        plate = info.data.get("plate")
        if not isinstance(plate, WellPlate):
            raise ValueError("Plate must be defined before selecting wells")

        if isinstance(value, list):
            value = tuple(value)
        # make falsey values select no wells (rather than all wells)
        if not value:
            value = slice(0)

        try:
            selected = plate.indices(value)
        except (TypeError, IndexError) as e:
            raise ValueError(
                f"Invalid well selection {value!r} for plate of "
                f"shape {plate.shape}: {e}"
            ) from e

        return handler(selected)  # type: ignore [no-any-return]

    @property
    def rotation_matrix(self) -> np.ndarray:
        """Convert self.rotation (which is in degrees) to a rotation matrix."""
        if self.rotation is None:
            return np.eye(2)
        rads = np.radians(self.rotation)
        return np.array([[np.cos(rads), np.sin(rads)], [-np.sin(rads), np.cos(rads)]])

    def __iter__(self) -> Iterator[Position]:  # type: ignore
        """Iterate over the selected positions."""
        yield from self.image_positions

    def __len__(self) -> int:
        """Return the total number of points (stage positions) to be acquired."""
        if self.selected_wells is None:
            n_wells = 0
        else:
            n_wells = len(self.selected_wells[0])
        return n_wells * self.num_points_per_well

    def __bool__(self) -> bool:
        """bool(WellPlatePlan) == True."""
        return True

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
        if isinstance(self.well_points_plan, PositionBase):
            return 1
        else:
            return self.well_points_plan.num_positions()

    @property
    def all_well_indices(self) -> np.ndarray:
        """Return the indices of all wells as array with shape (Rows, Cols, 2)."""
        return self.plate.all_well_indices

    @property
    def selected_well_indices(self) -> np.ndarray:
        """Return the indices of selected wells as array with shape (N, 2)."""
        return self.plate.all_well_indices[self.selected_wells].reshape(-1, 2)

    @cached_property
    def all_well_coordinates(self) -> np.ndarray:
        """Return the stage coordinates of all wells as array with shape (N, 2)."""
        return self._transorm_coords(self.plate.all_well_indices.reshape(-1, 2))

    @cached_property
    def selected_well_coordinates(self) -> np.ndarray:
        """Return the stage coordinates of selected wells as array with shape (N, 2)."""
        return self._transorm_coords(self.selected_well_indices)

    @property
    def all_well_names(self) -> np.ndarray:
        """Return the names of all wells as array of strings with shape (Rows, Cols)."""
        return self.plate.all_well_names

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
            Position(x=x * 1000, y=y * 1000, name=name)  # convert to µm
            for (y, x), name in zip(
                self.all_well_coordinates, self.all_well_names.reshape(-1)
            )
        ]

    @cached_property
    def selected_well_positions(self) -> Sequence[Position]:
        """Return selected wells (centers) as Position objects."""
        return [
            Position(x=x * 1000, y=y * 1000, name=name)  # convert to µm
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
        offsets = [wpp] if isinstance(wpp, RelativePosition) else wpp
        pos: List[Position] = []
        for well in self.selected_well_positions:
            pos.extend(well + offset for offset in offsets)
        return pos

    @property
    def affine_transform(self) -> np.ndarray:
        """Return transformation matrix that maps well indices to stage coordinates.

        This includes:
        1. scaling by plate.well_spacing
        2. rotation by rotation_matrix
        3. translation to a1_center_xy

        Note that the Y axis scale is inverted to go from linearly increasing index
        coordinates to cartesian "plate" coordinates (where y position decreases with
        increasing index.
        """
        translation = np.eye(3)
        a1_center_xy_mm = np.array(self.a1_center_xy) / 1000  # convert to mm
        translation[:2, 2] = a1_center_xy_mm[::-1]

        rotation = np.eye(3)
        rotation[:2, :2] = self.rotation_matrix

        scaling = np.eye(3)
        # invert the Y axis to convert "index" to "plate" coordinates.
        scale_x, scale_y = self.plate.well_spacing
        scaling[:2, :2] = np.diag([-scale_y, scale_x])

        return translation @ rotation @ scaling

    def plot(self, show_axis: bool = True) -> None:
        """Plot the selected positions on the plate."""
        from useq._plot import plot_plate

        plot_plate(self, show_axis=show_axis)


def _index_to_row_name(index: int) -> str:
    """Convert a zero-based column index to row name (A, B, ..., Z, AA, AB, ...)."""
    name = ""
    while index >= 0:
        name = chr(index % 26 + 65) + name
        index = index // 26 - 1
    return name


def _find_pattern(seq: Sequence[int]) -> tuple[list[int] | None, int | None]:
    n = len(seq)

    # Try different lengths of the potential repeating pattern
    for pattern_length in range(1, n // 2 + 1):
        pattern = list(seq[:pattern_length])
        repetitions = n // pattern_length

        # Check if the pattern repeats enough times
        if np.array_equal(pattern * repetitions, seq[: pattern_length * repetitions]):
            return (pattern, repetitions)

    return None, None


def _pattern_repr(pattern: Sequence[int]) -> str:
    """Turn pattern into a slice object if possible."""
    start = pattern[0]
    stop = pattern[-1] + 1
    if len(pattern) > 1:
        step = pattern[1] - pattern[0]
    else:
        step = 1
    if all(pattern[i] == pattern[0] + i * step for i in range(1, len(pattern))):
        if step == 1:
            if start == 0:
                return f"slice({stop})"
            return f"slice({start}, {stop})"
        return f"slice({start}, {stop}, {step})"
    return repr(pattern)


class _Repr:
    def __init__(self, string: str) -> None:
        self._string = string

    def __repr__(self) -> str:
        return self._string


def _expression_repr(expr: tuple[Sequence[int], Sequence[int]]) -> _Repr:
    """Try to represent an index expression as slice objects if possible."""
    e0, e1 = expr
    ptrn1, repeats = _find_pattern(e1)
    if ptrn1 is None:
        return _Repr(str(expr))
    ptrn0 = e0[:: len(ptrn1)]
    return _Repr(f"({_pattern_repr(ptrn0)}, {_pattern_repr(ptrn1)})")
