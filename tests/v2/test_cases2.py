from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rich import print  # noqa: F401
from tests.fixtures.cases import CASES, MDATestCase, assert_test_case_passes

from useq import v2

if TYPE_CHECKING:
    from useq._mda_event import MDAEvent


@pytest.mark.filterwarnings("ignore:Conflicting absolute pos")
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_mda_sequence(case: MDATestCase) -> None:
    if "af_z_position" in case.name:
        pytest.xfail("af_z_position is not yet working in useq.v2, ")

    v2_seq = v2.MDASequence.model_validate(case.seq)
    assert isinstance(v2_seq, v2.MDASequence)
    actual_events = list(v2_seq)

    assert_test_case_passes(case, actual_events)

    assert_v2_same_as_v1(list(case.seq), actual_events)


def assert_v2_same_as_v1(v1_seq: list[MDAEvent], v2_seq: list[MDAEvent]) -> None:
    """Assert that the v2 sequence is the same as the v1 sequence."""
    # test parity with v1
    v2_event_dicts = [x.model_dump(exclude={"sequence"}) for x in v2_seq]
    v1_event_dicts = [x.model_dump(exclude={"sequence"}) for x in v1_seq]
    if v2_event_dicts != v1_event_dicts:
        # print intelligible diff to see exactly what is different, including
        # total number of events, indices that differ, and a full repr
        # of the first event that differs

        msg = []
        if len(v2_event_dicts) != len(v1_event_dicts):
            msg.append(
                f"Number of events differ: {len(v2_event_dicts)} != {len(v1_event_dicts)}"
            )
        differing_indices = [
            i for i, (a, b) in enumerate(zip(v2_event_dicts, v1_event_dicts)) if a != b
        ]
        if differing_indices:
            msg.append(f"Indices that differ: {differing_indices}")

            # show the first differing event in full
            idx = differing_indices[0]

            v1_dict = v1_event_dicts[idx]
            v2_dict = v2_event_dicts[idx]

            diff_fields = {f for f in v1_dict if v1_dict[f] != v2_dict.get(f)}
            v1min = {k: v for k, v in v1_dict.items() if k in diff_fields}
            v2min = {k: v for k, v in v2_dict.items() if k in diff_fields}
            msg.extend(
                [
                    f"First differing event (index {idx}):",
                    f"  EXPECT: {v1min}",
                    f"  ACTUAL: {v2min}",
                ]
            )
        raise AssertionError(
            "Events differ between v1 and v2 MDASequence:\n\n" + "\n  ".join(msg)
        )
