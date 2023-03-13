from useq import MDASequence


# test channels
def test_channel_only_in_position_sub_sequence():
    # test that a sub-position with a sequence has a channel, but not the main sequence
    mda = MDASequence(
        stage_positions=[
            {},
            {"sequence": {"channels": [{"config": "488", "exposure": 100}]}},
        ],
    )

    p0, p1 = list(mda)
    assert p0.channel is None
    assert p1.channel.config == "488"
    assert p0.index == {"p": 0}
    assert p1.index == {"p": 1, "c": 0}
    assert p0.exposure is None
    assert p1.exposure == 100.0


def test_channel_in_main_and_position_sub_sequence():
    # test that a sub-position that specifies channel, overrides the global channel
    mda = MDASequence(
        stage_positions=[
            {},
            {"sequence": {"channels": [{"config": "488", "exposure": 100}]}},
        ],
        channels=[{"config": "Cy5", "exposure": 50}],
    )

    p0, p1 = list(mda)
    assert p0.channel.config == "Cy5"
    assert p1.channel.config == "488"
    assert p0.index == {"p": 0, "c": 0}
    assert p1.index == {"p": 1, "c": 0}
    assert p0.exposure == 50.0
    assert p1.exposure == 100.0


def test_subchannel_inherits_global_channel():
    # test that a sub-positions inherit the global channel
    mda = MDASequence(
        stage_positions=[
            {},
            {"sequence": {"z_plan": {"top": 0, "bottom": 0, "step": 0.5}}},
        ],
        channels=[{"config": "Cy5", "exposure": 50}],
    )

    assert all(e.channel.config == "Cy5" for e in mda)


# test grid_plan
def test_grid_relative_with_multi_stage_positions():
    # test that stage positions inherit the global relative grid plan
    mda = MDASequence(
        stage_positions=[(0, 0), (10, 20)],
        grid_plan={"rows": 2, "columns": 2},
    )
    # fmt: off
    assert [(i.global_index, i.index,         i.x_pos, i.y_pos) for i in mda] == [
            (0,              {"p": 0, "g": 0}, -0.5,    0.5),
            (1,              {"p": 0, "g": 1}, 0.5,     0.5),
            (2,              {"p": 0, "g": 2}, 0.5,     -0.5),
            (3,              {"p": 0, "g": 3}, -0.5,    -0.5),
            (4,              {"p": 1, "g": 0}, 9.5,     20.5),
            (5,              {"p": 1, "g": 1}, 10.5,    20.5),
            (6,              {"p": 1, "g": 2}, 10.5,    19.5),
            (7,              {"p": 1, "g": 3}, 9.5,     19.5),
    ]
    # fmt: on


def test_grid_relative_only_in_position_sub_sequence():
    # test a relative grid plan in a single stage position sub-sequence
    mda = MDASequence(
        stage_positions=[
            (0, 0),
            {
                "name": "test",
                "x": 10,
                "y": 10,
                "sequence": {"grid_plan": {"rows": 2, "columns": 2}},
            },
        ],
    )

    assert [(i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos) for i in mda] == [
        (0, {"p": 0}, None, 0.0, 0.0),
        (1, {"p": 1, "g": 0}, "test", 9.5, 10.5),
        (2, {"p": 1, "g": 1}, "test", 10.5, 10.5),
        (3, {"p": 1, "g": 2}, "test", 10.5, 9.5),
        (4, {"p": 1, "g": 3}, "test", 9.5, 9.5),
    ]


def test_grid_absolute_only_in_position_sub_sequence():
    # test a relative grid plan in a single stage position sub-sequence
    mda = MDASequence(
        stage_positions=[
            (0, 0),
            {
                "name": "test",
                "x": 10,
                "y": 10,
                "sequence": {
                    "grid_plan": {"top": 1, "bottom": -1, "left": 0, "right": 0}
                },
            },
        ],
    )
    assert [(i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos) for i in mda] == [
        (0, {"p": 0}, None, 0.0, 0.0),
        (1, {"p": 1, "g": 0}, "test", 0.0, 1.0),
        (2, {"p": 1, "g": 1}, "test", 0.0, 0.0),
        (3, {"p": 1, "g": 2}, "test", 0.0, -1.0),
    ]


