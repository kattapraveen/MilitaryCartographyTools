# -*- coding: utf-8 -*-

"""
Tests for terrain/tanaka_contours.py - the illuminated-contour
generation pipeline.

Military Cartography Tools
"""

import os

from unittest.mock import patch

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
from qgis.PyQt.QtGui import QColor, QPainter

from .qgis_test_case import build_synthetic_cone_dem, build_synthetic_sloped_dem, QgisTestCase

from MilitaryCartographyTools.core.coordinate_utils import WGS84
from MilitaryCartographyTools.terrain.tanaka_contours import (
    _apply_style,
    _band_min_max,
    _build_output_layer,
    _clip_and_reproject,
    _generate_contour_segments,
    _hypsometric_color,
    _light_vector,
    _segment_illumination,
    _smooth_illumination,
    default_insert_position,
    generate_tanaka_contours,
    LAND_RAMP,
    MONOCHROME_LIT_GRAY,
    MONOCHROME_SHADOW_GRAY,
    SEA_RAMP,
    STYLE_ELEVATION_COLOR,
    STYLE_ILLUMINATED_OVERLAY,
    STYLE_MONOCHROME,
    UPHILL_SAMPLE_OFFSET_M,
    UPHILL_SAMPLE_OFFSET_PIXEL_MARGIN,
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


class _StyledLayerTestCase(QgisTestCase):

    """
    Shared helpers for exercising _apply_style()'s data-defined
    StrokeColor/StrokeWidth QgsProperty objects against synthetic
    features, rather than just string-matching the expression text -
    a change that keeps the same text but breaks evaluation wouldn't
    slip through silently this way.
    """

    def _styled_layer(self, style_mode):

        layer = QgsVectorLayer(
            "LineString?crs=EPSG:32737&field=ELEV:double&field=ILLUM:double"
            "&field=R:int&field=G:int&field=B:int",
            "test",
            "memory"
        )

        _apply_style(layer, 0.15, 0.6, style_mode=style_mode)

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


    def _stroke_width_for(self, layer, illum):

        symbol_layer = layer.renderer().symbol().symbolLayer(0)

        prop = symbol_layer.dataDefinedProperties().property(
            QgsSymbolLayer.Property.StrokeWidth
        )

        feature = QgsFeature(layer.fields())

        feature.setAttribute("ILLUM", illum)

        context = QgsExpressionContext()

        context.setFeature(feature)
        context.setFields(layer.fields())

        width, ok = prop.valueAsDouble(context, -1.0)

        self.assertTrue(ok)

        return width


class TestContourWidthFormula(_StyledLayerTestCase):

    """
    Regression coverage for a real bug found against the documented
    Tanaka convention (confirmed against Manifold's own docs and the
    anitagraser.com tutorial): width should be thick at BOTH extremes
    (a segment facing directly toward the light AND one facing
    directly away/shadowed) and thin only at the perpendicular/
    grazing case - a symmetric function of abs(ILLUM), not a plain
    linear ramp across the signed -1..1 range. The old linear formula
    made a fully-LIT segment the THINNEST line on the map, the
    opposite of every documented source - that's the case most worth
    guarding against regressing back to.
    """

    def test_perpendicular_illumination_is_thinnest(self):

        layer = self._styled_layer(STYLE_ELEVATION_COLOR)

        width = self._stroke_width_for(layer, 0.0)

        self.assertAlmostEqual(width, 0.15)


    def test_fully_lit_is_thickest_not_thinnest(self):

        layer = self._styled_layer(STYLE_ELEVATION_COLOR)

        width = self._stroke_width_for(layer, 1.0)

        self.assertAlmostEqual(width, 0.6)


    def test_fully_shadowed_is_thickest(self):

        layer = self._styled_layer(STYLE_ELEVATION_COLOR)

        width = self._stroke_width_for(layer, -1.0)

        self.assertAlmostEqual(width, 0.6)


class TestContourStyleModes(_StyledLayerTestCase):

    def test_shadowed_feature_is_dark_gray_in_monochrome(self):

        layer = self._styled_layer(STYLE_MONOCHROME)

        color = self._stroke_color_for(layer, -1.0)

        self.assertEqual(
            (color.red(), color.green(), color.blue()),
            (MONOCHROME_SHADOW_GRAY,) * 3
        )


    def test_lit_feature_is_light_gray_in_monochrome(self):

        layer = self._styled_layer(STYLE_MONOCHROME)

        color = self._stroke_color_for(layer, 1.0)

        self.assertEqual(
            (color.red(), color.green(), color.blue()),
            (MONOCHROME_LIT_GRAY,) * 3
        )


    def test_default_mode_uses_elevation_rgb_fields(self):

        layer = self._styled_layer(STYLE_ELEVATION_COLOR)

        symbol_layer = layer.renderer().symbol().symbolLayer(0)

        expression = symbol_layer.dataDefinedProperties().property(
            QgsSymbolLayer.Property.StrokeColor
        ).expressionString()

        self.assertIn('"R"', expression)
        self.assertNotIn("color_mix_rgb", expression)


    def test_shadowed_feature_is_pure_black_in_illuminated_overlay(self):

        layer = self._styled_layer(STYLE_ILLUMINATED_OVERLAY)

        color = self._stroke_color_for(layer, -1.0)

        self.assertEqual(
            (color.red(), color.green(), color.blue()),
            (0, 0, 0)
        )


    def test_lit_feature_is_pure_white_in_illuminated_overlay(self):

        layer = self._styled_layer(STYLE_ILLUMINATED_OVERLAY)

        color = self._stroke_color_for(layer, 1.0)

        self.assertEqual(
            (color.red(), color.green(), color.blue()),
            (255, 255, 255)
        )


    def test_illuminated_overlay_sets_soft_light_blend_mode_on_the_layer(self):

        # Soft Light, not Overlay - confirmed live against a real DEM
        # with densely-packed contour rings that Overlay's full
        # darken/lighten swing muddied shadowed peak colours into a
        # dark red/maroon instead of the clean highlights references
        # show; Soft Light's gentler effect keeps the tint's own hue
        # recognisable. See _apply_style()'s own docstring.
        layer = self._styled_layer(STYLE_ILLUMINATED_OVERLAY)

        self.assertEqual(
            layer.blendMode(),
            QPainter.CompositionMode.CompositionMode_SoftLight
        )


    def test_other_modes_leave_the_layer_at_normal_blend_mode(self):

        for style_mode in (STYLE_ELEVATION_COLOR, STYLE_MONOCHROME):

            layer = self._styled_layer(style_mode)

            self.assertEqual(
                layer.blendMode(),
                QPainter.CompositionMode.CompositionMode_SourceOver
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


class TestSmoothIllumination(QgisTestCase):

    """
    _smooth_illumination() - the along-line moving average that fixes
    a real regression: on genuinely low-relief terrain (a gentle
    bathymetric shelf, confirmed live against a real GMRT DEM), DEM
    noise smaller than the true elevation difference across
    _segment_illumination()'s narrow sampling window can make the raw
    per-segment "which side is uphill" comparison flip essentially at
    random, showing up as an alternating light/dark "barcode" pattern
    along an otherwise smooth, correctly-traced contour line.
    """

    def _entries(self, illum_values, line_id="A"):

        return [
            {
                "geometry": None,
                "elevation": 0.0,
                "illum": value,
                "line_id": line_id,
                "order": order,
            }
            for order, value in enumerate(illum_values)
        ]


    def test_noisy_minority_flips_are_smoothed_toward_the_true_trend(self):

        # A segment sequence that should read as consistently lit
        # (true signal +1), with roughly a third of values flipped to
        # -1 by noise - matching the flip rates actually measured
        # live against noisy synthetic DEMs (5-40%, never a clean
        # 50/50 split), i.e. a real majority signal with a real but
        # not-dominant minority of noise-flipped segments - exactly
        # the "barcode" pattern reported live. A moving average
        # across several segments should pull the smoothed values
        # back toward the true, consistently-lit majority sign. (A
        # perfectly symmetric 50/50 alternation, unlike this, is
        # genuinely zero-mean noise with no real trend to recover -
        # not what a moving average is being asked to fix here.)
        noisy = [-1.0 if i % 3 == 0 else 1.0 for i in range(30)]

        smoothed = _smooth_illumination(
            self._entries(noisy)
        )

        positive_fraction = sum(1 for v in smoothed if v > 0) / len(smoothed)

        self.assertGreater(
            positive_fraction,
            0.8
        )


    def test_consistent_sequence_is_left_unchanged(self):

        # Smoothing a signal with no noise to average out shouldn't
        # perturb it - guards against the fix introducing drift on
        # the common, well-behaved case (which is also what every
        # existing synthetic-DEM integration test already exercises).
        consistent = [0.707] * 20

        smoothed = _smooth_illumination(
            self._entries(consistent)
        )

        for value in smoothed:
            self.assertAlmostEqual(value, 0.707, places=9)


    def test_different_lines_are_not_smoothed_into_each_other(self):

        # Two separate original contour lines, one fully lit and one
        # fully shadowed - the fully-shadowed line's own values must
        # stay negative rather than being pulled toward the other
        # line's values, which grouping by "line_id" (not just
        # position in the input list) is what prevents.
        entries = (
            self._entries([1.0] * 5, line_id="A")
            + self._entries([-1.0] * 5, line_id="B")
        )

        smoothed = _smooth_illumination(
            entries
        )

        self.assertTrue(
            all(v > 0 for v in smoothed[:5])
        )

        self.assertTrue(
            all(v < 0 for v in smoothed[5:])
        )


    def test_window_clamps_at_the_ends_of_a_short_line(self):

        # A line shorter than the smoothing window shouldn't error or
        # reach outside its own bounds - every position's window
        # should just clamp to whatever segments actually exist.
        short_line = [1.0, -1.0, 1.0]

        smoothed = _smooth_illumination(
            self._entries(short_line)
        )

        self.assertEqual(
            len(smoothed),
            len(short_line)
        )


    def test_empty_input_returns_empty(self):

        self.assertEqual(
            _smooth_illumination([]),
            []
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
        # result to the project - see core/_layer_utils.py's
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


class TestUphillSampleOffsetPixelSizeAwareness(QgisTestCase):

    """
    Regression test for a real, live-confirmed bug: on a curving
    contour ring (see build_synthetic_cone_dem()'s own docstring for
    why a straight-line DEM, like every other synthetic DEM in this
    test file, can't expose it), a perpendicular sampling offset
    smaller than the DEM's own reprojected pixel size makes both of
    _segment_illumination()'s sample points routinely land in the
    exact same pixel - an exact tie, whose tie-break always favours
    perpendicular_a - which, combined with a ring's continuously
    rotating tangent direction, produces a dense, near-uniform
    alternating illumination sign along an otherwise smooth, correctly
    traced contour line, even with zero injected noise. Confirmed live
    against both a clean synthetic cone DEM (52.65% flip rate at the
    old fixed 15m offset, dropping under 1% once the offset reached
    the DEM's own pixel size) and a real GMRT DEM reported to actually
    show this pattern (35.6% -> 4.1%).
    """

    def setUp(self):

        super().setUp()

        # A coarse pixel size (reprojects to roughly 40m at this
        # latitude) so the old fixed 15m offset sits well inside a
        # single pixel, deterministically reproducing the tie.
        self._dem_path = build_synthetic_cone_dem(
            width=60,
            height=60,
            pixel_size=0.00035
        )

        dem_layer = QgsRasterLayer(
            self._dem_path,
            "cone_dem"
        )

        self.assertTrue(
            dem_layer.isValid()
        )

        self._clipped_dem = _clip_and_reproject(
            dem_layer,
            dem_layer.extent(),
            dem_layer.crs()
        )

        self._pixel_size_m = self._clipped_dem.rasterUnitsPerPixelX()

        # A real elevation range wide enough to actually draw several
        # concentric rings, so there's more than one ring's worth of
        # tangent rotation to measure flips across.
        self._segment_layer = _generate_contour_segments(
            self._clipped_dem,
            interval=50.0,
            segment_length=20.0
        )


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def _flip_rate(self, sample_offset_m):

        dem_provider = self._clipped_dem.dataProvider()

        light_vector = _light_vector(315.0)

        by_line = {}

        for segment in self._segment_layer.getFeatures():

            illumination = _segment_illumination(
                segment.geometry(),
                dem_provider,
                light_vector,
                sample_offset_m
            )

            if illumination is None:
                continue

            by_line.setdefault(segment["ID"], []).append(
                (segment["order"], illumination)
            )

        flips = 0
        total = 0

        for entries in by_line.values():

            entries.sort(key=lambda entry: entry[0])

            for (_, a), (_, b) in zip(entries, entries[1:]):

                total += 1

                if (a > 0) != (b > 0):
                    flips += 1

        self.assertGreater(
            total, 0,
            "test DEM produced no adjacent segment pairs to compare"
        )

        return flips / total


    def test_offset_smaller_than_pixel_size_flips_illumination_often(self):

        self.assertGreater(
            self._flip_rate(UPHILL_SAMPLE_OFFSET_M),
            0.2
        )


    def test_offset_scaled_to_pixel_size_rarely_flips_illumination(self):

        effective_offset = max(
            UPHILL_SAMPLE_OFFSET_M,
            UPHILL_SAMPLE_OFFSET_PIXEL_MARGIN * self._pixel_size_m
        )

        self.assertLess(
            self._flip_rate(effective_offset),
            0.05
        )


    def test_build_output_layer_widens_the_offset_for_a_coarse_dem(self):

        # _build_output_layer() is production's own wiring point - a
        # unit test that the right offset actually reaches
        # _segment_illumination() from there, independent of the flip-
        # rate mechanism proved above, so a future refactor that
        # accidentally drops the pixel-size scaling (while leaving
        # _segment_illumination() itself untouched) still fails a test.
        expected_offset = max(
            UPHILL_SAMPLE_OFFSET_M,
            UPHILL_SAMPLE_OFFSET_PIXEL_MARGIN * self._pixel_size_m
        )

        self.assertGreater(
            expected_offset,
            UPHILL_SAMPLE_OFFSET_M,
            "test DEM's pixel size doesn't actually exercise the widening path"
        )

        min_elevation, max_elevation = _band_min_max(
            self._clipped_dem
        )

        with patch(
            "MilitaryCartographyTools.terrain.tanaka_contours._segment_illumination",
            wraps=_segment_illumination
        ) as spy:

            _build_output_layer(
                self._segment_layer,
                self._clipped_dem,
                315.0,
                self._clipped_dem.crs(),
                min_elevation,
                max_elevation
            )

        self.assertGreater(
            spy.call_count,
            0
        )

        for call in spy.call_args_list:

            self.assertAlmostEqual(
                call.args[3],
                expected_offset,
                places=6
            )
