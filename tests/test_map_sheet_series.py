# -*- coding: utf-8 -*-

"""
Tests for layout/map_sheet_series.py - the AO-tiling math
(compute_sheet_grid()), the real-grid-square-based sheet naming
(_assign_sheet_names()), and the generate_sheet_series()
orchestration that calls create_layout() once per sheet (each of
which gets its own grid position diagram automatically - see
tests/test_grid_position_diagram.py for that level).

Military Cartography Tools
"""

from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsRectangle

from .qgis_test_case import FakeIface, make_canvas, QgisTestCase

from MilitaryCartographyTools.layout.map_sheet_series import (
    _assign_sheet_names,
    compute_sheet_grid,
    generate_sheet_series,
    MAX_SHEETS,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestComputeSheetGrid(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_a_single_sheet_ao_produces_a_1x1_grid(self):

        # Dar es Salaam-ish, small enough to fit on one A4 landscape
        # sheet at 1:50,000.
        ao_extent = QgsRectangle(39.20, -6.80, 39.22, -6.78)

        grid = compute_sheet_grid(
            ao_extent,
            WGS84,
            width_mm=297.0,
            height_mm=210.0,
            scale=50000.0
        )

        self.assertEqual(len(grid), 1)
        self.assertEqual(len(grid[0]), 1)


    def test_a_larger_ao_produces_multiple_rows_and_columns(self):

        ao_extent = QgsRectangle(39.0, -7.0, 39.5, -6.5)

        grid = compute_sheet_grid(
            ao_extent,
            WGS84,
            width_mm=297.0,
            height_mm=210.0,
            scale=50000.0
        )

        self.assertGreater(len(grid), 1)
        self.assertGreater(len(grid[0]), 1)


    def test_row_0_is_the_northernmost_row(self):

        ao_extent = QgsRectangle(39.0, -7.0, 39.5, -6.5)

        grid = compute_sheet_grid(
            ao_extent,
            WGS84,
            width_mm=297.0,
            height_mm=210.0,
            scale=50000.0
        )

        top_row_lat = grid[0][0]["center_wgs84"].y()
        bottom_row_lat = grid[-1][0]["center_wgs84"].y()

        self.assertGreater(top_row_lat, bottom_row_lat)


    def test_col_0_is_the_westernmost_column(self):

        ao_extent = QgsRectangle(39.0, -7.0, 39.5, -6.5)

        grid = compute_sheet_grid(
            ao_extent,
            WGS84,
            width_mm=297.0,
            height_mm=210.0,
            scale=50000.0
        )

        left_col_lon = grid[0][0]["center_wgs84"].x()
        right_col_lon = grid[0][-1]["center_wgs84"].x()

        self.assertLess(left_col_lon, right_col_lon)


    def test_too_many_sheets_raises(self):

        # A huge AO (most of the globe) at a fine 1:1,000 scale -
        # each sheet only covers a small ground area at that scale,
        # so tiling the whole AO needs far more than MAX_SHEETS of
        # them.
        huge_ao = QgsRectangle(-170.0, -80.0, 170.0, 80.0)

        with self.assertRaises(ValueError):

            compute_sheet_grid(
                huge_ao,
                WGS84,
                width_mm=297.0,
                height_mm=210.0,
                scale=1000.0
            )


class TestAssignSheetNames(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _grid_with_wgs84_centers(self, *lonlats):

        from qgis.core import QgsPointXY

        return [
            [
                {"row": 0, "col": col, "center_wgs84": QgsPointXY(lon, lat)}
                for col, (lon, lat) in enumerate(lonlats)
            ]
        ]


    def test_names_use_the_real_gzd_and_100km_square(self):

        grid = self._grid_with_wgs84_centers((39.2083, -6.7924))

        _assign_sheet_names(grid)

        self.assertEqual(
            grid[0][0]["name"],
            "37M EN #1"
        )


    def test_sheets_in_different_100km_squares_each_start_at_1(self):

        # Two points far enough apart to fall in different 100km
        # squares (but still the same GZD).
        grid = self._grid_with_wgs84_centers(
            (39.2083, -6.7924),
            (39.9, -6.0),
        )

        _assign_sheet_names(grid)

        names = [sheet["name"] for sheet in grid[0]]

        self.assertTrue(all(name.endswith("#1") for name in names))
        self.assertNotEqual(names[0].rsplit(" #", 1)[0], names[1].rsplit(" #", 1)[0])


    def test_sheets_sharing_a_100km_square_get_sequential_numbers(self):

        # Two points close enough together to land in the same
        # 100km square.
        grid = self._grid_with_wgs84_centers(
            (39.2083, -6.7924),
            (39.2090, -6.7920),
        )

        _assign_sheet_names(grid)

        base_names = {
            sheet["name"].rsplit(" #", 1)[0] for sheet in grid[0]
        }

        self.assertEqual(len(base_names), 1)

        sequence_numbers = sorted(
            int(sheet["name"].rsplit(" #", 1)[1]) for sheet in grid[0]
        )

        self.assertEqual(sequence_numbers, [1, 2])


class TestGenerateSheetSeries(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.canvas = make_canvas()

        self.canvas.setExtent(
            QgsRectangle(39.0, -7.0, 39.2, -6.8)
        )

        self.iface = FakeIface(canvas=self.canvas)


    def test_creates_one_layout_per_sheet(self):

        layouts = generate_sheet_series(
            self.iface,
            self.canvas.extent(),
            WGS84,
            width_mm=297.0,
            height_mm=210.0,
            scale=100000.0
        )

        manager = QgsProject.instance().layoutManager()

        self.assertEqual(
            len(manager.layouts()),
            len(layouts)
        )

        self.assertGreater(len(layouts), 0)


    def test_layouts_are_named_with_a_sheet_prefix(self):

        layouts = generate_sheet_series(
            self.iface,
            self.canvas.extent(),
            WGS84,
            width_mm=297.0,
            height_mm=210.0,
            scale=100000.0
        )

        for layout in layouts:

            self.assertTrue(
                layout.name().startswith("Sheet ")
            )


    def test_does_not_open_any_layout_designer_windows(self):

        # Batch-generating potentially many sheets shouldn't flood
        # the user with that many open Designer windows.
        generate_sheet_series(
            self.iface,
            self.canvas.extent(),
            WGS84,
            width_mm=297.0,
            height_mm=210.0,
            scale=100000.0
        )

        self.assertEqual(
            len(self.iface.opened_layouts),
            0
        )


    def test_each_layout_has_a_grid_position_diagram(self):

        layouts = generate_sheet_series(
            self.iface,
            self.canvas.extent(),
            WGS84,
            width_mm=297.0,
            height_mm=210.0,
            scale=100000.0
        )

        for layout in layouts:

            matching = [
                item for item in layout.items()
                if hasattr(item, "id")
                and item.id()
                and item.id().startswith("mct_grid_position")
            ]

            self.assertGreater(len(matching), 0)