def test_grid_relative_in_main_and_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            (0, 0),
            {
                "name": "test",
                "x": 10,
                "y": 10,
                "sequence": {"grid_plan": {"rows": 2, "columns": 2}},
            },
        ],
        grid_plan={"rows": 2, "columns": 2},
    )
    assert [(i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos) for i in mda] == [
        (0, {"p": 0, "g": 0}, None, -0.5, 0.5),
        (1, {"p": 0, "g": 1}, None, 0.5, 0.5),
        (2, {"p": 0, "g": 2}, None, 0.5, -0.5),
        (3, {"p": 0, "g": 3}, None, -0.5, -0.5),
        (4, {"p": 1, "g": 0}, "test", 9.5, 10.5),
        (5, {"p": 1, "g": 1}, "test", 10.5, 10.5),
        (6, {"p": 1, "g": 2}, "test", 10.5, 9.5),
        (7, {"p": 1, "g": 3}, "test", 9.5, 9.5),
    ]


def test_grid_absolute_in_main_and_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            {},
            {
                "name": "test",
                "sequence": {
                    "grid_plan": {"top": 2, "bottom": -1, "left": 0, "right": 0}
                },
            },
        ],
        grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
    )
    assert [(i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos) for i in mda] == [
        (0, {"p": 0, "g": 0}, None, 0.0, 1.0),
        (1, {"p": 0, "g": 1}, None, 0.0, 0.0),
        (2, {"p": 0, "g": 2}, None, 0.0, -1.0),
        (3, {"p": 1, "g": 0}, "test", 0.0, 2.0),
        (4, {"p": 1, "g": 1}, "test", 0.0, 1.0),
        (5, {"p": 1, "g": 2}, "test", 0.0, 0.0),
        (6, {"p": 1, "g": 3}, "test", 0.0, -1.0),
    ]


def test_grid_absolute_in_main_and_grid_relative_in_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            {},
            {
                "name": "test",
                "x": 10,
                "y": 10,
                "sequence": {"grid_plan": {"rows": 2, "columns": 2}},
            },
        ],
        grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
    )
    assert [(i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos) for i in mda] == [
        (0, {"p": 0, "g": 0}, None, 0.0, 1.0),
        (1, {"p": 0, "g": 1}, None, 0.0, 0.0),
        (2, {"p": 0, "g": 2}, None, 0.0, -1.0),
        (3, {"p": 1, "g": 0}, "test", 9.5, 10.5),
        (4, {"p": 1, "g": 1}, "test", 10.5, 10.5),
        (5, {"p": 1, "g": 2}, "test", 10.5, 9.5),
        (6, {"p": 1, "g": 3}, "test", 9.5, 9.5),
    ]


def test_grid_relative_in_main_and_grid_absolute_in_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            (0, 0),
            {
                "name": "test",
                "sequence": {
                    "grid_plan": {"top": 1, "bottom": -1, "left": 0, "right": 0}
                },
            },
        ],
        grid_plan={"rows": 2, "columns": 2},
    )
    assert [(i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos) for i in mda] == [
        (0, {"p": 0, "g": 0}, None, -0.5, 0.5),
        (1, {"p": 0, "g": 1}, None, 0.5, 0.5),
        (2, {"p": 0, "g": 2}, None, 0.5, -0.5),
        (3, {"p": 0, "g": 3}, None, -0.5, -0.5),
        (4, {"p": 1, "g": 0}, "test", 0.0, 1.0),
        (5, {"p": 1, "g": 1}, "test", 0.0, 0.0),
        (6, {"p": 1, "g": 2}, "test", 0.0, -1.0),
    ]


