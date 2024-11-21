from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from useq._mda_event import MDAEvent
from useq._mda_sequence import MDASequence

if TYPE_CHECKING:
    from useq.experimental.protocols import PSignal

try:
    from psygnal import Signal, SignalGroup
except ImportError as e:
    raise ImportError("Please install psygnal to use this module.") from e


class MDASignaler(SignalGroup):
    """Psygnal-backed signal-emitter for MDA signals emitted by the runner."""

    sequenceStarted: PSignal = Signal(MDASequence, dict)
    sequencePauseToggled: PSignal = Signal(bool)
    sequenceCanceled: PSignal = Signal(MDASequence)
    sequenceFinished: PSignal = Signal(MDASequence)
    frameReady: PSignal = Signal(np.ndarray, MDAEvent, dict)
    awaitingEvent: PSignal = Signal(MDAEvent, float)
    eventStarted: PSignal = Signal(MDAEvent)
