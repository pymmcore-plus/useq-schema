"""Simple tests for v2 grid iteration to understand how it works."""

import pytest

from useq._enums import RelativeTo, Shape
from useq._point_visiting import OrderMode, TraversalOrder
from useq.v2._grid import GridFromEdges, GridRowsColumns, GridWidthHeight, RandomPoints


class TestGridFromEdges:
    """Test absolute positioning with GridFromEdges."""

    def test_simple_2x2_grid(self) -> None:
        """Simple 2x2 grid with no overlap."""
        grid = GridFromEdges(
            top=10,
            left=0,
            bottom=0,
            right=10,
            fov_width=5,
            fov_height=5,
        )

        positions = list(grid)

        # Should have 4 positions (2x2)
        assert len(positions) == 4
        assert len(grid) == 4

        # Check position coordinates (absolute positioning)
        coords = [(p.x, p.y) for p in positions]
        expected = [
            (2.5, 7.5),  # top-left
            (7.5, 7.5),  # top-right
            (7.5, 2.5),  # bottom-right (snake pattern)
            (2.5, 2.5),  # bottom-left
        ]
        assert coords == expected

        # All should be absolute positions
        assert all(not p.is_relative for p in positions)

    def test_single_position(self) -> None:
        """When bounding box equals FOV size, should have 1 position."""
        grid = GridFromEdges(
            top=5,
            left=0,
            bottom=0,
            right=5,
            fov_width=5,
            fov_height=5,
        )

        positions = list(grid)
        assert len(positions) == 1

        # Position should be at center of bounding box
        pos = positions[0]
        assert pos.x == 2.5
        assert pos.y == 2.5
        assert not pos.is_relative

    def test_with_overlap(self) -> None:
        """Test grid with 50% overlap."""
        grid = GridFromEdges(
            top=10,
            left=0,
            bottom=0,
            right=10,
            fov_width=5,
            fov_height=5,
            overlap=50,  # 50% overlap
        )

        positions = list(grid)

        # With 50% overlap, step size is 2.5, so we need more positions
        assert len(positions) > 4

        # Check first few positions have correct spacing
        coords = [(p.x, p.y) for p in positions[:4]]
        expected_step = 2.5  # 5 * (1 - 0.5)
        assert coords[0] == (2.5, 7.5)  # first position
        assert coords[1] == (2.5 + expected_step, 7.5)  # second position


class TestGridRowsColumns:
    """Test relative positioning with GridRowsColumns."""

    def test_2x3_centered_grid(self) -> None:
        """2 rows, 3 columns, centered around origin."""
        grid = GridRowsColumns(
            rows=2,
            columns=3,
            relative_to=RelativeTo.center,
            fov_width=1,
            fov_height=1,
        )

        positions = list(grid)
        assert len(positions) == 6
        assert len(grid) == 6

        # Check coordinates - should be centered around (0,0)
        coords = [(p.x, p.y) for p in positions]
        expected = [
            (-1.0, 0.5),  # top-left
            (0.0, 0.5),  # top-center
            (1.0, 0.5),  # top-right
            (1.0, -0.5),  # bottom-right (snake pattern)
            (0.0, -0.5),  # bottom-center
            (-1.0, -0.5),  # bottom-left
        ]
        assert coords == expected

        # All should be relative positions
        assert all(p.is_relative for p in positions)

    def test_2x2_top_left(self) -> None:
        """2x2 grid positioned at top-left corner."""
        grid = GridRowsColumns(
            rows=2,
            columns=2,
            relative_to=RelativeTo.top_left,
            fov_width=1,
            fov_height=1,
        )

        positions = list(grid)
        coords = [(p.x, p.y) for p in positions]

        # First position should be at (0.5, -0.5) since top-left corner is at origin
        expected = [
            (0.5, -0.5),  # top-left
            (1.5, -0.5),  # top-right
            (1.5, -1.5),  # bottom-right
            (0.5, -1.5),  # bottom-left
        ]
        assert coords == expected

    def test_with_overlap(self) -> None:
        """Test grid with overlap."""
        grid = GridRowsColumns(
            rows=2,
            columns=2,
            relative_to=RelativeTo.center,
            fov_width=2,
            fov_height=2,
            overlap=(25, 50),  # 25% x overlap, 50% y overlap
        )

        positions = list(grid)
        coords = [(p.x, p.y) for p in positions]

        # Step sizes: dx = 2 * (1 - 0.25) = 1.5, dy = 2 * (1 - 0.5) = 1
        expected_dx, expected_dy = 1.5, 1.0

        # Check spacing between positions
        x_spacing = abs(coords[1][0] - coords[0][0])
        y_spacing = abs(coords[2][1] - coords[0][1])

        assert abs(x_spacing - expected_dx) < 0.01
        assert abs(y_spacing - expected_dy) < 0.01