def test_multi_g_in_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            {"sequence": {"grid_plan": {"rows": 1, "columns": 2}}},
            {"sequence": {"grid_plan": {"rows": 2, "columns": 2}}},
            {
                "sequence": {
                    "grid_plan": {"top": 1, "bottom": -1, "left": 0, "right": 0}
                }
            },
        ]
    )
    assert [(i.global_index, i.index, i.x_pos, i.y_pos) for i in mda] == [
        (0, {"p": 0, "g": 0}, -0.5, 0.0),
        (1, {"p": 0, "g": 1}, 0.5, 0.0),
        (2, {"p": 1, "g": 0}, -0.5, 0.5),
        (3, {"p": 1, "g": 1}, 0.5, 0.5),
        (4, {"p": 1, "g": 2}, 0.5, -0.5),
        (5, {"p": 1, "g": 3}, -0.5, -0.5),
        (6, {"p": 2, "g": 0}, 0.0, 1.0),
        (7, {"p": 2, "g": 1}, 0.0, 0.0),
        (8, {"p": 2, "g": 2}, 0.0, -1.0),
    ]


# test_z_plan
def test_z_relative_with_multi_stage_positions():
    mda = MDASequence(
        stage_positions=[(0, 0, 0), (10, 20, 10)], z_plan={"range": 2, "step": 1}
    )
    assert [(i.global_index, i.index, i.x_pos, i.y_pos, i.z_pos) for i in mda] == [
        (0, {"p": 0, "z": 0}, 0.0, 0.0, -1.0),
        (1, {"p": 0, "z": 1}, 0.0, 0.0, 0.0),
        (2, {"p": 0, "z": 2}, 0.0, 0.0, 1.0),
        (3, {"p": 1, "z": 0}, 10.0, 20.0, 9.0),
        (4, {"p": 1, "z": 1}, 10.0, 20.0, 10.0),
        (5, {"p": 1, "z": 2}, 10.0, 20.0, 11.0),
    ]


def test_z_absolute_with_multi_stage_positions():
    mda = MDASequence(
        stage_positions=[(0, 0), (10, 20)], z_plan={"top": 60, "bottom": 58, "step": 1}
    )
    assert [(i.global_index, i.index, i.x_pos, i.y_pos, i.z_pos) for i in mda] == [
        (0, {"p": 0, "z": 0}, 0.0, 0.0, 58.0),
        (1, {"p": 0, "z": 1}, 0.0, 0.0, 59.0),
        (2, {"p": 0, "z": 2}, 0.0, 0.0, 60.0),
        (3, {"p": 1, "z": 0}, 10.0, 20.0, 58.0),
        (4, {"p": 1, "z": 1}, 10.0, 20.0, 59.0),
        (5, {"p": 1, "z": 2}, 10.0, 20.0, 60.0),
    ]


def test_z_relative_only_in_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            (None, None, 0),
            {
                "name": "test",
                "z": 10,
                "sequence": {"z_plan": {"range": 2, "step": 1}},
            },
        ],
    )
    assert [(i.global_index, i.index, i.pos_name, i.z_pos) for i in mda] == [
        (0, {"p": 0}, None, 0.0),
        (1, {"p": 1, "z": 0}, "test", 9.0),
        (2, {"p": 1, "z": 1}, "test", 10.0),
        (3, {"p": 1, "z": 2}, "test", 11.0),
    ]


def test_z_absolute_only_in_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            (None, None, 0),
            {
                "name": "test",
                "sequence": {"z_plan": {"top": 60, "bottom": 58, "step": 1}},
            },
        ],
    )
    assert [(i.global_index, i.index, i.pos_name, i.z_pos) for i in mda] == [
        (0, {"p": 0}, None, 0.0),
        (1, {"p": 1, "z": 0}, "test", 58.0),
        (2, {"p": 1, "z": 1}, "test", 59.0),
        (3, {"p": 1, "z": 2}, "test", 60.0),
    ]


