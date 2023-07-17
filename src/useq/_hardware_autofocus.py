from typing import TYPE_CHECKING, Any, Optional, Tuple, Union, cast

from pydantic import PrivateAttr

from ._actions import HardwareAutofocus
from ._base_model import FrozenModel
from ._mda_event import MDAEvent

if TYPE_CHECKING:
    from useq._z import AnyZPlan


class AutoFocusPlan(FrozenModel):
    """Base class for hardware autofocus plans.

    Attributes
    ----------
    autofocus_device_name : str
        Name of the hardware autofocus z device.
    autofocus_motor_offset : float | None
        Before autofocus is performed, the autofocus motor should be moved to this
        offset.
    """

    autofocus_device_name: str
    autofocus_motor_offset: Optional[float] = None

    def as_action(self) -> HardwareAutofocus:
        """Return a [`useq.HardwareAutofocus`][] for this autofocus plan."""
        return HardwareAutofocus(
            autofocus_device_name=self.autofocus_device_name,
            autofocus_motor_offset=self.autofocus_motor_offset,
        )

    def event(self, event: MDAEvent) -> Optional[MDAEvent]:
        """Return an autofocus [`useq.MDAEvent`][] if autofocus should be performed.

        The z position of the new [`useq.MDAEvent`][] is also updated if a relative
        zplan is provided since autofocus shuld be performed on the home z stack
        position.
        """
        if self.should_autofocus(event):
            updates: dict[str, Any] = {"action": self.as_action()}
            if event.z_pos is not None:
                zplan = cast("AnyZPlan | None", getattr(event.sequence, "z_plan", None))
                updates["z_pos"] = event.z_pos
                if "z" in event.index and zplan:
                    updates["z_pos"] -= list(zplan)[event.index["z"]]

            return event.copy(update=updates)
        return None

    def should_autofocus(self, event: MDAEvent) -> bool:
        """Method that must be implemented by a subclass.

        Should return True if autofocus should be performed (see
        [`useq.AxesBasedAF`][]).
        """
        raise NotImplementedError("should_autofocus() must be implemented by subclass.")


class AxesBasedAF(AutoFocusPlan):
    """Autofocus plan that performs autofocus when any of the specified axes change.

    Attributes
    ----------
    axes : Tuple[str, ...]
        Tuple of axis label to use for hardware autofocus.  At every event in which
        *any* axis in this tuple is change, autofocus will be performed.  For example,
        if `axes` is `('p',)` then autofocus will be performed every time the `p` axis
        is change, (in other words: every time the position is changed.).
    """

    axes: Tuple[str, ...]
    _previous: dict = PrivateAttr(default_factory=dict)

    def should_autofocus(self, event: MDAEvent) -> bool:
        """Return `True` if autofocus should be performed at this event.

        Will return `True` if any of the axes specified in `axes` have changed from the
        previous event.
        """
        self._previous, previous = dict(event.index), self._previous
        return any(
            axis in self.axes and previous.get(axis) != index
            for axis, index in event.index.items()
        )


class NoAF(AutoFocusPlan):
    """No hardware autofocus plan."""

    autofocus_device_name: str = "__no_autofocus__"

    def __bool__(self) -> bool:
        return False

    def should_autofocus(self, event: MDAEvent) -> bool:
        return False


AnyAutofocusPlan = Union[AxesBasedAF, NoAF]
