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
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    COMMAND_POST_ENTITY,
    NBC_SHELTER_ENTITY,
    SIGINT_RADAR_ENTITY,
    render_nonnato_control_measure_svg,
)
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


    def test_echelon_status_and_designations_all_reach_the_render(self):

        svg = self._svg_for(
            "mct_nonnato_unit_svg("
            "'hostile', 'infantry', 'team_crew', 'planned', "
            "'HQ 3', 'CO B', false)"
        )

        self.assertNotIn("M80,40L120,20", svg)  # Detachment fixup applied
        self.assertIn("stroke-dasharray", svg)  # Planned -> dashed
        self.assertIn("HQ 3", svg)
        self.assertIn("CO B", svg)


    def test_combined_arms_flag_adds_the_rectangle(self):

        without = self._svg_for("mct_nonnato_unit_svg('friend', 'infantry')")
        with_ca = self._svg_for(
            "mct_nonnato_unit_svg('friend', 'infantry', '', '', '', '', true)"
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

        # At its neighbours' stroke width since 2026-09-17.
        self.assertNotIn('stroke-width="3"', svg)
        self.assertIn('stroke-width="3.9"', svg)


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


    def test_jammer_and_sigint_radar_render_too(self):

        # Merged in from the retired standalone SIGINT layer,
        # 2026-09-02 ("merge sigint glyphs (since there are only two)
        # with land equipment") - same function, same no-frame rule,
        # just a different SIDC symbol_set under the hood
        # (nonnato_symbol_engine._EQUIPMENT_SYMBOL_SET_OVERRIDES).
        # SIGINT's own Radar is stored as SIGINT_RADAR_ENTITY, not the
        # literal "radar" - that key is already Land Equipment's own
        # distinct "Radar" entity (see _EQUIPMENT_ENTITY_KEY_ALIASES).
        radar_svg = self._svg_for(
            f"mct_nonnato_equipment_svg('friend', '{SIGINT_RADAR_ENTITY}')"
        )
        jammer_svg = self._svg_for("mct_nonnato_equipment_svg('hostile', 'jammer')")

        self.assertTrue(radar_svg.startswith("<svg"))
        self.assertIn("#3060c0", radar_svg)
        self.assertNotIn("M25,50", radar_svg)  # no frame at all
        self.assertIn(">J<", jammer_svg)


    def test_jammer_and_sigint_radar_designation_renders_centred_below(self):

        # Same centred-below-the-icon treatment every Land Equipment
        # entity gets - see inject_centered_designation_below()'s own
        # docstring for the 2026-09-02 fix this is.
        svg = self._svg_for(
            f"mct_nonnato_equipment_svg('friend', '{SIGINT_RADAR_ENTITY}', 'a1')"
        )

        self.assertIn(">A1<", svg)
        self.assertIn('text-anchor="middle"', svg)


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

        # At its neighbours' stroke width since 2026-09-17.
        self.assertNotIn('stroke-width="3"', svg)
        self.assertIn('stroke-width="3.9"', svg)


class TestNonnatoWidthFunctions(QgisTestCase):

    """
    Icon-size stabilisation companions - see mct_nonnato_unit_svg_
    width()'s own docstring for the 2026-09-02 fix these belong to.
    Each width function must take the SAME argument list as its own
    non-width sibling and report a LARGER width once a designation is
    added (the whole premise the compensation math relies on).
    """

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


    def test_unit_width_grows_with_a_designation(self):

        plain = self._evaluate(
            "mct_nonnato_unit_svg_width("
            "'friend','infantry','unspecified','present','','','false')"
        )
        amplified = self._evaluate(
            "mct_nonnato_unit_svg_width("
            "'friend','infantry','unspecified','present','HQ 3','','false')"
        )

        self.assertGreater(amplified, plain)


    def test_equipment_width_is_unaffected_by_a_designation(self):

        # Superseded 2026-09-02: Land Equipment's own designation text
        # is now drawn centred BELOW the icon (inject_centered_
        # designation_below()), not via milsymbol's own uniqueDesignation
        # option, so it no longer widens the viewBox at all - only its
        # height, which this width function does not report. The
        # stabilisation ratio this feeds (land_equipment_layer_nonnato
        # .py's own renderer) still computes correctly either way, it
        # just always comes out as 1 for this layer now.
        plain = self._evaluate(
            "mct_nonnato_equipment_svg_width('friend','tank','')"
        )
        amplified = self._evaluate(
            "mct_nonnato_equipment_svg_width('friend','tank','HQ 3')"
        )

        self.assertEqual(amplified, plain)


    def test_equipment_width_is_unaffected_by_a_designation_for_sigint_radar_too(self):

        # Jammer/Radar merged into mct_nonnato_equipment_svg_width()
        # 2026-09-02 - same width function every other Equipment entity
        # uses, just a different SIDC symbol_set under the hood. SIGINT's
        # own Radar is stored as SIGINT_RADAR_ENTITY, not "radar" (see
        # _EQUIPMENT_ENTITY_KEY_ALIASES).
        plain = self._evaluate(
            f"mct_nonnato_equipment_svg_width('friend','{SIGINT_RADAR_ENTITY}','')"
        )
        amplified = self._evaluate(
            f"mct_nonnato_equipment_svg_width('friend','{SIGINT_RADAR_ENTITY}','HQ 3')"
        )

        self.assertEqual(amplified, plain)


    def test_pillbox_width_grows_with_a_designation(self):

        # `shelter` defines no designation slot of milsymbol's own, so
        # until 2026-09-24 its width genuinely did not change and the
        # stabilisation ratio came out as 1. The designation is now
        # injected instead, which widens the declared box exactly as it
        # does for Command Post - which is what keeps the GLYPH the
        # same size and lets the text hang outside it.
        plain = self._evaluate(
            "mct_nonnato_control_measure_svg_width('friend','shelter','present','')"
        )
        amplified = self._evaluate(
            "mct_nonnato_control_measure_svg_width('friend','shelter','present','HQ 3')"
        )

        self.assertGreater(amplified, plain)


    def test_control_measure_width_grows_with_a_designation(self):

        plain = self._evaluate(
            f"mct_nonnato_control_measure_svg_width('friend','{COMMAND_POST_ENTITY}','present','')"
        )
        amplified = self._evaluate(
            f"mct_nonnato_control_measure_svg_width('friend','{COMMAND_POST_ENTITY}','present','HQ 3')"
        )

        self.assertGreater(amplified, plain)


    def test_nbc_shelters_default_text_can_be_left_out_of_the_width(self):

        with_default = self._evaluate(
            f"mct_nonnato_control_measure_svg_width('friend','{NBC_SHELTER_ENTITY}','present','')"
        )
        bare = self._evaluate(
            f"mct_nonnato_control_measure_svg_width('friend','{NBC_SHELTER_ENTITY}','present','',false)"
        )

        self.assertEqual(bare, 108.0)
        self.assertGreater(with_default, bare)


    def test_an_invalid_entity_returns_zero_not_a_crash(self):

        result = self._evaluate(
            "mct_nonnato_unit_svg_width('friend', 'not_a_real_entity')"
        )

        self.assertEqual(result, 0.0)


class TestMctNonnatoControlMeasureSvg(QgisTestCase):

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

        svg = self._svg_for("mct_nonnato_control_measure_svg('friend', 'shelter')")

        self.assertTrue(svg.startswith("<svg"))
        self.assertIn('fill="none"', svg)


    def test_every_argument_reaches_the_render(self):

        svg = self._svg_for(
            "mct_nonnato_control_measure_svg("
            f"'hostile', '{COMMAND_POST_ENTITY}', 'planned', 'A1')"
        )

        self.assertIn("#c02020", svg)
        self.assertIn("stroke-dasharray", svg)
        self.assertIn(">A1</text>", svg)


    def test_matches_the_engine(self):

        svg = self._svg_for(
            f"mct_nonnato_control_measure_svg('friend', '{NBC_SHELTER_ENTITY}')"
        )

        self.assertEqual(
            svg,
            render_nonnato_control_measure_svg("friend", NBC_SHELTER_ENTITY),
        )


    def test_missing_required_arguments(self):

        result = self._evaluate("mct_nonnato_control_measure_svg('friend')")

        self.assertEqual(result, "Need at least an affiliation and an entity")


    def test_an_invalid_entity_returns_error_text_not_a_crash(self):

        result = self._evaluate(
            "mct_nonnato_control_measure_svg('friend', 'not_a_real_entity')"
        )

        self.assertIn("not_a_real_entity", result)
