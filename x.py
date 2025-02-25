from rich import print

from useq import TIntervalLoops, ZRangeAround
from useq._channel import Channel, Channels
from useq._mda_sequence import MDASequence
from useq._multi_axis_sequence import MultiDimSequence
from useq._stage_positions import StagePositions

t = TIntervalLoops(interval=0.2, loops=4)
z = ZRangeAround(range=4, step=2)
p = StagePositions([(0, 0), (1, 1), (2, 2)])
c = Channels(
    [
        Channel(config="DAPI", do_stack=False),
        Channel(config="FITC", z_offset=100),
        Channel(config="Cy5", acquire_every=2),
    ]
)
seq1 = MDASequence(time_plan=t, z_plan=z, stage_positions=list(p), channels=list(c))
seq2 = MultiDimSequence(axes=(t, p, c, z))

for i, (e1, e2) in enumerate(zip(seq1, seq2)):
    if e1 != e2:
        print(f"{i} ----")
        print(e1)
        print(e2)
        breakpoint()
        break
else:
    assert list(seq1) == list(seq2)
