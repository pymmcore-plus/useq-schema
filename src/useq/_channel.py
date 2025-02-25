from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast

from pydantic import Field, RootModel, model_validator

from useq._axis_iterable import AxisIterableBase, IterItem
from useq._base_model import FrozenModel
from useq._utils import Axis

if TYPE_CHECKING:
    from useq._iter_sequence import MDAEventDict
    from useq._z import ZPlan


class Channel(FrozenModel):
    """Define an acquisition channel.

    Attributes
    ----------
    config : str
        Name of the configuration to use for this channel, (e.g. `"488nm"`, `"DAPI"`,
        `"FITC"`).
    group : str
        Optional name of the group to which this channel belongs. By default,
        `"Channel"`.
    exposure : float | None
        Exposure time in milliseconds. Must be positive.  If not provided, implies use
        current exposure time. By default, `None`.
    do_stack : bool
        If `True`, instructs engine to include this channel in any Z stacks being
        acquired. By default, `True`.
    z_offset : float
        Relative Z offset from current position, in microns. By default, `0`.
    acquire_every : int
        Acquire every Nth frame (if acquiring a time series). By default, `1`.
    camera: str | None
        Name of the camera to use for this channel. If not provided, implies use
        current camera. By default, `None`.
    """

    config: str
    group: str = "Channel"
    exposure: Optional[float] = Field(None, gt=0.0)
    do_stack: bool = True
    z_offset: float = 0.0
    acquire_every: int = Field(default=1, gt=0)  # acquire every n frames
    camera: Optional[str] = None

    @model_validator(mode="before")
    def _validate_model(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"config": value}
        return value


class Channels(RootModel, AxisIterableBase):
    root: tuple[Channel, ...]
    axis_key: ClassVar[str] = "c"

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def create_event_kwargs(self, val: Channel) -> "MDAEventDict":
        """Convert a value from the iterator to kwargs for an MDAEvent."""
        from useq._mda_event import Channel

        d: MDAEventDict = {"channel": Channel(config=val.config, group=val.group)}
        if val.z_offset:
            d["z_pos_rel"] = val.z_offset
        return d

    def length(self) -> int:
        """Return the number of axis values.

        If the axis is infinite, return -1.
        """
        return len(self.root)

    def should_skip(self, kwargs: dict[str, IterItem]) -> bool:
        if Axis.CHANNEL not in kwargs:
            return False
        channel = cast("Channel", kwargs[Axis.CHANNEL].value)

        if Axis.TIME in kwargs:
            if kwargs[Axis.TIME].axis_index % channel.acquire_every:
                return True

        # only acquire on the middle plane:
        if not channel.do_stack:
            if Axis.Z in kwargs:
                z_plan = cast("ZPlan", kwargs[Axis.Z].axis_iterable)
                z_index = kwargs[Axis.Z].axis_index
                if z_index != z_plan.num_positions() // 2:
                    return True

        return False
