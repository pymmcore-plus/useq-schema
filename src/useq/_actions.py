from typing import Literal

from ._base_model import UseqModel


class Action(UseqModel):
    """Base class for all [`useq.MDAEvent`][] actions.

    Parameters
    ----------
    type : str
        Type of the action that should be performed at the [`useq.MDAEvent`][].
    """

    type: str


class Snap(Action):
    """Action to snap an image.

    Attributes
    ----------
    type : Literal["snap"]
        This action can be used to snap an image.
    """

    type: Literal["snap"] = "snap"


class HardwareAutofocus(Action):
    """Action to perform a hardware autofocus.

    Attributes
    ----------
    type : Literal["autofocus"]
        This action can be used to trigger hardware autofocus.
    autofocus_z_device_name : str
        The name of the hardware autofocus z device.
    autofocus_motor_offset: float
        Before autofocus is performed, the autofocus motor should be moved to this
        offset.
    """

    type: Literal["hardware_autofocus"] = "hardware_autofocus"
    autofocus_z_device_name: str
    autofocus_motor_offset: float
