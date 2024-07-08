from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable

try:
    import matplotlib.pyplot as plt
    from matplotlib import patches
except ImportError as e:
    raise ImportError(
        "Matplotlib is required for plotting functions.  Please install matplotlib."
    ) from e

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from useq._plate import WellPlatePlan
    from useq._position import PositionBase


def plot_points(points: Iterable[PositionBase], ax: Axes | None = None) -> None:
    """Plot a list of positions.

    Can be used with any iterable of PositionBase objects.
    """
    if ax is None:
        _, ax = plt.subplots()

    x, y = zip(*[(point.x, point.y) for point in points])
    ax.scatter(x, y)
    ax.scatter(x[0], y[0], color="red")  # mark the first point
    ax.plot(x, y, alpha=0.5, color="gray")  # connect the points
    ax.axis("equal")
    plt.show()


def plot_plate(
    plate_plan: WellPlatePlan, show_axis: bool = True, ax: Axes | None = None
) -> None:
    if ax is None:
        _, ax = plt.subplots()

    # hide axes
    if not show_axis:
        ax.axis("off")

    # ################ draw outline of all wells ################
    height, width = plate_plan.plate.well_size  # mm
    height, width = height * 1000, width * 1000  # µm

    kwargs = {}
    offset_x, offset_y = 0.0, 0.0
    if plate_plan.plate.circular_wells:
        patch_type: Callable = patches.Ellipse
    else:
        patch_type = patches.Rectangle
        offset_x, offset_y = -width / 2, -height / 2
        kwargs["rotation_point"] = "center"

    for well in plate_plan.all_well_positions:
        sh = patch_type(
            (well.x + offset_x, well.y + offset_y),  # type: ignore[operator]
            width=width,
            height=height,
            angle=plate_plan.rotation or 0,
            facecolor="none",
            edgecolor="gray",
            linewidth=0.5,
            linestyle="--",
            **kwargs,
        )
        ax.add_patch(sh)

    ################ plot image positions ################
    w, h = plate_plan.well_points_plan.fov_width, plate_plan.well_points_plan.fov_height

    for img_point in plate_plan.image_positions:
        x, y = float(img_point.x), float(img_point.y)  # type: ignore[arg-type] # µm
        if w and h:
            ax.add_patch(
                patches.Rectangle(
                    (x - w / 2, y - h / 2),
                    width=w,
                    height=h,
                    facecolor="magenta",
                    edgecolor="gray",
                    linewidth=0.5,
                    alpha=0.5,
                )
            )
        else:
            plt.plot(x, y, "mo", markersize=3, alpha=0.5)

    # ################ draw names on used wells ################
    offset_x, offset_y = -width / 2, -height / 2
    for well in plate_plan.selected_well_positions:
        x, y = float(well.x), float(well.y)  # type: ignore[arg-type]
        # draw name next to spot
        ax.text(x + offset_x, y - offset_y, well.name, fontsize=7)

    ax.axis("equal")
    plt.show()
