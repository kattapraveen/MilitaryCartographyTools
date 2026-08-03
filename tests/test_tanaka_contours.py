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
    LAND_RAMP,
    SEA_RAMP,
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
    _hypsometric_color() - the blue-below-sea-level,
    green-through-white-above-it colour convention (SEA_RAMP/
    LAND_RAMP), normalised against each generation's own min/max
    elevation rather than a fixed global scale.

    The normalisation is the fix for a real complaint: a first
    version keyed straight off fixed absolute elevation anchors, and
    a real Tanzania DEM clip - whose local relief only spanned a
    few hundred metres, all within one narrow band of that global
    scale - came out almost entirely one shade of brown. Confirmed
    live against the user's own report before rewriting this.
    """

    def test_inland_dataset_reaches_both_ends_of_the_land_ramp(self):

        # No negative elevations anywhere in this generation's own
        # output (the common case - a single inland AOI), regardless
        # of how high up that range actually sits.
        self.assertEqual(
            _hypsometric_color(1200.0, min_elevation=1200.0, max_elevation=1400.0),
            LAND_RAMP[0][1]
        )

        self.assertEqual(
            _hypsometric_color(1400.0, min_elevation=1200.0, max_elevation=1400.0),
            LAND_RAMP[-1][1]
        )


    def test_coastal_dataset_still_anchors_land_and_sea_at_zero(self):

        # A real coastline present in this generation's own output -
        # land and sea are each normalised over their own side,
        # anchored at 0 rather than at this dataset's own min/max.
        self.assertEqual(
            _hypsometric_color(0.0, min_elevation=-500.0, max_elevation=1000.0),
            LAND_RAMP[0][1]
        )

        self.assertEqual(
            _hypsometric_color(1000.0, min_elevation=-500.0, max_elevation=1000.0),
            LAND_RAMP[-1][1]
        )

        self.assertEqual(
            _hypsometric_color(-500.0, min_elevation=-500.0, max_elevation=1000.0),
            SEA_RAMP[-1][1]
        )


    def test_out_of_range_elevation_clamps_rather_than_extrapolates(self):

        self.assertEqual(
            _hypsometric_color(-100.0, min_elevation=0.0, max_elevation=500.0),
            LAND_RAMP[0][1]
        )

        self.assertEqual(
            _hypsometric_color(9999.0, min_elevation=0.0, max_elevation=500.0),
            LAND_RAMP[-1][1]
        )


    def test_interpolates_between_adjacent_land_ramp_stops(self):

        fraction_a, color_a = LAND_RAMP[0]
        fraction_b, color_b = LAND_RAMP[1]

        midpoint_fraction = (fraction_a + fraction_b) / 2

        elevation = midpoint_fraction * 1000.0

        red, green, blue = _hypsometric_color(
            elevation, min_elevation=0.0, max_elevation=1000.0
        )

        for channel, low, high in zip(
            (red, green, blue), color_a, color_b
        ):

            self.assertGreaterEqual(channel, min(low, high))
            self.assertLessEqual(channel, max(low, high))


    def test_coastline_is_a_hard_edge_not_a_blend(self):

        # A real hypsometric tint jumps at the coastline rather than
        # fading through it - colours right at 0 shouldn't sit
        # "between" the two ramps.
        just_below = _hypsometric_color(-0.001, min_elevation=-1000.0, max_elevation=1000.0)
        at_sea_level = _hypsometric_color(0.0, min_elevation=-1000.0, max_elevation=1000.0)

        self.assertEqual(just_below, SEA_RAMP[0][1])
        self.assertEqual(at_sea_level, LAND_RAMP[0][1])
        self.assertNotEqual(just_below, at_sea_level)


    def test_flat_dataset_does_not_divide_by_zero(self):

        # min == max (every contour at the exact same elevation) -
        # must resolve deterministically rather than raising.
        self.assertEqual(
            _hypsometric_color(250.0, min_elevation=250.0, max_elevation=250.0),
            LAND_RAMP[0][1]
        )


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
        # LAND_RAMP, normalised against this output's own min/max
        # elevation - each channel a valid 0-255 int, and matching
        # what _hypsometric_color() itself would produce for that
        # segment's own ELEV against that same range.
        elev_values = [f["ELEV"] for f in output.getFeatures()]

        min_elev, max_elev = min(elev_values), max(elev_values)

        # A real colour spread requires an actual elevation range to
        # normalise against - guards against this test accidentally
        # passing vacuously if the synthetic DEM stopped varying.
        self.assertGreater(max_elev, min_elev)

        for feature in output.getFeatures():

            expected = _hypsometric_color(
                feature["ELEV"], min_elev, max_elev
            )

            actual = (feature["R"], feature["G"], feature["B"])

            self.assertEqual(actual, expected)

            for channel in actual:

                self.assertGreaterEqual(channel, 0)
                self.assertLessEqual(channel, 255)

        # The whole ramp should actually be exercised end to end -
        # the lowest-elevation segment should be tinted with
        # LAND_RAMP's first stop, the highest with its last, not
        # some narrow slice of it (the original, monochromatic bug).
        lowest = min(output.getFeatures(), key=lambda f: f["ELEV"])
        highest = max(output.getFeatures(), key=lambda f: f["ELEV"])

        self.assertEqual(
            (lowest["R"], lowest["G"], lowest["B"]),
            LAND_RAMP[0][1]
        )

        self.assertEqual(
            (highest["R"], highest["G"], highest["B"]),
            LAND_RAMP[-1][1]
        )

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
