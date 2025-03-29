from pathlib import Path

import pytest

from useq import MDASequence


@pytest.mark.parametrize("ext", ["json", "yaml"])
def test_serialization(mda1: MDASequence, ext: str) -> None:
    FILE = Path(__file__).parent / "fixtures" / f"mda.{ext}"
    text = FILE.read_text()
    mda = MDASequence.from_file(str(FILE))
    assert mda == mda1
    if ext == "json":
        # NOTE: this is extremely sensitive to the format of the JSON fixture file
        # things MUST be in the same order there... so if you get errors here, double
        # check the order of the fields in the fixture file.
        dump = mda.model_dump_json(exclude_unset=True)
        assert dump == text.replace("\n", "").replace(" ", "")
    else:
        assert mda.yaml() == text

    it = iter(mda)
    for _ in range(20):
        if ext == "json":
            assert next(it).model_dump_json()
        else:
            assert next(it).yaml()
