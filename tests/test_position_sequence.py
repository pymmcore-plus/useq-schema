from useq import MDASequence

# def test_position_sequence_channels() -> None:
#     mda = MDASequence(
#         axis_order="tpgcz",
#         stage_positions=[
#             (10, 20, 0),
#             {
#                 "name": "test",
#                 "x": 10,
#                 "y": 20,
#                 "z": 50,
#                 "sequence": {"channels": [{"config": "DAPI", "exposure": 200}]},
#             },
#             {
#                 "name": "test_1",
#                 "x": 30,
#                 "y": 0,
#                 "z": 20,
#                 "sequence": {
#                     "channels": [
#                         {"config": "DAPI", "exposure": 100},
#                         {"config": "Cy3", "exposure": 80},
#                     ]
#                 },
#             },
#         ],
#         channels=[
#             {"config": "Cy5", "exposure": 50},
#             {"config": "FITC", "exposure": 100.0},
#         ],
#     )

#     assert [
#         (i.global_index, i.index, i.channel.config, i.exposure)
#         for i in mda.iter_events()
#     ] == [
#         (0, {"p": 0, "c": 0}, "Cy5", 50.0),
#         (1, {"p": 0, "c": 1}, "FITC", 100.0),
#         (2, {"p": 1, "c": 0}, "DAPI", 200.0),
#         (3, {"p": 2, "c": 0}, "DAPI", 100.0),
#         (4, {"p": 2, "c": 1}, "Cy3", 80.0),
#     ]


# def test_position_sequence_zplan() -> None:
#     mda = MDASequence(
#         axis_order="tpgcz",
#         stage_positions=[
#             (10, 20, 0),
#             {
#                 "name": "test",
#                 "x": 10,
#                 "y": 20,
#                 "z": 50,
#                 "sequence": {"z_plan": {"top": 60, "bottom": 55, "step": 1}},
#             },
#             {
#                 "name": "test_1",
#                 "x": 100,
#                 "y": 150,
#                 "z": 30,
#                 "sequence": {"z_plan": {"top": 20, "bottom": 16, "step": 1}},
#             },
#             {
#                 "x": 200,
#                 "y": 50,
#                 "z": 20,
#                 "sequence": {"z_plan": {"range": 2.0, "step": 0.5}},
#             },
#         ],
#         channels=[{"config": "Cy5", "exposure": 50}],
#         z_plan={"range": 1.0, "step": 0.5},
#     )

#     assert [
#         (i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos, i.z_pos)
#         for i in mda.iter_events()
#     ] == [
#         (0, {"p": 0, "c": 0, "z": 0}, None, 10.0, 20.0, -0.5),
#         (1, {"p": 0, "c": 0, "z": 1}, None, 10.0, 20.0, 0.0),
#         (2, {"p": 0, "c": 0, "z": 2}, None, 10.0, 20.0, 0.5),

#         (3, {"p": 1, "c": 0, "z": 0}, "test", 10.0, 20.0, 55.0),
#         (4, {"p": 1, "c": 0, "z": 1}, "test", 10.0, 20.0, 56.0),
#         (5, {"p": 1, "c": 0, "z": 2}, "test", 10.0, 20.0, 57.0),
#         (6, {"p": 1, "c": 0, "z": 3}, "test", 10.0, 20.0, 58.0),
#         (7, {"p": 1, "c": 0, "z": 4}, "test", 10.0, 20.0, 59.0),
#         (8, {"p": 1, "c": 0, "z": 5}, "test", 10.0, 20.0, 60.0),

#         (9, {"p": 2, "c": 0, "z": 0}, "test_1", 100.0, 150.0, 16.0),
#         (10, {"p": 2, "c": 0, "z": 1}, "test_1", 100.0, 150.0, 17.0),
#         (11, {"p": 2, "c": 0, "z": 2}, "test_1", 100.0, 150.0, 18.0),
#         (12, {"p": 2, "c": 0, "z": 3}, "test_1", 100.0, 150.0, 19.0),
#         (13, {"p": 2, "c": 0, "z": 4}, "test_1", 100.0, 150.0, 20.0),

