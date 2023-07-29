# breaks
from datetime import timedelta

import numpy as np
import pytest

import useq


def test_from_numpy() -> None:
    useq.ZRelativePositions(relative=np.arange(-1.5, 1.5, 0.5))


def estimate_time(seq: useq.MDASequence) -> float:
    n_timepoints = seq.time_plan.num_timepoints() if seq.time_plan else 1

    if isinstance(seq.time_plan, useq.MultiPhaseTimePlan):
        min_t_interval = min(p.interval for p in seq.time_plan.phases)
    else:
        min_t_interval = seq.time_plan.interval if seq.time_plan else timedelta(0)

    n_positions = len(seq.stage_positions or [0])
    num_z = seq.z_plan.num_positions() if seq.z_plan else 1
    num_grid = seq.grid_plan.num_positions() if seq.grid_plan else 1

    exposure_sum = sum((ch.exposure or 1) / 1000 for ch in seq.channels)
    per_timepoint_time_s = exposure_sum * n_positions * num_z * num_grid

    # the actual interval between timepoints will be the greater of the
    # prescribed interval (according to the time plan) and the time it takes
    # to actually acquire the data
    max_interval = max(min_t_interval.total_seconds(), per_timepoint_time_s)
    # note: the last per_timepoint_time_s depends on whether each channel has acquire_every
    return (n_timepoints - 1) * max_interval + per_timepoint_time_s


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


def _sizes_str(param: useq.MDASequence) -> str:
    # key used for test ids
    return "".join([f"{k}{v}" for k, v in param.sizes.items()])


# a list of (sequence, expected total time)
SEQS_NO_T: dict[useq.MDASequence, float] = {
    useq.MDASequence(channels=[DAPI_10]): 0.01,
    SEQ_40: 0.04,
    SEQ_40.replace(stage_positions=[(0, 0, 0)]): 0.04,
    SEQ_40.replace(stage_positions=TWO_POS): 0.08,
    SEQ_40.replace(stage_positions=TWO_POS, z_plan=Z_4): 0.32,
    SEQ_40.replace(stage_positions=TWO_POS, z_plan=Z_4, grid_plan=GRID_4): 1.28,
}


@pytest.mark.parametrize("seq", SEQS_NO_T, ids=_sizes_str)
def test_time_estimation_without_t(seq: useq.MDASequence) -> None:
    assert estimate_time(seq) == SEQS_NO_T[seq]


SEQS_WITH_T: dict[useq.MDASequence, float] = {
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
    SEQ_40_T2.replace(stage_positions=TWO_POS, z_plan=Z_4, grid_plan=GRID_4): 2.56,
}


@pytest.mark.parametrize("seq", SEQS_WITH_T, ids=_sizes_str)
def test_time_estimation_with_t(seq: useq.MDASequence) -> None:
    assert estimate_time(seq) == SEQS_WITH_T[seq]


# SEQS_WITH_T_AND_SKIPS: dict[useq.MDASequence, float] = {}


# @pytest.mark.parametrize("seq", SEQS_WITH_T_AND_SKIPS, ids=_sizes_str)
# def test_time_estimation_with_t(seq: useq.MDASequence) -> None:
#     assert estimate_time(seq) == SEQS_WITH_T[seq]
