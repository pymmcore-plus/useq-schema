# import time

# import useq

# seq = useq.MDASequence(
#     channels=["A", "B"],
#     stage_positions=[
#         (0, 0, 1),
#         useq.Position(
#             sequence=useq.MDASequence(grid_plan=useq.GridRelative(rows=10, columns=10))  # noqa
#         ),
#     ],
#     time_plan=useq.TIntervalLoops(interval=1, loops=10),
#     z_plan=useq.ZRangeAround(step=1, range=10),
# )


# start = time.perf_counter()
# events = list(seq)
# end = time.perf_counter()
# print(f"Generated {len(events)} events in {end - start:.2f} seconds")

import cProfile
import pstats

import useq

seq = useq.MDASequence(
    channels=["A", "B"],
    stage_positions=[(0, 0, 1), (0, 1, 1), (3, 0, 1)],
    time_plan=useq.TIntervalLoops(interval=1, loops=1000),
    z_plan=useq.ZRangeAround(step=1, range=10),
)

pr = cProfile.Profile()
pr.enable()
print(len(list(seq)))
pr.disable()

ps = pstats.Stats(pr).sort_stats("cumtime")
ps.print_stats(20)