def test_z_relative_in_main_and_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            (None, None, 0),
            {
                "name": "test",
                "z": 10,
                "sequence": {"z_plan": {"range": 3, "step": 1}},
            },
        ],
        z_plan={"range": 2, "step": 1},
    )
    assert [(i.global_index, i.index, i.pos_name, i.z_pos) for i in mda] == [
        (0, {"p": 0, "z": 0}, None, -1.0),
        (1, {"p": 0, "z": 1}, None, 0.0),
        (2, {"p": 0, "z": 2}, None, 1.0),
        (3, {"p": 1, "z": 0}, "test", 8.5),
        (4, {"p": 1, "z": 1}, "test", 9.5),
        (5, {"p": 1, "z": 2}, "test", 10.5),
        (6, {"p": 1, "z": 3}, "test", 11.5),
    ]


def test_z_absolute_in_main_and_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            {},
            {
                "name": "test",
                "sequence": {"z_plan": {"top": 30, "bottom": 28, "step": 1}},
            },
        ],
        z_plan={"top": 60, "bottom": 58, "step": 1},
    )
    assert [(i.global_index, i.index, i.pos_name, i.z_pos) for i in mda] == [
        (0, {"p": 0, "z": 0}, None, 58.0),
        (1, {"p": 0, "z": 1}, None, 59.0),
        (2, {"p": 0, "z": 2}, None, 60.0),
        (3, {"p": 1, "z": 0}, "test", 28.0),
        (4, {"p": 1, "z": 1}, "test", 29.0),
        (5, {"p": 1, "z": 2}, "test", 30.0),
    ]


def test_z_absolute_in_main_and_z_relative_in_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            {},
            {"name": "test", "z": 10, "sequence": {"z_plan": {"range": 3, "step": 1}}},
        ],
        z_plan={"top": 60, "bottom": 58, "step": 1},
    )
    assert [(i.global_index, i.index, i.pos_name, i.z_pos) for i in mda] == [
        (0, {"p": 0, "z": 0}, None, 58.0),
        (1, {"p": 0, "z": 1}, None, 59.0),
        (2, {"p": 0, "z": 2}, None, 60.0),
        (3, {"p": 1, "z": 0}, "test", 8.5),
        (4, {"p": 1, "z": 1}, "test", 9.5),
        (5, {"p": 1, "z": 2}, "test", 10.5),
        (6, {"p": 1, "z": 3}, "test", 11.5),
    ]


def test_z_relative_in_main_and_z_absolute_in_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            (None, None, 0),
            {
                "name": "test",
                "sequence": {"z_plan": {"top": 60, "bottom": 58, "step": 1}},
            },
        ],
        z_plan={"range": 3, "step": 1},
    )
    assert [(i.global_index, i.index, i.pos_name, i.z_pos) for i in mda] == [
        (0, {"p": 0, "z": 0}, None, -1.5),
        (1, {"p": 0, "z": 1}, None, -0.5),
        (2, {"p": 0, "z": 2}, None, 0.5),
        (3, {"p": 0, "z": 3}, None, 1.5),
        (4, {"p": 1, "z": 0}, "test", 58.0),
        (5, {"p": 1, "z": 1}, "test", 59.0),
        (6, {"p": 1, "z": 2}, "test", 60.0),
    ]


def test_multi_z_in_position_sub_sequence():
    mda = MDASequence(
        stage_positions=[
            {"sequence": {"z_plan": {"top": 60, "bottom": 58, "step": 1}}},
            {"sequence": {"z_plan": {"range": 3, "step": 1}}},
            {"sequence": {"z_plan": {"top": 30, "bottom": 28, "step": 1}}},
        ],
    )

    assert [(i.global_index, i.index, i.z_pos) for i in mda] == [
        (0, {"p": 0, "z": 0}, 58.0),
        (1, {"p": 0, "z": 1}, 59.0),
        (2, {"p": 0, "z": 2}, 60.0),
        (3, {"p": 1, "z": 0}, -1.5),
        (4, {"p": 1, "z": 1}, -0.5),
        (5, {"p": 1, "z": 2}, 0.5),
        (6, {"p": 1, "z": 3}, 1.5),
        (7, {"p": 2, "z": 0}, 28.0),
        (8, {"p": 2, "z": 1}, 29.0),
        (9, {"p": 2, "z": 2}, 30.0),
    ]


