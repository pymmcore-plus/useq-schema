from typing import List, Any
from enum import Enum


class AcquisitionOrder(Enum):
    TPZC = 0
    TPCZ = 1
    PTZC = 2
    PTCZ = 3


class ChannelSpec:
    channelGroup: str
    channelConfig: str
    exposure: float
    zOffset: float
    doZstack: bool
    skipFactorFrame_: int  # n frames to skip between acq
    useChannel: bool  # whether to use at all
    camera: str  # name of camera to use


class SequenceSettings:

    numFrames: int = 1
    intervalMs: float = 0.0
    displayTimeUnit: int = 0
    useCustomIntervals: bool = False
    customIntervalsMs: List[float]
    channels: List[ChannelSpec]
    slices: List = []
    relativeZSlice: bool = False
    slicesFirst: bool = False
    timeFirst: bool = False
    keepShutterOpenSlices: bool = False
    keepShutterOpenChannels: bool = False
    useAutofocus: bool = False
    skipAutofocusCount: int = 0
    save: bool = False
    root: str = None
    prefix: str = None
    zReference: float = 0.0
    comment: str = ""
    channelGroup: str = ""
    usePositionList: bool = False
    cameraTimeout: int = 20000
    shouldDisplayImages: bool = True
    useSlices: bool = False
    useFrames: bool = False
    useChannels: bool = False
    sliceZStepUm: float = 1.0
    sliceZBottomUm: float = 0.0
    sliceZTopUm: float = 0.0
    acqOrderMode: AcquisitionOrder

    # saveMode: Datastore.SaveMode = "MULTIPAGE_TIFF"


# clojure acqEngine


class acq_settings:
    frames: Any
    positions: Any
    channels: Any
    slices: Any
    slices_first: Any
    time_first: Any
    keep_shutter_open_slices: Any
    keep_shutter_open_channels: Any
    use_autofocus: Any
    autofocus_skip: Any
    relative_slices: Any
    exposure: Any
    interval_ms: Any
    custom_intervals_ms: Any
