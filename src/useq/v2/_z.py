from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Union

from pydantic import Field
from typing_extensions import deprecated

from useq._enums import Axis
from useq.v2._axes_iterator import AxisIterable
from useq.v2._position import Position

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from useq._mda_event import MDAEvent


from useq import _z


class ZPlan(AxisIterable[Position], _z.ZPlan):
    axis_key: Literal[Axis.Z] = Field(default=Axis.Z, frozen=True, init=False)

    def __iter__(self) -> Iterator[Position]:  # type: ignore[override]
        """Iterate over Z positions."""
        positions = self.positions()
        if not self.go_up:
            positions = positions[::-1]
        for p in positions:
            yield Position(z=p, is_relative=self.is_relative)

    @deprecated(
        "num_positions() is deprecated, use len(z_plan) instead.",
        category=UserWarning,
        stacklevel=2,
    )
    def num_positions(self) -> int:
        """Get the number of Z positions."""
        return len(self)

    def contribute_event_kwargs(
        self, value: Position, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        """Contribute Z position to the MDA event."""
        if value.z is not None:
            if self.is_relative:
                return {"z_pos_rel": value.z}  # type: ignore [typeddict-unknown-key]
            else:
                return {"z_pos": value.z}
        return {}


class ZTopBottom(ZPlan, _z.ZTopBottom): ...


class ZAboveBelow(ZPlan, _z.ZAboveBelow): ...


class ZRangeAround(ZPlan, _z.ZRangeAround): ...


class ZAbsolutePositions(ZPlan, _z.ZAbsolutePositions):
    def __len__(self) -> int:
        return len(self.absolute)


class ZRelativePositions(ZPlan, _z.ZRelativePositions):
    def __len__(self) -> int:
        return len(self.relative)


# order matters... this is the order in which pydantic will try to coerce input.
# should go from most specific to least specific
AnyZPlan = Union[
    ZTopBottom, ZAboveBelow, ZRangeAround, ZAbsolutePositions, ZRelativePositions
]
