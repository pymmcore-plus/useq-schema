from typing import Any

import numpy as np
import pytest

import useq
from useq import _plate, _plate_registry


def test_plate_plan() -> None:
    pp = useq.WellPlatePlan(
        plate=96, a1_center_xy=(500, 200), rotation=5, selected_wells=np.s_[1:5:2, :6:3]
    )
    assert pp.plate.rows == 8
    assert pp.plate.columns == 12
    assert pp.plate.size == 96
    assert len(pp) == 4
    assert pp.selected_well_names == ["B1", "B4", "D1", "D4"]
    pos0 = next(iter(pp))
    assert isinstance(pos0, useq.Position)
    assert pos0 == pp[0]
    assert pos0.name == "B1"
    assert round(pos0.x, 2) == 1284.4  # first row, but rotataed slightly, µm
    assert round(pos0.y, 2) == -8765.75  # second column, µm

    js = pp.model_dump_json()

    pp2 = useq.WellPlatePlan.model_validate_json(js)
    assert pp2 == pp


def test_plate_plan_well_points() -> None:
    pp = useq.WellPlatePlan(
        plate=96,
        a1_center_xy=(500, 200),
        rotation="0.2rad",
        well_points_plan=useq.RandomPoints(num_points=10),
        selected_wells=slice(None),
    )
    assert len(pp) == 96 * 10

    pp2 = useq.WellPlatePlan(plate=96, a1_center_xy=(500, 200), selected_wells=None)
    assert len(pp2) == 0


def test_plate_plan_plot(monkeypatch: pytest.MonkeyPatch) -> None:
    mpl = pytest.importorskip("matplotlib.pyplot")
    monkeypatch.setattr(mpl, "show", lambda: None)
    pp = useq.WellPlatePlan(
        plate=96,
        a1_center_xy=(500, 200),
        rotation="4˚",
        selected_wells=np.s_[1:5:2, :6:3],
    )
    pp.plot()
    pp2 = useq.WellPlatePlan(plate=1536, a1_center_xy=(500, 200))
    pp2.plot()

    pp3 = useq.WellPlatePlan(
        plate=96,
        a1_center_xy=(500, 200),
        well_points_plan=useq.RandomPoints(num_points=10, fov_height=0.85, fov_width=1),
    )
    pp3.plot()


def test_plate_errors() -> None:
    useq.WellPlatePlan(plate=12, a1_center_xy=(0, 0), selected_wells=[(0, 0), (1, 2)])
    with pytest.raises(ValueError, match="Invalid well selection"):
        useq.WellPlatePlan(
            plate=12, a1_center_xy=(0, 0), selected_wells=[(0, 0), (100, 100)]
        )


def test_custom_plate(monkeypatch: pytest.MonkeyPatch) -> None:
    plates: dict = {}
    monkeypatch.setattr(_plate_registry, "_PLATE_REGISTRY", plates)
    monkeypatch.setattr(_plate, "_PLATE_REGISTRY", plates)

    useq.register_well_plates(
        {
            "silly": useq.WellPlate(
                rows=1, columns=1, well_spacing=1, circular_wells=False, well_size=1
            )
        },
        myplate={"rows": 8, "columns": 8, "well_spacing": 9, "well_size": 10},
    )
    assert "myplate" in plates
    assert "silly" in useq.registered_well_plate_keys()

    with pytest.raises(ValueError, match="Unknown plate name"):
        useq.WellPlatePlan(plate="bad", a1_center_xy=(0, 0))

    pp = useq.WellPlatePlan(plate="silly", a1_center_xy=(0, 0))
    assert pp.plate.rows == 1
    assert not pp.plate.circular_wells
    pp = useq.WellPlatePlan(plate="myplate", a1_center_xy=(0, 0))
    assert pp.plate.rows == 8


def test_plate_plan_serialization() -> None:
    pp = useq.WellPlatePlan(
        plate=96,
        a1_center_xy=(500, 200),
        rotation=5,
        selected_wells=np.s_[1:5:2, :6:3],
        well_points_plan=useq.RandomPoints(num_points=10),
    )
    js = pp.model_dump_json()
    pp2 = useq.WellPlatePlan.model_validate_json(js)
    assert pp2 == pp


def test_plate_plan_position_order() -> None:
    pp = useq.WellPlatePlan(
        plate=96,
        a1_center_xy=(0, 0),
        rotation=0,
        selected_wells=np.s_[1:5:2, :6:3],
        well_points_plan=useq.RandomPoints(num_points=3),
    )
    # check that the positions are ordered grouped by well name
    # e.g. A1_0000, A1_0001, B1_0000, B1_0001, ... and not A1_0000, B1_0000, A1_0001, B1_0001
    names = [p.name.split("_")[0] for p in pp]
    for i in range(0, len(names), 3):
        chunk = names[i : i + 3]
        assert len(set(chunk)) == 1, f"Chunk {chunk} does not have the same elements"


