from rich import print

from useq import TIntervalLoops, ZRangeAround
from useq._channel import Channel, Channels
from useq._grid import GridRowsColumns
from useq._mda_sequence import MDASequence
from useq._multi_axis_sequence import MultiDimSequence
from useq._stage_positions import StagePositions

t = TIntervalLoops(interval=0.2, loops=4)
z = ZRangeAround(range=4, step=2)
g = GridRowsColumns(rows=2, columns=2)
c = Channels(
    [
        Channel(config="DAPI"),
        # Channel(config="FITC", z_offset=100),
        # Channel(config="Cy5", acquire_every=2),
    ]
)
seq1 = MDASequence(
    time_plan=t,
    z_plan=z,
    stage_positions=[
        (0, 0),
        {
            "x": 10,
            "y": 10,
            "sequence": MDASequence(time_plan=t, z_plan=z, axis_order="tz"),
        },
    ],
    channels=list(c),
    grid_plan=g,
    axis_order="tpgcz",
)
seq2 = MultiDimSequence(
    axes=(
        t,
        StagePositions(
            [
                (0, 0),
                {"x": 10, "y": 10, "sequence": MultiDimSequence(axes=(t, z))},
            ]
        ),
        g,
        c,
        z,
    )
)

for i, (e1, e2) in enumerate(zip(seq1, seq2)):
    print(f"{i} ----")
    print(e1)
    print(e2)
    if e1 != e2:
        breakpoint()
        break
else:
    assert list(seq1) == list(seq2)
