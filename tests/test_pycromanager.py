from __future__ import annotations

from typing import TYPE_CHECKING

from useq.pycromanager import to_pycromanager

if TYPE_CHECKING:
    from useq import MDASequence


def test_pycromanager_events(mda1: MDASequence) -> None:
    events = to_pycromanager(mda1)
    assert isinstance(events, list)
    assert isinstance(events[0], dict)
