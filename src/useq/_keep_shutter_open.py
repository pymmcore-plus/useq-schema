from typing import Tuple

from pydantic import PrivateAttr

from ._base_model import FrozenModel
from ._mda_event import MDAEvent


class ShutterOpenAxes(FrozenModel):
    """Plan for keeping the shutter open for a subset of axes.

    Attributes
    ----------
    axes : Tuple[str, ...]
        Tuple of axes label to use to keep the shutter open. At every event in which
        *any* axis in this tuple is change, shutter will be set to open.  For example,
        if `axes` is `('c',)` then the shutter will be kept open every time the `c` axis
        is change, (in other words: every time the channel is changed.).
    """

    axes: Tuple[str, ...] = ()
    _previous: dict = PrivateAttr(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.axes)

    def should_keep_open(self, event: MDAEvent) -> bool:
        """Return `True` if shutter should be kept open at this event.

        Will return `True` if any of the axes specified in `axes` have changed from the
        previous event.
        """
        self._previous, previous = dict(event.index), self._previous
        return any(
            axis in self.axes and previous.get(axis) != index
            for axis, index in event.index.items()
        )
