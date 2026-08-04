# -*- coding: utf-8 -*-

"""
Tests for terrain/tanaka_contours.py - the illuminated-contour
generation pipeline.

Military Cartography Tools
"""

import os

from qgis.core import (
    QgsExpressionContext,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsRasterLayer,
    QgsRectangle,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import build_synthetic_sloped_dem, QgisTestCase

from MilitaryCartographyTools.core.coordinate_utils import WGS84
from MilitaryCartographyTools.terrain.tanaka_contours import (
    _apply_style,
    _band_min_max,
    _clip_and_reproject,
    _hypsometric_color,
    _light_vector,
    _segment_illumination,
    default_insert_position,
    generate_tanaka_contours,
    LAND_RAMP,
    MONOCHROME_LIT_GRAY,
    MONOCHROME_SHADOW_GRAY,
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
    a real DEM clip - whose local relief only spanned a
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


class TestMonochromeStyle(QgisTestCase):

    """
    _apply_style()'s monochrome=True mode - a plain grayscale blend
    driven by ILLUM instead of the R/G/B hypsometric fields, for the
    classic monochrome Tanaka look. Evaluates the actual data-defined
    QgsProperty against synthetic features rather than just
    string-matching the expression, so a change that keeps the same
    text but breaks evaluation wouldn't slip through silently.
    """

    def _styled_layer(self, monochrome):

        layer = QgsVectorLayer(
            "LineString?crs=EPSG:32737&field=ELEV:double&field=ILLUM:double"
            "&field=R:int&field=G:int&field=B:int",
            "test",
            "memory"
        )

        _apply_style(layer, 0.15, 0.6, monochrome=monochrome)

        return layer


    def _stroke_color_for(self, layer, illum):

        symbol_layer = layer.renderer().symbol().symbolLayer(0)

        prop = symbol_layer.dataDefinedProperties().property(
            QgsSymbolLayer.Property.StrokeColor
        )

        feature = QgsFeature(layer.fields())

        feature.setAttribute("ILLUM", illum)

        context = QgsExpressionContext()

        context.setFeature(feature)
        context.setFields(layer.fields())

        color, ok = prop.valueAsColor(context, QColor())

        self.assertTrue(ok)

        return color


    def test_shadowed_feature_is_dark_gray(self):

        layer = self._styled_layer(monochrome=True)

        color = self._stroke_color_for(layer, -1.0)

        self.assertEqual(
            (color.red(), color.green(), color.blue()),
            (MONOCHROME_SHADOW_GRAY,) * 3
        )


    def test_lit_feature_is_light_gray(self):

        layer = self._styled_layer(monochrome=True)

        color = self._stroke_color_for(layer, 1.0)

        self.assertEqual(
            (color.red(), color.green(), color.blue()),
            (MONOCHROME_LIT_GRAY,) * 3
        )


    def test_default_mode_is_not_monochrome(self):

        layer = self._styled_layer(monochrome=False)

        symbol_layer = layer.renderer().symbol().symbolLayer(0)

        expression = symbol_layer.dataDefinedProperties().property(
            QgsSymbolLayer.Property.StrokeColor
        ).expressionString()

        self.assertIn('"R"', expression)
        self.assertNotIn("color_mix_rgb", expression)


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
    "some contours came out". Located close to UTM zone 37S's own
    central meridian, matching the real DEM this pipeline was
    verified against during development.
    """

    def setUp(self):

        super().setUp()

        self._dem_path = build_synthetic_sloped_dem(width=40, height=40)


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


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

        # Colour is normalised against the clipped DEM's own raw
        # pixel min/max (not the drawn contour lines' own elevation
        # range, which is quantised to the interval and rarely
        # reaches the DEM's true extremes) - deliberately so a
        # hypsometric tint layer generated over the same DEM/extent
        # agrees on colour with these contours. Recompute that same
        # ground truth independently here (same clip pipeline the
        # real code path uses) rather than trusting the output's own
        # ELEV spread, so this test would actually catch a regression
        # back to the old, mismatched normalisation.
        clipped_dem = _clip_and_reproject(dem_layer, extent, WGS84)

        min_elev, max_elev = _band_min_max(clipped_dem)

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

        # The whole ramp should actually be exercised, not some
        # narrow slice of it (the original, monochromatic bug) -
        # the lowest- and highest-elevation segments should land
        # close to LAND_RAMP's first/last stops respectively, even
        # if not landing exactly on them (contour levels are
        # quantised to the interval, so they rarely touch the DEM's
        # true min/max exactly).
        lowest = min(output.getFeatures(), key=lambda f: f["ELEV"])
        highest = max(output.getFeatures(), key=lambda f: f["ELEV"])

        self.assertLess(
            (lowest["R"], lowest["G"], lowest["B"]),
            (highest["R"], highest["G"], highest["B"])
        )

        def channel_distance(color_a, color_b):
            return sum(
                abs(a - b) for a, b in zip(color_a, color_b)
            )

        lowest_color = (lowest["R"], lowest["G"], lowest["B"])
        highest_color = (highest["R"], highest["G"], highest["B"])

        # The lowest-elevation segment should sit closer to
        # LAND_RAMP's first stop than its last, and vice versa for
        # the highest - a relative check rather than a tight absolute
        # tolerance, since contour levels are quantised to the
        # interval and won't land exactly on the DEM's true min/max.
        self.assertLess(
            channel_distance(lowest_color, LAND_RAMP[0][1]),
            channel_distance(lowest_color, LAND_RAMP[-1][1])
        )

        self.assertLess(
            channel_distance(highest_color, LAND_RAMP[-1][1]),
            channel_distance(highest_color, LAND_RAMP[0][1])
        )

        # The slope rises eastward everywhere, so every contour's
        # uphill direction is east - with the default NW light
        # azimuth, that's the shadowed side, so illumination should
        # be consistently negative across the whole layer rather
        # than a random mix.
        self.assertTrue(
            all(value < 0 for value in illumination_values)
        )


    def test_output_layer_is_not_added_to_the_project(self):

        # generate_tanaka_contours() deliberately doesn't add its
        # result to the project - see terrain/_layer_utils.py's
        # module docstring for why (a real bug: generate() self-
        # inserting, then replace_named_layer() moving that same
        # layer to its remembered position, could make the layer
        # vanish in a live GUI session). Insertion is the dialog's
        # job - see tests/test_tanaka_dialog.py.
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

        self.assertTrue(
            output.isValid()
        )

        self.assertIsNone(
            QgsProject.instance().mapLayer(output.id())
        )


    def test_default_insert_position_places_it_at_the_top_of_the_tree(self):

        from qgis.core import QgsProject, QgsVectorLayer

        project = QgsProject.instance()

        existing = QgsVectorLayer("Point?crs=EPSG:4326", "Existing", "memory")
        project.addMapLayer(existing, False)
        project.layerTreeRoot().insertLayer(0, existing)

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

        project.addMapLayer(output, False)

        default_insert_position(project, output)

        root = project.layerTreeRoot()

        self.assertEqual(
            [c.name() for c in root.children()],
            [output.name(), "Existing"]
        )
