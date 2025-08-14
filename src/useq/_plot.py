from __future__ import annotations

from typing import TYPE_CHECKING, Callable

try:
    import matplotlib.pyplot as plt
    from matplotlib import patches
    from matplotlib.figure import Figure
except ImportError as e:
    raise ImportError(
        "Matplotlib is required for plotting functions.  Please install matplotlib."
    ) from e

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from matplotlib.axes import Axes

    from useq._plate import WellPlatePlan
    from useq._position import PositionBase


def plot_points(
    points: Iterable[PositionBase],
    *,
    rect_size: tuple[float, float] | None = None,
    bounding_poly: Sequence[tuple[float, float]] | None = None,
    polygon: tuple[float, float] | None = None,
    ax: Axes | None = None,
    hide_axes: bool = False,
    aspect_ratio_multiplier: float = 5.0,
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
    bounding_poly : Sequence[tuple[float, float]] | None
        A polygon to draw around the points as a sequence of (x, y) vertices.
        If None, no bounding polygon is drawn.
    ax : Axes | None
        The axes to plot on. If None, a new figure and axes are created.
    hide_axes : bool
        Whether to hide the axes. Defaults to False.
    aspect_ratio_multiplier : float
        The multiplier for the aspect ratio of the plot. Defaults to 5.0.
        This is used to dynamically adjust the figure size based on the aspect ratio.
    show : bool
        Whether to show the plot. If False, the plot is not shown.
        Defaults to True.

    Returns
    -------
    Axes
        The axes with the plot.
    """
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    if not isinstance(fig, Figure):
        raise TypeError("Expected a Figure instance.")

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

    if polygon is not None:
        y_poly, x_poly, *_ = zip(*list(polygon))
        y_poly += (y_poly[0],)
        x_poly += (x_poly[0],)
        ax.scatter(y_poly, x_poly, color="magenta")
        ax.plot(y_poly, x_poly, color="yellow")

    if bounding_poly is not None:
        # draw a thicker dashed line around the bounding polygon
        poly_x = [vertex[0] for vertex in bounding_poly] + [bounding_poly[0][0]]
        poly_y = [vertex[1] for vertex in bounding_poly] + [bounding_poly[0][1]]
        ax.plot(
            poly_x,
            poly_y,
            color="black",
            linestyle="--",
            linewidth=2,
            alpha=0.5,
        )
        # ensure the bounding polygon is visible
        min_x, max_x = min(poly_x), max(poly_x)
        min_y, max_y = min(poly_y), max(poly_y)
        ax.set_xlim(min_x - 10, max_x + 10)
        ax.set_ylim(min_y - 10, max_y + 10)
    # ax.invert_yaxis()
    ax.axis("equal")

    # dynamically adjust figure size based on aspect ratio
    x_range = max(x) - min(x)
    y_range = (max(y) - min(y)) or 1
    aspect_ratio = x_range / y_range
    mpx = aspect_ratio_multiplier
    if x_range < y_range:
        fig.set_size_inches(
            mpx, mpx / (aspect_ratio if aspect_ratio > 0.0 else 1), forward=True
        )
    else:
        fig.set_size_inches(mpx * aspect_ratio, mpx, forward=True)

    if hide_axes:
        ax.axis("off")
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