#         (14, {"p": 3, "c": 0, "z": 0}, None, 200.0, 50.0, 18.5),
#         (15, {"p": 3, "c": 0, "z": 1}, None, 200.0, 50.0, 19.0),
#         (16, {"p": 3, "c": 0, "z": 2}, None, 200.0, 50.0, 19.5),
#         (17, {"p": 3, "c": 0, "z": 3}, None, 200.0, 50.0, 20.0),
#         (18, {"p": 3, "c": 0, "z": 4}, None, 200.0, 50.0, 20.5),
#     ]


# def test_position_sequence_gridplan() -> None:
#     mda = MDASequence(
#         axis_order="tpgcz",
#         stage_positions=[
#             (10, 20, 0),
#             {
#                 "name": "test",
#                 "x": 10,
#                 "y": 20,
#                 "z": 50,
#                 "sequence": {"grid_plan": {"rows": 2, "columns": 2}},
#             },
#             {
#                 "name": "test_1",
#                 "x": 10,
#                 "y": 20,
#                 "z": 50,
#                 "sequence": {
#                     "grid_plan": {"top": 1, "bottom": -1, "left": 0, "right": 0}
#                 },
#             },
#         ],
#         channels=[{"config": "Cy5", "exposure": 50}],
#         grid_plan={"rows": 1, "columns": 2},
#     )

#     # assert [
#     #     (i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos, i.z_pos)
#     #     for i in mda.iter_events()
#     # ] == [
#     #     (0, {"p": 0, "g": 0, "c": 0}, None, 9.5, 20.0, 0.0),
#     #     (1, {"p": 0, "g": 1, "c": 0}, None, 10.5, 20.0, 0.0),
#     #     (2, {"p": 1, "g": 0, "c": 0}, "test", 9.0, 20.5, 50.0),
#     #     (3, {"p": 1, "g": 1, "c": 0}, "test", 10.0, 20.5, 50.0),
#     #     (4, {"p": 1, "g": 2, "c": 0}, "test", 10.0, 19.5, 50.0),
#     #     (5, {"p": 1, "g": 3, "c": 0}, "test", 9.0, 19.5, 50.0),
#     #     (6, {"p": 2, "g": 0, "c": 0}, "test_1", 9.5, 20.0, 50.0),
#     #     (7, {"p": 2, "g": 1, "c": 0}, "test_1", 9.5, 20.0, 50.0),
#     #     (8, {"p": 2, "g": 2, "c": 0}, "test_1", 9.5, 20.0, 50.0),
#     # ]

#     print(" ")
#     for p in  [
#         (i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos, i.z_pos, i.channel.config)
#         for i in mda.iter_events()
#     ]:
#         print(p)


# # def test_position_sequence_g_and_z():
# #     mda = MDASequence(
# #         axis_order="tpgcz",
# #         stage_positions=[
# #             (10, 20, 0),
# #             {
# #                 "name": "test",
# #                 "x": 10,
# #                 "y": 20,
# #                 "z": 50,
# #                 "sequence": {"grid_plan": {"rows": 2, "columns": 1}},
# #             },
# #         ],
# #         channels=[{"config": "Cy5", "exposure": 50}],
# #         z_plan={"range": 3, "step": 1},
#     # )

