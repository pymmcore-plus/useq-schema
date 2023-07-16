from typing import Optional, Tuple, Union

from pydantic import PrivateAttr

from ._actions import HardwareAutofocus
from ._base_model import FrozenModel
from ._mda_event import MDAEvent
from ._z import AnyZPlan, NoZ


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
        """Return a [`HardwareAutofocus`][useq.HardwareAutofocus] [`Action`][useq.Action]
        for this autofocus plan.
        """  # noqa: D205, E501
        return HardwareAutofocus(
            autofocus_device_name=self.autofocus_device_name,
            autofocus_motor_offset=self.autofocus_motor_offset,
        )

    def event(self, event: MDAEvent, zplan: AnyZPlan) -> Optional[MDAEvent]:
        """Return a new [`MDAEvent`][useq.MDAEvent] with a
        [`HardwareAutofocus`][useq.HardwareAutofocus] [`Action`][useq.Action]
        if [should_autofocus][useq.AutoFocusPlan.should_autofocus] returns `True`.

        The z position of the new [`useq.MDAEvent`][] is also updated if a relative
        zplan is provided since autofocus shuld be performed on the home z stack
        position.
        """  # noqa: D205
        if self.should_autofocus(event):
            new_z: Optional[float] = None
            if event.z_pos is None:
                new_z = None
            elif "z" not in event.index or isinstance(zplan, NoZ):
                new_z = event.z_pos
            else:
                new_z = event.z_pos - list(zplan)[event.index["z"]]

            return event.copy(update={"action": self.as_action(), "z_pos": new_z})
        return None

    def should_autofocus(self, event: MDAEvent) -> bool:
        """Method that must be implemented by a subclass.

        Should return True if autofocus should be performed (see
        [`AxesBasedAF`][useq.AxesBasedAF]).
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
        for axis, index in event.index.items():
            if axis in self.axes and previous.get(axis) != index:
                return True
        return False


class NoAF(AutoFocusPlan):
    """No hardware autofocus plan."""

    autofocus_device_name: str = "__no_autofocus__"

    def __bool__(self) -> bool:
        return False

    def should_autofocus(self, event: MDAEvent) -> bool:
        return False


AnyAutofocusPlan = Union[AxesBasedAF, NoAF]
