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
    SIGINT_RADAR_ENTITY,
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


    def test_pillbox_width_is_unaffected_by_a_designation(self):

        # Unlike every other width function here - `shelter` defines no
        # designation slot at all (see mct_nonnato_pillbox_svg()'s own
        # test of this), so its width genuinely does not change. The
        # stabilisation ratio still computes correctly either way (it
        # simply comes out as 1), it just has nothing to compensate for
        # on this one entity.
        plain = self._evaluate(
            "mct_nonnato_pillbox_svg_width('friend','present','')"
        )
        amplified = self._evaluate(
            "mct_nonnato_pillbox_svg_width('friend','present','HQ 3')"
        )

        self.assertEqual(amplified, plain)


    def test_an_invalid_entity_returns_zero_not_a_crash(self):

        result = self._evaluate(
            "mct_nonnato_unit_svg_width('friend', 'not_a_real_entity')"
        )

        self.assertEqual(result, 0.0)


class TestMctNonnatoPillboxSvg(QgisTestCase):

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

        svg = self._svg_for("mct_nonnato_pillbox_svg('friend')")

        self.assertTrue(svg.startswith("<svg"))
        self.assertIn('fill="none"', svg)


    def test_designation_is_accepted_but_milsymbol_draws_nothing_for_it(self):

        # See render_nonnato_pillbox_svg()'s own test of this - `shelter`
        # defines no designation slot at all, so this is a pre-existing
        # milsymbol limitation, not a regression from this function.
        without = self._svg_for("mct_nonnato_pillbox_svg('friend')")
        with_designation = self._svg_for(
            "mct_nonnato_pillbox_svg('friend', 'present', 'a1')"
        )

        self.assertEqual(without, with_designation)


    def test_missing_required_arguments(self):

        result = self._evaluate("mct_nonnato_pillbox_svg()")

        self.assertEqual(result, "Need at least an affiliation")
