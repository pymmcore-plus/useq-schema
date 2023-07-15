from typing import Literal

from ._base_model import FrozenModel


class Action(FrozenModel):
    """Base class for all [`useq.MDAEvent`][] actions.

    Parameters
    ----------
    type : str
        Type of the action that should be performed at the [`useq.MDAEvent`][].
    """

    type: str


class AcquireImage(Action):
    """Action to acquire an image.

    Attributes
    ----------
    type : Literal["acquire_image"]
        This action can be used to acquire an image.
    """

    type: Literal["acquire_image"] = "acquire_image"


class HardwareAutofocus(Action):
    """Action to perform a hardware autofocus.

    Attributes
    ----------
    type : Literal["hardware_autofocus"]
        This action can be used to trigger hardware autofocus.
    autofocus_device_name : str
        The name of the hardware autofocus device.
    autofocus_motor_offset: float
        Before autofocus is performed, the autofocus motor should be moved to this
        offset.
    """

    type: Literal["hardware_autofocus"] = "hardware_autofocus"
    autofocus_device_name: str
    autofocus_motor_offset: float
