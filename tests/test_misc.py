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

    if isinstance(seq.grid_plan, useq.GridRelative):
        num_grid = seq.grid_plan.rows * seq.grid_plan.columns

    exposure_sum = sum((ch.exposure or 1) / 1000 for ch in seq.channels)
    per_timepoint_time_s = exposure_sum * n_positions * num_z * num_grid

    min_interval = min(min_t_interval.total_seconds(), per_timepoint_time_s)
    # note: the last per_timepoint_time_s depends on whether each channel has acquire_every
    return (n_timepoints - 1) * min_interval + per_timepoint_time_s


DAPI_10 = useq.Channel(config="DAPI", exposure=10)
FITC_20 = useq.Channel(config="DAPI", exposure=20)
TWO_CH_30 = [DAPI_10, FITC_20]
TWO_POS = [(0, 0), (1, 1)]
Z_3 = useq.ZRangeAround(range=2, step=1)
GRID_4 = useq.GridRelative(columns=2, rows=2)


def test_z_num_pos() -> None:
    assert Z_3.num_positions() == 3


# a list of (sequence, expected total time)
SEQS: dict[useq.MDASequence, float] = {
    useq.MDASequence(channels=[DAPI_10]): 0.01,
    useq.MDASequence(channels=TWO_CH_30): 0.03,
    useq.MDASequence(channels=TWO_CH_30, stage_positions=[(0, 0, 0)]): 0.03,
    useq.MDASequence(channels=TWO_CH_30, stage_positions=TWO_POS): 0.06,
    useq.MDASequence(channels=TWO_CH_30, stage_positions=TWO_POS, z_plan=Z_3): 0.18,
    useq.MDASequence(
        channels=TWO_CH_30, stage_positions=TWO_POS, z_plan=Z_3, grid_plan=GRID_4
    ): 0.72,
}


@pytest.mark.parametrize("seq,expected", SEQS.items())
def test_time_estimation(seq: useq.MDASequence, expected: float) -> None:
    assert estimate_time(seq) == expected
