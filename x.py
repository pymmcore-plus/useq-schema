from typing import Any

from useq import Axis
from useq.new import (
    MultiDimSequence,
    SimpleAxis,
    iterate_multi_dim_sequence,
)
from useq.new._multidim_seq import AxisIterable

# Example usage:
# A simple test: no overrides, just yield combinations.
multi_dim = MultiDimSequence(
    axes=(
        SimpleAxis(Axis.TIME, [0, 1, 2]),
        SimpleAxis(Axis.CHANNEL, ["red", "green", "blue"]),
        SimpleAxis(Axis.Z, [0.1, 0.2, 0.3]),
    ),
    axis_order=(Axis.TIME, Axis.CHANNEL, Axis.Z),
)

for indices in iterate_multi_dim_sequence(multi_dim):
    # Print a cleaned version that drops the axis objects.
    clean = {k: v[:2] for k, v in indices.items()}
    print(clean)

print("-------------")


# As an example, we override should_skip for the Axis.Z axis:
class FilteredZ(SimpleAxis):
    """Example of a filtered axis."""

    def should_skip(self, prefix: dict[str, tuple[int, Any, AxisIterable]]) -> bool:
        """Return True if this axis wants to skip the combination."""
        # If c is green, then only allow combinations where z equals 0.2.
        # Get the c value from the prefix:
        c_val = prefix.get(Axis.CHANNEL, (None, None))[1]
        z_val = prefix.get(Axis.Z, (None, None))[1]
        return bool(c_val == "green" and z_val != 0.2)


multi_dim = MultiDimSequence(
    axes=(
        SimpleAxis(Axis.TIME, [0, 1, 2]),
        SimpleAxis(Axis.CHANNEL, ["red", "green", "blue"]),
        FilteredZ(Axis.Z, [0.1, 0.2, 0.3]),
    ),
    axis_order=(Axis.TIME, Axis.CHANNEL, Axis.Z),
)
for indices in iterate_multi_dim_sequence(multi_dim):
    # Print a cleaned version that drops the axis objects.
    clean = {k: v[:2] for k, v in indices.items()}
    print(clean)
