from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

import pint
from pint.facets.plain.quantity import PlainQuantity
from pydantic_core import core_schema
from typing_extensions import Annotated

if TYPE_CHECKING:
    from pint._typing import UnitLike
    from pint.facets.plain.quantity import MagnitudeT
    from pydantic import GetCoreSchemaHandler

ureg = pint.UnitRegistry()
ureg.formatter.default_format = "#~"


def make_unit_validator(
    units: UnitLike, mag_type: MagnitudeT | None = None
) -> Callable[[Any], PlainQuantity]:
    """Return a function that casts a value to a pint.Quantity with the given units."""

    def validate_unit(value: Any) -> PlainQuantity[MagnitudeT]:
        """Cast a `value` to a pint.Quantity with the given units."""
        quant: PlainQuantity = ureg.Quantity(value)
        if quant.dimensionless:
            quant = ureg.Quantity(value, units=units)
        if not quant.check(units):
            raise ValueError(f"Expected a quantity with units {units}, got {quant}")
        if mag_type is not None:
            quant = ureg.Quantity(mag_type(quant.magnitude), quant.units)
        with suppress(pint.UndefinedUnitError):
            # try to cast to the given units.
            # This may fail, even if quant.check() passed, if `units` is just a dimenson
            quant = quant.to(units)
        return quant

    return validate_unit


@dataclass(unsafe_hash=True)
class UnitValidator:
    units: UnitLike
    mag_type: MagnitudeT | None = None

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_before_validator_function(
            function=make_unit_validator(self.units, mag_type=self.mag_type),
            schema=core_schema.any_schema(),
            serialization=core_schema.to_string_ser_schema(),
            # this is more accurate, but will prevent model_json_schema() from working
            # schema=core_schema.is_instance_schema(PlainQuantity),
        )


Microns = Annotated[PlainQuantity[float], UnitValidator("um", float)]
Millimeters = Annotated[PlainQuantity[float], UnitValidator("mm", float)]
Seconds = Annotated[PlainQuantity[float], UnitValidator("s", float)]
Milliseconds = Annotated[PlainQuantity[float], UnitValidator("ms", float)]
