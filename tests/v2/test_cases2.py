from __future__ import annotations

import pytest
from rich import print  # noqa: F401
from tests.fixtures.cases import CASES, MDATestCase, assert_test_case_passes

from useq import v2


@pytest.mark.filterwarnings("ignore:Conflicting absolute pos")
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_mda_sequence(case: MDATestCase) -> None:
    if "af_z_position" in case.name:
        pytest.xfail("af_z_position is not yet working in useq.v2, ")

    v2_seq = v2.MDASequence.model_validate(case.seq)
    assert isinstance(v2_seq, v2.MDASequence)
    actual_events = list(v2_seq)

    assert_test_case_passes(case, actual_events)