#     # assert [
#     #     (i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos, i.z_pos)
#     #     for i in mda.iter_events()
#     # ] == [
#     #     (0, {'p': 0, 'c': 0, 'z': 0}, None, 10.0, 20.0, -1.5),
#     #     (1, {'p': 0, 'c': 0, 'z': 1}, None, 10.0, 20.0, -0.5),
#     #     (2, {'p': 0, 'c': 0, 'z': 2}, None, 10.0, 20.0, 0.5),
#     #     (3, {'p': 0, 'c': 0, 'z': 3}, None, 10.0, 20.0, 1.5),
#     #     (4, {'p': 1, 'c': 0, 'z': 0, 'g': 0}, 'test', 10.0, 20.5, 47.0),
#     #     (5, {'p': 1, 'c': 0, 'z': 1, 'g': 0}, 'test', 10.0, 20.5, 48.0),
#     #     (6, {'p': 1, 'c': 0, 'z': 2, 'g': 0}, 'test', 10.0, 20.5, 49.0),
#     #     (7, {'p': 1, 'c': 0, 'z': 3, 'g': 0}, 'test', 10.0, 20.5, 50.0),
#     #     (8, {'p': 1, 'c': 0, 'z': 0, 'g': 1}, 'test', 10.0, 19.5, 47.0),
#     #     (9, {'p': 1, 'c': 0, 'z': 1, 'g': 1}, 'test', 10.0, 19.5, 48.0),
#     #     (10, {'p': 1, 'c': 0, 'z': 2, 'g': 1}, 'test', 10.0, 19.5, 49.0),
#     #     (11, {'p': 1, 'c': 0, 'z': 3, 'g': 1}, 'test', 10.0, 19.5, 50.0)
#     # ]

#     # for p in  [
#     #     (i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos, i.z_pos)
#     #     for i in mda.iter_events()
#     # ]:
#     #     print(p)


# def test_position_sequence_time() -> None:
#     mda = MDASequence(
#         axis_order="tpgcz",
#         stage_positions=[
#             (10, 20, 0),
#             {
#                 "name": "test",
#                 "x": 10,
#                 "y": 20,
#                 "z": 50,
#                 "sequence": {"time_plan": [{"interval": 1, "loops": 5}]},
#             },
#         ],
#         channels=[{"config": "Cy5", "exposure": 50}],
#         time_plan=[{"interval": 1, "loops": 2}],
#     )

#     assert [(i.global_index, i.index, i.min_start_time) for i in mda.iter_events()] == [
#         (0, {"t": 0, "p": 0, "c": 0}, 0.0),
#         (1, {"t": 0, "p": 1, "c": 0}, 0.0),
#         (2, {"t": 1, "p": 1, "c": 0}, 1.0),
#         (3, {"t": 2, "p": 1, "c": 0}, 2.0),
#         (4, {"t": 3, "p": 1, "c": 0}, 3.0),
#         (5, {"t": 4, "p": 1, "c": 0}, 4.0),
#         (6, {"t": 1, "p": 0, "c": 0}, 1.0),
#         (7, {"t": 0, "p": 1, "c": 0}, 0.0),
#         (8, {"t": 1, "p": 1, "c": 0}, 1.0),
#         (9, {"t": 2, "p": 1, "c": 0}, 2.0),
#         (10, {"t": 3, "p": 1, "c": 0}, 3.0),
#         (11, {"t": 4, "p": 1, "c": 0}, 4.0),
#     ]


# def test_position_sequence_warning():
#     mda = MDASequence(
#         axis_order="tpgcz",
#         stage_positions=[
#             {
#                 "name": "test",
#                 "x": 10,
#                 "y": 20,
#                 "z": 50,
#                 "sequence": {"stage_positions": [(50, 60, 3), (70, 80, 8)]},
#             },
#         ],
#         channels=[
#             {"config": "Cy5", "exposure": 50},
#         ],
#     )

#     warning_string = (
#         "Currently, 'Position' sequence cannot have a 'stage_positons' "
#         "argument and it will be ignored."
#     )
#     with pytest.warns(UserWarning, match=warning_string):
#         assert [
#             (i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos, i.z_pos)
#             for i in mda.iter_events()
#         ] == [(0, {"p": 0, "c": 0}, "test", 10.0, 20.0, 50.0)]


# g
g_mda1 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {"channels": [{"config": "488", "exposure": 200}]},
        },
    ],
    channels=[{"config": "Cy5", "exposure": 50}],
    grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
)

g_mda2 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {"channels": [{"config": "488", "exposure": 200}]},
        },
    ],
    channels=[{"config": "Cy5", "exposure": 50}],
    grid_plan={"rows": 2, "columns": 2},
)

