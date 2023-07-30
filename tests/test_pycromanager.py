from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from useq import MDASequence


def test_pycromanager_events(mda1: MDASequence) -> None:
    # after deprecation is removed, use this import directly
    # from useq.pycromanager import to_pycromanager

    with pytest.warns(FutureWarning, match="deprecated"):
        events = mda1.to_pycromanager()
        assert isinstance(events, list)
        assert isinstance(events[0], dict)
