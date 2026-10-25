# -*- coding: utf-8 -*-

"""
Tests for terrain/contours.py - plain contour lines with the usual
topographic styling.

Deliberately not Tanaka Contours: this tool emits one feature per
contour line and never splits or samples, which is what makes it
usable at small scale. See the module's own docstring.

Military Cartography Tools
"""

import os

from unittest.mock import patch

from qgis.core import (
    QgsExpression,
    QgsFeatureRequest,
    QgsRasterLayer,
    QgsRuleBasedLabeling,
    QgsRuleBasedRenderer,
)

from .qgis_test_case import build_synthetic_cone_dem, QgisTestCase

from MilitaryCartographyTools.terrain import contours
from MilitaryCartographyTools.terrain.contours import (
    DEFAULT_COLOUR,
    DEFAULT_INDEX_EVERY,
    DEFAULT_INTERVAL,
    INDEX_SYMBOL_LAYER_ID,
    INTERMEDIATE_SYMBOL_LAYER_ID,
    OUTPUT_LAYER_NAME,
    _index_filter,
    generate_contours,
    round_up_nicely,
    suggested_interval,
)


class TestSuggestedInterval(QgisTestCase):

    """
    The suggestion follows published sheet practice, NOT the 0.4 mm
    legibility rule. That rule gives a floor of about 1 m at 1:50,000
    on moderate ground - far finer than anything anyone draws, and
    finer than SRTM's own vertical error can support. See
    _INTERVAL_BY_SCALE's own comment.
    """

    def test_it_matches_what_sheets_at_those_scales_actually_use(self):

        for scale, expected in (
            (25_000, 10.0),
            (50_000, 20.0),
            (250_000, 50.0),
            (1_000_000, 200.0),
        ):

            with self.subTest(scale=scale):
                self.assertEqual(suggested_interval(scale), expected)


    def test_a_scale_inside_a_band_takes_that_bands_interval(self):

        # 1:40,000 is inside the 1:50,000 band.
        self.assertEqual(suggested_interval(40_000), 20.0)


    def test_beyond_the_table_it_keeps_the_small_scale_ratio(self):

        # 1:5,000,000 / 5,000 = 1,000 m.
        self.assertEqual(suggested_interval(5_000_000), 1000.0)


    def test_a_nonsense_scale_gives_the_plain_default(self):

        for scale in (0, -1):

            with self.subTest(scale=scale):
                self.assertEqual(suggested_interval(scale), DEFAULT_INTERVAL)


    def test_it_never_suggests_something_finer_than_srtm_supports(self):

        """
        SRTM's vertical error is around +/-10 m, so a sub-10 m
        interval contours the noise. The finest band is 5 m, for
        1:10,000 work where the DEM would not be SRTM anyway.
        """

        self.assertGreaterEqual(suggested_interval(50_000), 10.0)


class TestRoundUpNicely(QgisTestCase):

    def test_rounds_up_to_one_two_or_five_times_a_power_of_ten(self):

        for value, expected in (
            (183.47, 200),
            (51.0, 100),
            (20.0, 20),
            (1234.0, 2000),
        ):

            with self.subTest(value=value):
                self.assertEqual(round_up_nicely(value), expected)


    def test_zero_and_negative_give_zero(self):

        self.assertEqual(round_up_nicely(0), 0)
        self.assertEqual(round_up_nicely(-3), 0)


