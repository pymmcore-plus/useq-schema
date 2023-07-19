# breaks
import numpy as np

import useq


def test_from_numpy() -> None:
    useq.ZRelativePositions(relative=np.arange(-1.5, 1.5, 0.5))
