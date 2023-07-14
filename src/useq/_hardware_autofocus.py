from typing import Optional, Tuple, Union

from ._base_model import FrozenModel


class AutoFocusPlan(FrozenModel):
    """Base class for hardware autofocus plans.

    Attributes
    ----------
    autofocus_z_device_name : str
        Name of the hardware autofocus z device.
    af_motor_offset : float | None
        Before autofocus is performed, the autofocus motor should be moved to this
        offset.
    """

    autofocus_z_device_name: str
    autofocus_motor_offset: Optional[float] = None


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


class NoAF(AutoFocusPlan):
    """No hardware autofocus plan."""

    autofocus_z_device_name: str = "__no_autofocus__"

    def __bool__(self) -> bool:
        return False


AnyAF = Union[AxesBasedAF, NoAF]