class TestIndexFilter(QgisTestCase):

    """
    ELEV is a double written by gdal:contour, so an exact `% == 0` is
    a coin toss: 1500.0 % 500 can land on 499.99999999 as easily as
    on 0. The filter compares against a tolerance instead, and this
    is the regression test for that.
    """

    def _matches(self, elevation, interval, index_every):

        expression = QgsExpression(
            _index_filter(interval, index_every).replace(
                '"ELEV"', str(elevation)
            )
        )

        return bool(expression.evaluate())


    def test_a_multiple_of_the_index_interval_is_an_index_contour(self):

        for elevation in (0.0, 250.0, 500.0, 1000.0, 1500.0, 2500.0):

            with self.subTest(elevation=elevation):
                self.assertTrue(self._matches(elevation, 50.0, 5))


    def test_a_line_between_index_contours_is_not_one(self):

        for elevation in (50.0, 100.0, 150.0, 200.0, 1450.0):

            with self.subTest(elevation=elevation):
                self.assertFalse(self._matches(elevation, 50.0, 5))


    def test_floating_point_drift_still_counts_as_an_index_contour(self):

        """The whole reason the comparison is tolerant."""

        self.assertTrue(self._matches(1500.0000000001, 50.0, 5))
        self.assertTrue(self._matches(1499.9999999999, 50.0, 5))


    def test_negative_elevations_work_too(self):

        self.assertTrue(self._matches(-500.0, 50.0, 5))
        self.assertFalse(self._matches(-475.0, 50.0, 5))


