from __future__ import annotations

from typing import TYPE_CHECKING, Callable

try:
    import matplotlib.pyplot as plt
    from matplotlib import patches
except ImportError as e:
    raise ImportError(
        "Matplotlib is required for plotting functions.  Please install matplotlib."
    ) from e

if TYPE_CHECKING:
    from collections.abc import Iterable

    from matplotlib.axes import Axes

    from useq._plate import WellPlatePlan
    from useq._position import PositionBase


def plot_points(
    points: Iterable[PositionBase],
    *,
    rect_size: tuple[float, float] | None = None,
    bounding_box: tuple[float, float, float, float] | None = None,
    ax: Axes | None = None,
    show: bool = True,
) -> Axes:
    """Plot a list of positions.

    Can be used with any iterable of PositionBase objects.

    Parameters
    ----------
    points : Iterable[PositionBase]
        The points to plot.
    rect_size : tuple[float, float] | None
        The size of the rectangles to draw around each point. If None, no rectangles
        are drawn.
    bounding_box : tuple[float, float, float, float] | None
        A bounding box to draw around the points (left, top, right, bottom).
        If None, no bounding box is drawn.
    ax : Axes | None
        The axes to plot on. If None, a new figure and axes are created.
    show : bool
        Whether to show the plot. If False, the plot is not shown.
        Defaults to True.

    Returns
    -------
    Axes
        The axes with the plot.
    """
    if ax is None:
        _, ax = plt.subplots()

    x, y = zip(*[(point.x, point.y) for point in points])
    ax.scatter(x, y)
    ax.scatter(x[0], y[0], color="red")  # mark the first point
    ax.plot(x, y, alpha=0.5, color="gray")  # connect the points

    if rect_size is not None:
        # show FOV rectangles at each point:
        for point in points:
            if point.x is not None and point.y is not None:
                half_width = rect_size[0] / 2
                half_height = rect_size[1] / 2
                rect = patches.Rectangle(
                    (point.x - half_width, point.y - half_height),
                    width=rect_size[0],
                    height=rect_size[1],
                    edgecolor="blue",
                    alpha=0.2,
                    facecolor="gray",
                )
                ax.add_patch(rect)

                # make sure the entire rectangle is visible
                ax.set_xlim(min(x) - half_width, max(x) + half_width)
                ax.set_ylim(min(y) - half_height, max(y) + half_height)

    if bounding_box is not None:
        # draw a thicker dashed line around the bounding box
        x0, y0, x1, y1 = bounding_box
        ax.plot(
            [x0, x1, x1, x0, x0],
            [y0, y0, y1, y1, y0],
            color="black",
            linestyle="--",
            linewidth=4,
            alpha=0.25,
        )
        # ensure the bounding box is visible
        ax.set_xlim(min(x0, x1) - 10, max(x0, x1) + 10)
        ax.set_ylim(min(y0, y1) - 10, max(y0, y1) + 10)

    ax.axis("equal")
    if show:
        plt.show()
    return ax


def plot_plate(
    plate_plan: WellPlatePlan,
    *,
    show_axis: bool = True,
    ax: Axes | None = None,
    show: bool = True,
) -> Axes:
    """Plot a well plate with the image positions.

    Parameters
    ----------
    plate_plan : WellPlatePlan
        The plate plan to plot.
    show_axis : bool
        Whether to show the axes. Defaults to True.
    ax : Axes | None
        The axes to plot on. If None, a new figure and axes are created.
    show : bool
        Whether to show the plot. If False, the plot is not shown.
        Defaults to True.
    """
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
        ax.text(x + offset_x, y - offset_y, well.name or "", fontsize=7)

    ax.axis("equal")
    if show:
        plt.show()
    return ax