def test_plate_plan_equality() -> None:
    """Various ways of selecting wells should result in the same plan."""
    pp = useq.WellPlatePlan(
        plate=96, a1_center_xy=(0, 0), selected_wells=np.s_[1:5:2, :6:3]
    )
    pp2 = useq.WellPlatePlan(
        plate="96-well",
        a1_center_xy=(0, 0),
        selected_wells=[(1, 1, 3, 3), (0, 3, 0, 3)],
    )
    pp3 = useq.WellPlatePlan.model_validate_json(pp.model_dump_json())

    assert pp == pp2 == pp3


def test_plate_repr() -> None:
    # both can be reduced
    pp = useq.WellPlatePlan(
        plate=96, a1_center_xy=(0, 0), selected_wells=np.s_[1:5, 3:12:2]
    )
    rpp = repr(pp)
    assert "selected_wells=(slice(1, 5), slice(3, 12, 2))" in rpp
    assert eval(rpp, vars(useq)) == pp  # noqa: S307

    # can't be reduced
    pp = useq.WellPlatePlan(
        plate=96, a1_center_xy=(0, 0), selected_wells=[(1, 1, 1, 2), (7, 3, 4, 2)]
    )
    rpp = repr(pp)
    assert "selected_wells=((1, 1, 1, 2), (7, 3, 4, 2))" in rpp
    assert eval(rpp, vars(useq)) == pp  # noqa: S307

    # one can be reduced
    pp = useq.WellPlatePlan(
        plate=96, a1_center_xy=(0, 0), selected_wells=np.s_[(1, 2, 2, 3), 1:5]
    )
    rpp = repr(pp)
    assert "selected_wells=((1, 2, 2, 3), slice(1, 5))" in rpp
    assert eval(rpp, vars(useq)) == pp  # noqa: S307

    pp = useq.WellPlatePlan(plate=96, a1_center_xy=(0, 0), selected_wells=np.s_[:, 1:2])
    rpp = repr(pp)
    assert "selected_wells=(slice(8), slice(1, 2))" in rpp
    assert eval(rpp, vars(useq)) == pp  # noqa: S307


@pytest.mark.parametrize(
    "pp",
    [
        useq.WellPlatePlan(
            plate=96,
            a1_center_xy=(500, 200),
            rotation=5,
            selected_wells=np.s_[1:5:2, :6:3],
        ),
        {
            "plate": 96,
            "a1_center_xy": (500, 200),
            "rotation": 5,
            "selected_wells": np.s_[1:5:2, :6:3],
        },
    ],
)
def test_plate_plan_in_seq(pp: Any) -> None:
    seq = useq.MDASequence(stage_positions=pp)
    assert isinstance(seq.stage_positions, useq.WellPlatePlan)
    assert seq.stage_positions.plate.size == 96


@pytest.mark.parametrize(
    "well_points_plan",
    [
        useq.RelativePosition(),
        useq.GridRowsColumns(rows=2, columns=2, fov_width=100, fov_height=100),
        useq.RandomPoints(num_points=3, max_width=1000, max_height=1000),
    ],
    ids=["RelativePosition", "GridRowsColumns", "RandomPoints"],
)
def test_plate_plan_positions_without_z(well_points_plan: Any) -> None:
    """The wells have no z, so the image positions must have no z (not z=0)."""
    pp = useq.WellPlatePlan(
        plate=96,
        a1_center_xy=(500, 200),
        selected_wells=np.s_[0:2, 0:2],
        well_points_plan=well_points_plan,
    )
    positions = list(pp)
    assert len(positions) == 4 * pp.num_points_per_well
    assert all(p.x is not None and p.y is not None for p in positions)
    assert all(p.z is None for p in positions)

    seq = useq.MDASequence(stage_positions=pp)
    assert isinstance(seq.stage_positions, useq.WellPlatePlan)
    assert all(e.z_pos is None for e in seq)


@pytest.mark.parametrize(
    "offset, expected_z",
    [
        (useq.RelativePosition(), 100),
        (useq.RelativePosition(x=10, z=2), 102),
    ],
)
def test_well_with_z_adds_offset_z(
    offset: useq.RelativePosition, expected_z: float
) -> None:
    pp = useq.WellPlatePlan(plate=96, a1_center_xy=(0, 0), selected_wells=([0], [0]))
    well = pp.selected_well_positions[0].model_copy(update={"z": 100})
    assert (well + offset).z == expected_z
