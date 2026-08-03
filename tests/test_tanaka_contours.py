# -*- coding: utf-8 -*-

"""
Tests for terrain/tanaka_contours.py - the illuminated-contour
generation pipeline.

Military Cartography Tools
"""

import os
import tempfile

from qgis.core import QgsGeometry, QgsPointXY, QgsRasterLayer, QgsRectangle

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.core.coordinate_utils import WGS84
from MilitaryCartographyTools.terrain.tanaka_contours import (
    _hypsometric_color,
    _light_vector,
    _segment_illumination,
    generate_tanaka_contours,
    LAND_STOPS,
    SEA_LEVEL_STOPS,
)


class _FakeRasterProvider:

    """
    Stands in for a real QgsRasterDataProvider in
    _segment_illumination() tests - just enough to answer sample()
    from a caller-supplied function of (x, y), so the pure geometry/
    illumination math can be tested in isolation without needing an
    actual raster.
    """

    def __init__(self, elevation_at):
        self._elevation_at = elevation_at

    def sample(self, point, band):
        return self._elevation_at(point.x(), point.y()), True


class TestLightVector(QgisTestCase):

    def test_north_azimuth_points_north(self):

        x, y = _light_vector(0.0)

        self.assertAlmostEqual(x, 0.0, places=9)
        self.assertAlmostEqual(y, 1.0, places=9)


    def test_east_azimuth_points_east(self):

        x, y = _light_vector(90.0)

        self.assertAlmostEqual(x, 1.0, places=9)
        self.assertAlmostEqual(y, 0.0, places=9)


    def test_default_northwest_azimuth_points_northwest(self):

        x, y = _light_vector(315.0)

        self.assertLess(x, 0)
        self.assertGreater(y, 0)


class TestHypsometricColor(QgisTestCase):

    """
    _hypsometric_color() - the fixed blue-below-sea-level,
    green-through-white-above-it colour convention (SEA_LEVEL_STOPS/
    LAND_STOPS), keyed purely on a contour's own elevation.
    """

    def test_deep_ocean_matches_lowest_sea_stop(self):

        self.assertEqual(
            _hypsometric_color(-999999),
            SEA_LEVEL_STOPS[0][1]
        )


    def test_high_peak_matches_highest_land_stop(self):

        self.assertEqual(
            _hypsometric_color(999999),
            LAND_STOPS[-1][1]
        )


    def test_just_above_sea_level_uses_land_stops_not_sea_stops(self):

        # 0 itself is the boundary - LAND_STOPS (not SEA_LEVEL_STOPS)
        # owns it, per _hypsometric_color()'s "elevation < 0" test.
        self.assertEqual(
            _hypsometric_color(0.0),
            LAND_STOPS[0][1]
        )


    def test_just_below_sea_level_uses_sea_stops(self):

        self.assertEqual(
            _hypsometric_color(-0.5),
            SEA_LEVEL_STOPS[-1][1]
        )


    def test_interpolates_between_adjacent_land_stops(self):

        elev_a, color_a = LAND_STOPS[0]
        elev_b, color_b = LAND_STOPS[1]

        midpoint = (elev_a + elev_b) / 2

        red, green, blue = _hypsometric_color(midpoint)

        for channel, low, high in zip(
            (red, green, blue), color_a, color_b
        ):

            self.assertGreaterEqual(channel, min(low, high))
            self.assertLessEqual(channel, max(low, high))


    def test_coastline_is_a_hard_edge_not_a_blend(self):

        # A real hypsometric tint jumps at the coastline rather than
        # fading through it - colours right at 0 shouldn't sit
        # "between" the two tables.
        just_below = _hypsometric_color(-0.001)
        at_sea_level = _hypsometric_color(0.0)

        self.assertEqual(just_below, SEA_LEVEL_STOPS[-1][1])
        self.assertEqual(at_sea_level, LAND_STOPS[0][1])
        self.assertNotEqual(just_below, at_sea_level)