class TestGridWidthHeight:
    """Test relative positioning with GridWidthHeight."""

    def test_3x2_area_centered(self) -> None:
        """Cover 3x2 area with 1x1 FOV, centered."""
        grid = GridWidthHeight(
            width=3, height=2, relative_to=RelativeTo.center, fov_width=1, fov_height=1
        )

        positions = list(grid)

        # Should need 3x2 = 6 positions to cover the area
        assert len(positions) == 6
        assert len(grid) == 6

        coords = [(p.x, p.y) for p in positions]
        expected = [
            (-1.0, 0.5),  # top-left
            (0.0, 0.5),  # top-center
            (1.0, 0.5),  # top-right
            (1.0, -0.5),  # bottom-right (snake pattern)
            (0.0, -0.5),  # bottom-center
            (-1.0, -0.5),  # bottom-left
        ]
        assert coords == expected

        # All should be relative positions
        assert all(p.is_relative for p in positions)

    def test_top_left_positioning(self) -> None:
        """Test top-left positioning."""
        grid = GridWidthHeight(
            width=2,
            height=2,
            relative_to=RelativeTo.top_left,
            fov_width=1,
            fov_height=1,
        )

        positions = list(grid)
        coords = [(p.x, p.y) for p in positions]

        # Should start at (0.5, -0.5) for top-left positioning
        expected = [
            (0.5, -0.5),  # top-left
            (1.5, -0.5),  # top-right
            (1.5, -1.5),  # bottom-right
            (0.5, -1.5),  # bottom-left
        ]
        assert coords == expected

    def test_fractional_coverage(self) -> None:
        """Test when width/height don't divide evenly by FOV."""
        grid = GridWidthHeight(
            width=2.5,
            height=1.5,  # Not evenly divisible by FOV
            relative_to=RelativeTo.center,
            fov_width=1,
            fov_height=1,
        )

        positions = list(grid)

        # Should need ceil(2.5/1) x ceil(1.5/1) = 3x2 = 6 positions
        assert len(positions) == 6


class TestRandomPoints:
    """Test random point generation."""

    def test_fixed_seed_ellipse(self) -> None:
        """Test random points in ellipse with fixed seed."""
        grid = RandomPoints(
            num_points=5,
            max_width=10,
            max_height=6,
            shape=Shape.ELLIPSE,
            random_seed=42,  # Fixed seed for reproducible results
        )

        positions = list(grid)
        assert len(positions) == 5
        assert len(grid) == 5

        # All should be relative positions
        assert all(p.is_relative for p in positions)

        # Points should be within the ellipse bounds
        for pos in positions:
            # Ellipse equation: (x/(w/2))^2 + (y/(h/2))^2 <= 1
            ellipse_val = (pos.x / 5) ** 2 + (pos.y / 3) ** 2
            assert ellipse_val <= 1.01  # Small tolerance for floating point

    def test_fixed_seed_rectangle(self) -> None:
        """Test random points in rectangle with fixed seed."""
        grid = RandomPoints(
            num_points=4,
            max_width=8,
            max_height=4,
            shape=Shape.RECTANGLE,
            random_seed=123,
        )

        positions = list(grid)
        assert len(positions) == 4

        # Points should be within rectangle bounds
        for pos in positions:
            assert -4 <= pos.x <= 4  # max_width/2 = 4
            assert -2 <= pos.y <= 2  # max_height/2 = 2

    def test_no_overlap_prevention(self) -> None:
        """Test non-overlapping point generation."""
        grid = RandomPoints(
            num_points=3,
            max_width=10,
            max_height=10,
            shape=Shape.RECTANGLE,
            fov_width=2,
            fov_height=2,
            allow_overlap=False,
            random_seed=456,
        )

        positions = list(grid)

        # Should get some positions (exact number depends on random generation)
        assert len(positions) >= 1

        # Check that positions don't overlap (2 micron spacing required)
        coords = [(p.x, p.y) for p in positions]
        for i, (x1, y1) in enumerate(coords):
            for j, (x2, y2) in enumerate(coords):
                if i != j:
                    # Should be at least fov_width and fov_height apart
                    assert abs(x1 - x2) >= 2 or abs(y1 - y2) >= 2

    def test_traversal_ordering(self) -> None:
        """Test that traversal ordering affects point order."""
        # Create two identical grids with different ordering
        grid1 = RandomPoints(
            num_points=5,
            random_seed=789,
            order=None,  # No ordering
        )

        grid2 = RandomPoints(
            num_points=5,
            random_seed=789,
            order=TraversalOrder.TWO_OPT,  # With ordering
        )

        positions1 = list(grid1)
        positions2 = list(grid2)

        # Should have same number of points
        assert len(positions1) == len(positions2) == 5

        # Coordinates might be different due to ordering
        coords1 = [(p.x, p.y) for p in positions1]
        coords2 = [(p.x, p.y) for p in positions2]

        # The sets of coordinates should be the same, but order might differ
        assert set(coords1) == set(coords2)


class TestTraversalModes:
    """Test different traversal modes work across grid types."""

    def test_row_wise_vs_column_wise(self) -> None:
        """Compare row-wise vs column-wise traversal."""
        GridRowsColumns(rows=2, columns=3, fov_width=1, fov_height=1)

        # Row-wise snake (default)
        grid_row = GridRowsColumns(
            rows=2, columns=3, mode=OrderMode.row_wise_snake, fov_width=1, fov_height=1
        )

        # Column-wise snake
        grid_col = GridRowsColumns(
            rows=2,
            columns=3,
            mode=OrderMode.column_wise_snake,
            fov_width=1,
            fov_height=1,
        )

        positions_row = list(grid_row)
        positions_col = list(grid_col)

        # Should have same number of positions
        assert len(positions_row) == len(positions_col) == 6

        # But different ordering
        coords_row = [(p.x, p.y) for p in positions_row]
        coords_col = [(p.x, p.y) for p in positions_col]

        # First position should be the same (top-left)
        assert coords_row[0] == coords_col[0]

        # But second position should be different
        assert coords_row[1] != coords_col[1]


def test_position_naming() -> None:
    """Test that positions get proper names."""
    grid = GridRowsColumns(rows=2, columns=2, fov_width=1, fov_height=1)
    positions = list(grid)

    names = [p.name for p in positions]
    expected_names = ["0000", "0001", "0002", "0003"]
    assert names == expected_names


if __name__ == "__main__":
    # Simple way to run tests manually
    pytest.main([__file__, "-v"])