# test time_plan
def test_t_with_multi_stage_positions() -> None:
    mda = MDASequence(
        stage_positions=[
            {},
            {},
        ],
        time_plan=[{"interval": 1, "loops": 2}],
    )
    assert [(i.global_index, i.index, i.min_start_time) for i in mda] == [
        (0, {"t": 0, "p": 0}, 0.0),
        (1, {"t": 0, "p": 1}, 0.0),
        (2, {"t": 1, "p": 0}, 1.0),
        (3, {"t": 1, "p": 1}, 1.0),
    ]


def test_t_only_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            {},
            {"sequence": {"time_plan": [{"interval": 1, "loops": 5}]}},
        ],
    )
    assert [(i.global_index, i.index, i.min_start_time) for i in mda] == [
        (0, {"p": 0}, None),
        (1, {"p": 1, "t": 0}, 0.0),
        (2, {"p": 1, "t": 1}, 1.0),
        (3, {"p": 1, "t": 2}, 2.0),
        (4, {"p": 1, "t": 3}, 3.0),
        (5, {"p": 1, "t": 4}, 4.0),
    ]


def test_t_in_main_and_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            {},
            {"sequence": {"time_plan": [{"interval": 1, "loops": 5}]}},
        ],
        time_plan=[{"interval": 1, "loops": 2}],
    )
    assert [(i.global_index, i.index, i.min_start_time) for i in mda] == [
        (0, {"t": 0, "p": 0}, 0.0),
        (1, {"t": 0, "p": 1}, 0.0),
        (2, {"t": 1, "p": 1}, 1.0),
        (3, {"t": 2, "p": 1}, 2.0),
        (4, {"t": 3, "p": 1}, 3.0),
        (5, {"t": 4, "p": 1}, 4.0),
        (6, {"t": 1, "p": 0}, 1.0),
        (7, {"t": 0, "p": 1}, 0.0),
        (8, {"t": 1, "p": 1}, 1.0),
        (9, {"t": 2, "p": 1}, 2.0),
        (10, {"t": 3, "p": 1}, 3.0),
        (11, {"t": 4, "p": 1}, 4.0),
    ]


