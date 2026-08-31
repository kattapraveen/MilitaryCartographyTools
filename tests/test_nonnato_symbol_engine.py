# -*- coding: utf-8 -*-

"""
Tests for military_symbology/nonnato_symbol_engine.py - the SVG
post-processing non-NATO symbology needs on top of milsymbol.js's own
output (frame/fill/monoColor themselves need no fixup, see
symbol_engine.py's tests for that half of the pipeline).

Military Cartography Tools
"""

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.military_symbology import (
    nonnato_symbol_engine as nse,
    symbol_engine,
)
from MilitaryCartographyTools.military_symbology.sidc import build_sidc


_FRIEND = nse.AFFILIATION_COLOURS["friend"]


class TestDetachmentSlashStrip(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_strips_the_crossing_line_but_keeps_the_circle(self):

        sidc = build_sidc(
            affiliation="friend", entity="infantry", echelon="team_crew",
            edition="2525E",
        )

        svg = symbol_engine.render_symbol_svg(
            sidc, {"frame": True, "fill": False, "monoColor": _FRIEND}
        )

        self.assertIn("M80,40L120,20", svg)

        fixed = nse.apply_nonnato_unit_fixups(svg, "infantry", "team_crew")

        self.assertNotIn("M80,40L120,20", fixed)
        self.assertIn('<circle cx="100" cy="30" r="15"', fixed)


    def test_leaves_other_echelons_untouched(self):

        sidc = build_sidc(
            affiliation="friend", entity="infantry", echelon="company",
            edition="2525E",
        )

        svg = symbol_engine.render_symbol_svg(
            sidc, {"frame": True, "fill": False, "monoColor": _FRIEND}
        )

        fixed = nse.apply_nonnato_unit_fixups(svg, "infantry", "company")

        self.assertEqual(svg, fixed)


class TestArmyAviationPropeller(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_propeller_becomes_hollow_not_filled(self):

        sidc = build_sidc(
            affiliation="hostile", entity="aviation_fixed_wing",
            edition="2525E",
        )

        svg = symbol_engine.render_symbol_svg(
            sidc,
            {
                "frame": True,
                "fill": False,
                "monoColor": nse.AFFILIATION_COLOURS["hostile"],
            },
        )

        # Confirms the fixture assumption this fixup's regex depends
        # on: milsymbol really does draw this icon filled regardless
        # of the fill:false option (one of the hardcoded-fill
        # exceptions), so there is something real to fix.
        self.assertIn('stroke="none" fill="#c02020"', svg)

        fixed = nse.apply_nonnato_unit_fixups(
            svg, "aviation_fixed_wing", "unspecified"
        )

        self.assertNotIn('stroke="none"', fixed)
        self.assertIn('stroke="#c02020" fill="none"', fixed)


class TestParachuteRiggerComposite(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_adds_infantry_cross_and_shrinks_the_parachute(self):

        sidc = build_sidc(
            affiliation="friend", entity="parachute_rigger",
            edition="2525E",
        )

        svg = symbol_engine.render_symbol_svg(
            sidc, {"frame": True, "fill": False, "monoColor": _FRIEND}
        )

        fixed = nse.apply_nonnato_unit_fixups(
            svg, "parachute_rigger", "unspecified"
        )

        self.assertIn("M25,50 L175,150 M25,150 L175,50", fixed)
        self.assertIn('transform="translate(20, 49.5) scale(0.8)"', fixed)

        # The shrunk copy's own stroke-width is boosted so the line
        # keeps its visual weight once the group scales it back down.
        self.assertIn('stroke-width="3.75"', fixed)


    def test_untouched_when_the_icon_has_no_matching_path(self):

        # A made-up SVG with no parachute path at all - the fixup
        # must not raise or mangle anything it doesn't recognise.
        svg = '<svg><path d="M0,0 L1,1" stroke-width="3" ' \
              'stroke="#000" fill="none"></path></svg>'

        self.assertEqual(svg, nse.composite_parachute_rigger(svg))


class TestCombinedArmsRect(QgisTestCase):

    def test_no_echelon_uses_the_floor_size(self):

        rect = nse.combined_arms_rect_svg("unspecified", _FRIEND)

        self.assertIn('width="37.5"', rect)
        self.assertIn('height="33.3333"', rect)


    def test_bottom_edge_always_sits_on_the_frame_top(self):

        for echelon in (
            "unspecified", "team_crew", "squad", "platoon", "company",
            "battalion", "brigade", "division", "corps", "army",
            "army_group",
        ):
            rect = nse.combined_arms_rect_svg(echelon, _FRIEND)

            y = float(rect.split('y="')[1].split('"')[0])
            height = float(rect.split('height="')[1].split('"')[0])

            self.assertAlmostEqual(
                y + height, 50,
                msg=f"{echelon}: bottom edge should sit on y=50"
            )


    def test_widest_echelon_matches_the_recorded_size(self):

        rect = nse.combined_arms_rect_svg("army_group", _FRIEND)

        self.assertIn('width="179"', rect)
        self.assertIn('height="42"', rect)


    def test_unrecognised_echelon_falls_back_to_the_floor(self):

        rect = nse.combined_arms_rect_svg("nonexistent", _FRIEND)

        self.assertIn('width="37.5"', rect)


class TestEnemyInfoUnknown(QgisTestCase):

    def test_is_enemy_info_unknown(self):

        self.assertTrue(nse.is_enemy_info_unknown("enemy_info_unknown"))
        self.assertFalse(nse.is_enemy_info_unknown("infantry"))


    def test_svg_has_two_concentric_unfilled_rectangles(self):

        svg = nse.enemy_info_unknown_svg()

        self.assertEqual(svg.count("<rect"), 2)
        self.assertNotIn('fill="#', svg)
        self.assertIn('stroke="#c02020"', svg)

        # Inner rectangle inset 15 units on every side of the outer.
        self.assertIn('x="25" y="50" width="150" height="100"', svg)
        self.assertIn('x="40" y="65" width="120" height="70"', svg)


class TestRenderNonnatoUnitSvg(QgisTestCase):

    """
    End-to-end: the one function land_unit_layer_nonnato.py's renderer
    actually calls, exercising the real milsymbol.js render, both
    fixups, the affiliation colour map, and the Combined Arms overlay
    together - not just each piece in isolation.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_plain_infantry_is_framed_unfilled_and_stroke_scaled(self):

        svg = nse.render_nonnato_unit_svg("friend", "infantry")

        self.assertIn(f'stroke="{_FRIEND}"', svg)
        self.assertIn("M25,50 l150,0", svg)  # the frame itself

        # DEFAULT_STROKE_SCALE (1.3) applied on top of milsymbol's own
        # stroke-width="4"/"3" - not left at the raw, unscaled values.
        self.assertIn('stroke-width="5.2"', svg)  # 4 * 1.3
        self.assertIn('stroke-width="3.9"', svg)  # 3 * 1.3


    def test_all_six_affiliation_colours_reach_the_render(self):

        for affiliation, colour in nse.AFFILIATION_COLOURS.items():

            svg = nse.render_nonnato_unit_svg(affiliation, "infantry")

            self.assertIn(
                colour, svg, f"expected {colour} for {affiliation}"
            )


    def test_the_frame_stays_a_rectangle_for_every_affiliation(self):

        # Regression test: milsymbol does NOT treat frame:true as "draw
        # a rectangle" - it draws whichever frame SHAPE the SIDC's own
        # affiliation digit selects (hostile -> diamond, neutral ->
        # square, unknown -> quatrefoil), confirmed live and caught by
        # an actual rendered smoke test, not by any of the tests above
        # (which only ever checked that a colour string was present,
        # never the frame's own path). SIDC_AFFILIATION_FOR exists
        # specifically to prevent this; this test is what would fail if
        # that mapping regressed back to a same-name one.
        rectangle_frame = "M25,50 l150,0 0,100 -150,0 z"

        for affiliation in nse.AFFILIATION_COLOURS:

            svg = nse.render_nonnato_unit_svg(affiliation, "infantry")

            self.assertIn(
                rectangle_frame, svg,
                f"{affiliation} did not render a plain rectangle frame"
            )


    def test_team_crew_echelon_gets_the_stripped_slash(self):

        svg = nse.render_nonnato_unit_svg(
            "friend", "infantry", echelon="team_crew"
        )

        self.assertNotIn("M80,40L120,20", svg)
        self.assertIn('<circle cx="100" cy="30" r="15"', svg)


    def test_aviation_fixed_wing_propeller_is_hollow(self):

        svg = nse.render_nonnato_unit_svg("hostile", "aviation_fixed_wing")

        self.assertNotIn('stroke="none"', svg)


    def test_designation_is_uppercased_and_drawn(self):

        svg = nse.render_nonnato_unit_svg(
            "friend", "infantry", designation="1st bn"
        )

        self.assertIn("1ST BN", svg)


    def test_combined_arms_adds_a_rectangle_sized_for_the_echelon(self):

        without = nse.render_nonnato_unit_svg("friend", "infantry")
        with_ca = nse.render_nonnato_unit_svg(
            "friend", "infantry", combined_arms=True
        )

        self.assertEqual(without.count("<rect"), 0)
        self.assertEqual(with_ca.count("<rect"), 1)

        # No echelon -> the fixed floor size, same colour as the icon.
        self.assertIn('width="37.5" height="33.3333"', with_ca)
        self.assertIn(f'stroke="{_FRIEND}"', with_ca)


    def test_combined_arms_on_the_widest_echelon(self):

        svg = nse.render_nonnato_unit_svg(
            "hostile", "infantry", echelon="army_group", combined_arms=True
        )

        # 179 x 42 pre-scale, then DEFAULT_STROKE_SCALE only touches
        # stroke-width, not the rect's own geometry.
        self.assertIn('width="179" height="42"', svg)


    def _assert_rect_within_viewbox(self, svg, rect_x, rect_y, rect_w, rect_h):

        import re

        # A small tolerance, not exact <=/>=: the SVG's own numbers are
        # formatted with %g (6 significant digits), so a value can
        # round UP by a fraction of a unit versus the full-precision
        # float this test computes independently - invisible on any
        # actual render, and not the clipping bug this test exists to
        # catch (which was off by whole units, not thousandths).
        tolerance = 0.01

        vb = re.search(
            r'viewBox="([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)"', svg
        )
        self.assertIsNotNone(vb, "no viewBox found")

        vb_x, vb_y, vb_w, vb_h = (float(v) for v in vb.groups())

        self.assertLessEqual(vb_x, rect_x + tolerance, "rect clipped on the left")
        self.assertLessEqual(vb_y, rect_y + tolerance, "rect clipped on the top")
        self.assertGreaterEqual(
            vb_x + vb_w, rect_x + rect_w - tolerance, "rect clipped on the right"
        )
        self.assertGreaterEqual(
            vb_y + vb_h, rect_y + rect_h - tolerance, "rect clipped on the bottom"
        )


    def test_combined_arms_rect_is_never_clipped_by_the_viewbox(self):

        # Regression test: found via an actual rendered smoke test, not
        # by any test above - the Combined Arms rectangle was being
        # drawn correctly but clipped clean out of the visible picture
        # whenever it extended past whatever viewBox the base render
        # already had (milsymbol's own echelon-driven widening isn't
        # generous enough for Army Group's 179-wide rectangle, and
        # Enemy Info Unknown's hand-built SVG has no echelon-awareness
        # in its viewBox at all).
        for entity, echelon in (
            ("infantry", "unspecified"),
            ("infantry", "army_group"),
            (nse.ENEMY_INFO_UNKNOWN_ENTITY, "unspecified"),
            (nse.ENEMY_INFO_UNKNOWN_ENTITY, "army_group"),
        ):
            with self.subTest(entity=entity, echelon=echelon):

                svg = nse.render_nonnato_unit_svg(
                    "friend", entity, echelon=echelon, combined_arms=True
                )

                rect_x, rect_y, rect_w, rect_h = nse.combined_arms_bounds(
                    echelon
                )

                self._assert_rect_within_viewbox(
                    svg, rect_x, rect_y, rect_w, rect_h
                )


    def test_enemy_info_unknown_ignores_the_entity_specific_pipeline(self):

        svg = nse.render_nonnato_unit_svg(
            "friend", nse.ENEMY_INFO_UNKNOWN_ENTITY
        )

        # Always hostile red, regardless of the affiliation passed in -
        # confirmed as the settled rule, not a bug.
        self.assertIn(nse.AFFILIATION_COLOURS["hostile"], svg)
        self.assertNotIn(_FRIEND, svg)
        self.assertEqual(svg.count("<rect"), 2)


    def test_enemy_info_unknown_combined_arms_still_works(self):

        svg = nse.render_nonnato_unit_svg(
            "friend", nse.ENEMY_INFO_UNKNOWN_ENTITY, combined_arms=True
        )

        self.assertEqual(svg.count("<rect"), 3)
