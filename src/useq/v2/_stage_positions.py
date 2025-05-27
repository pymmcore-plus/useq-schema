from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, Union

import numpy as np
from pydantic import Field, model_validator

from useq import Axis
from useq._base_model import FrozenModel
from useq.v2._axes_iterator import AxisIterable
from useq.v2._position import Position

if TYPE_CHECKING:
    from useq._mda_event import MDAEvent
    from useq.v2._mda_sequence import MDASequence


class StagePositions(AxisIterable[Position], FrozenModel):
    axis_key: Literal[Axis.POSITION] = Field(
        default=Axis.POSITION, frozen=True, init=False
    )
    values: list[Union[Position, MDASequence]] = Field(default_factory=list)

    def __iter__(self) -> Iterator[Position | MDASequence]:  # type: ignore[override]
        yield from self.values

    def __len__(self) -> int:
        """Return the number of axis values."""
        return len(self.values)

    @model_validator(mode="before")
    @classmethod
    def _cast_any(cls, values: Any) -> Any:
        """Try to cast any value to a ChannelsPlan."""
        if isinstance(values, np.ndarray):
            if values.ndim == 1:
                values = [values]
            elif values.ndim == 2:
                values = list(values)
            else:
                raise ValueError(
                    f"Invalid number of dimensions for stage positions: {values.ndim}"
                )
        if isinstance(values, Sequence) and not isinstance(values, str):
            values = {"values": values}

        return values

    # FIXME: fix type ignores
    def contribute_event_kwargs(  # type: ignore
        self,
        value: Position,
        index: Mapping[str, int],
    ) -> MDAEvent.Kwargs:
        """Contribute channel information to the MDA event."""
        kwargs = {}
        if isinstance(value, Position):
            for key in ("x", "y", "z"):
                if (val := getattr(value, key)) is not None:
                    kwargs[f"{key}_pos"] = val
            if value.name is not None:
                kwargs["pos_name"] = value.name
        return kwargs  # type: ignore[return-value]
