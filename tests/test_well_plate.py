import numpy as np
import pytest

import useq
from useq import _plate


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
    assert round(pos0.x, 2) == 500.78  # first row, but rotataed slightly
    assert round(pos0.y, 2) == 208.97  # second column

    js = pp.model_dump_json()

    pp2 = useq.WellPlatePlan.model_validate_json(js)
    assert pp2 == pp


def test_plate_plan_well_points() -> None:
    pp = useq.WellPlatePlan(
        plate=96,
        a1_center_xy=(500, 200),
        rotation="0.2rad",
        well_points_plan=useq.RandomPoints(num_points=10),
    )
    assert len(pp) == 96 * 10


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
    monkeypatch.setattr(_plate, "_KNOWN_PLATES", plates)

    useq.register_well_plates(
        {
            "silly": useq.WellPlate(
                rows=1, columns=1, well_spacing=1, circular_wells=False
            )
        },
        myplate={"rows": 8, "columns": 8, "well_spacing": 9},
    )
    assert "myplate" in plates
    assert "silly" in useq.known_well_plate_keys()

    with pytest.raises(ValueError, match="Unknown plate name"):
        useq.WellPlatePlan(plate="bad", a1_center_xy=(0, 0))

    pp = useq.WellPlatePlan(plate="silly", a1_center_xy=(0, 0))
    assert pp.plate.rows == 1
    assert not pp.plate.circular_wells
    pp = useq.WellPlatePlan(plate="myplate", a1_center_xy=(0, 0))
    assert pp.plate.rows == 8
