from enum import Enum
from typing import Dict, List, Any, Iterable, Tuple


class SpecialFlag(Enum):
    AcqusitionFinished = 0
    AcqusitionSequenceEnd = 1


class Acquisition:
    pass


# https://github.com/micro-manager/AcqEngJ/blob/master/src/main/java/org/micromanager/acqj/api/AcquisitionEvent.java

class AcquisitionEvent:
    acquisition: Acquisition
    axisPositions: Dict[str, int]
    channelGroup_: str
    channelConfig_: str
    exposure_: float
    miniumumStartTime_ms_: int
    zPosition_: float
    xPosition_: float
    yPosition_: float
    gridRow_: int
    gridCol_: int
    keepShutterOpen_: bool
    acquireImage_: bool
    slmImage_: Any
    properties_: Iterable[Tuple[str, str, str]]
    sequence_: List["AcquisitionEvent"]
    xySequenced_: bool
    zSequenced_: bool = False
    exposureSequenced_: bool = False
    channelSequenced_: bool = False
    specialFlag_: SpecialFlag

    # TODO: SLM, Galvo, etc
