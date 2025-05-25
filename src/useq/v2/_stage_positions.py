from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from pydantic import Field, model_validator

from useq import Axis
from useq._base_model import FrozenModel
from useq.v2._axes_iterator import AxesIterator, SimpleValueAxis
from useq.v2._position import Position

if TYPE_CHECKING:
    from useq._mda_event import MDAEvent


class StagePositions(SimpleValueAxis[Position | AxesIterator], FrozenModel):
    axis_key: Literal[Axis.POSITION] = Field(
        default=Axis.POSITION, frozen=True, init=False
    )

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

    def contribute_to_mda_event(
        self, value: Position, index: Mapping[str, int]
    ) -> "MDAEvent.Kwargs":
        """Contribute channel information to the MDA event."""
        return {
            "x_pos": value.x,
            "y_pos": value.y,
            "z_pos": value.z,
            "pos_name": value.name,
        }
