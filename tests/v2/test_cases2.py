from __future__ import annotations

from typing import Any

import pytest
from rich import print  # noqa: F401
from tests.fixtures.cases import CASES, MDATestCase

from useq import v2


@pytest.mark.filterwarnings("ignore:Conflicting absolute pos")
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_mda_sequence(case: MDATestCase) -> None:
    if "af_z_position" in case.name:
        pytest.xfail("af_z_position is not yet working in useq.v2, ")
    seq = v2.MDASequence.model_validate(case.seq)
    assert isinstance(seq, v2.MDASequence)

    # test case expressed the expectation as a predicate
    if case.predicate is not None:
        # (a function that returns a non-empty error message if the test fails)
        if msg := case.predicate(seq):
            raise AssertionError(f"\nExpectation not met in '{case.name}':\n  {msg}\n")

    # test case expressed the expectation as a list of MDAEvent
    elif isinstance(case.expected, list):
        actual_events = list(seq)
        if len(actual_events) != len(case.expected):
            raise AssertionError(
                f"\nMismatch in case '{case.name}':\n"
                f"  expected: {len(case.expected)} events\n"
                f"    actual: {len(actual_events)} events\n"
            )
        for i, event in enumerate(actual_events):
            if event != case.expected[i]:
                raise AssertionError(
                    f"\nMismatch in case '{case.name}':\n"
                    f"  expected: {case.expected[i]}\n"
                    f"    actual: {event}\n"
                )

    # test case expressed the expectation as a dict of {Event attr -> values list}
    else:
        assert isinstance(case.expected, dict), f"Invalid test case: {case.name!r}"
        actual: dict[str, list[Any]] = {k: [] for k in case.expected}
        for event in case.seq:
            for attr in case.expected:
                actual[attr].append(getattr(event, attr))

        if mismatched_fields := {
            attr for attr in actual if actual[attr] != case.expected[attr]
        }:
            msg = f"\nMismatch in case '{case.name}':\n"
            for attr in mismatched_fields:
                msg += f"  {attr}:\n"
                msg += f"    expected: {case.expected[attr]}\n"
                msg += f"      actual: {actual[attr]}\n"
            raise AssertionError(msg)
