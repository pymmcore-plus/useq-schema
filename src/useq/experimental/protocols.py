from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol, Union, runtime_checkable

from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, Callable

    from numpy.typing import NDArray

    from useq import MDAEvent, MDASequence

    PImagePayload = tuple[NDArray, MDAEvent, dict]


@runtime_checkable
class PMDAEngine(Protocol):
    """Protocol that all MDA engines must implement."""

    @abstractmethod
    def setup_sequence(self, sequence: MDASequence) -> dict | None:
        """Setup state of system (hardware, etc.) before an MDA is run.

        This method is called once at the beginning of a sequence.
        """

    @abstractmethod
    def setup_event(self, event: MDAEvent) -> None:
        """Prepare state of system (hardware, etc.) for `event`.

        This method is called before each event in the sequence.  It is
        responsible for preparing the state of the system for the event.
        The engine should be in a state where it can call `exec_event`
        without any additional preparation.  (This means that the engine
        should perform any waits or blocks required for system state
        changes to complete.)
        """

    @abstractmethod
    def exec_event(self, event: MDAEvent) -> Iterable[PImagePayload]:
        """Execute `event`.

        This method is called after `setup_event` and is responsible for
        executing the event.  The default assumption is to acquire an image,
        but more elaborate events will be possible.

        The protocol for the returned object is still under development.  However, if
        the returned object has an `image` attribute, then the
        [`MDARunner`][pymmcore_plus.mda.MDARunner] will emit a
        [`frameReady`][pymmcore_plus.mda.PMDASignaler.frameReady] signal
        """
        # TODO: nail down a spec for the return object.

    # ------------- The following methods are optional -------------

    # def event_iterator(self, events: Iterable[MDAEvent]) -> Iterator[MDAEvent]:
    #     """Wrapper on the event iterator.

    #     **Optional.**

    #     This can be used to wrap the event iterator to perform any event merging
    #     (e.g. if the engine supports HardwareSequencing) or event modification.
    #     The default implementation is just `iter(events)`.

    #     Be careful when using this method.  It is powerful and can result in
    #     unexpected event iteration if used incorrectly.
    #     """

    # def teardown_event(self, event: MDAEvent) -> None:
    #     """Teardown state of system (hardware, etc.) after `event`.

    #     **Optional.**

    #     If the engine provides this function, it will be called after
    #     `exec_event` to perform any cleanup or teardown required after
    #     the event has been executed.
    #     """

    # def teardown_sequence(self, sequence: MDASequence) -> None:
    #     """Perform any teardown required after the sequence has been executed.

    #     **Optional.**

    #     If the engine provides this function, it will be called after the
    #     last event in the sequence has been executed.
    #     """


@runtime_checkable
class PSignalInstance(Protocol):
    """The protocol that a signal instance must implement.

    In practice this will likely be either a `pyqtSignal/pyqtBoundSignal` or a
    `psygnal.SignalInstance`.
    """

    def connect(self, slot: Callable) -> Any:
        """Connect slot to this signal."""

    def disconnect(self, slot: Callable | None = None) -> Any:
        """Disconnect slot from this signal.

        If `None`, all slots should be disconnected.
        """

    def emit(self, *args: Any) -> Any:
        """Emits the signal with the given arguments."""


@runtime_checkable
class PSignalDescriptor(Protocol):
    """Descriptor that returns a signal instance."""

    def __get__(self, instance: Any | None, owner: Any) -> PSignalInstance:
        """Returns the signal instance for this descriptor."""


PSignal: TypeAlias = Union[PSignalDescriptor, PSignalInstance]


@runtime_checkable
class PMDASignaler(Protocol):
    """Declares the protocol for all signals that will be emitted from [`pymmcore_plus.mda.MDARunner`][]."""  # noqa: E501

    sequenceStarted: PSignal
    """Emits `(sequence: MDASequence, metadata: dict)` when an acquisition sequence is started.

    For the default [`MDAEngine`][pymmcore_plus.mda.MDAEngine], the metadata `dict` will
    be of type [`SummaryMetaV1`][pymmcore_plus.metadata.schema.SummaryMetaV1].
    """  # noqa: E501
    sequencePauseToggled: PSignal
    """Emits `(paused: bool)` when an acquisition sequence is paused or unpaused."""
    sequenceCanceled: PSignal
    """Emits `(sequence: MDASequence)` when an acquisition sequence is canceled."""
    sequenceFinished: PSignal
    """Emits `(sequence: MDASequence)` when an acquisition sequence is finished."""
    frameReady: PSignal
    """Emits `(img: np.ndarray, event: MDAEvent, metadata: dict)` after an image is acquired during an acquisition sequence.

    For the default [`MDAEngine`][pymmcore_plus.mda.MDAEngine], the metadata `dict` will
    be of type [`FrameMetaV1`][pymmcore_plus.metadata.schema.FrameMetaV1].
    """  # noqa: E501
    awaitingEvent: PSignal
    """Emits `(event: MDAEvent, remaining_sec: float)` when the runner is waiting to start an event.

    Note: Not all events in a sequence will emit this signal. This will only be emitted
    if the wait time is non-zero.
    """  # noqa: E501
    eventStarted: PSignal
    """Emits `(event: MDAEvent)` immediately before event setup and execution."""
