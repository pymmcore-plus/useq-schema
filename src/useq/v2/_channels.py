from collections.abc import Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, model_validator

from useq import Axis, Channel
from useq._base_model import FrozenModel
from useq.v2._axes_iterator import AxesIterator, AxisIterable

if TYPE_CHECKING:
    from useq._mda_event import MDAEvent


class ChannelsPlan(AxisIterable[Channel], FrozenModel):
    axis_key: Literal[Axis.CHANNEL] = Field(
        default=Axis.CHANNEL, frozen=True, init=False
    )
    channels: list[Channel] = Field(
        default_factory=list,
        description="List of channels to use in the MDA sequence.",
    )

    def __iter__(self) -> Iterator[Channel | AxesIterator]:  # type: ignore[override]
        """Iterate over the channels in this plan."""
        yield from self.channels

    @model_validator(mode="before")
    @classmethod
    def _cast_any(cls, values: Any) -> Any:
        """Try to cast any value to a ChannelsPlan."""
        if isinstance(values, Sequence) and not isinstance(values, str):
            values = {"channels": values}
        return values

    def contribute_to_mda_event(
        self, value: Channel, index: Mapping[str, int]
    ) -> "MDAEvent.Kwargs":
        """Contribute channel information to the MDA event."""
        kwargs: MDAEvent.Kwargs = {
            "channel": {"config": value.config, "group": value.group},
        }
        if value.exposure is not None:
            kwargs["exposure"] = value.exposure
        return kwargs