def test_mix_cgz_axes():
    mda = MDASequence(
        axis_order="tpgcz",
        stage_positions=[
            (0, 0),
            {
                "name": "test",
                "x": 10,
                "y": 10,
                "z": 30,
                "sequence": {
                    "channels": [
                        {"config": "488", "exposure": 200},
                        {"config": "561", "exposure": 100},
                    ],
                    "grid_plan": {"rows": 2, "columns": 1},
                    "z_plan": {"range": 2, "step": 1},
                },
            },
        ],
        channels=[{"config": "Cy5", "exposure": 50}],
        z_plan={"top": 100, "bottom": 98, "step": 1},
        grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
    )
    assert [
        (
            i.global_index,
            i.index,
            i.pos_name,
            i.x_pos,
            i.y_pos,
            i.z_pos,
            i.channel.config,
            i.exposure,
        )
        for i in mda
    ] == [
        (0, {"p": 0, "g": 0, "c": 0, "z": 0}, None, 0.0, 1.0, 98.0, "Cy5", 50.0),
        (1, {"p": 0, "g": 0, "c": 0, "z": 1}, None, 0.0, 1.0, 99.0, "Cy5", 50.0),
        (2, {"p": 0, "g": 0, "c": 0, "z": 2}, None, 0.0, 1.0, 100.0, "Cy5", 50.0),
        (3, {"p": 0, "g": 1, "c": 0, "z": 0}, None, 0.0, 0.0, 98.0, "Cy5", 50.0),
        (4, {"p": 0, "g": 1, "c": 0, "z": 1}, None, 0.0, 0.0, 99.0, "Cy5", 50.0),
        (5, {"p": 0, "g": 1, "c": 0, "z": 2}, None, 0.0, 0.0, 100.0, "Cy5", 50.0),
        (6, {"p": 0, "g": 2, "c": 0, "z": 0}, None, 0.0, -1.0, 98.0, "Cy5", 50.0),
        (7, {"p": 0, "g": 2, "c": 0, "z": 1}, None, 0.0, -1.0, 99.0, "Cy5", 50.0),
        (8, {"p": 0, "g": 2, "c": 0, "z": 2}, None, 0.0, -1.0, 100.0, "Cy5", 50.0),
        (9, {"p": 1, "g": 0, "c": 0, "z": 0}, "test", 10.0, 10.5, 29.0, "488", 200.0),
        (10, {"p": 1, "g": 0, "c": 0, "z": 1}, "test", 10.0, 10.5, 30.0, "488", 200.0),
        (11, {"p": 1, "g": 0, "c": 0, "z": 2}, "test", 10.0, 10.5, 31.0, "488", 200.0),
        (12, {"p": 1, "g": 0, "c": 1, "z": 0}, "test", 10.0, 10.5, 29.0, "561", 100.0),
        (13, {"p": 1, "g": 0, "c": 1, "z": 1}, "test", 10.0, 10.5, 30.0, "561", 100.0),
        (14, {"p": 1, "g": 0, "c": 1, "z": 2}, "test", 10.0, 10.5, 31.0, "561", 100.0),
        (15, {"p": 1, "g": 1, "c": 0, "z": 0}, "test", 10.0, 9.5, 29.0, "488", 200.0),
        (16, {"p": 1, "g": 1, "c": 0, "z": 1}, "test", 10.0, 9.5, 30.0, "488", 200.0),
        (17, {"p": 1, "g": 1, "c": 0, "z": 2}, "test", 10.0, 9.5, 31.0, "488", 200.0),
        (18, {"p": 1, "g": 1, "c": 1, "z": 0}, "test", 10.0, 9.5, 29.0, "561", 100.0),
        (19, {"p": 1, "g": 1, "c": 1, "z": 1}, "test", 10.0, 9.5, 30.0, "561", 100.0),
        (20, {"p": 1, "g": 1, "c": 1, "z": 2}, "test", 10.0, 9.5, 31.0, "561", 100.0),
    ]


# axes order????
def test_order():
    mda = MDASequence(
        axis_order="tpgcz",
        stage_positions=[
            (None, None, 0),
            {
                "z": 50,
                "sequence": {
                    "axis_order": "tpgzc",
                    "channels": [
                        {"config": "488", "exposure": 200},
                        {"config": "561", "exposure": 200},
                    ],
                },
            },
        ],
        channels=[
            {"config": "FITC", "exposure": 50},
            {"config": "Cy5", "exposure": 50},
        ],
        z_plan={"range": 2, "step": 1},
    )

    assert [(i.global_index, i.index, i.z_pos, i.channel.config) for i in mda] == [
        (0, {"p": 0, "c": 0, "z": 0}, -1.0, "FITC"),
        (1, {"p": 0, "c": 0, "z": 1}, 0.0, "FITC"),
        (2, {"p": 0, "c": 0, "z": 2}, 1.0, "FITC"),
        (3, {"p": 0, "c": 1, "z": 0}, -1.0, "Cy5"),
        (4, {"p": 0, "c": 1, "z": 1}, 0.0, "Cy5"),
        (5, {"p": 0, "c": 1, "z": 2}, 1.0, "Cy5"),
        # might appear confusing at first, but the sub-position had no z plan to iterate
        # so, specifying a different axis_order for the subplan does not change the
        # order of the z positions (specified globally)
        (6, {"p": 1, "c": 0, "z": 0}, 49.0, "488"),
        (7, {"p": 1, "c": 1, "z": 0}, 49.0, "561"),
        (8, {"p": 1, "c": 0, "z": 1}, 50.0, "488"),
        (9, {"p": 1, "c": 1, "z": 1}, 50.0, "561"),
        (10, {"p": 1, "c": 0, "z": 2}, 51.0, "488"),
        (11, {"p": 1, "c": 1, "z": 2}, 51.0, "561"),
    ]


