import json
from pathlib import Path

import pytest

from useq import MDASequence


@pytest.mark.parametrize("ext", ["json", "yaml"])
def test_serialization(mda1: MDASequence, ext: str) -> None:
    FILE = Path(__file__).parent / "fixtures" / f"mda.{ext}"
    text = FILE.read_text()
    mda = MDASequence.parse_file(str(FILE))
    assert mda == mda1
    if ext == "json":
        assert json.loads(mda.json(exclude={"uid"})) == json.loads(text)
    else:
        assert mda.yaml() == text

    it = iter(mda)
    for _ in range(20):
        assert getattr(next(it), ext)()
