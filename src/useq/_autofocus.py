from typing import Optional, Tuple

from ._base_model import FrozenModel


class AutoFocusPlan(FrozenModel):
    """Base class for autofocus plans.

    Attributes
    ----------
    autofocus_z_device_name : str
        Name of the autofocus z device.
    z_autofocus_position : float | None
        Optional autofocus z motor position.
    z_focus_position : float | None
        Optional focus z motor position.
    axes : Tuple[str, ...] | None
        Optional tuple of axes to that will use autofocus.
    """

    autofocus_z_device_name: str
    z_autofocus_position: Optional[float]
    z_focus_position: Optional[float]
    axes: Optional[Tuple[str, ...]]


class NoAF(AutoFocusPlan):
    """No autofocus plan."""

    autofocus_z_device_name: str = ""
    z_autofocus_position: Optional[float] = None
    z_focus_position: Optional[float] = None
    axes: Optional[Tuple[str, ...]] = None
