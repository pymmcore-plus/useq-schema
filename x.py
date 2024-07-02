import numpy as np

import useq

pp = useq.WellPlatePlan(
    # plate object, string key, or number of wells
    plate=96,
    a1_center_xy=(100, 200),
    # rotation can be expressed as a string or number (degrees)
    rotation=-10,
    # selected_wells is any 1-2D indexing expression.
    # Here is a random selection of 20% of wells
    selected_wells=np.where(np.random.rand(8, 12) > 0.8),
    well_points_plan=useq.RandomPoints(
        num_points=10, fov_height=0.85, fov_width=1, allow_overlap=False
    ),
    # well_points_plan=useq.GridRowsColumns(
    #     rows=3, columns=3, fov_height=0.85, fov_width=1, overlap=-20
    # ),
)
pp.plot()