class TestSegmentIllumination(QgisTestCase):

    """
    A flat, east-west test segment over terrain that rises steadily
    northward (elevation == y) - its uphill direction is always
    (0, 1) regardless of which way the segment happens to be drawn,
    which makes the expected illumination for a given light azimuth
    exact rather than approximate.
    """

    def _segment(self, x1, y1, x2, y2):

        return QgsGeometry.fromPolylineXY(
            [QgsPointXY(x1, y1), QgsPointXY(x2, y2)]
        )


    def test_light_from_the_uphill_side_is_fully_lit(self):

        provider = _FakeRasterProvider(lambda x, y: y)

        segment = self._segment(0, 0, 10, 0)

        illumination = _segment_illumination(
            segment,
            provider,
            _light_vector(0.0)
        )

        self.assertAlmostEqual(illumination, 1.0, places=6)


    def test_light_from_the_downhill_side_is_fully_shadowed(self):

        provider = _FakeRasterProvider(lambda x, y: y)

        segment = self._segment(0, 0, 10, 0)

        illumination = _segment_illumination(
            segment,
            provider,
            _light_vector(180.0)
        )

        self.assertAlmostEqual(illumination, -1.0, places=6)


    def test_illumination_independent_of_segment_direction(self):

        # The same physical segment, drawn start-to-end the other
        # way around, must resolve the same uphill side - a
        # regression guard against accidentally depending on vertex
        # order rather than actual terrain.
        provider = _FakeRasterProvider(lambda x, y: y)

        forward = self._segment(0, 0, 10, 0)
        backward = self._segment(10, 0, 0, 0)

        light = _light_vector(45.0)

        self.assertAlmostEqual(
            _segment_illumination(forward, provider, light),
            _segment_illumination(backward, provider, light),
            places=6
        )


    def test_degenerate_geometry_returns_none(self):

        provider = _FakeRasterProvider(lambda x, y: 0)

        single_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0)]
        )

        self.assertIsNone(
            _segment_illumination(single_point, provider, _light_vector(0.0))
        )


class TestGenerateTanakaContoursIntegration(QgisTestCase):

    """
    End-to-end pipeline test against a small synthetic DEM with a
    known, simple slope (rises steadily eastward), so the expected
    illumination sign can be checked precisely rather than just
    "some contours came out". Located near Kilimanjaro, close to
    UTM zone 37S's own central meridian, matching the real DEM this
    pipeline was verified against during development.
    """

    def setUp(self):

        super().setUp()

        self._dem_path = self._build_synthetic_dem()


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def _build_synthetic_dem(self):

        import numpy
        from osgeo import gdal, osr

        width, height = 40, 40
        pixel_size = 0.0001

        origin_lon, origin_lat = 37.34, -3.09

        path = tempfile.mktemp(suffix=".tif")

        driver = gdal.GetDriverByName("GTiff")

        dataset = driver.Create(
            path, width, height, 1, gdal.GDT_Float32
        )

        dataset.SetGeoTransform(
            [origin_lon, pixel_size, 0, origin_lat, 0, -pixel_size]
        )

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        dataset.SetProjection(srs.ExportToWkt())

        # Elevation rises steadily eastward (with column) only - a
        # single, clean gradient direction so the expected uphill
        # side is unambiguous.
        band = numpy.fromfunction(
            lambda row, col: col * 10.0,
            (height, width),
            dtype="float32"
        )

        dataset.GetRasterBand(1).WriteArray(band)
        dataset.FlushCache()
        dataset = None

        return path


    def test_pipeline_produces_valid_segments(self):

        dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        self.assertTrue(
            dem_layer.isValid()
        )

        extent = QgsRectangle(
            37.3405, -3.0935,
            37.3435, -3.0905
        )

        output = generate_tanaka_contours(
            dem_layer,
            extent,
            WGS84,
            interval=20.0,
            segment_length=5.0
        )

        self.assertGreater(
            output.featureCount(),
            0
        )

        field_names = [f.name() for f in output.fields()]

        self.assertIn("ELEV", field_names)
        self.assertIn("ILLUM", field_names)
        self.assertIn("R", field_names)
        self.assertIn("G", field_names)
        self.assertIn("B", field_names)

        illumination_values = [
            f["ILLUM"] for f in output.getFeatures()
        ]

        for value in illumination_values:

            self.assertGreaterEqual(value, -1.0001)
            self.assertLessEqual(value, 1.0001)

        # The synthetic DEM's elevations (col * 10.0, 40 columns) are
        # all >= 0, so every segment's colour should come from
        # LAND_STOPS - each channel a valid 0-255 int, and matching
        # what _hypsometric_color() itself would produce for that
        # segment's own ELEV.
        for feature in output.getFeatures():

            expected = _hypsometric_color(feature["ELEV"])

            actual = (feature["R"], feature["G"], feature["B"])

            self.assertEqual(actual, expected)

            for channel in actual:

                self.assertGreaterEqual(channel, 0)
                self.assertLessEqual(channel, 255)

        # The slope rises eastward everywhere, so every contour's
        # uphill direction is east - with the default NW light
        # azimuth, that's the shadowed side, so illumination should
        # be consistently negative across the whole layer rather
        # than a random mix.
        self.assertTrue(
            all(value < 0 for value in illumination_values)
        )


    def test_output_layer_added_to_project(self):

        from qgis.core import QgsProject

        dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        extent = QgsRectangle(
            37.3405, -3.0935,
            37.3435, -3.0905
        )

        output = generate_tanaka_contours(
            dem_layer,
            extent,
            WGS84,
            interval=20.0,
            segment_length=5.0
        )

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(output.id())
        )
