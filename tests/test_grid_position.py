# -*- coding: utf-8 -*-

"""
Tests for layout/grid_position.py's compute_grid_position() (which
tier - GZD mosaic, 100km mosaic, or single 100km square - applies to
a given map extent, and the footprint fraction describing where that
extent sits within whatever's shown) and grid_label_for_point() (the
real-grid-square name used for Map Sheet Series sheet naming).

Military Cartography Tools
"""

from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsRectangle

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.core.coordinate_utils import get_utm_crs_from_zone_band
from MilitaryCartographyTools.layout.grid_position import (
    compute_grid_position,
    grid_label_for_point,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestComputeGridPositionTiers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_a_small_extent_is_tier_3_a_single_square(self):

        extent = QgsRectangle(39.2080, -6.7926, 39.2090, -6.7916)

        result = compute_grid_position(extent, WGS84)

        self.assertEqual(result["tier"], 3)
        self.assertEqual(len(result["cells"]), 1)
        self.assertEqual(len(result["cells"][0]), 1)
        self.assertEqual(result["cells"][0][0]["label"], "EN")


    def test_an_extent_spanning_multiple_100km_squares_is_tier_2(self):

        extent = QgsRectangle(38.0, -8.0, 40.5, -5.5)

        result = compute_grid_position(extent, WGS84)

        self.assertEqual(result["tier"], 2)
        self.assertGreater(len(result["cells"]) * len(result["cells"][0]), 1)


    def test_an_extent_spanning_multiple_gzds_is_tier_1(self):

        # Deliberately crosses the zone 37/38 boundary at 42E.
        extent = QgsRectangle(41.0, -7.0, 43.0, -3.0)

        result = compute_grid_position(extent, WGS84)

        self.assertEqual(result["tier"], 1)

        labels = {
            cell["label"] for row in result["cells"] for cell in row
        }

        self.assertTrue(any(label.startswith("37") for label in labels))
        self.assertTrue(any(label.startswith("38") for label in labels))


    def test_row_0_is_the_northernmost_row_in_every_tier(self):

        tier1_extent = QgsRectangle(41.0, -7.0, 43.0, -3.0)
        tier1 = compute_grid_position(tier1_extent, WGS84)
        # Band letters increase northward, so row 0's label should
        # have a "later" band letter than the last row's.
        self.assertGreater(
            tier1["cells"][0][0]["label"][-1],
            tier1["cells"][-1][0]["label"][-1]
        )


class TestFootprintFraction(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.utm_crs = get_utm_crs_from_zone_band(37, "M")


    def test_an_extent_exactly_matching_one_square_fills_it_completely(self):

        exact_square = QgsRectangle(500000, 9200000, 600000, 9300000)

        result = compute_grid_position(exact_square, self.utm_crs)

        self.assertEqual(result["tier"], 3)

        left, top, right, bottom = result["footprint_fraction"]

        self.assertAlmostEqual(left, 0.0)
        self.assertAlmostEqual(top, 0.0)
        self.assertAlmostEqual(right, 1.0)
        self.assertAlmostEqual(bottom, 1.0)


    def test_a_centred_extent_is_centred_in_the_fraction(self):

        centred = QgsRectangle(520000, 9220000, 580000, 9280000)

        result = compute_grid_position(centred, self.utm_crs)

        left, top, right, bottom = result["footprint_fraction"]

        self.assertAlmostEqual(left, 0.2)
        self.assertAlmostEqual(top, 0.2)
        self.assertAlmostEqual(right, 0.8)
        self.assertAlmostEqual(bottom, 0.8)


class TestGridLabelForPoint(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_returns_gzd_and_100km_square(self):

        gzd, hundred_km_id = grid_label_for_point(-6.7924, 39.2083)

        self.assertEqual(gzd, "37M")
        self.assertEqual(hundred_km_id, "EN")
