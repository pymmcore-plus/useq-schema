from __future__ import annotations

import numpy as np
import pytest

import useq


def test_from_numpy() -> None:
    useq.ZRelativePositions(relative=np.arange(-1.5, 1.5, 0.5))


DAPI_10 = useq.Channel(config="DAPI", exposure=10)
FITC_30 = useq.Channel(config="DAPI", exposure=30)
TWO_CH_40 = [DAPI_10, FITC_30]
TWO_POS = [(0, 0), (1, 1)]
Z_4 = useq.ZRangeAround(range=3, step=1)
GRID_4 = useq.GridRelative(columns=2, rows=2)
SEQ_40 = useq.MDASequence(channels=TWO_CH_40)

LOOP_1Sx2 = useq.TIntervalLoops(interval=1, loops=2)
SEQ_40_T2 = useq.MDASequence(channels=TWO_CH_40, time_plan=LOOP_1Sx2)


def test_num_pos() -> None:
    # sanity checks to make sure that time_estimation has good inputs
    assert Z_4.num_positions() == 4
    assert GRID_4.num_positions() == 4


def _sizes_str(seq: useq.MDASequence) -> str:
    # key used for test ids
    sizes = "".join([f"{k}{v}" for k, v in seq.sizes.items() if v])
    if seq.channels and any(not ch.do_stack for ch in seq.channels):
        sizes += "_Zskip"
    return sizes


# a list of (sequence, expected total time)
SEQS_NO_T: dict[useq.MDASequence, float] = {
    useq.MDASequence(channels=[DAPI_10]): 0.01,
    SEQ_40: 0.04,
    SEQ_40.replace(stage_positions=[(0, 0, 0)]): 0.04,
    SEQ_40.replace(stage_positions=TWO_POS): 0.08,
    SEQ_40.replace(stage_positions=TWO_POS, z_plan=Z_4): 0.32,
    SEQ_40.replace(stage_positions=TWO_POS, z_plan=Z_4, grid_plan=GRID_4): 1.28,
}


def _duration_exceeded(seq: useq.MDASequence) -> tuple[float, bool]:
    estimate = seq.estimate_duration()
    return estimate.total_duration, estimate.time_interval_exceeded


@pytest.mark.parametrize("seq", SEQS_NO_T, ids=_sizes_str)
def test_time_estimation_without_t(seq: useq.MDASequence) -> None:
    assert _duration_exceeded(seq) == (SEQS_NO_T[seq], False)


SEQS_WITH_T: dict[useq.MDASequence, float | tuple[float, bool]] = {
    # with a simple time plan, the total duration is (ntime - 1) * interval + per_t_time
    # because the first timepoint is acquired immediately
    useq.MDASequence(channels=[DAPI_10], time_plan={"interval": 1, "loops": 2}): 1.01,
    useq.MDASequence(channels=[DAPI_10], time_plan={"interval": 1, "loops": 3}): 2.01,
    useq.MDASequence(channels=TWO_CH_40, time_plan={"interval": 1, "loops": 4}): 3.04,
    SEQ_40_T2: 1.04,  # 1 position is implied
    SEQ_40_T2.replace(stage_positions=[(0, 0, 0)]): 1.04,
    SEQ_40_T2.replace(stage_positions=TWO_POS): 1.08,
    SEQ_40_T2.replace(stage_positions=TWO_POS, z_plan=Z_4): 1.32,
    # HERE, however, a single timepoint takes 1.28s, longer than the time interval
    # so the total time is 1.28s * n_timepoints = 1.28s * 2 = 2.56s
    SEQ_40_T2.replace(stage_positions=TWO_POS, z_plan=Z_4, grid_plan=GRID_4): (
        2.56,
        True,  # time interval exceeded
    ),
}


@pytest.mark.parametrize("seq", SEQS_WITH_T, ids=_sizes_str)
def test_time_estimation_with_t(seq: useq.MDASequence) -> None:
    expect = SEQS_WITH_T[seq]
    if not isinstance(expect, tuple):
        expect = (expect, False)
    assert _duration_exceeded(seq) == expect


DAPI_10_NOZ = DAPI_10.replace(do_stack=False)
SEQS_WITH_Z_SKIPS: dict[useq.MDASequence, float | tuple[float, bool]] = {
    useq.MDASequence(channels=[DAPI_10], z_plan=Z_4): 0.04,
    useq.MDASequence(channels=[DAPI_10_NOZ], z_plan=Z_4): 0.01,
    useq.MDASequence(channels=[FITC_30], z_plan=Z_4): 0.12,
    useq.MDASequence(channels=[DAPI_10_NOZ, FITC_30], z_plan=Z_4): 0.13,  # 0.01 + 0.12
    useq.MDASequence(channels=[DAPI_10, FITC_30], z_plan=Z_4): 0.16,  # 0.04 + 0.12
    # time interval-limited
    useq.MDASequence(
        channels=[DAPI_10_NOZ, FITC_30], z_plan=Z_4, time_plan=LOOP_1Sx2
    ): 1.13,
    useq.MDASequence(
        channels=[DAPI_10_NOZ, FITC_30],
        stage_positions=TWO_POS,
        z_plan=Z_4,
        time_plan=LOOP_1Sx2,
    ): 1.26,  # two positions = 1s interval + 0.13 * 2
    # acquisition-limited
    useq.MDASequence(
        channels=[DAPI_10],
        z_plan=useq.ZRangeAround(range=199, step=1),
        time_plan=LOOP_1Sx2,
    ): (4.0, True),
    useq.MDASequence(
        channels=[DAPI_10_NOZ],  # with NOZ, the time is 0.01s plus a 1sec T interval
        z_plan=useq.ZRangeAround(range=199, step=1),
        time_plan=LOOP_1Sx2,
    ): 1.01,
}


@pytest.mark.parametrize("seq", SEQS_WITH_Z_SKIPS, ids=_sizes_str)
def test_time_estimation_with_z_skips(seq: useq.MDASequence) -> None:
    expect = SEQS_WITH_Z_SKIPS[seq]
    if not isinstance(expect, tuple):
        expect = (expect, False)
    assert _duration_exceeded(seq) == expect


SEQS_WITH_SUBSEQS: dict[useq.MDASequence, float | tuple[float, bool]] = {
    useq.MDASequence(channels=[DAPI_10], stage_positions=TWO_POS): 0.02,
    useq.MDASequence(
        channels=[DAPI_10],
        stage_positions=[
            (0, 0),  # 0.01
            useq.Position(x=1, sequence=useq.MDASequence(grid_plan=GRID_4)),  # 0.04
        ],
    ): 0.05,  # 0.01 + 0.04
}


@pytest.mark.parametrize("seq", SEQS_WITH_SUBSEQS, ids=_sizes_str)
def test_time_estimation_with_position_seqs(seq: useq.MDASequence) -> None:
    expect = SEQS_WITH_SUBSEQS[seq]
    if not isinstance(expect, tuple):
        expect = (expect, False)
    assert _duration_exceeded(seq) == expect