def test_channels_and_pos_grid_plan():
    # test that all channels are acquired for each grid position
    mda = MDASequence(
        axis_order="tpgcz",
        channels=[
            {"config": "Cy5", "exposure": 10},
            {"config": "FITC", "exposure": 10},
        ],
        stage_positions=[
            {
                "x": 0,
                "y": 0,
                "sequence": {"grid_plan": {"rows": 2, "columns": 1}},
            },
        ],
    )

    assert [
        (i.global_index, i.index, i.x_pos, i.y_pos, i.channel.config) for i in mda
    ] == [
        (0, {"p": 0, "c": 0, "g": 0}, 0.0, 0.5, "Cy5"),
        (1, {"p": 0, "c": 0, "g": 1}, 0.0, -0.5, "Cy5"),
        (2, {"p": 0, "c": 1, "g": 0}, 0.0, 0.5, "FITC"),
        (3, {"p": 0, "c": 1, "g": 1}, 0.0, -0.5, "FITC"),
    ]


def test_channels_and_pos_z_plan():
    # test that all channels are acquired for each z position
    mda = MDASequence(
        axis_order="tpgcz",
        channels=[
            {"config": "Cy5", "exposure": 10},
            {"config": "FITC", "exposure": 10},
        ],
        stage_positions=[
            {"x": 0, "y": 0, "z": 0, "sequence": {"z_plan": {"range": 2, "step": 1}}}
        ],
    )

    assert [(i.global_index, i.index, i.z_pos, i.channel.config) for i in mda] == [
        (0, {"p": 0, "c": 0, "z": 0}, -1.0, "Cy5"),
        (1, {"p": 0, "c": 0, "z": 1}, 0.0, "Cy5"),
        (2, {"p": 0, "c": 0, "z": 2}, 1.0, "Cy5"),
        (3, {"p": 0, "c": 1, "z": 0}, -1.0, "FITC"),
        (4, {"p": 0, "c": 1, "z": 1}, 0.0, "FITC"),
        (5, {"p": 0, "c": 1, "z": 2}, 1.0, "FITC"),
    ]


def test_channels_and_pos_time_plan():
    # test that all channels are acquired for each timepoint
    mda = MDASequence(
        axis_order="tpgcz",
        channels=[
            {"config": "Cy5", "exposure": 10},
            {"config": "FITC", "exposure": 10},
        ],
        stage_positions=[
            {"x": 0, "y": 0, "sequence": {"time_plan": [{"interval": 1, "loops": 3}]}},
        ],
    )

    assert [
        (i.global_index, i.index, i.min_start_time, i.channel.config) for i in mda
    ] == [
        (0, {"p": 0, "c": 0, "t": 0}, 0.0, "Cy5"),
        (1, {"p": 0, "c": 0, "t": 1}, 1.0, "Cy5"),
        (2, {"p": 0, "c": 0, "t": 2}, 2.0, "Cy5"),
        (3, {"p": 0, "c": 1, "t": 0}, 0.0, "FITC"),
        (4, {"p": 0, "c": 1, "t": 1}, 1.0, "FITC"),
        (5, {"p": 0, "c": 1, "t": 2}, 2.0, "FITC"),
    ]


def test_channels_and_pos_z_grid_and_time_plan():
    # test that all channels are acquired for each z and grid positions
    mda = MDASequence(
        axis_order="tpgcz",
        channels=[
            {"config": "Cy5", "exposure": 10},
            {"config": "FITC", "exposure": 10},
        ],
        stage_positions=[
            {
                "x": 0,
                "y": 0,
                "z": 0,
                "sequence": {
                    "z_plan": {"range": 2, "step": 1},
                    "grid_plan": {"rows": 2, "columns": 1},
                    "time_plan": [{"interval": 1, "loops": 2}],
                },
            }
        ],
    )

    chs = {i.channel.config for i in mda}
    assert chs == {"Cy5", "FITC"}