g_mda3 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [{"config": "488", "exposure": 200}],
                "grid_plan": {"rows": 2, "columns": 2},
            },
        },
    ],
    channels=[{"config": "Cy5", "exposure": 50}],
    grid_plan={"rows": 2, "columns": 2},
)

g_mda4 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [{"config": "488", "exposure": 200}],
                "grid_plan": {"top": 2, "bottom": -1, "left": 0, "right": 0},
            },
        },
        {
            "name": "test",
            "x": 100,
            "y": 100,
            "z": 50,
            "sequence": {
                "channels": [{"config": "488", "exposure": 200}],
                "grid_plan": {"top": 1, "bottom": -1, "left": 0, "right": 0},
            },
        },
    ],
    channels=[{"config": "Cy5", "exposure": 50}],
    grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
)

g_mda5 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [{"config": "488", "exposure": 200}],
                "grid_plan": {"rows": 2, "columns": 1},
            },
        },
    ],
    channels=[{"config": "Cy5", "exposure": 50}],
    grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
)

mdas = [g_mda1, g_mda2, g_mda3, g_mda4, g_mda5]


# c
c_mda1 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                    {"config": "561", "exposure": 200},
                ],
            },
        },
    ],
    channels=[{"config": "Cy5", "exposure": 50}, {"config": "488", "exposure": 200}],
)

c_mda2 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                    {"config": "561", "exposure": 200},
                ],
            },
        },
    ],
)

c_mda3 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                    {"config": "561", "exposure": 200},
                ],
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    z_plan={"range": 2, "step": 1},
)

mdas.extend([c_mda1, c_mda2, c_mda3])


# z
z_mda1 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    z_plan={"range": 2, "step": 1},
)

z_mda2 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    z_plan={"top": 60, "bottom": 55, "step": 1},
)

z_mda3 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
                "z_plan": {"top": 60, "bottom": 55, "step": 1},
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
)

z_mda4 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
                "z_plan": {"range": 2, "step": 1},
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
)

z_mda5 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
                "z_plan": {"range": 2, "step": 1},
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    z_plan={"range": 2, "step": 1},
)

z_mda6 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 50,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
                "z_plan": {"top": 30, "bottom": 25, "step": 1},
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    z_plan={"top": 60, "bottom": 55, "step": 1},
)

z_mda7 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 30,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
                "z_plan": {"range": 2, "step": 1},
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    z_plan={"top": 60, "bottom": 55, "step": 1},
)

z_mda8 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 30,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
                "z_plan": {"top": 60, "bottom": 55, "step": 1},
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    z_plan={"range": 2, "step": 1},
)

mdas.extend([z_mda1, z_mda2, z_mda3, z_mda4, z_mda5, z_mda6, z_mda7, z_mda8])


zg_mda1 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 30,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
                "grid_plan": {"rows": 2, "columns": 1},
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    z_plan={"top": 100, "bottom": 96, "step": 1},
)
mdas.append(zg_mda1)

zg_mda2 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 30,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
                "grid_plan": {"top": 1, "bottom": -1, "left": 0, "right": 0},
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    z_plan={"range": 2, "step": 1},
)

mdas.append(zg_mda2)

zg_mda3 = MDASequence(
    axis_order="tpgcz",
    stage_positions=[
        (0, 0, 0),
        {
            "name": "test",
            "x": 10,
            "y": 10,
            "z": 30,
            "sequence": {
                "channels": [
                    {"config": "488", "exposure": 200},
                ],
                "z_plan": {"range": 2, "step": 1},
            },
        },
    ],
    channels=[
        {"config": "Cy5", "exposure": 50},
    ],
    grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
)

mdas.append(zg_mda3)


def test_all():
    for mda in mdas:
        print(" ")
        print("____________")
        print(mda.channels)
        print(mda.stage_positions)
        print(mda.z_plan)
        print(mda.grid_plan)
        for p in [
            (i.global_index, i.index, i.pos_name, i.x_pos, i.y_pos, i.z_pos, i.channel)
            for i in mda.iter_events()
        ]:
            print(p)
