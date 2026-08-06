# -*- coding: utf-8 -*-

"""
Tests for military_symbology/symbol_engine.py - rendering a MIL-STD-2525/
APP-6 symbol from a SIDC by running the vendored milsymbol.js through Qt's
QJSEngine, entirely offline/in-process.

Military Cartography Tools
"""

import base64
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
