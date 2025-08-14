from useq import GridFromPolygon

grid = GridFromPolygon(
    vertices=[(0, 0), (3, 0), (3, 0.82), (1, 1), (0.7, 3), (0, 3)],
    fov_height=0.4,
    fov_width=0.4,
    # convex_hull=True,
)

grid.plot(show=True)
