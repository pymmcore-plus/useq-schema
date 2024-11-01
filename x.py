from rich import print

from useq import TIntervalLoops, ZRangeAround
from useq._multi_axis_sequence import MultiDimSequence

seq = MultiDimSequence(
    axes=(
        TIntervalLoops(interval=0.2, loops=4),
        ZRangeAround(range=4, step=2),
    )
)

for e in seq:
    print(e)
