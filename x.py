from rich import print

from useq import TIntervalLoops, ZRangeAround
from useq._channel import Channel, Channels
from useq._grid import GridRowsColumns
from useq._mda_sequence import MDASequence
from useq._multi_axis_sequence import MultiDimSequence
from useq._stage_positions import StagePositions

t = TIntervalLoops(interval=0.2, loops=3)
z = ZRangeAround(range=4, step=2)
g = GridRowsColumns(rows=2, columns=2)
c = Channels(
    [
        Channel(config="DAPI"),
        Channel(config="FITC"),
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
            "z": 20,
            "sequence": MDASequence(grid_plan=g, z_plan=ZRangeAround(range=2, step=1)),
        },
    ],
    channels=list(c),
    axis_order="tpgcz",
)
print(seq1.sizes)
seq2 = MultiDimSequence(
    axes=(
        t,
        StagePositions(
            [
                (0, 0),
                {
                    "x": 10,
                    "y": 10,
                    "z": 20,
                    "sequence": MultiDimSequence(
                        axes=(g, ZRangeAround(range=2, step=1))
                    ),
                },
            ]
        ),
        c,
        z,
    )
)
print(len(list(seq1)))
print(len(list(seq2)))
# for i, (e1, e2) in enumerate(zip(seq1, seq2)):
#     print(f"{i} ----")
#     print(e1)
#     print(e2)
#     if e1 != e2:
#         print("NOT EQUAL")
#         break
# else:
#     assert list(seq1) == list(seq2)
