from __future__ import annotations

import pytest

from tests.fixtures.cases import CASES, MDATestCase, assert_test_case_passes


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_mda_sequence(case: MDATestCase) -> None:
    assert_test_case_passes(case, list(case.seq))
