# -*- coding: utf-8 -*-

"""
Tests for military_symbology/symbol_engine.py - rendering a MIL-STD-2525/
APP-6 symbol from a SIDC by running the vendored milsymbol.js through Qt's
QJSEngine, entirely offline/in-process.

Military Cartography Tools
"""

import base64
import re
from unittest import mock

from qgis.core import QgsExpression, QgsExpressionContext

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.military_symbology import symbol_engine
from MilitaryCartographyTools.military_symbology.sidc import build_sidc
from MilitaryCartographyTools.expressions import military_symbology_functions


class TestRenderSymbolSvg(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_produces_valid_svg_for_a_friendly_unit(self):

        sidc = build_sidc(affiliation="friend", entity="infantry")

        svg = symbol_engine.render_symbol_svg(sidc)

        self.assertTrue(svg.startswith("<svg"))

        # Standard MIL-STD-2525 affiliation colour convention - confirmed
        # live against milsymbol.js's own output, not assumed.
        self.assertIn("rgb(128,224,255)", svg)


    def test_affiliation_drives_the_fill_colour(self):

        expected = {
            "friend": "rgb(128,224,255)",
            "hostile": "rgb(255,128,128)",
            "neutral": "rgb(170,255,170)",
            "unknown": "rgb(255,255,128)",
        }

        for affiliation, colour in expected.items():

            sidc = build_sidc(affiliation=affiliation, entity="infantry")

            svg = symbol_engine.render_symbol_svg(sidc)

            self.assertIn(
                colour,
                svg,
                f"expected {colour} for affiliation={affiliation}"
            )


    def test_repeated_calls_use_the_cache(self):

        sidc = build_sidc(affiliation="friend", entity="armor")

        first = symbol_engine.render_symbol_svg(sidc)

        with mock.patch.object(
            symbol_engine,
            "_get_engine"
        ) as mocked_get_engine:

            second = symbol_engine.render_symbol_svg(sidc)

        self.assertEqual(first, second)

        mocked_get_engine.assert_not_called()


    def test_different_options_are_cached_separately(self):

        sidc = build_sidc(affiliation="friend", entity="infantry")

        small = symbol_engine.render_symbol_svg(sidc, {"size": 20})
        large = symbol_engine.render_symbol_svg(sidc, {"size": 60})

        self.assertNotEqual(small, large)


class TestRenderSymbolBase64Path(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_starts_with_the_base64_prefix(self):

        sidc = build_sidc(affiliation="friend", entity="infantry")

        path = symbol_engine.render_symbol_base64_path(sidc)

        self.assertTrue(path.startswith("base64:"))


    def test_round_trips_to_the_original_svg(self):

        sidc = build_sidc(affiliation="hostile", entity="armor")

        svg = symbol_engine.render_symbol_svg(sidc)
        path = symbol_engine.render_symbol_base64_path(sidc)

        decoded = base64.b64decode(path[len("base64:"):]).decode("utf-8")

        self.assertEqual(decoded, svg)


class TestMctSidcSvgFunction(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_evaluates_through_a_real_qgs_expression(self):

        sidc = build_sidc(affiliation="friend", entity="infantry")

        expression = QgsExpression(f"mct_sidc_svg('{sidc}')")

        context = QgsExpressionContext()

        result = expression.evaluate(context)

        self.assertFalse(
            expression.hasEvalError(),
            expression.evalErrorString()
        )

        self.assertTrue(result.startswith("base64:"))


    def _svg_for(self, sidc, stroke_scale_arg):

        expression = QgsExpression(
            f"mct_sidc_svg('{sidc}', '', '', '', {stroke_scale_arg})"
        )

        context = QgsExpressionContext()

        result = expression.evaluate(context)

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return base64.b64decode(result[len("base64:"):]).decode("utf-8")


    def test_default_stroke_scale_applies_when_the_fifth_argument_is_omitted(self):

        # U-3, 2026-08-19: every mct_sidc_svg() call in the plugin omits
        # this argument, so DEFAULT_STROKE_SCALE is what makes the
        # thickening global - see that constant's own comment.
        sidc = build_sidc(affiliation="friend", entity="infantry")

        expression = QgsExpression(f"mct_sidc_svg('{sidc}')")
        context = QgsExpressionContext()
        result = expression.evaluate(context)

        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())

        omitted_svg = base64.b64decode(
            result[len("base64:"):]
        ).decode("utf-8")

        explicit_svg = symbol_engine.render_symbol_base64_path(sidc)
        explicit_svg = base64.b64decode(explicit_svg[len("base64:"):]).decode("utf-8")

        raw_widths = [float(w) for w in re.findall(r'stroke-width="([\d.]+)"', explicit_svg)]
        omitted_widths = [float(w) for w in re.findall(r'stroke-width="([\d.]+)"', omitted_svg)]

        self.assertTrue(raw_widths)
        self.assertEqual(len(raw_widths), len(omitted_widths))

        for raw, scaled in zip(raw_widths, omitted_widths):
            self.assertAlmostEqual(
                scaled, raw * military_symbology_functions.DEFAULT_STROKE_SCALE,
                places=6
            )


    def test_an_explicit_stroke_scale_overrides_the_default(self):

        sidc = build_sidc(affiliation="friend", entity="infantry")

        raw_svg = symbol_engine.render_symbol_base64_path(sidc)
        raw_svg = base64.b64decode(raw_svg[len("base64:"):]).decode("utf-8")
        raw_widths = [float(w) for w in re.findall(r'stroke-width="([\d.]+)"', raw_svg)]

        overridden_svg = self._svg_for(sidc, "1.0")
        overridden_widths = [
            float(w) for w in re.findall(r'stroke-width="([\d.]+)"', overridden_svg)
        ]

        self.assertEqual(raw_widths, overridden_widths)


class TestDominantBaselineIsBakedIn(QgisTestCase):

    """
    **Qt's SVG renderer silently ignores `dominant-baseline`.**

    Probed directly through QSvgRenderer: the same <text> rasterises
    pixel-for-pixel identically with and without the attribute. Every
    label milsymbol means to CENTRE on its own y therefore sat with its
    BASELINE there instead, ~0.26 em high - harmless on most icons,
    a collision on any icon that puts a letter just under a centre dot.
    Table H-XIV's Reference Points were the report: Corridor Tab's "C",
    Data Link's "D", Marshall's "M" all printed ON the dot.
    """

    def _text_y(self, entity):

        svg = symbol_engine.render_symbol_svg(
            build_sidc(
                "friend",
                entity,
                symbol_set="control_measure",
                echelon="unspecified",
                status="present",
            )
        )

        return svg, float(
            re.search(r'<text[^>]*\by="(-?[\d.]+)"', svg).group(1)
        )


    def test_the_letter_is_pushed_clear_of_the_centre_dot(self):

        svg, y = self._text_y("corridor_tab_point")

        # milsymbol asks for the glyph's middle at y=140; the dot is
        # cx/cy 100 r 15, so its underside is at 115. Left as a raw
        # baseline the cap top lands at ~111 - four units INSIDE the
        # dot.
        self.assertGreater(y, 140.0)

        font_size = float(
            re.search(r'<text[^>]*font-size="([\d.]+)"', svg).group(1)
        )

        # Cap top now clears the dot outright.
        self.assertGreater(y - font_size * 0.72, 115.0)


    def test_the_shift_is_the_fonts_own_half_x_height(self):

        _svg, y = self._text_y("corridor_tab_point")

        # SVG's own definition of the "middle" dominant baseline, not a
        # tuned nudge: half the x-height above the alphabetic baseline.
        # Arial is 0.519 em, so 40 * 0.2595 = 10.4.
        self.assertAlmostEqual(y, 140.0 + 40.0 * 0.2595, delta=0.6)


    def test_the_attribute_is_left_in_place_for_renderers_that_honour_it(self):

        svg, _y = self._text_y("corridor_tab_point")

        self.assertIn('dominant-baseline="middle"', svg)


class TestSonobuoyViewboxCorrection(QgisTestCase):

    """
    milsymbol declares a 128-wide bounding box for six of the sixteen
    sonobuoys whose drawn content is only 80 wide, so at a fixed marker
    size they rendered ~31% smaller than the ten beside them. See
    symbol_engine's own _VIEWBOX_CORRECTIONS for the full reasoning.
    """

    _WIDE = (
        "expired_sonobuoy",
        "kingpin_sonobuoy",
        "low_frequency_analysis_and_recording_sonobuoy",
        "pattern_center_sonobuoy",
        "range_only_sonobuoy",
        "vertical_line_array_directional_frequency_analysis_and_recording"
        "_sonobuoy",
    )

    _NARROW = (
        "sonobuoy",
        "air_transportable_communication_sonobuoy",
        "barra_sonobuoy",
        "command_active_multi_beam_sonobuoy",
        "expendable_reliable_acoustic_path_sonobuoy",
    )

    def _viewbox_width(self, entity):

        svg = symbol_engine.render_symbol_svg(
            build_sidc(
                "friend",
                entity,
                symbol_set="control_measure",
                echelon="unspecified",
                status="present",
            )
        )

        return float(
            re.search(r'viewBox="\S+ \S+ (\S+) \S+"', svg).group(1)
        )


    def test_every_sonobuoy_now_shares_one_width(self):

        widths = {
            entity: self._viewbox_width(entity)
            for entity in self._WIDE + self._NARROW
        }

        self.assertEqual(set(widths.values()), {88.0}, widths)


    def test_the_circle_itself_was_never_the_thing_that_differed(self):

        # The whole point: all sixteen draw the SAME circle. It was only
        # ever the declared box around it that varied, which is why this
        # is a bbox correction and not a redrawn icon.
        for entity in self._WIDE + self._NARROW:

            svg = symbol_engine.render_symbol_svg(
                build_sidc(
                    "friend",
                    entity,
                    symbol_set="control_measure",
                    echelon="unspecified",
                    status="present",
                )
            )

            self.assertIn('cx="100" cy="100" r="40"', svg, entity)


    def test_an_amplifier_widens_the_corrected_box_back_out(self):

        # Table H-XIV's own sonobuoy examples hang the T and H fields
        # OUTSIDE the circle ("99", "HOT", upper right). Swapping in the
        # bare icon box alone clipped a unique designation clean off -
        # confirmed in a render before the text was measured back in.
        # VLAD, not Range Only: milsymbol only defines the
        # uniqueDesignation slot on some icons, and Range Only is one
        # that ignores it (a harmless no-op, documented in
        # mct_sidc_svg). VLAD draws it, which is what this needs.
        entity = (
            "vertical_line_array_directional_frequency_analysis_and"
            "_recording_sonobuoy"
        )

        plain = symbol_engine.render_symbol_svg(
            build_sidc(
                "friend",
                entity,
                symbol_set="control_measure",
                echelon="unspecified",
                status="present",
            )
        )

        sidc = build_sidc(
            "friend",
            entity,
            symbol_set="control_measure",
            echelon="unspecified",
            status="present",
        )

        military_symbology_functions.register()

        try:

            expression = QgsExpression(
                "mct_sidc_svg('{}', 'A1', 'uniqueDesignation')".format(sidc)
            )

            amplified = expression.evaluate(QgsExpressionContext())

            self.assertFalse(
                expression.hasEvalError(),
                expression.evalErrorString()
            )

        finally:

            military_symbology_functions.unregister()

        amplified = base64.b64decode(
            amplified.split("base64:", 1)[1]
        ).decode("utf-8")

        plain_width = float(
            re.search(r'viewBox="\S+ \S+ (\S+) \S+"', plain).group(1)
        )

        amplified_width = float(
            re.search(r'viewBox="\S+ \S+ (\S+) \S+"', amplified).group(1)
        )

        self.assertGreater(amplified_width, plain_width)

        self.assertIn("A1", amplified)


    def test_only_the_six_verified_icons_are_corrected(self):

        # A correction table is a place typos hide. Every key must be a
        # sonobuoy the drawn geometry was actually read for.
        self.assertEqual(
            set(symbol_engine._VIEWBOX_CORRECTIONS),
            {"213510", "213511", "213512", "213513", "213514", "213515"}
        )


class TestSidcSvgWidth(QgisTestCase):

    """
    mct_sidc_svg_width() must report the width of exactly the symbol
    mct_sidc_svg() returns for the same arguments - the two are always
    called side by side to hold an icon's drawn size still while its
    amplifier text hangs outside (see _point_symbol_layer.py).
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _evaluate(self, text):

        sidc = build_sidc(
            "friend",
            "decontamination_point",
            symbol_set="control_measure",
            echelon="unspecified",
            status="present",
        )

        width = QgsExpression(
            "mct_sidc_svg_width('{}', '{}', 'uniqueDesignation')".format(
                sidc, text
            )
        )

        svg = QgsExpression(
            "mct_sidc_svg('{}', '{}', 'uniqueDesignation')".format(
                sidc, text
            )
        )

        context = QgsExpressionContext()

        return width.evaluate(context), svg.evaluate(context)


    def test_it_reports_the_width_of_the_very_svg_that_is_drawn(self):

        for text in ("", "A", "LONGER"):

            width, path = self._evaluate(text)

            markup = base64.b64decode(
                path.split("base64:", 1)[1]
            ).decode("utf-8")

            self.assertAlmostEqual(
                width,
                float(
                    re.search(
                        r'viewBox="\S+ \S+ (\S+) \S+"', markup
                    ).group(1)
                ),
                places=6,
                msg=text,
            )


    def test_longer_amplifier_text_widens_the_box(self):

        # The premise the size compensation rests on. If milsymbol ever
        # stopped widening, the ratio would be 1 and the compensation a
        # harmless no-op - but it would also mean this defect is gone,
        # and that is worth knowing rather than assuming.
        plain, _ = self._evaluate("")
        short, _ = self._evaluate("A")
        long_, _ = self._evaluate("LONGER")

        self.assertGreater(short, plain)
        self.assertGreater(long_, short)