class TestGenerateContours(QgisTestCase):

    def setUp(self):

        super().setUp()

        self._dem_path = build_synthetic_cone_dem(
            width=120,
            height=120,
            pixel_size=0.00035,
            peak_elevation=1200.0,
            slope_per_pixel=8.0
        )

        self.dem = QgsRasterLayer(self._dem_path, "cone")


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass

        super().tearDown()


    def _generate(self, **kwargs):

        return generate_contours(
            self.dem,
            self.dem.extent(),
            self.dem.crs(),
            **kwargs
        )


    def test_it_produces_a_named_valid_layer_with_contours_in_it(self):

        layer = self._generate(interval=50.0)

        self.assertTrue(layer.isValid())
        self.assertEqual(layer.name(), OUTPUT_LAYER_NAME)
        self.assertGreater(layer.featureCount(), 0)


    def test_every_contour_is_a_multiple_of_the_interval(self):

        layer = self._generate(interval=50.0)

        for feature in layer.getFeatures():

            with self.subTest(elevation=feature["ELEV"]):
                self.assertAlmostEqual(feature["ELEV"] % 50.0, 0.0, places=6)


    def test_it_styles_index_and_intermediate_contours_differently(self):

        layer = self._generate(interval=50.0)

        renderer = layer.renderer()

        self.assertIsInstance(renderer, QgsRuleBasedRenderer)

        rules = renderer.rootRule().children()

        self.assertEqual(
            [rule.label() for rule in rules],
            ["Index contour", "Intermediate contour"]
        )

        index_width = rules[0].symbol().symbolLayer(0).width()
        intermediate_width = rules[1].symbol().symbolLayer(0).width()

        self.assertGreater(index_width, intermediate_width)


    def test_the_symbol_layers_carry_the_ids_the_label_mask_needs(self):

        """
        A text mask references a symbol layer by id, so these cannot
        be left to QGIS's generated ones.
        """

        # The layer MUST be held in a local. Calling .renderer() on a
        # temporary gives "RuntimeError: wrapped C/C++ object of type
        # QgsRuleBasedRenderer has been deleted" - the layer is
        # collected and takes the renderer with it.
        layer = self._generate(interval=50.0)

        rules = layer.renderer().rootRule().children()

        self.assertEqual(
            rules[0].symbol().symbolLayer(0).id(),
            INDEX_SYMBOL_LAYER_ID
        )
        self.assertEqual(
            rules[1].symbol().symbolLayer(0).id(),
            INTERMEDIATE_SYMBOL_LAYER_ID
        )


    def test_only_the_index_contours_are_labelled(self):

        """
        On a real sheet only the index lines carry their height.
        Labelling every line at a 20 m interval buries the map.
        """

        layer = self._generate(interval=50.0, index_every=5)

        labeling = layer.labeling()

        self.assertIsInstance(labeling, QgsRuleBasedLabeling)
        self.assertTrue(layer.labelsEnabled())

        rules = labeling.rootRule().children()

        self.assertEqual(len(rules), 1)
        self.assertEqual(
            rules[0].filterExpression(),
            _index_filter(50.0, 5)
        )


    def test_the_label_cuts_a_gap_in_the_line_rather_than_sitting_on_it(self):

        layer = self._generate(interval=50.0)

        # Every step held in its own local. Chaining
        # settings.format().mask() SEGFAULTS: format() hands back a
        # temporary QgsTextFormat, mask() returns a reference into it,
        # and the temporary is collected before maskedSymbolLayers()
        # reads from it. Confirmed by crash, 2026-10-26.
        labeling = layer.labeling()
        rule = labeling.rootRule().children()[0]
        settings = rule.settings()
        text_format = settings.format()
        mask = text_format.mask()

        self.assertTrue(mask.enabled())
        self.assertGreater(mask.size(), 0)

        # symbolLayerIdV2() gives the plain string that was set;
        # symbolLayerId() returns a QgsSymbolLayerId, which is not
        # even hashable.
        masked = {
            reference.symbolLayerIdV2()
            for reference in mask.maskedSymbolLayers()
        }

        self.assertIn(INDEX_SYMBOL_LAYER_ID, masked)


    def test_the_label_has_no_thousands_separator(self):

        """
        A contour labelled "1,000" is not how any sheet draws it.
        """

        layer = self._generate(interval=50.0)

        settings = layer.labeling().rootRule().children()[0].settings()

        self.assertNotIn("format_number", settings.fieldName)
        self.assertIn("to_string", settings.fieldName)


    def test_the_colour_reaches_both_rules_and_the_label(self):

        layer = self._generate(interval=50.0, colour="#112233")

        rules = layer.renderer().rootRule().children()

        for rule in rules:

            with self.subTest(rule=rule.label()):
                self.assertEqual(
                    rule.symbol().color().name(),
                    "#112233"
                )

        labeling = layer.labeling()
        rule = labeling.rootRule().children()[0]
        settings = rule.settings()
        text_format = settings.format()

        self.assertEqual(text_format.color().name(), "#112233")


    def test_the_default_colour_is_the_topographic_brown(self):

        layer = self._generate(interval=50.0)

        self.assertEqual(
            layer.renderer().rootRule().children()[0].symbol().color().name(),
            DEFAULT_COLOUR
        )


    def test_index_every_changes_which_lines_are_index_contours(self):

        layer = self._generate(interval=50.0, index_every=2)

        index = [
            feature["ELEV"]
            for feature in layer.getFeatures(
                QgsFeatureRequest(QgsExpression(_index_filter(50.0, 2)))
            )
        ]

        self.assertTrue(index)

        for elevation in index:

            with self.subTest(elevation=elevation):
                self.assertAlmostEqual(elevation % 100.0, 0.0, places=6)


    def test_a_nonpositive_interval_is_refused(self):

        for interval in (0.0, -10.0):

            with self.subTest(interval=interval):

                with self.assertRaises(ValueError):
                    self._generate(interval=interval)


    def test_index_every_below_one_is_refused(self):

        with self.assertRaises(ValueError):
            self._generate(interval=50.0, index_every=0)


    def test_a_dem_too_large_to_contour_is_refused_before_contouring(self):

        # clip_and_reproject_dem is stubbed rather than left to run:
        # patching contours.processing.run would also patch
        # _dem_utils's, since `import processing` yields the same
        # module object, and the clip would break before the guard
        # was ever reached.
        with patch.object(
            contours, "clip_and_reproject_dem", return_value=self.dem
        ):

            with patch.object(contours, "MAX_DEM_PIXELS", 10):

                with patch.object(contours.processing, "run") as never_run:

                    with self.assertRaises(ValueError) as raised:
                        self._generate(interval=50.0)

        self.assertEqual(never_run.call_count, 0)
        self.assertIn("too large to contour", str(raised.exception))


    def test_the_defaults_are_usable_on_their_own(self):

        layer = self._generate()

        self.assertTrue(layer.isValid())
        self.assertGreater(layer.featureCount(), 0)
        self.assertEqual(
            layer.labeling().rootRule().children()[0].filterExpression(),
            _index_filter(DEFAULT_INTERVAL, DEFAULT_INDEX_EVERY)
        )
