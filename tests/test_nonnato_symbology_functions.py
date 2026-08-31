# -*- coding: utf-8 -*-

"""
Tests for expressions/nonnato_symbology_functions.py -
mct_nonnato_unit_svg(), the one function land_unit_layer_nonnato.py's
renderer calls.

Military Cartography Tools
"""

import base64

from qgis.core import QgsExpression, QgsExpressionContext

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.military_symbology import symbol_engine
from MilitaryCartographyTools.expressions import nonnato_symbology_functions


class TestMctNonnatoUnitSvg(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()

        nonnato_symbology_functions.register()

        self.addCleanup(nonnato_symbology_functions.unregister)


    def _evaluate(self, expression_text):

        expression = QgsExpression(expression_text)

        result = expression.evaluate(QgsExpressionContext())

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def _svg_for(self, expression_text):

        result = self._evaluate(expression_text)

        self.assertTrue(result.startswith("base64:"))

        return base64.b64decode(result[len("base64:"):]).decode("utf-8")


    def test_evaluates_through_a_real_qgs_expression(self):

        svg = self._svg_for("mct_nonnato_unit_svg('friend', 'infantry')")

        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("#3060c0", svg)


    def test_echelon_status_and_designation_all_reach_the_render(self):

        svg = self._svg_for(
            "mct_nonnato_unit_svg("
            "'hostile', 'infantry', 'team_crew', 'planned', 'HQ 3', false)"
        )

        self.assertNotIn("M80,40L120,20", svg)  # Detachment fixup applied
        self.assertIn("stroke-dasharray", svg)  # Planned -> dashed
        self.assertIn("HQ 3", svg)


    def test_combined_arms_flag_adds_the_rectangle(self):

        without = self._svg_for("mct_nonnato_unit_svg('friend', 'infantry')")
        with_ca = self._svg_for(
            "mct_nonnato_unit_svg('friend', 'infantry', '', '', '', true)"
        )

        self.assertEqual(without.count("<rect"), 0)
        self.assertEqual(with_ca.count("<rect"), 1)


    def test_enemy_info_unknown_needs_no_valid_ground_unit_entity(self):

        svg = self._svg_for(
            "mct_nonnato_unit_svg('friend', 'enemy_info_unknown')"
        )

        self.assertEqual(svg.count("<rect"), 2)


    def test_an_invalid_entity_returns_readable_error_text_not_a_crash(self):

        result = self._evaluate(
            "mct_nonnato_unit_svg('friend', 'not_a_real_entity')"
        )

        self.assertNotIn("base64:", result)
        self.assertIn("not_a_real_entity", result)


    def test_missing_required_arguments(self):

        result = self._evaluate("mct_nonnato_unit_svg('friend')")

        self.assertEqual(
            result, "Need at least an affiliation and an entity"
        )


class TestMctNonnatoEquipmentSvg(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()

        nonnato_symbology_functions.register()

        self.addCleanup(nonnato_symbology_functions.unregister)


    def _evaluate(self, expression_text):

        expression = QgsExpression(expression_text)

        result = expression.evaluate(QgsExpressionContext())

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def _svg_for(self, expression_text):

        result = self._evaluate(expression_text)

        self.assertTrue(result.startswith("base64:"))

        return base64.b64decode(result[len("base64:"):]).decode("utf-8")


    def test_evaluates_through_a_real_qgs_expression(self):

        svg = self._svg_for("mct_nonnato_equipment_svg('friend', 'tank')")

        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("#3060c0", svg)
        self.assertNotIn("M25,50", svg)  # no frame at all for Equipment


    def test_designation_reaches_the_render(self):

        svg = self._svg_for(
            "mct_nonnato_equipment_svg('hostile', 'tank', 'a1')"
        )

        self.assertIn("A1", svg)


    def test_mine_entity_is_green_regardless_of_affiliation(self):

        svg = self._svg_for(
            "mct_nonnato_equipment_svg('friend', 'antitank_mine')"
        )

        self.assertIn("#009b00", svg)
        self.assertNotIn("#3060c0", svg)


    def test_synthetic_mine_entity_needs_no_valid_sidc(self):

        svg = self._svg_for(
            "mct_nonnato_equipment_svg('friend', 'nonnato_bar_mine')"
        )

        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("#009b00", svg)


    def test_an_invalid_entity_returns_readable_error_text_not_a_crash(self):

        result = self._evaluate(
            "mct_nonnato_equipment_svg('friend', 'not_a_real_entity')"
        )

        self.assertNotIn("base64:", result)
        self.assertIn("not_a_real_entity", result)


    def test_missing_required_arguments(self):

        result = self._evaluate("mct_nonnato_equipment_svg('friend')")

        self.assertEqual(
            result, "Need at least an affiliation and an entity"
        )


class TestMctNonnatoSigintSvg(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()

        nonnato_symbology_functions.register()

        self.addCleanup(nonnato_symbology_functions.unregister)


    def _evaluate(self, expression_text):

        expression = QgsExpression(expression_text)

        result = expression.evaluate(QgsExpressionContext())

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def _svg_for(self, expression_text):

        result = self._evaluate(expression_text)

        self.assertTrue(result.startswith("base64:"))

        return base64.b64decode(result[len("base64:"):]).decode("utf-8")


    def test_evaluates_through_a_real_qgs_expression(self):

        svg = self._svg_for("mct_nonnato_sigint_svg('friend', 'radar')")

        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("#3060c0", svg)
        self.assertNotIn("M25,50", svg)  # no frame at all for SIGINT


    def test_jammer_renders_too(self):

        svg = self._svg_for("mct_nonnato_sigint_svg('hostile', 'jammer')")

        self.assertIn(">J<", svg)


    def test_designation_reaches_the_render(self):

        svg = self._svg_for(
            "mct_nonnato_sigint_svg('hostile', 'radar', 'a1')"
        )

        self.assertIn("A1", svg)


    def test_an_invalid_entity_returns_readable_error_text_not_a_crash(self):

        result = self._evaluate(
            "mct_nonnato_sigint_svg('friend', 'not_a_real_entity')"
        )

        self.assertNotIn("base64:", result)
        self.assertIn("not_a_real_entity", result)


    def test_missing_required_arguments(self):

        result = self._evaluate("mct_nonnato_sigint_svg('friend')")

        self.assertEqual(
            result, "Need at least an affiliation and an entity"
        )


class TestMctNonnatoBoobyTrapSvg(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()

        nonnato_symbology_functions.register()

        self.addCleanup(nonnato_symbology_functions.unregister)


    def test_evaluates_through_a_real_qgs_expression(self):

        expression = QgsExpression("mct_nonnato_booby_trap_svg()")

        result = expression.evaluate(QgsExpressionContext())

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertTrue(result.startswith("base64:"))

        svg = base64.b64decode(result[len("base64:"):]).decode("utf-8")

        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("#009b00", svg)
