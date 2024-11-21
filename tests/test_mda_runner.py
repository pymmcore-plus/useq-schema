from __future__ import annotations

import time
from queue import Queue
from threading import Thread
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import numpy as np
import pytest

from useq import MDAEvent, MDASequence
from useq.experimental import MDARunner
from useq.experimental.pysgnals import MDASignaler

if TYPE_CHECKING:
    from collections.abc import Iterable

    from useq.experimental.protocols import PImagePayload


class GoodEngine:
    def setup_sequence(self, sequence: MDASequence) -> None: ...

    def setup_event(self, event: MDAEvent) -> None: ...

    def exec_event(self, event: MDAEvent) -> Iterable[PImagePayload]:
        yield (np.ndarray(0), event, {})

    # def event_iterator(self, events: Iterable[MDAEvent]) -> Iterator[MDAEvent]:
    #     yield from events
    # def teardown_event(self, event: MDAEvent) -> None: ...
    # def teardown_sequence(self, sequence: MDASequence) -> None: ...


class BrokenEngine(GoodEngine):
    def setup_event(self, event: MDAEvent) -> None:
        raise ValueError("something broke")


MDA = MDASequence(
    channels=["Cy5"],
    time_plan={"interval": 0.2, "loops": 2},
    axis_order="tpcz",
    stage_positions=[(222, 1, 1), (111, 0, 0)],
)


def test_mda_runner() -> None:
    runner = MDARunner(MDASignaler())
    engine = GoodEngine()
    runner.set_engine(engine)
    assert runner.engine is engine

    start_mock = Mock()
    frame_mock = Mock()
    finished_mock = Mock()
    runner.events.sequenceStarted.connect(start_mock)
    runner.events.frameReady.connect(frame_mock)
    runner.events.sequenceFinished.connect(finished_mock)
    runner.run(MDA)

    start_mock.assert_called_once_with(MDA, {})
    frame_mock.assert_called()
    finished_mock.assert_called_once_with(MDA)


def test_mda_runner_pause_cancel() -> None:
    runner = MDARunner(MDASignaler())
    runner.set_engine(GoodEngine())

    pause_mock = Mock()
    cancel_mock = Mock()
    runner.events.sequencePauseToggled.connect(pause_mock)
    runner.events.sequenceCanceled.connect(cancel_mock)

    q: Queue[MDAEvent] = Queue()

    thread = Thread(target=runner.run, args=(iter(q.get, None),))
    thread.start()

    # this is a little bit of a hack/bug for the Queue case, but if we don't process at
    # least one event, the runner will never check for cancellation
    q.put(MDAEvent())

    t0 = time.time()
    while not runner.is_running():
        if time.time() - t0 > 1:
            raise TimeoutError("timeout")
        time.sleep(0.01)

    assert not runner.is_paused()
    runner.toggle_pause()
    assert runner.is_paused()
    pause_mock.assert_called_once_with(True)

    runner.toggle_pause()
    assert not runner.is_paused()
    pause_mock.assert_called_with(False)

    runner.cancel()
    q.put(MDAEvent())  # same bug here
    thread.join()
    assert not runner.is_running()


def test_mda_failures() -> None:
    runner = MDARunner(MDASignaler())
    runner.set_engine(GoodEngine())

    # error in user callback
    def cb(img: Any, event: Any) -> None:
        raise ValueError("uh oh")

    runner.events.frameReady.connect(cb)
    runner.run(MDA)

    assert not runner.is_running()
    assert not runner.is_paused()
    assert not runner._canceled
    runner.events.frameReady.disconnect(cb)

    # Hardware failure, e.g. a serial connection error
    # we should fail gracefully
    with patch.object(runner, "_engine", BrokenEngine()):
        with pytest.raises(ValueError):
            runner.run(MDA)
        assert not runner.is_running()
        assert not runner.is_paused()
        assert not runner._canceled
