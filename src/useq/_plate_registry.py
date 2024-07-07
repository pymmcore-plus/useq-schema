from __future__ import annotations

from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from typing import Iterable, Mapping, Required, TypeAlias, TypedDict

    from useq._plate import WellPlate

    class KnownPlateKwargs(TypedDict, total=False):
        rows: Required[int]
        columns: Required[int]
        well_spacing: Required[tuple[float, float] | float]
        well_size: tuple[float, float] | float | None
        circular_wells: bool
        name: str

    PlateOrKwargs: TypeAlias = KnownPlateKwargs | WellPlate


_PLATE_REGISTRY: dict[str, PlateOrKwargs] = {
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
    "coverslip-18mm-square": {
        "rows": 1,
        "columns": 1,
        "well_spacing": 0.0,
        "well_size": 18.0,
        "circular_wells": False,
        "name": "18mm coverslip",
    },
    "coverslip-22mm-square": {
        "rows": 1,
        "columns": 1,
        "well_spacing": 0.0,
        "well_size": 22.0,
        "circular_wells": False,
        "name": "22mm coverslip",
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
    _PLATE_REGISTRY.update(plates, **kwargs)


def registered_well_plate_keys() -> set[str]:
    """Return a set of all registered well-plate keys.

    These keys may be used as an argument to `WellPlatePlan.plate` to select a plate
    definition.
    """
    return set(_PLATE_REGISTRY)
