# -*- coding: utf-8 -*-

"""
Tests for military_symbology/nonnato_symbol_engine.py - the SVG
post-processing non-NATO symbology needs on top of milsymbol.js's own
output (frame/fill/monoColor themselves need no fixup, see
symbol_engine.py's tests for that half of the pipeline).

Military Cartography Tools
"""

import math
import re

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

    def test_is_enemy_unknown_covers_all_four(self):

        for entity in nse.ENEMY_ENTITIES:

            with self.subTest(entity=entity):

                self.assertTrue(nse.is_enemy_unknown(entity))

        self.assertFalse(nse.is_enemy_unknown("infantry"))
        self.assertEqual(len(nse.ENEMY_ENTITIES), 4)


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


    def test_amphibious_oval_is_removed_leaving_the_frame_and_wave(self):

        # "i want the oval inside the rectangle removed - so the result
        # is only the rectangle and the wave" - the wave is the icon's
        # own multi-hump path, kept untouched.
        svg = nse.render_nonnato_unit_svg("friend", "amphibious")

        self.assertNotIn("C150,80 150,120 125,120", svg)  # the oval, gone
        self.assertIn("M25,50 l150,0 0,100 -150,0 z", svg)  # frame stays
        self.assertIn("c 18.8,0 0,20 18.8,20", svg)  # wave stays


    def test_air_defense_artillery_is_air_defense_plus_artillery_dot(self):

        # "use the Air Defence Glyph and add a dot in the center
        # (basically Air Defence and Artillery glyphs merged)" -
        # confirmed live: Air Defence's own real glyph is a single arc
        # path, Artillery's own real glyph is a single filled centre
        # dot - the merge keeps Air Defence's arc and adds Artillery's
        # own exact dot geometry on top.
        air_defense = nse.render_nonnato_unit_svg("friend", "air_defense")
        merged = nse.render_nonnato_unit_svg(
            "friend", nse.AIR_DEFENSE_ARTILLERY_ENTITY
        )

        self.assertIn("C25,110 175,110 175,150", air_defense)  # the arc
        self.assertNotIn("<circle", air_defense)

        self.assertIn("C25,110 175,110 175,150", merged)  # same arc kept
        self.assertIn(
            '<circle cx="100" cy="100" r="15" ', merged
        )
        self.assertIn(f'fill="{_FRIEND}"', merged)


    def test_air_defense_artillery_dot_follows_the_affiliation_colour(self):

        svg = nse.render_nonnato_unit_svg(
            "hostile", nse.AIR_DEFENSE_ARTILLERY_ENTITY
        )

        hostile_colour = nse.AFFILIATION_COLOURS["hostile"]

        self.assertIn(f'fill="{hostile_colour}"', svg)


    def test_air_defense_artillery_does_not_affect_plain_air_defense(self):

        # Regression guard for the alias mechanism: the fixup is keyed
        # on the SYNTHETIC entity, not the real "air_defense" key it
        # resolves to for the SIDC build - a plain Air Defence render
        # must stay dot-free.
        svg = nse.render_nonnato_unit_svg("friend", "air_defense")

        self.assertNotIn("<circle", svg)


    def test_air_force_is_army_aviation_with_the_right_arc_opened(self):

        # "use the Army Aviation glyph, the figure of 8 is open on the
        # right - so +-30 deg at 90deg i.e. 60 to 120 deg - keep the
        # arc open, rest of the figure of eight remains".
        aviation = nse.render_nonnato_unit_svg("friend", "aviation_fixed_wing")
        air_force = nse.render_nonnato_unit_svg("friend", nse.AIR_FORCE_ENTITY)

        # The original, unbroken right-arc bezier must be gone, and the
        # left wing/centre-line geometry it shares with Army Aviation
        # must still be present.
        self.assertIn("c15,0 15,24 0,24", aviation)
        self.assertNotIn("c15,0 15,24 0,24", air_force)
        self.assertIn("L100,100 70,112 c-15,0 -15,-24 0,-24", air_force)

        # The gap is a genuine break in the path (a second M), not just
        # a redrawn continuous arc.
        self.assertEqual(air_force.count("<path"), aviation.count("<path"))
        self.assertIn(" M140.4,106 ", air_force)

        # Still hollow (stroke, not fill) like Army Aviation.
        self.assertNotIn('fill="#3060c0"', air_force)


    def test_air_force_does_not_affect_plain_army_aviation(self):

        # Regression guard for the alias mechanism, same as Air Defence
        # Artillery's own above: the fixup is keyed on the SYNTHETIC
        # entity, not the real "aviation_fixed_wing" key it resolves to.
        svg = nse.render_nonnato_unit_svg("friend", "aviation_fixed_wing")

        self.assertIn("c15,0 15,24 0,24", svg)


    def test_left_and_right_designations_are_uppercased_and_drawn(self):

        svg = nse.render_nonnato_unit_svg(
            "friend", "infantry",
            designation_left="1st bn", designation_right="2nd co",
        )

        self.assertIn("1ST BN", svg)
        self.assertIn("2ND CO", svg)


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


class TestMineFamily(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_antipersonnel_mine_is_already_a_plain_hollow_circle(self):

        # land_mine - no fixup needed, matches the rule as-is.
        sidc = build_sidc(
            affiliation="friend", entity="land_mine",
            symbol_set="land_equipment", edition="2525E",
        )
        svg = nse.apply_nonnato_equipment_fixups(
            symbol_engine.render_symbol_svg(
                sidc, {"frame": False, "fill": False, "monoColor": nse.MINE_GREEN}
            ),
            "land_mine",
        )

        self.assertIn('fill="none"', svg)
        self.assertNotIn(f'fill="{nse.MINE_GREEN}"', svg)


    def test_antitank_mine_is_already_solid(self):

        # antitank_mine - hardcoded-fill exception, matches the rule
        # as-is (no fixup).
        sidc = build_sidc(
            affiliation="friend", entity="antitank_mine",
            symbol_set="land_equipment", edition="2525E",
        )
        svg = nse.apply_nonnato_equipment_fixups(
            symbol_engine.render_symbol_svg(
                sidc, {"frame": False, "fill": False, "monoColor": nse.MINE_GREEN}
            ),
            "antitank_mine",
        )

        self.assertIn(f'fill="{nse.MINE_GREEN}"', svg)


    def test_antipersonnel_fragmentation_mine_circle_becomes_hollow(self):

        sidc = build_sidc(
            affiliation="friend", entity="antipersonnel_land_mine",
            symbol_set="land_equipment", edition="2525E",
        )
        raw = symbol_engine.render_symbol_svg(
            sidc, {"frame": False, "fill": False, "monoColor": nse.MINE_GREEN}
        )

        # Confirms the fixture assumption: both the circle and the
        # horns render filled by default, so there is something real
        # to fix.
        self.assertEqual(raw.count(f'fill="{nse.MINE_GREEN}"'), 2)

        fixed = nse.apply_nonnato_equipment_fixups(
            raw, "antipersonnel_land_mine"
        )

        # Circle hollow, horns still filled - exactly one fill left.
        self.assertEqual(fixed.count(f'fill="{nse.MINE_GREEN}"'), 1)
        self.assertIn(
            '<circle cx="100" cy="100" r="22" stroke-width="3" '
            f'stroke="{nse.MINE_GREEN}" fill="none"',
            fixed,
        )


    def test_unknown_mine_is_a_hollow_circle_with_a_vertical_line(self):

        svg = nse.unknown_mine_svg(nse.MINE_GREEN)

        self.assertEqual(svg.count("<circle"), 1)
        self.assertNotIn(f'fill="{nse.MINE_GREEN}"', svg)
        self.assertIn("M100,78 L100,122", svg)


    def test_influence_mine_anti_tank_is_solid_with_arrow_horns(self):

        svg = nse.influence_mine_anti_tank_svg(nse.MINE_GREEN)

        self.assertIn(f'fill="{nse.MINE_GREEN}"', svg)  # solid circle
        self.assertEqual(svg.count("<path"), 4)  # 2 shafts + 2 arrowheads


    def test_influence_mine_anti_personnel_is_hollow_with_arrow_horns(self):

        svg = nse.influence_mine_anti_personnel_svg(nse.MINE_GREEN)

        self.assertNotIn(f'fill="{nse.MINE_GREEN}"', svg)
        self.assertEqual(svg.count("<path"), 4)


    def test_antitank_mine_booby_trapped_has_four_horns_no_arrowheads(self):

        svg = nse.antitank_mine_booby_trapped_svg(nse.MINE_GREEN)

        self.assertIn(f'fill="{nse.MINE_GREEN}"', svg)  # solid circle
        self.assertEqual(svg.count("<path"), 4)  # 4 plain horn lines
        self.assertNotIn("L131.9,68.1 L", svg)  # no arrowhead chevrons


    def test_bar_mine_geometry(self):

        svg = nse.bar_mine_svg(nse.MINE_GREEN)

        self.assertIn('width="88" height="14.6667"', svg)
        self.assertIn('stroke-dasharray="8,3"', svg)


    def test_directional_mine_is_a_hollow_circle_with_two_dashed_horn_pairs(self):

        # "use booby trap symbol to begin with, remove the bottom
        # lines at 315 and 225 deg, change the top lines to dashed,
        # add a parallel line each to the two top lines also dashed" -
        # starts from booby_trap_control_measure_svg()'s own hollow
        # circle + 4-horn shape; bottom horns dropped, top two each
        # become a dashed pair (4 dashed <path> elements total, no
        # plain undashed horn left).
        svg = nse.directional_mine_svg(nse.MINE_GREEN)

        self.assertNotIn(f'fill="{nse.MINE_GREEN}"', svg)  # hollow circle
        self.assertEqual(svg.count("<path"), 4)
        # "8,3" since 2026-09-17 - "4,3" drew dots once the horns were
        # thickened; see _DIRECTIONAL_MINE_DASH.
        self.assertEqual(svg.count('stroke-dasharray="8,3"'), 4)
        self.assertNotIn('stroke-dasharray="4,3"', svg)

        # Bottom horns (225/315 degrees) are gone.
        self.assertNotIn("M84.4,115.6", svg)
        self.assertNotIn("M115.6,115.6", svg)

        # Each top horn's own parallel twin sits 7 units out along its
        # own 45-degree direction (offset = 7 / sqrt(2) per axis) -
        # widened from an initial 5 units, live: "increase the gap
        # between the parallel lines slightly".
        offset = 7 / (2 ** 0.5)
        self.assertIn(f"M{115.6 + offset:g},{84.4 + offset:g}", svg)
        self.assertIn(f"M{84.4 - offset:g},{84.4 + offset:g}", svg)

        # Each horn is 20% longer than the original 45-degree segment,
        # and its own pre-scale stroke width is 30% bigger (3 -> 3.9) -
        # both requested live after a smoke test found the parallel
        # lines hard to make out.
        self.assertIn("L135.2,64.8", svg)
        self.assertIn("L64.8,64.8", svg)
        self.assertEqual(svg.count('stroke-width="3.9"'), 4)


    def test_directional_mine_is_registered_as_a_mine_entity(self):

        self.assertIn(nse.DIRECTIONAL_MINE_ENTITY, nse.MINE_ENTITIES)
        self.assertTrue(nse.is_synthetic_entity(nse.DIRECTIONAL_MINE_ENTITY))


class TestInjectCenteredDesignationBelow(QgisTestCase):

    """
    nonnato_symbol_engine.inject_centered_designation_below() - the
    2026-09-02 fix reported live: "the unique designation is still too
    far from the glyphs... I want the unique designation to be
    directly under the glyph, with text centered". Replaces milsymbol's
    own uniqueDesignation option entirely for Land Equipment.

    Corrected again the same day - "it is a bit far, can we move it as
    close to the glyph as possible with some gap - this should be
    dynamic as we move ahead with the modifications in future" -
    anchored to the icon's own real rendered content bounds
    (_content_bounds(), via Qt's own QSvgRenderer) rather than its
    declared viewBox, which routinely carries far more padding below
    the actual ink than the gap alone (Jammer/Radar especially - see
    test_a_padded_declared_viewbox_does_not_widen_the_gap() below).
    """

    def test_no_designation_is_a_no_op(self):

        svg = nse.render_nonnato_equipment_svg("friend", "tank")

        self.assertEqual(
            svg, nse.inject_centered_designation_below(svg, None, _FRIEND)
        )
        self.assertEqual(
            svg, nse.inject_centered_designation_below(svg, "", _FRIEND)
        )


    def test_text_is_centred_under_the_icons_own_original_viewbox(self):

        base_svg = nse.render_nonnato_equipment_svg("friend", "tank")

        match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', base_svg)
        vb_x, vb_y, vb_w, vb_h = (float(g) for g in match.groups())

        svg = nse.inject_centered_designation_below(base_svg, "a1", _FRIEND)

        text_match = re.search(
            r'<text x="(\S+)" y="(\S+)" text-anchor="middle"[^>]*>A1</text>',
            svg,
        )

        self.assertIsNotNone(text_match)

        text_x, text_y = float(text_match.group(1)), float(text_match.group(2))

        self.assertAlmostEqual(text_x, vb_x + vb_w / 2, places=3)
        self.assertGreater(text_y, vb_y + vb_h)  # below the original icon


    def test_a_padded_declared_viewbox_does_not_widen_the_gap(self):

        # The core regression: Jammer's own declared viewBox extends
        # ~30 units below its actual "J" glyph (milsymbol allocates
        # room generically, not tightly) - confirmed live. Anchoring to
        # the declared viewBox, like the first version of this function
        # did, would draw the designation ~30 units further from the
        # glyph than tank's own (whose declared viewBox sits within
        # ~2 units of its own real ink) - a per-icon inconsistency this
        # fix exists to remove. The gap from the REAL content bottom to
        # the text baseline must be the same fixed budget
        # (_DESIGNATION_GAP + font-size-derived ascent) for both.
        tank_svg = nse.render_nonnato_equipment_svg("friend", "tank")
        jammer_svg = nse.render_nonnato_equipment_svg("friend", "jammer")

        tank_with = nse.inject_centered_designation_below(tank_svg, "a1", _FRIEND)
        jammer_with = nse.inject_centered_designation_below(jammer_svg, "a1", _FRIEND)

        def content_bottom_and_baseline(base_svg, injected_svg):

            content_bottom = (
                nse._content_bounds(base_svg, fallback=(0, 0, 0, 0))[1]
                + nse._content_bounds(base_svg, fallback=(0, 0, 0, 0))[3]
            )

            # search() only, not the whole string - Jammer's own base
            # svg already has its OWN <text> element (the "J" glyph
            # itself), so this must match the INJECTED designation
            # specifically, not just the first <text> tag found.
            baseline_match = re.search(
                r'<text x="\S+" y="(\S+)" text-anchor="middle"[^>]*>A1</text>',
                injected_svg,
            )

            return content_bottom, float(baseline_match.group(1))

        tank_bottom, tank_baseline = content_bottom_and_baseline(tank_svg, tank_with)
        jammer_bottom, jammer_baseline = content_bottom_and_baseline(
            jammer_svg, jammer_with
        )

        self.assertAlmostEqual(
            tank_baseline - tank_bottom, jammer_baseline - jammer_bottom, places=1
        )


    def test_upper_cases_the_designation(self):

        base_svg = nse.render_nonnato_equipment_svg("friend", "tank")

        svg = nse.inject_centered_designation_below(base_svg, "hq 3", _FRIEND)

        self.assertIn(">HQ 3<", svg)


    def test_viewbox_height_grows_but_width_does_not(self):

        base_svg = nse.render_nonnato_equipment_svg("friend", "tank")

        match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', base_svg)
        vb_w, vb_h = float(match.group(3)), float(match.group(4))

        svg = nse.inject_centered_designation_below(base_svg, "a1", _FRIEND)

        new_match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', svg)
        new_w, new_h = float(new_match.group(3)), float(new_match.group(4))

        self.assertAlmostEqual(new_w, vb_w, places=3)
        self.assertGreater(new_h, vb_h)


    def test_width_and_height_attributes_stay_in_sync_with_the_viewbox(self):

        base_svg = nse.render_nonnato_equipment_svg("friend", "tank")

        svg = nse.inject_centered_designation_below(base_svg, "a1", _FRIEND)

        vb_match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', svg)
        vb_w, vb_h = float(vb_match.group(3)), float(vb_match.group(4))

        wh_match = re.search(r'width="(\S+)" height="(\S+)"', svg)

        self.assertIsNotNone(wh_match)

        declared_w, declared_h = float(wh_match.group(1)), float(wh_match.group(2))

        self.assertAlmostEqual(declared_w / declared_h, vb_w / vb_h, places=3)


    def test_a_long_designation_shrinks_to_fit_rather_than_widening_the_icon(self):

        base_svg = nse.render_nonnato_equipment_svg("friend", "tank")

        match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', base_svg)
        vb_w = float(match.group(3))

        svg = nse.inject_centered_designation_below(
            base_svg, "a very long designation indeed", _FRIEND
        )

        new_match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', svg)
        new_w = float(new_match.group(3))

        self.assertAlmostEqual(new_w, vb_w, places=3)

        font_size_match = re.search(r'font-size="(\S+)"[^>]*>A VERY', svg)

        self.assertIsNotNone(font_size_match)
        self.assertLess(float(font_size_match.group(1)), nse._DESIGNATION_FONT_SIZE)


    def test_works_on_an_svg_with_no_width_height_attributes(self):

        # Synthetic mine icons (e.g. bar_mine_svg()) declare no width/
        # height on the outer <svg> tag itself, only a viewBox (though
        # bar_mine_svg()'s own <rect> legitimately has its own "width" -
        # a different attribute entirely) - must not crash.
        base_svg = nse.bar_mine_svg(nse.MINE_GREEN)

        opening_tag_before = base_svg.split(">", 1)[0]
        self.assertNotIn("width=", opening_tag_before)

        svg = nse.inject_centered_designation_below(
            base_svg, "a1", nse.MINE_GREEN
        )

        opening_tag_after = svg.split(">", 1)[0]

        self.assertIn(">A1<", svg)
        self.assertNotIn("width=", opening_tag_after)


class TestInjectSideDesignations(QgisTestCase):

    """
    nonnato_symbol_engine.inject_side_designations() - Land Unit's own
    2026-09-02 replacement for milsymbol's single, side-anchored
    uniqueDesignation slot: "i want two unique designators - unique
    designator (left) and unique designator (right)... both left and
    right designators should be vertically middle aligned to the left
    or right of the glyph, the present unique designator can be
    removed or ignored". Reuses the same _content_bounds()-based
    measurement TestInjectCenteredDesignationBelow above already
    exercises for Land Equipment.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_no_text_is_a_no_op(self):

        svg = nse.render_nonnato_unit_svg("friend", "infantry")

        self.assertEqual(
            svg, nse.inject_side_designations(svg, None, None, _FRIEND)
        )
        self.assertEqual(
            svg, nse.inject_side_designations(svg, "", "", _FRIEND)
        )


    def test_left_text_sits_left_of_and_vertically_centred_on_the_content(self):

        base_svg = nse.render_nonnato_unit_svg("friend", "infantry")

        content_x, content_y, content_w, content_h = nse._content_bounds(
            base_svg, fallback=(0, 0, 0, 0)
        )

        svg = nse.inject_side_designations(base_svg, "a1", None, _FRIEND)

        text_match = re.search(
            r'<text x="(\S+)" y="(\S+)" text-anchor="end"[^>]*>A1</text>',
            svg,
        )

        self.assertIsNotNone(text_match)

        text_x, text_y = float(text_match.group(1)), float(text_match.group(2))

        self.assertLess(text_x, content_x)

        # The INK is centred on the content, not the `y` attribute:
        # `y` is the baseline (Qt ignores dominant-baseline), so the cap
        # box runs from y - cap to y and its own middle is what has to
        # land on the content's midpoint. See inject_side_designations()
        # for the 2026-09-05 fix this checks.
        cap_height = nse._SIDE_DESIGNATION_FONT_SIZE * nse._CAP_HEIGHT_RATIO

        self.assertAlmostEqual(
            text_y - cap_height / 2, content_y + content_h / 2, places=3
        )


    def test_right_text_sits_right_of_and_vertically_centred_on_the_content(self):

        base_svg = nse.render_nonnato_unit_svg("friend", "infantry")

        content_x, content_y, content_w, content_h = nse._content_bounds(
            base_svg, fallback=(0, 0, 0, 0)
        )

        svg = nse.inject_side_designations(base_svg, None, "b2", _FRIEND)

        text_match = re.search(
            r'<text x="(\S+)" y="(\S+)" text-anchor="start"[^>]*>B2</text>',
            svg,
        )

        self.assertIsNotNone(text_match)

        text_x, text_y = float(text_match.group(1)), float(text_match.group(2))

        self.assertGreater(text_x, content_x + content_w)

        # The INK is centred on the content, not the `y` attribute:
        # `y` is the baseline (Qt ignores dominant-baseline), so the cap
        # box runs from y - cap to y and its own middle is what has to
        # land on the content's midpoint. See inject_side_designations()
        # for the 2026-09-05 fix this checks.
        cap_height = nse._SIDE_DESIGNATION_FONT_SIZE * nse._CAP_HEIGHT_RATIO

        self.assertAlmostEqual(
            text_y - cap_height / 2, content_y + content_h / 2, places=3
        )


    def test_the_designators_carry_no_dominant_baseline_at_all(self):

        # The attribute is what put them 16.2 units high against an
        # explicit "vertically middle aligned" request - Qt ignores it,
        # so the baseline is computed instead (2026-09-05). Guarding
        # this because reaching for the attribute is the natural thing
        # to write and it silently does nothing.
        svg = nse.inject_side_designations(
            nse.render_nonnato_unit_svg("friend", "infantry"), "a1", "b2", _FRIEND
        )

        self.assertNotIn("dominant-baseline", svg)


    def test_the_two_sides_share_one_baseline(self):

        svg = nse.inject_side_designations(
            nse.render_nonnato_unit_svg("friend", "infantry"), "a1", "b2", _FRIEND
        )

        baselines = {
            float(y) for y in
            re.findall(r'<text x="\S+" y="(\S+)"[^>]*>(?:A1|B2)</text>', svg)
        }

        self.assertEqual(len(baselines), 1)


    def test_both_sides_render_independently(self):

        base_svg = nse.render_nonnato_unit_svg("friend", "infantry")

        svg = nse.inject_side_designations(base_svg, "a1", "b2", _FRIEND)

        self.assertIn(">A1<", svg)
        self.assertIn(">B2<", svg)
        self.assertEqual(svg.count("<text"), 2)


    def test_upper_cases_both_designations(self):

        base_svg = nse.render_nonnato_unit_svg("friend", "infantry")

        svg = nse.inject_side_designations(base_svg, "hq 3", "co b", _FRIEND)

        self.assertIn(">HQ 3<", svg)
        self.assertIn(">CO B<", svg)


    def test_viewbox_grows_sideways_but_not_vertically(self):

        base_svg = nse.render_nonnato_unit_svg("friend", "infantry")

        match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', base_svg)
        vb_h = float(match.group(4))

        svg = nse.inject_side_designations(base_svg, "a1", "b2", _FRIEND)

        new_match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', svg)
        new_h = float(new_match.group(4))

        self.assertAlmostEqual(new_h, vb_h, places=3)


    def test_width_and_height_attributes_stay_in_sync_with_the_viewbox(self):

        base_svg = nse.render_nonnato_unit_svg("friend", "infantry")

        svg = nse.inject_side_designations(base_svg, "a1", "b2", _FRIEND)

        vb_match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', svg)
        vb_w, vb_h = float(vb_match.group(3)), float(vb_match.group(4))

        wh_match = re.search(r'width="(\S+)" height="(\S+)"', svg)

        self.assertIsNotNone(wh_match)

        declared_w, declared_h = float(wh_match.group(1)), float(wh_match.group(2))

        self.assertAlmostEqual(declared_w / declared_h, vb_w / vb_h, places=3)


class TestContentBounds(QgisTestCase):

    """nonnato_symbol_engine._content_bounds() on its own - the Qt QSvgRenderer-based measurement inject_centered_designation_below() relies on."""

    def test_measures_tighter_than_the_declared_viewbox_for_a_padded_icon(self):

        # Jammer is deliberately the test subject here, not an
        # arbitrary choice: it is pure `<text>` (no path/circle/rect at
        # all), which is exactly the case QSvgRenderer.boundsOnElement()
        # cannot measure on QGIS 3's own Qt SVG module (confirmed live:
        # always returns an empty rect for text, on any attributes) -
        # this test is the regression guard for that cross-version bug,
        # caught only by running both QGIS_APP targets, not something
        # the newer environment this was first built against could
        # have shown on its own.
        svg = nse.render_nonnato_equipment_svg("friend", "jammer")

        match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', svg)
        vb_x, vb_y, vb_w, vb_h = (float(g) for g in match.groups())

        content_x, content_y, content_w, content_h = nse._content_bounds(
            svg, fallback=(vb_x, vb_y, vb_w, vb_h)
        )

        self.assertLess(content_y + content_h, vb_y + vb_h)


    def test_text_element_bounds_respects_anchor_and_baseline(self):

        left, top, width, height = nse._text_element_bounds(
            x=100, y=100,
            attrs=' text-anchor="middle" font-size="40" dominant-baseline="middle"',
            content="AB",
        )

        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        self.assertLess(left, 100)  # centred anchor pulls left of x
        self.assertLess(top, 100)  # middle baseline pulls top above y


    def test_falls_back_when_the_svg_has_no_viewbox_at_all(self):

        fallback = (1.0, 2.0, 3.0, 4.0)

        result = nse._content_bounds("<not-an-svg/>", fallback=fallback)

        self.assertEqual(result, fallback)


class TestRenderNonnatoEquipmentSvg(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_a_real_equipment_entity_has_no_frame(self):

        svg = nse.render_nonnato_equipment_svg("friend", "tank")

        self.assertNotIn("M25,50", svg)
        self.assertIn(_FRIEND, svg)


    def test_designation_reaches_the_render(self):

        svg = nse.render_nonnato_equipment_svg(
            "hostile", "tank", designation="a1"
        )

        self.assertIn("A1", svg)


    def test_mine_entities_are_always_green_regardless_of_affiliation(self):

        for affiliation in nse.AFFILIATION_COLOURS:

            with self.subTest(affiliation=affiliation):

                svg = nse.render_nonnato_equipment_svg(affiliation, "antitank_mine")

                self.assertIn(nse.MINE_GREEN, svg)
                for colour in nse.AFFILIATION_COLOURS.values():
                    if colour != nse.MINE_GREEN:
                        self.assertNotIn(colour, svg)


    def test_synthetic_mine_entities_render_with_no_sidc_call(self):

        for entity in (
            nse.UNKNOWN_MINE_ENTITY,
            nse.INFLUENCE_MINE_ANTI_TANK_ENTITY,
            nse.INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY,
            nse.ANTITANK_MINE_BOOBY_TRAPPED_ENTITY,
            nse.BAR_MINE_ENTITY,
        ):
            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                self.assertTrue(svg.startswith("<svg"))
                self.assertIn(nse.MINE_GREEN, svg)


    def test_weapon_tier_siblings_all_render(self):

        # Spot-check a few of the newly-required Light/Medium/Heavy
        # siblings actually resolve - not exhaustive (that belongs to
        # the layer-level test), just confirms the plumbing works for
        # more than one hand-picked entity.
        for entity in (
            "tank", "tank_light", "tank_medium",
            "howitzer", "howitzer_light", "howitzer_medium",
            "rifle", "single_shot_rifle", "semiautomatic_rifle",
        ):
            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                self.assertTrue(svg.startswith("<svg"))


    def test_machine_gun_tiers_have_the_right_number_of_horizontal_lines(self):

        # Two rules at once, both reported live. The tier lines must
        # run 0/1/2 - "light has no horizontal line in center, medium
        # has one line and heavy two lines - same as all other"
        # (2026-09-02) - and the body must be APP-6E's RIFLE glyph,
        # renamed, not its real machine_gun one, which draws a short
        # foot line under the arrow at EVERY tier: "normal, light and
        # heavy have a small horizontal line below the arrow ... what
        # was required was that we use the rifle glyph of app-6e,
        # rename it machine gun for non-nato, and then use the
        # horizontal lines for medium and heavy" (2026-09-12). Taking
        # the rifle family's first three fire modes satisfies both, so
        # test both here: a rebuild on machine_gun/light/medium would
        # still pass the line counts alone.
        light = nse.render_nonnato_equipment_svg("friend", "rifle")
        medium = nse.render_nonnato_equipment_svg(
            "friend", "single_shot_rifle"
        )
        heavy = nse.render_nonnato_equipment_svg(
            "friend", "semiautomatic_rifle"
        )

        # Each tier line is a "30,0" horizontal segment - Light has
        # none, Medium's own extra <path> carries one, Heavy's own
        # extra <path> carries two (drawn as one multi-segment path,
        # not two separate <path> elements).
        self.assertEqual(light.count("30,0"), 0)
        self.assertEqual(medium.count("30,0"), 1)
        self.assertEqual(heavy.count("30,0"), 2)

        # And no foot line. The real machine_gun body is the rifle's
        # own path plus a wider horizontal segment at the shaft's foot
        # ("M 80,140 120,140", 40 units against a tier line's 30) -
        # asserted against the real glyph rather than hardcoded alone,
        # so this notices if milsymbol ever redraws it.
        foot = nse.render_nonnato_equipment_svg("friend", "machine_gun")

        self.assertIn("M 80,140 120,140", foot)

        for tier, svg in (
            ("light", light), ("medium", medium), ("heavy", heavy)
        ):
            with self.subTest(tier=tier):

                self.assertNotIn("M 80,140 120,140", svg)


    def test_missile_launcher_dome_stays_one_connected_u_shape(self):

        # "no you misunderstood, the side lines and dome are one entity
        # like an inverted U" - a first draft wrongly detached the dome
        # from its own legs; the fix must keep them as a single
        # continuous subpath, only trimming the centre line's own reach.
        for entity in (
            "antitank_missile_launcher",
            "air_defense_missile_launcher",
            "missile_launcher",
        ):
            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                # The dome curve and its two flanking legs must all sit
                # in the SAME unbroken subpath (no M/m between the two
                # legs' own "c 0,-20 30,-20 30,0" dome and either leg).
                self.assertIn(
                    "85,75 c 0,-20 30,-20 30,0 l 0,45", svg
                )


    def test_missile_launcher_centre_line_has_a_gap_below_the_dome(self):

        # "adjust the length of the dome... it should have a gap with
        # the other lines on top" - the centre line's own top tip must
        # stop short of the dome's peak, not touch it, by
        # _MISSILE_DOME_GAP (doubled live from 5 to 10: "increase the
        # gap between the line and top of dome by 100%").
        antitank = nse.render_nonnato_equipment_svg(
            "friend", "antitank_missile_launcher"
        )
        air_defense = nse.render_nonnato_equipment_svg(
            "friend", "air_defense_missile_launcher"
        )
        plain = nse.render_nonnato_equipment_svg("friend", "missile_launcher")

        self.assertEqual(nse._MISSILE_DOME_GAP, 10)
        self.assertIn("0,-55", antitank)  # 65 - 10
        self.assertIn("0,-55", air_defense)  # 65 - 10
        self.assertIn("0,-70", plain)  # 80 - 10

        # The old, touching-the-peak reach must be gone.
        self.assertNotIn("0,-65", antitank)
        self.assertNotIn("0,-65", air_defense)
        self.assertNotIn("0,-80", plain)


    def test_air_defense_and_plain_missile_launcher_legs_match_antitanks(self):

        # "reduce the length of the domes sides to match that of the
        # anti tank missile launcher" - Antitank's own U-legs were
        # already 45 units; Air Defence's and plain Missile Launcher's
        # own legs (65 units) must shrink to match.
        for entity in ("air_defense_missile_launcher", "missile_launcher"):

            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                self.assertIn("M 85,120 85,75 c 0,-20 30,-20 30,0 l 0,45", svg)
                self.assertNotIn("l 0,65", svg)


    def test_missile_launcher_fixup_applies_to_every_tier(self):

        for entity in (
            "antitank_missile_launcher", "antitank_missile_launcher_light",
            "antitank_missile_launcher_medium",
            "air_defense_missile_launcher", "air_defense_missile_launcher_light",
            "air_defense_missile_launcher_medium",
            "missile_launcher", "missile_launcher_light",
            "missile_launcher_medium",
        ):
            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                self.assertNotIn("0,-65", svg)
                self.assertNotIn("0,-80", svg)


    def test_missile_launcher_tier_line_is_inset_from_the_dome_legs(self):

        # "everything is fine except that the dome legs are touching
        # the horizontal lines, so introduce a small gap, 50% of that
        # between dome top and vertical line, on both sides" -
        # _MISSILE_DOME_GAP is 10, so the tier line insets by 5 on each
        # side (30 wide -> 20 wide, still centred).
        self.assertEqual(nse._MISSILE_TIER_LINE_GAP, 5)

        for family in (
            "antitank_missile_launcher",
            "air_defense_missile_launcher",
            "missile_launcher",
        ):
            with self.subTest(family=family):

                medium_tier = nse.render_nonnato_equipment_svg(
                    "friend", f"{family}_light"
                )
                heavy_tier = nse.render_nonnato_equipment_svg(
                    "friend", f"{family}_medium"
                )

                self.assertIn('d="m 90,100 20,0"', medium_tier)
                self.assertNotIn('d="m 85,100 30,0"', medium_tier)

                self.assertIn('d="m 90,105 20,0 m -20,-10 20,0"', heavy_tier)
                self.assertNotIn(
                    'd="m 85,105 30,0 m -30,-10 30,0"', heavy_tier
                )


    def test_missile_launcher_tier_line_inset_does_not_leak_to_other_families(self):

        # The tier-line geometry is shared/generic across every tiered
        # weapon family, not unique to missile launchers - the inset
        # must stay scoped to the three missile-launcher fixups only.
        howitzer_medium_tier = nse.render_nonnato_equipment_svg(
            "friend", "howitzer_light"
        )

        self.assertIn('d="m 85,100 30,0"', howitzer_medium_tier)
        self.assertNotIn('d="m 90,100 20,0"', howitzer_medium_tier)


    def test_bridge_layer_tank_adds_a_chevron_at_the_top_of_the_oval(self):

        # "use the Armoured Protected Vehicle (APV) glyph - over the
        # oval, add a < on the top left - slightly inward say 1/3rd
        # inside", corrected live: "shift the < to the top of the oval
        # not inside it, and increase the < size by double", corrected
        # again: "the bottom of < or / should touch the top of the
        # oval".
        apv = nse.render_nonnato_equipment_svg("friend", "armored_protected_vehicle")
        blt = nse.render_nonnato_equipment_svg(
            "friend", nse.BRIDGE_LAYER_TANK_ENTITY
        )

        # The oval itself is untouched.
        self.assertIn(
            'd="M125,80 C150,80 150,120 125,120 L75,120 C50,120 50,80 '
            '75,80 Z"',
            blt,
        )
        self.assertEqual(apv.count("<path"), 1)
        self.assertEqual(blt.count("<path"), 2)

        # The chevron sits entirely above the oval's own top edge
        # (y=80), its own lower arm-tip touching that edge exactly.
        self.assertIn("L89.1,80", blt)


    def test_armoured_recce_vehicle_adds_a_slash_at_the_top_of_the_oval(self):

        # "start with the APV glyph and add a / at the same position as
        # the Bridge Layer Tank <", corrected live: "same - shift the /
        # to the top of the oval, increase size by 50%", corrected
        # again: "the bottom of < or / should touch the top of the
        # oval".
        arv = nse.render_nonnato_equipment_svg(
            "friend", nse.ARMOURED_RECCE_VEHICLE_ENTITY
        )

        self.assertEqual(arv.count("<path"), 2)
        self.assertIn(
            '<path d="M75,80 L85.6,58.8"', arv
        )


    def test_bridge_layer_tank_chevron_is_bigger_than_armoured_recce_vehicles_slash(self):

        # "increase the < size by double" (Bridge Layer Tank) vs
        # "increase size by 50%" (Armoured Recce Vehicle) - the two are
        # no longer the same size, only the same anchor point.
        self.assertGreater(
            nse._BRIDGE_LAYER_TANK_ARM, nse._ARMOURED_RECCE_VEHICLE_ARM
        )


    def test_apv_synthetic_entities_do_not_affect_the_plain_apv_render(self):

        # Regression guard for the alias mechanism, same as Air Defence
        # Artillery's/Air Force's own above.
        svg = nse.render_nonnato_equipment_svg(
            "friend", "armored_protected_vehicle"
        )

        self.assertEqual(svg.count("<path"), 1)
        self.assertEqual(svg.count("<circle"), 0)


    def test_an_invalid_entity_raises_a_key_error(self):

        with self.assertRaises(KeyError):

            nse.render_nonnato_equipment_svg("friend", "not_a_real_entity")


    def test_sigint_radar_renders_line_art_with_no_frame(self):

        # Jammer/Radar (Land-scoped SIGINT) merged in 2026-09-02 -
        # "merge sigint glyphs (since there are only two) with land
        # equipment" - now render through this same function, just
        # against symbol_set "sigint_land" under the hood (see
        # _EQUIPMENT_SYMBOL_SET_OVERRIDES). SIGINT's own Radar is stored
        # as SIGINT_RADAR_ENTITY, not the literal "radar" - that key is
        # already Land Equipment's own, genuinely different, real
        # "Radar" entity (a physical radar system) - see
        # _EQUIPMENT_ENTITY_KEY_ALIASES for how the alias resolves.
        svg = nse.render_nonnato_equipment_svg(
            "friend", nse.SIGINT_RADAR_ENTITY
        )

        self.assertTrue(svg.startswith("<svg"))
        self.assertNotIn("M25,50", svg)
        self.assertIn(_FRIEND, svg)


    def test_sigint_radar_is_distinct_from_land_equipments_own_radar(self):

        sigint_radar_svg = nse.render_nonnato_equipment_svg(
            "friend", nse.SIGINT_RADAR_ENTITY
        )
        land_equipment_radar_svg = nse.render_nonnato_equipment_svg(
            "friend", "radar"
        )

        self.assertNotEqual(sigint_radar_svg, land_equipment_radar_svg)


    def test_sigint_radar_has_a_centre_mast(self):

        # Reported live, 2026-09-02: "add a small vertical line from
        # the center of the arc of the radar, length about 1/2 the
        # current height of the radar glyph" - later lengthened
        # another 20% the same day. See add_radar_center_mast()'s own
        # docstring for the full geometry derivation.
        svg = nse.render_nonnato_equipment_svg("friend", nse.SIGINT_RADAR_ENTITY)

        self.assertIn('d="M90,112 L90,133"', svg)


    def test_land_equipments_own_radar_has_no_mast(self):

        # add_radar_center_mast() is keyed to SIGINT_RADAR_ENTITY only
        # in _EQUIPMENT_ENTITY_FIXUPS - Land Equipment's own separate
        # "radar" entity (still resolvable directly through the engine,
        # even though the layer's own dropdown no longer offers it)
        # must not gain a mast it was never asked to have.
        svg = nse.render_nonnato_equipment_svg("friend", "radar")

        self.assertNotIn("M90,112", svg)


    def test_jammer_renders_the_bare_letter_glyph(self):

        svg = nse.render_nonnato_equipment_svg("friend", "jammer")

        self.assertTrue(svg.startswith("<svg"))
        self.assertIn(">J<", svg)
        self.assertIn(_FRIEND, svg)


    def test_jammer_and_sigint_radar_every_affiliation_renders_the_same_shape(self):

        shapes = set()

        for affiliation in nse.AFFILIATION_COLOURS:

            svg = nse.render_nonnato_equipment_svg(
                affiliation, nse.SIGINT_RADAR_ENTITY
            )

            colour = nse.AFFILIATION_COLOURS[affiliation]
            self.assertIn(colour, svg)

            shapes.add(svg.replace(colour, ""))

        self.assertEqual(len(shapes), 1)


    def test_jammer_and_sigint_radar_designation_renders_centred_below(self):

        # Same centred-below-the-icon treatment every Land Equipment
        # entity gets (inject_centered_designation_below()) - see that
        # function's own docstring for the 2026-09-02 fix this is.
        svg = nse.render_nonnato_equipment_svg(
            "hostile", nse.SIGINT_RADAR_ENTITY, designation="a1"
        )

        self.assertIn(">A1<", svg)
        self.assertIn('text-anchor="middle"', svg)


class TestBoobyTrapControlMeasureSvg(QgisTestCase):

    def test_renders_a_hollow_circle_with_four_horns(self):

        # Corrected twice, live, 2026-09-02 - see
        # booby_trap_control_measure_svg()'s own docstring for the full
        # back-and-forth. Final shape: hollow circle (same geometry as
        # Antitank Mine's own real icon - cx=100, cy=100, r=22, see
        # _mine_circle()) plus four plain, non-dashed horns at
        # 45/135/225/315 degrees - the same coordinates
        # antitank_mine_booby_trapped_svg() uses for its own (filled-
        # circle) version.
        svg = nse.booby_trap_control_measure_svg()

        self.assertTrue(svg.startswith("<svg"))
        self.assertEqual(svg.count("<circle"), 1)
        self.assertEqual(svg.count("<path"), 4)
        self.assertEqual(svg.count("stroke-dasharray"), 0)
        self.assertIn('cx="100" cy="100" r="22"', svg)
        self.assertIn('fill="none"></circle>', svg)


    def test_all_four_horns_at_the_right_angles(self):

        svg = nse.booby_trap_control_measure_svg()

        for coordinate in (
            "M115.6,84.4 L131.9,68.1",   # 45 degrees
            "M84.4,84.4 L68.1,68.1",     # 135 degrees
            "M84.4,115.6 L68.1,131.9",   # 225 degrees
            "M115.6,115.6 L131.9,131.9", # 315 degrees
        ):
            with self.subTest(coordinate=coordinate):
                self.assertIn(coordinate, svg)


    def test_defaults_to_mine_green(self):

        svg = nse.booby_trap_control_measure_svg()

        self.assertIn(nse.MINE_GREEN, svg)


    def test_accepts_a_colour_override(self):

        svg = nse.booby_trap_control_measure_svg("#000000")

        self.assertIn("#000000", svg)
        self.assertNotIn(nse.MINE_GREEN, svg)


class TestPillboxFixup(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_renders_hollow_with_real_affiliation_colour(self):

        # Reported live: "pillbox is rendering as filled rectangle, it
        # should be just the outline, no fill" - milsymbol's own
        # `fill: false` option does nothing for this icon (confirmed
        # live: fill matched stroke either way), so this is a
        # post-render fixup instead. Affiliation colouring is otherwise
        # untouched NATO behaviour (Part C) - friend/neutral/unknown
        # render black, hostile renders red, same as every other entity
        # on this layer.
        friend_svg = nse.render_nonnato_pillbox_svg("friend")
        hostile_svg = nse.render_nonnato_pillbox_svg("hostile")

        for svg in (friend_svg, hostile_svg):

            self.assertTrue(svg.startswith("<svg"))
            self.assertIn('fill="none"', svg)

        self.assertIn("black", friend_svg)
        self.assertIn("255, 0, 0", hostile_svg)


    def test_the_designation_is_injected_because_milsymbol_draws_none(self):

        # Confirmed live: `shelter`'s own milsymbol icon defines NO
        # designation slot at all - uniqueDesignation/uniqueDesignation1
        # /additionalInformation/additionalInformation1 all draw
        # identically with or without one. That was accepted behaviour
        # until 2026-09-24, when the maintainer took the fix across
        # every entity milsymbol will not designate; Pill Box now gets
        # one injected here, to the right of its own ink.
        without = nse.render_nonnato_pillbox_svg("friend")
        with_designation = nse.render_nonnato_pillbox_svg(
            "friend", designation="a1"
        )

        self.assertNotIn("<text", without)

        assert_only_gained_a_designation(
            self, with_designation, without, "A1"
        )


    def test_status_makes_no_visible_difference(self):

        # Confirmed live: milsymbol only dashes a FRAME's own stroke
        # for Planned status, and Pill Box (like every other bare-
        # glyph control-measure point) has no frame - present vs
        # planned render byte-identical, same defect class already
        # documented for non-NATO Equipment/SIGINT.
        present = nse.render_nonnato_pillbox_svg("friend", status="present")
        planned = nse.render_nonnato_pillbox_svg("friend", status="planned")

        self.assertEqual(present, planned)


class TestVehicleFamily(QgisTestCase):

    """
    'B' Vehicle, 'C' Vehicle and Light Recce Vehicle - the three fully
    synthetic entities that replaced APP-6E's own real "vehicle" entity
    on Land Equipment, 2026-09-05.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _rect(self, svg):

        match = re.search(
            r'<rect x="(\S+)" y="(\S+)" width="(\S+)" height="(\S+)"', svg
        )

        self.assertIsNotNone(match, "no rectangle in the vehicle icon")

        return tuple(float(value) for value in match.groups())


    def test_the_rectangle_matches_the_land_unit_frames_own_dimensions(self):

        # "draw a rectangle, similar dimensions as land unit" - read as
        # the literal frame every Land Unit icon uses, 150 x 100 at
        # x 25..175, y 50..150.
        for entity in (
            nse.B_VEHICLE_ENTITY,
            nse.C_VEHICLE_ENTITY,
            nse.LIGHT_RECCE_VEHICLE_ENTITY,
        ):

            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                self.assertEqual(self._rect(svg), (25.0, 50.0, 150.0, 100.0))


    def test_two_wheels_follow_apv_wheeleds_own_rule_without_its_middle_one(self):

        # "draw two circles - similar to what we did for the APV
        # wheeled with the center wheel removed": radius = 1/3 of the
        # shape's own semi-minor axis (half the rectangle's height),
        # each wheel's own top touching the bottom edge, inset one
        # radius from the left/right edges.
        svg = nse.render_nonnato_equipment_svg("friend", nse.B_VEHICLE_ENTITY)

        wheels = re.findall(r'<circle cx="(\S+)" cy="(\S+)" r="(\S+)"', svg)

        self.assertEqual(len(wheels), 2)

        (left_x, left_y, radius), (right_x, right_y, _) = (
            tuple(float(value) for value in wheel) for wheel in wheels
        )

        self.assertAlmostEqual(radius, 100 / 2 / 3, places=3)
        self.assertAlmostEqual(left_y - radius, 150, places=3)
        self.assertAlmostEqual(right_y, left_y, places=3)
        self.assertAlmostEqual(left_x - radius, 25, places=3)
        self.assertAlmostEqual(right_x + radius, 175, places=3)


    def test_b_and_c_differ_only_by_their_own_letter(self):

        # "same construction for 'C' Vehicle except that 'B' is
        # replaced with 'C'" - nothing else about the two may drift
        # apart.
        b_svg = nse.render_nonnato_equipment_svg("friend", nse.B_VEHICLE_ENTITY)
        c_svg = nse.render_nonnato_equipment_svg("friend", nse.C_VEHICLE_ENTITY)

        self.assertIn(">B</text>", b_svg)
        self.assertIn(">C</text>", c_svg)

        self.assertEqual(b_svg.replace(">B</text>", ">C</text>"), c_svg)


    def test_the_letter_sits_in_the_rectangles_own_centre(self):

        # Qt's own SVG engine honours no dominant-baseline on either
        # version tested here, so the baseline is computed instead -
        # confirmed against a render, where the first draft's letter
        # sat a half cap-height high.
        svg = nse.render_nonnato_equipment_svg("friend", nse.B_VEHICLE_ENTITY)

        match = re.search(
            r'<text x="(\S+)" y="(\S+)"[^>]*font-size="(\S+)"[^>]*>B</text>', svg
        )

        x, baseline, font_size = (float(value) for value in match.groups())

        self.assertAlmostEqual(x, 100.0)

        # The cap's own vertical midpoint, using the same 0.7-of-font-
        # size estimate _text_element_bounds() works to.
        # places=2 rather than 3 purely because the baseline is written
        # out through "%g", which rounds it to six significant figures.
        self.assertAlmostEqual(baseline - font_size * 0.7 / 2, 100.0, places=2)

        self.assertNotIn("dominant-baseline", svg)


    def test_light_recce_carries_a_mast_and_no_letter(self):

        # "start with vehicle 'B', remove the alphabet B and put a "/"
        # on top of the rectangle" - the mark's own lower end touches
        # the rectangle's own top-left corner exactly, the same way
        # Armoured Recce Vehicle's own "/" meets the oval.
        svg = nse.render_nonnato_equipment_svg(
            "friend", nse.LIGHT_RECCE_VEHICLE_ENTITY
        )

        self.assertNotIn("</text>", svg)

        match = re.search(r'<path d="M(\S+),(\S+) L(\S+),(\S+)"', svg)

        x1, y1, x2, y2 = (float(value) for value in match.groups())

        self.assertAlmostEqual(x1, 25.0)
        self.assertAlmostEqual(y1, 50.0)

        # Above the rectangle and to its right - a "/" leaning the same
        # way Armoured Recce Vehicle's own does.
        self.assertLess(y2, 50.0)
        self.assertGreater(x2, x1)


    def test_the_mast_is_armoured_recce_vehicles_own_mark_grown_125_percent(self):

        # "increase the mast height of the light recce vehicle by 125%"
        # - 2.25x, read the same way every other "increase by N%" on
        # this branch has been, and applied uniformly so the mark keeps
        # Armoured Recce Vehicle's own angle.
        svg = nse.render_nonnato_equipment_svg(
            "friend", nse.LIGHT_RECCE_VEHICLE_ENTITY
        )

        x1, y1, x2, y2 = (
            float(value)
            for value in re.search(r'<path d="M(\S+),(\S+) L(\S+),(\S+)"', svg).groups()
        )

        self.assertAlmostEqual(
            y1 - y2, 2 * nse._ARMOURED_RECCE_VEHICLE_ARM * 2.25, places=3
        )
        self.assertAlmostEqual(
            x2 - x1, nse._ARMOURED_RECCE_VEHICLE_ARM * 2.25, places=3
        )


    def test_the_viewbox_holds_every_part_of_the_icon(self):

        # Nothing may fall outside the declared viewBox - the mast in
        # particular reaches well above the rectangle.
        for entity in (
            nse.B_VEHICLE_ENTITY,
            nse.C_VEHICLE_ENTITY,
            nse.LIGHT_RECCE_VEHICLE_ENTITY,
        ):

            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                vb_x, vb_y, vb_w, vb_h = (
                    float(value)
                    for value in nse._VIEWBOX_PATTERN.search(svg).groups()
                )

                left, top, width, height = nse._content_bounds(svg, None)

                self.assertGreaterEqual(left, vb_x)
                self.assertGreaterEqual(top, vb_y)
                self.assertLessEqual(left + width, vb_x + vb_w)
                self.assertLessEqual(top + height, vb_y + vb_h)


    def test_the_designation_clears_the_wheels(self):

        # These wheels ARE in the SVG (unlike Armoured Protected
        # Vehicle (Wheeled)'s), so the ordinary content-bounds
        # measurement already has to place the text below them.
        svg = nse.render_nonnato_equipment_svg(
            "friend", nse.B_VEHICLE_ENTITY, designation="a1"
        )

        baseline = float(
            re.search(r'<text x="\S+" y="(\S+)"[^>]*>A1</text>', svg).group(1)
        )

        wheel_bottom = 150 + 2 * (100 / 2 / 3)

        self.assertGreater(baseline - nse._DESIGNATION_FONT_SIZE, wheel_bottom)


    def test_they_are_synthetic_and_never_reach_a_sidc(self):

        for entity in (
            nse.B_VEHICLE_ENTITY,
            nse.C_VEHICLE_ENTITY,
            nse.LIGHT_RECCE_VEHICLE_ENTITY,
        ):

            with self.subTest(entity=entity):

                self.assertTrue(nse.is_synthetic_entity(entity))
                self.assertNotIn(entity, nse._EQUIPMENT_ENTITY_KEY_ALIASES)


    def test_they_take_the_affiliation_colour(self):

        # Not mines - these follow the ordinary six-colour palette.
        for affiliation, colour in nse.AFFILIATION_COLOURS.items():

            with self.subTest(affiliation=affiliation):

                svg = nse.render_nonnato_equipment_svg(
                    affiliation, nse.B_VEHICLE_ENTITY
                )

                self.assertIn(colour, svg)


class TestViewboxExpansionLeavesDrawnRectanglesAlone(QgisTestCase):

    """
    A real bug found 2026-09-05 while building the Vehicle family: the
    width/height rescale that follows a viewBox expansion matched the
    FIRST width="..." height="..." pair anywhere in the document. Every
    milsymbol render declares that pair on its own root <svg>, so it
    happened to be right for them - but an SVG hand-built in this
    module declares neither, and the first pair is then a <rect> the
    icon actually draws with. Invisible until a designation grew the
    viewBox.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_bar_mines_own_bar_keeps_its_height_under_a_designation(self):

        def bar(svg):
            return tuple(
                float(value)
                for value in re.search(
                    r'<rect x="\S+" y="\S+" width="(\S+)" height="(\S+)"', svg
                ).groups()
            )

        plain = nse.render_nonnato_equipment_svg("friend", nse.BAR_MINE_ENTITY)
        with_designation = nse.render_nonnato_equipment_svg(
            "friend", nse.BAR_MINE_ENTITY, designation="mf 12"
        )

        self.assertEqual(bar(plain), bar(with_designation))


    def test_a_root_declared_width_and_height_still_rescale(self):

        # The other half of the fix: a real milsymbol render, which DOES
        # declare both on its root, must still have them grown with the
        # viewBox - that is what QGIS sizes the marker by.
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" '
            'viewBox="46 46 108 108"><rect x="50" y="50" width="10" '
            'height="10"></rect></svg>'
        )

        grown = nse._expand_viewbox_for_rect(svg, 46, 46, 108, 216)

        self.assertIn('width="108" height="216"', grown)
        self.assertIn('<rect x="50" y="50" width="10" height="10">', grown)


class TestDesignationSizeIsUniformOnTheMap(QgisTestCase):

    """
    A designation must draw the same size on the map whatever viewBox
    its icon was authored in and whatever per-entity multiplier scales
    that icon - settled 2026-09-05, having been flagged and deliberately
    deferred when the Vehicle family's own strokes were compensated the
    same way.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _apparent_size(self, entity, marker_size_mm):

        """
        The designation's own rendered height in millimetres - font size
        in icon units times (marker size * multiplier / viewBox width),
        which is exactly how QGIS scales an SVG marker.
        """

        svg = nse.render_nonnato_equipment_svg("friend", entity, "a1")

        viewbox_width = float(nse._VIEWBOX_PATTERN.search(svg).group(3))

        font_size = float(
            re.search(r'<text x="\S+" y="\S+"[^>]*font-size="([\d.]+)"[^>]*>A1</text>', svg)
            .group(1)
        )

        multiplier = nse.nonnato_entity_size_multiplier(entity)

        return font_size * (marker_size_mm * multiplier / viewbox_width)


    def test_the_plain_case_is_unchanged(self):

        # An icon in milsymbol's own 108-wide viewBox with no
        # multiplier keeps the bare constant - the great majority of
        # entities, and the calibration everything else is measured
        # against.
        self.assertAlmostEqual(
            nse.designation_font_size_in_icon_units(108, 1.0),
            nse._DESIGNATION_FONT_SIZE,
        )


    def test_a_wider_viewbox_scales_the_font_up(self):

        # Its units are smaller on screen, so it needs more of them.
        self.assertAlmostEqual(
            nse.designation_font_size_in_icon_units(216, 1.0),
            nse._DESIGNATION_FONT_SIZE * 2,
        )


    def test_a_size_multiplier_scales_the_font_down(self):

        # The whole marker is already being scaled up, text included.
        self.assertAlmostEqual(
            nse.designation_font_size_in_icon_units(108, 2.0),
            nse._DESIGNATION_FONT_SIZE / 2,
        )


    def test_bar_mines_own_two_factors_cancel(self):

        # Bar Mine is why this is one formula rather than two separate
        # fixes: its 160-wide viewBox and its own 160/108 multiplier
        # cancel exactly, so its designation was already correct and
        # must come out of this unchanged.
        multiplier = nse.nonnato_entity_size_multiplier(nse.BAR_MINE_ENTITY)

        self.assertAlmostEqual(
            nse.designation_font_size_in_icon_units(160, multiplier),
            nse._DESIGNATION_FONT_SIZE,
        )


    def test_every_land_equipment_entity_draws_it_the_same_size(self):

        from MilitaryCartographyTools.military_symbology import (
            land_equipment_layer_nonnato as layer_module,
        )

        sizes = {
            entity: self._apparent_size(entity, layer_module.MARKER_SIZE_MM)
            for entity in layer_module.ENTITY_LABELS
        }

        reference = sizes["tank"]

        for entity, size in sizes.items():

            with self.subTest(entity=entity):

                # places=4 rather than exact: the font size reaches the
                # SVG through "%g", which rounds it to six significant
                # figures (28/1.8 becomes 15.5556).
                self.assertAlmostEqual(size, reference, places=4)


    def test_every_mine_draws_it_the_same_size(self):

        from MilitaryCartographyTools.military_symbology import (
            mines_and_obstacles_layer_nonnato as layer_module,
        )

        # Booby Trap never carries a designation at all, and Minefield
        # draws its own inside the frame as a count rather than below
        # the icon as a label - so neither has a designation to measure.
        entities = [
            entity for entity in layer_module.ENTITY_LABELS
            if entity not in (
                layer_module.BOOBY_TRAP_ENTITY,
                nse.MINEFIELD_WITH_NUMBER_ENTITY,
            )
        ]

        sizes = {
            entity: self._apparent_size(entity, layer_module.MARKER_SIZE_MM)
            for entity in entities
        }

        reference = sizes["land_mine"]

        for entity, size in sizes.items():

            with self.subTest(entity=entity):

                # places=4 rather than exact: the font size reaches the
                # SVG through "%g", which rounds it to six significant
                # figures (28/1.8 becomes 15.5556).
                self.assertAlmostEqual(size, reference, places=4)


    def test_a_long_designation_still_shrinks_to_fit(self):

        # The shrink-to-fit works off the COMPENSATED base, not the
        # bare constant - otherwise a wide-viewBox icon would either
        # never shrink or shrink at the wrong point.
        long_text = "A VERY LONG DESIGNATION INDEED"

        for entity in ("tank", nse.B_VEHICLE_ENTITY):

            with self.subTest(entity=entity):

                short = nse.render_nonnato_equipment_svg("friend", entity, "a1")
                long = nse.render_nonnato_equipment_svg("friend", entity, long_text)

                def font_size(svg):
                    return float(
                        re.search(r'font-size="([\d.]+)"[^>]*>[^<]*</text>\s*</svg>', svg)
                        .group(1)
                    )

                self.assertLess(font_size(long), font_size(short))


    def test_the_multiplier_table_is_the_single_source_of_truth(self):

        # Both layers build their own CASE expression from this table
        # rather than keeping a second copy - the split that caused the
        # Vehicle family's designation to be wrong in the first place.
        from MilitaryCartographyTools.military_symbology import (
            land_equipment_layer_nonnato as equipment,
            mines_and_obstacles_layer_nonnato as mines,
        )

        expression = nse.nonnato_entity_size_multiplier_expression(
            equipment.ENTITY_LABELS
        )

        self.assertIn("jammer", expression)
        self.assertIn(nse.B_VEHICLE_ENTITY, expression)

        # A layer never carries a branch for an entity it does not offer.
        self.assertNotIn(nse.BAR_MINE_ENTITY, expression)

        mine_expression = nse.nonnato_entity_size_multiplier_expression(
            mines.ENTITY_LABELS
        )

        self.assertIn(nse.BAR_MINE_ENTITY, mine_expression)
        self.assertNotIn("jammer", mine_expression)


    def test_an_entity_with_no_multiplier_gets_one(self):

        self.assertEqual(nse.nonnato_entity_size_multiplier("tank"), 1)


class TestTextBoundsIgnoreDominantBaseline(QgisTestCase):

    """
    Qt's own SVG module honours `dominant-baseline` on neither version
    this project tests against - measured directly, 2026-09-05, by
    rendering one letter with and without the attribute and comparing
    the painted rows (identical). _text_element_bounds() therefore
    treats `y` as the baseline always, which is what decides where a
    designation sits under a letter-glyph icon.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_qt_really_does_ignore_it(self):

        # The measurement the estimate is based on, kept as a test so
        # it fails loudly if a future Qt starts honouring the
        # attribute - at which point _text_element_bounds() has to
        # learn the distinction again.
        from qgis.PyQt.QtCore import QByteArray, QRectF
        from qgis.PyQt.QtGui import QColor, QImage, QPainter
        from qgis.PyQt.QtSvg import QSvgRenderer

        def painted_rows(attrs):

            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
                'baseProfile="tiny" viewBox="0 0 200 200">'
                '<text x="100" y="100" text-anchor="middle" font-size="40" '
                f'font-family="Arial" stroke="none" fill="#000000" {attrs}>X</text>'
                '</svg>'
            )

            image = QImage(200, 200, QImage.Format.Format_ARGB32)
            image.fill(QColor("white"))

            painter = QPainter(image)
            QSvgRenderer(QByteArray(svg.encode())).render(
                painter, QRectF(0, 0, 200, 200)
            )
            painter.end()

            rows = [
                y for y in range(200)
                if any(QColor(image.pixel(x, y)).value() < 200 for x in range(200))
            ]

            return (min(rows), max(rows)) if rows else None

        self.assertEqual(
            painted_rows(""), painted_rows('dominant-baseline="middle"')
        )


    def test_the_estimate_treats_y_as_the_baseline_either_way(self):

        plain = nse._text_element_bounds(100, 100, 'font-size="40"', "X")
        middle = nse._text_element_bounds(
            100, 100, 'font-size="40" dominant-baseline="middle"', "X"
        )

        self.assertEqual(plain, middle)

        _, top, _, height = plain

        self.assertAlmostEqual(top + height, 100.0)


    def test_a_letter_glyphs_designation_sits_close_under_it(self):

        # Improvised Explosives Device is a bare milsymbol <text> glyph
        # with the attribute, and was the icon this showed up on: its
        # designation used to sit half a cap height lower than the gap
        # asks for.
        plain = nse.render_nonnato_equipment_svg(
            "friend", "improvised_explosives_device"
        )
        svg = nse.render_nonnato_equipment_svg(
            "friend", "improvised_explosives_device", "a1"
        )

        # Measured on the icon WITHOUT the designation - the whole point
        # is where the text gets placed relative to the glyph alone.
        _, top, _, height = nse._content_bounds(plain, None)

        baseline = float(
            re.search(r'<text x="\S+" y="(\S+)"[^>]*>A1</text>', svg).group(1)
        )

        # Exactly one gap plus one font size below the glyph's own
        # measured bottom - the same rule every other icon follows.
        self.assertAlmostEqual(
            baseline,
            top + height + nse._DESIGNATION_GAP + nse._DESIGNATION_FONT_SIZE,
            places=3,
        )


class TestMobilityIndicators(QgisTestCase):

    """
    Tracked and Self-Propelled - the two marks any Land Equipment entity
    can carry below its glyph, added 2026-09-06. Drawn straight into the
    SVG: the "QGIS clips a shape added below milsymbol's own draw area"
    conclusion that made Armoured Protected Vehicle (Wheeled)'s wheels
    separate symbol layers was wrong, re-measured through a real map
    render on both QGIS versions, and confirmed by the maintainer.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _added_path(self, entity, mobility):

        plain = nse.render_nonnato_equipment_svg("friend", entity)
        marked = nse.render_nonnato_equipment_svg(
            "friend", entity, mobility=mobility
        )

        added = [
            d for d in re.findall(r'<path d="([^"]+)"', marked)
            if f'd="{d}"' not in plain
        ]

        self.assertEqual(len(added), 1, "expected exactly one added path")

        return added[0]


    def _numbers(self, path_d):

        return [float(n) for n in re.findall(r"-?[\d.]+", path_d)]


    def test_nothing_is_added_without_a_mobility_value(self):

        plain = nse.render_nonnato_equipment_svg("friend", "tank")

        for empty in (None, "", "unknown_value"):

            with self.subTest(mobility=empty):

                self.assertEqual(
                    nse.render_nonnato_equipment_svg(
                        "friend", "tank", mobility=empty
                    ),
                    plain,
                )


    def test_both_marks_touch_the_glyphs_own_bottom(self):

        # "the oval and rhombus should touch the glyph bottom" - no gap
        # at all, unlike a designation, which stands clear of the whole
        # icon.
        plain = nse.render_nonnato_equipment_svg("friend", "tank")

        _, top, _, height = nse._content_bounds(plain, None)

        glyph_bottom = top + height

        # The mark is positioned against the glyph's ink as measured at
        # injection time, which is BEFORE scale_svg_stroke_width()'s own
        # final, uniform 1.3x - so the finished outlines end up
        # overlapping by half of that extra width, on both shapes
        # equally. Which is what "touching" means for stroked geometry:
        # a hair of overlap, never a gap.
        half_added_stroke = 3 * (nse.DEFAULT_STROKE_SCALE - 1) / 2

        for mobility in (nse.MOBILITY_TRACKED, nse.MOBILITY_SELF_PROPELLED):

            with self.subTest(mobility=mobility):

                numbers = self._numbers(self._added_path("tank", mobility))

                # Every y in the added path, the smallest of which is
                # the mark's own top edge.
                ys = numbers[1::2]

                self.assertAlmostEqual(
                    min(ys), glyph_bottom, delta=half_added_stroke + 0.001
                )

                # ...and never a gap: the mark starts at or above the
                # measured bottom, so the two always meet.
                self.assertLessEqual(min(ys), glyph_bottom)


    def test_tracked_is_apvs_own_stadium_at_a_third_of_its_size(self):

        # "for tracked - we use the same glyph as in APV i.e. the
        # ellipse but it is 1/3 the size of the actual glyph".
        numbers = self._numbers(self._added_path("tank", nse.MOBILITY_TRACKED))

        xs, ys = numbers[0::2], numbers[1::2]

        self.assertAlmostEqual(max(xs) - min(xs), nse.TRACKED_WIDTH, places=3)
        self.assertAlmostEqual(max(ys) - min(ys), nse.TRACKED_HEIGHT, places=3)

        # A third of Armoured Protected Vehicle's own 100 x 40 bounding
        # box, and the same shape - a stadium, drawn with its own two
        # cubic caps, not an ellipse and not a rectangle.
        self.assertAlmostEqual(nse.TRACKED_WIDTH, 100 / 3, places=6)
        self.assertAlmostEqual(nse.TRACKED_HEIGHT, 40 / 3, places=6)

        self.assertEqual(
            self._added_path("tank", nse.MOBILITY_TRACKED).count("C"), 2
        )


    def test_self_propelled_is_a_diamond_a_third_of_the_standard_viewbox(self):

        # "for self-propelled - we need to add a diamond or rhombus -
        # size 1/3 of the standard rectangle view box".
        path = self._added_path("tank", nse.MOBILITY_SELF_PROPELLED)

        numbers = self._numbers(path)

        xs, ys = numbers[0::2], numbers[1::2]

        self.assertAlmostEqual(
            max(xs) - min(xs), nse.SELF_PROPELLED_SIZE, places=3
        )
        self.assertAlmostEqual(
            max(ys) - min(ys), nse.SELF_PROPELLED_SIZE, places=3
        )

        # A third of the standard 108 viewBox, less the 20% trim
        # asked for once it was seen rendered.
        self.assertAlmostEqual(
            nse.SELF_PROPELLED_SIZE, 108 / 3 * 0.8, places=6
        )

        # Four straight sides, no curves.
        self.assertNotIn("C", path)
        self.assertEqual(path.count("L"), 3)


    def test_a_mark_pushes_the_designation_down(self):

        # "so the unique designation text needs to shift if selected" -
        # this comes free, because the designation is placed from the
        # SVG's own measured ink and the mark is part of that ink.
        def baseline(mobility):
            svg = nse.render_nonnato_equipment_svg(
                "friend", "tank", "a1", mobility
            )
            return float(
                re.search(r'<text x="\S+" y="(\S+)"[^>]*>A1</text>', svg).group(1)
            )

        plain = baseline(None)

        for mobility in (nse.MOBILITY_TRACKED, nse.MOBILITY_SELF_PROPELLED):

            with self.subTest(mobility=mobility):

                self.assertGreater(baseline(mobility), plain)

        # ...and further for the taller of the two marks.
        self.assertGreater(
            baseline(nse.MOBILITY_SELF_PROPELLED),
            baseline(nse.MOBILITY_TRACKED),
        )


    def test_the_viewbox_grows_to_hold_the_marks_stroked_outline(self):

        # WITHOUT a designation as well as with - that distinction is
        # the whole bug this guards. The first version grew the viewBox
        # to the mark's geometry and left its stroke hanging ~1.95 units
        # outside, which a designation then hid by growing the box
        # further down: "the very bottom extremity is getting clipped,
        # however when we add the unique designation, it is ok"
        # (reported with a screenshot, 2026-09-06).
        for entity in ("tank", "howitzer", "armored_protected_vehicle"):

            for mobility in (nse.MOBILITY_TRACKED, nse.MOBILITY_SELF_PROPELLED):

                for designation in (None, "a1"):

                    with self.subTest(
                        entity=entity,
                        mobility=mobility,
                        designation=designation,
                    ):

                        self._assert_ink_inside_viewbox(
                            nse.render_nonnato_equipment_svg(
                                "friend", entity, designation, mobility
                            )
                        )


    def _assert_ink_inside_viewbox(self, svg):

        # _content_bounds() measures through QSvgRenderer, whose bounds
        # include the stroke - so this really does check the drawn
        # outline, not just the geometry.
        vb_x, vb_y, vb_w, vb_h = (
            float(value) for value in nse._VIEWBOX_PATTERN.search(svg).groups()
        )

        left, top, width, height = nse._content_bounds(svg, None)

        self.assertGreaterEqual(left, vb_x - 0.01)
        self.assertGreaterEqual(top, vb_y - 0.01)
        self.assertLessEqual(left + width, vb_x + vb_w + 0.01)
        self.assertLessEqual(top + height, vb_y + vb_h + 0.01)


    def test_the_viewbox_clears_the_stroke_by_exactly_half_its_width(self):

        # The specific number the clipping bug was short by, pinned so a
        # future change to DEFAULT_STROKE_SCALE cannot silently
        # reintroduce it.
        svg = nse.render_nonnato_equipment_svg(
            "friend", "tank", mobility=nse.MOBILITY_SELF_PROPELLED
        )

        vb_y, vb_h = (
            float(nse._VIEWBOX_PATTERN.search(svg).group(n)) for n in (2, 4)
        )

        lowest_geometry = max(
            self._numbers(self._added_path("tank", nse.MOBILITY_SELF_PROPELLED))[1::2]
        )

        self.assertAlmostEqual(
            vb_y + vb_h - lowest_geometry,
            3 * nse.DEFAULT_STROKE_SCALE / 2,
            places=3,
        )


    def test_it_takes_the_affiliation_colour(self):

        for affiliation, colour in nse.AFFILIATION_COLOURS.items():

            with self.subTest(affiliation=affiliation):

                svg = nse.render_nonnato_equipment_svg(
                    "friend" if False else affiliation,
                    "tank",
                    mobility=nse.MOBILITY_TRACKED,
                )

                self.assertIn(colour, svg)


    def test_the_dropdown_offers_exactly_none_tracked_and_self_propelled(self):

        self.assertEqual(
            nse.MOBILITY_LABELS,
            {
                "": "None",
                nse.MOBILITY_TRACKED: "Tracked",
                nse.MOBILITY_SELF_PROPELLED: "Self-Propelled",
            },
        )


class TestApvWheeledWheels(QgisTestCase):

    """
    Armoured Protected Vehicle (Wheeled)'s three wheels, drawn straight
    into the SVG since 2026-09-06. They were three separate QGIS
    simple-marker symbol layers for three days, on the strength of a
    clipping conclusion that turned out to be wrong - see
    apv_wheeled_marks().
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _wheels(self, svg):

        return [
            tuple(float(v) for v in wheel)
            for wheel in re.findall(
                r'<circle cx="(\S+?)" cy="(\S+?)" r="(\S+?)"', svg
            )
        ]


    def test_three_wheels_are_drawn_into_the_svg(self):

        svg = nse.render_nonnato_equipment_svg("friend", nse.APV_WHEELED_ENTITY)

        self.assertEqual(len(self._wheels(svg)), 3)


    def test_they_sit_on_the_ovals_own_edges(self):

        # "add three circles below the oval, slightly inside the edges,
        # touching the oval, radii size can be 1/3 of semi-minor axis" -
        # the oval's straight bottom edge is y=120, its straight sides
        # x=75 and x=125, and its semi-minor axis is 20.
        wheels = self._wheels(
            nse.render_nonnato_equipment_svg("friend", nse.APV_WHEELED_ENTITY)
        )

        (left_x, y, radius), (middle_x, _, _), (right_x, _, _) = wheels

        # places=3, not exact: the numbers reach the SVG through "%g",
        # which rounds them to six significant figures - so a coordinate
        # near 126.667 carries about three decimals of precision.
        self.assertAlmostEqual(radius, 20 / 3, places=3)
        self.assertAlmostEqual(y - radius, 120, places=3)
        self.assertAlmostEqual(left_x - radius, 75, places=3)
        self.assertAlmostEqual(right_x + radius, 125, places=3)
        self.assertAlmostEqual(middle_x, (left_x + right_x) / 2, places=3)


    def test_the_plain_apv_never_grows_wheels(self):

        plain = nse.render_nonnato_equipment_svg(
            "friend", "armored_protected_vehicle"
        )

        self.assertEqual(self._wheels(plain), [])


    def test_they_take_the_hulls_own_colour_and_line_weight(self):

        for affiliation, colour in nse.AFFILIATION_COLOURS.items():

            with self.subTest(affiliation=affiliation):

                svg = nse.render_nonnato_equipment_svg(
                    affiliation, nse.APV_WHEELED_ENTITY
                )

                circles = re.findall(r"<circle[^>]*>", svg)

                self.assertEqual(len(circles), 3)

                for circle in circles:

                    self.assertIn(f'stroke="{colour}"', circle)

                    # The same width the hull itself ends up with, after
                    # the module's own final uniform scaling.
                    self.assertIn(
                        f'stroke-width="{3 * nse.DEFAULT_STROKE_SCALE:g}"',
                        circle,
                    )


    def test_the_designation_drops_below_them_without_being_told(self):

        # The whole point of drawing them into the SVG: the designation
        # measures the icon's own ink, so it clears the wheels with no
        # min_content_bottom floor and no rendered-height expression.
        wheeled = nse.render_nonnato_equipment_svg(
            "friend", nse.APV_WHEELED_ENTITY, "a1"
        )
        plain = nse.render_nonnato_equipment_svg(
            "friend", "armored_protected_vehicle", "a1"
        )

        def baseline(svg):
            return float(
                re.search(r'<text x="\S+" y="(\S+)"[^>]*>A1</text>', svg).group(1)
            )

        wheels = self._wheels(wheeled)

        wheel_bottom = wheels[0][1] + wheels[0][2]

        self.assertGreater(
            baseline(wheeled) - nse._DESIGNATION_FONT_SIZE, wheel_bottom
        )

        # ...and lower than the same glyph without wheels.
        self.assertGreater(baseline(wheeled), baseline(plain))


    def test_a_mobility_mark_also_clears_them_on_its_own(self):

        svg = nse.render_nonnato_equipment_svg(
            "friend", nse.APV_WHEELED_ENTITY, mobility=nse.MOBILITY_TRACKED
        )

        wheels = self._wheels(svg)

        wheel_bottom = wheels[0][1] + wheels[0][2]

        mark_top = min(
            float(n)
            for n in re.findall(r"-?[\d.]+", re.findall(r'<path d="([^"]+)"', svg)[-1])[1::2]
        )

        self.assertGreaterEqual(mark_top, wheel_bottom - 0.001)


    def test_the_viewbox_holds_the_wheels_stroked_outline(self):

        # Same lesson the mobility mark's own clipping bug taught: grow
        # for the stroke, not just the geometry.
        for designation in (None, "a1"):

            with self.subTest(designation=designation):

                svg = nse.render_nonnato_equipment_svg(
                    "friend", nse.APV_WHEELED_ENTITY, designation
                )

                vb_x, vb_y, vb_w, vb_h = (
                    float(v) for v in nse._VIEWBOX_PATTERN.search(svg).groups()
                )

                left, top, width, height = nse._content_bounds(svg, None)

                self.assertGreaterEqual(left, vb_x - 0.01)
                self.assertGreaterEqual(top, vb_y - 0.01)
                self.assertLessEqual(left + width, vb_x + vb_w + 0.01)
                self.assertLessEqual(top + height, vb_y + vb_h + 0.01)


class TestEnemyQuestionMarks(QgisTestCase):

    """
    Enemy (Echelon / Designation / Type Unknown), added 2026-09-06 -
    the same two concentric rectangles Enemy (Info Unknown) has always
    drawn, differing only in where a "?" goes.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _render(self, entity, left=None, right=None):

        return nse.render_nonnato_unit_svg(
            "hostile", entity, "unspecified", "present", left, right, False
        )


    def _question(self, svg):

        match = re.search(
            r'<text x="(\S+?)" y="(\S+?)" text-anchor="(\w+?)"[^>]*'
            r'font-size="(\S+?)"[^>]*>\?</text>',
            svg,
        )

        self.assertIsNotNone(match, "no question mark in the icon")

        x, y, anchor, size = match.groups()

        return float(x), float(y), anchor, float(size)


    def test_info_unknown_is_untouched(self):

        # "enemy (info unknown) remains as is".
        svg = self._render(nse.ENEMY_INFO_UNKNOWN_ENTITY)

        self.assertNotIn("?", svg)
        self.assertEqual(svg.count("<rect"), 2)


    def test_all_four_share_the_same_two_rectangles(self):

        plain = self._render(nse.ENEMY_INFO_UNKNOWN_ENTITY)

        rects = re.findall(r"<rect[^>]*>", plain)

        for entity in nse.ENEMY_ENTITIES:

            with self.subTest(entity=entity):

                svg = self._render(entity)

                self.assertEqual(re.findall(r"<rect[^>]*>", svg), rects)


    def test_echelon_unknowns_mark_sits_above_the_glyph(self):

        # "add a ? on top of the glyph".
        svg = self._render(nse.ENEMY_ECHELON_UNKNOWN_ENTITY)

        x, baseline, anchor, size = self._question(svg)

        plain = self._render(nse.ENEMY_INFO_UNKNOWN_ENTITY)

        left, top, width, _ = nse._content_bounds(plain, None)

        self.assertEqual(anchor, "middle")
        self.assertAlmostEqual(x, left + width / 2, places=3)

        # Its own baseline is one gap above the glyph, so the whole
        # glyph is clear below it. The delta is half of what
        # scale_svg_stroke_width() adds to the frame's own 4-unit
        # stroke at the very end - the mark is placed against the ink
        # as measured BEFORE that final widening, same as every other
        # injected element here.
        half_added_stroke = 4 * (nse.DEFAULT_STROKE_SCALE - 1) / 2

        self.assertAlmostEqual(
            baseline,
            top - nse._DESIGNATION_GAP,
            delta=half_added_stroke + 0.001,
        )

        self.assertLess(baseline, top)


    def test_designation_unknowns_mark_sits_where_a_right_designation_would(self):

        # "add a ? to the right center of the glyph (same place as
        # unique designation right)" - taken literally: same anchor,
        # same baseline, same size as a real right designation.
        marked = self._render(nse.ENEMY_DESIGNATION_UNKNOWN_ENTITY)

        designated = self._render(nse.ENEMY_INFO_UNKNOWN_ENTITY, None, "1")

        real = re.search(
            r'<text x="(\S+?)" y="(\S+?)" text-anchor="(\w+?)"[^>]*'
            r'font-size="(\S+?)"[^>]*>1</text>',
            designated,
        )

        x, baseline, anchor, size = self._question(marked)

        self.assertEqual(anchor, real.group(3))
        self.assertAlmostEqual(x, float(real.group(1)), places=3)
        self.assertAlmostEqual(baseline, float(real.group(2)), places=3)
        self.assertAlmostEqual(size, float(real.group(4)), places=3)


    def test_type_unknowns_mark_sits_in_the_middle(self):

        # "add a ? in the center of the glyph".
        svg = self._render(nse.ENEMY_TYPE_UNKNOWN_ENTITY)

        x, baseline, anchor, size = self._question(svg)

        left, top, width, height = nse._content_bounds(
            self._render(nse.ENEMY_INFO_UNKNOWN_ENTITY), None
        )

        self.assertEqual(anchor, "middle")
        self.assertAlmostEqual(x, left + width / 2, places=3)

        # The cap box's own middle on the glyph's own middle, the same
        # rule the side designations follow.
        self.assertAlmostEqual(
            baseline - size * nse._CAP_HEIGHT_RATIO / 2,
            top + height / 2,
            places=3,
        )


    def test_a_typed_designation_keeps_its_own_place(self):

        # The "?" is injected AFTER the designations, so a real one is
        # never displaced - and on Designation Unknown the "?" steps
        # outside it instead of landing on top of it.
        marked = self._render(nse.ENEMY_DESIGNATION_UNKNOWN_ENTITY, "A", "1")

        plain = self._render(nse.ENEMY_INFO_UNKNOWN_ENTITY, "A", "1")

        for text in ("A", "1"):

            with self.subTest(designation=text):

                pattern = r'<text x="(\S+?)" y="(\S+?)"[^>]*>' + text + "</text>"

                self.assertEqual(
                    re.search(pattern, marked).groups(),
                    re.search(pattern, plain).groups(),
                )

        question_x, _, _, _ = self._question(marked)

        designation_x = float(
            re.search(r'<text x="(\S+?)"[^>]*>1</text>', marked).group(1)
        )

        self.assertGreater(question_x, designation_x)


    def test_they_are_all_hostile_red_whatever_the_affiliation(self):

        red = nse.AFFILIATION_COLOURS["hostile"]

        for entity in nse.ENEMY_ENTITIES:

            for affiliation in ("friend", "neutral", "unknown", "hostile"):

                with self.subTest(entity=entity, affiliation=affiliation):

                    svg = nse.render_nonnato_unit_svg(
                        affiliation, entity, "unspecified", "present",
                        None, None, False,
                    )

                    self.assertIn(red, svg)


    def test_the_viewbox_holds_every_mark(self):

        for entity in nse.ENEMY_ENTITIES:

            for left, right in ((None, None), ("A", "1")):

                with self.subTest(entity=entity, designations=(left, right)):

                    svg = self._render(entity, left, right)

                    vb_x, vb_y, vb_w, vb_h = (
                        float(v)
                        for v in nse._VIEWBOX_PATTERN.search(svg).groups()
                    )

                    l, t, w, h = nse._content_bounds(svg, None)

                    self.assertGreaterEqual(l, vb_x - 0.01)
                    self.assertGreaterEqual(t, vb_y - 0.01)
                    self.assertLessEqual(l + w, vb_x + vb_w + 0.01)
                    self.assertLessEqual(t + h, vb_y + vb_h + 0.01)


class TestMotorisedInfantry(QgisTestCase):

    """Infantry with the Vehicle family's own two wheels, added 2026-09-06."""

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _render(self, entity, left=None, right=None, echelon="unspecified"):

        return nse.render_nonnato_unit_svg(
            "friend", entity, echelon, "present", left, right, False
        )


    def test_it_is_infantrys_own_glyph_plus_two_wheels(self):

        plain = self._render("infantry")
        motorised = self._render(nse.MOTORISED_INFANTRY_ENTITY)

        # Every path infantry draws is still there, untouched.
        for path in re.findall(r"<path[^>]*>", plain):
            self.assertIn(path, motorised)

        self.assertEqual(plain.count("<circle"), 0)
        self.assertEqual(motorised.count("<circle"), 2)


    def test_the_wheels_are_the_vehicle_familys_own(self):

        # "add the two wheels under it (from the B vehicle or C vehicle
        # glyphs in land equipment)" - literally those, reusing the same
        # constants, which line up because the Land Unit frame and the
        # Vehicle body are the same 150 x 100 rectangle.
        svg = self._render(nse.MOTORISED_INFANTRY_ENTITY)

        wheels = [
            tuple(float(v) for v in w)
            for w in re.findall(r'<circle cx="(\S+?)" cy="(\S+?)" r="(\S+?)"', svg)
        ]

        expected_xs = sorted(nse._VEHICLE_WHEEL_CENTRE_XS)

        for (x, y, radius), expected_x in zip(wheels, expected_xs):

            self.assertAlmostEqual(x, expected_x, places=3)
            self.assertAlmostEqual(y, nse._VEHICLE_WHEEL_CENTRE_Y, places=3)
            self.assertAlmostEqual(radius, nse._VEHICLE_WHEEL_RADIUS, places=3)

        # Their own tops touch the frame's own bottom edge (y=150).
        self.assertAlmostEqual(
            nse._VEHICLE_WHEEL_CENTRE_Y - nse._VEHICLE_WHEEL_RADIUS, 150, places=6
        )


    def test_it_resolves_to_infantrys_own_real_sidc(self):

        self.assertEqual(
            nse._UNIT_ENTITY_KEY_ALIASES[nse.MOTORISED_INFANTRY_ENTITY], "infantry"
        )


    def test_the_designations_stay_centred_on_the_frame(self):

        # The wheels are injected AFTER the designations, so they never
        # drag the side text down with them.
        motorised = self._render(nse.MOTORISED_INFANTRY_ENTITY, "A", "1")
        plain = self._render("infantry", "A", "1")

        for text in ("A", "1"):

            with self.subTest(designation=text):

                pattern = r'<text x="(\S+?)" y="(\S+?)"[^>]*>' + text + "</text>"

                self.assertEqual(
                    re.search(pattern, motorised).groups(),
                    re.search(pattern, plain).groups(),
                )


    def test_the_viewbox_holds_the_wheels(self):

        for echelon in ("unspecified", "battalion"):

            for designations in ((None, None), ("A", "1")):

                with self.subTest(echelon=echelon, designations=designations):

                    svg = self._render(
                        nse.MOTORISED_INFANTRY_ENTITY, *designations,
                        echelon=echelon,
                    )

                    vb_x, vb_y, vb_w, vb_h = (
                        float(v)
                        for v in nse._VIEWBOX_PATTERN.search(svg).groups()
                    )

                    l, t, w, h = nse._content_bounds(svg, None)

                    self.assertGreaterEqual(l, vb_x - 0.01)
                    self.assertGreaterEqual(t, vb_y - 0.01)
                    self.assertLessEqual(l + w, vb_x + vb_w + 0.01)
                    self.assertLessEqual(t + h, vb_y + vb_h + 0.01)


class TestAdminLogisticsUnit(QgisTestCase):

    """A bare circle at the Land Unit frame's own height, added 2026-09-06."""

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _render(self, left=None, right=None, affiliation="friend"):

        return nse.render_nonnato_unit_svg(
            "friend" if affiliation is None else affiliation,
            nse.ADMIN_LOGISTICS_ENTITY,
            "unspecified", "present", left, right, False,
        )


    def test_it_is_one_circle_and_nothing_else(self):

        svg = self._render()

        self.assertEqual(svg.count("<circle"), 1)
        self.assertEqual(svg.count("<path"), 0)
        self.assertEqual(svg.count("<rect"), 0)


    def test_it_matches_the_frames_own_vertical_extent(self):

        # "same dimensions as the rectangle of land units" - the frame
        # is 150 x 100 at x 25..175, y 50..150, so the circle shares its
        # top and bottom edges.
        svg = self._render()

        x, y, radius = (
            float(v)
            for v in re.search(
                r'<circle cx="(\S+?)" cy="(\S+?)" r="(\S+?)"', svg
            ).groups()
        )

        self.assertAlmostEqual(x, 100.0)
        self.assertAlmostEqual(y, 100.0)
        self.assertAlmostEqual(y - radius, 50.0)
        self.assertAlmostEqual(y + radius, 150.0)


    def test_it_follows_the_affiliation_colour(self):

        # Unlike the Enemy family, this one is NOT pinned to a colour.
        for affiliation, colour in nse.AFFILIATION_COLOURS.items():

            with self.subTest(affiliation=affiliation):

                self.assertIn(colour, self._render(affiliation=affiliation))


    def test_it_takes_both_side_designations(self):

        # "option to add unique designation left/right as existing".
        svg = self._render("A", "1")

        self.assertIn(">A</text>", svg)
        self.assertIn(">1</text>", svg)

        left_x = float(re.search(r'<text x="(\S+?)"[^>]*>A</text>', svg).group(1))
        right_x = float(re.search(r'<text x="(\S+?)"[^>]*>1</text>', svg).group(1))

        # Measured off the CIRCLE's own edges (x 50..150), not the
        # rectangle's - inject_side_designations() measures real ink.
        self.assertLess(left_x, 50)
        self.assertGreater(right_x, 150)


class TestHeadquartersFlagMast(QgisTestCase):

    """
    milsymbol's own Field S amplifier, exposed on the non-NATO Land Unit
    layer 2026-09-06 - "there is a choice for Headquarters in the NATO
    symbology wherein a flag mast is added to the glyph - implement the
    same in non-nato also".
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _render(self, entity="infantry", headquarters=False):

        return nse.render_nonnato_unit_svg(
            "friend", entity, "unspecified", "present", None, None,
            False, headquarters,
        )


    def test_it_adds_a_mast_and_defaults_to_off(self):

        plain = self._render()
        hq = self._render(headquarters=True)

        self.assertNotEqual(plain, hq)

        # Off by default - the same icon as passing it explicitly False.
        self.assertEqual(
            plain,
            nse.render_nonnato_unit_svg(
                "friend", "infantry", "unspecified", "present", None, None, False
            ),
        )


    def test_the_mast_reaches_below_the_frame(self):

        hq = self._render(headquarters=True)

        _, _, _, plain_height = nse._content_bounds(self._render(), None)
        _, _, _, hq_height = nse._content_bounds(hq, None)

        self.assertGreater(hq_height, plain_height)


    def test_it_works_alongside_the_scheme_s_own_additions(self):

        # Motorised Infantry's wheels are injected after milsymbol has
        # already drawn the mast - both must survive.
        svg = self._render(nse.MOTORISED_INFANTRY_ENTITY, headquarters=True)

        self.assertEqual(svg.count("<circle"), 2)

        self.assertNotEqual(
            svg, self._render(nse.MOTORISED_INFANTRY_ENTITY)
        )


    def test_the_enemy_entities_ignore_it(self):

        # They never reach a SIDC, so there is nothing for milsymbol to
        # amplify - documented behaviour, not an oversight.
        for entity in nse.ENEMY_ENTITIES:

            with self.subTest(entity=entity):

                self.assertEqual(
                    self._render(entity), self._render(entity, headquarters=True)
                )


class TestStaticFormationHeadquarters(QgisTestCase):

    """A pennant-shaped frame carrying the HQ mast, added 2026-09-06."""

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _render(self, left=None, right=None, affiliation="friend"):

        return nse.render_nonnato_unit_svg(
            affiliation, nse.STATIC_FORMATION_HQ_ENTITY,
            "unspecified", "present", left, right, False,
        )


    def test_the_outline_is_the_frame_with_its_right_side_notched_in(self):

        # "instead of right line of rectangle - replace with a < the
        # resulting rectangle looks like a flag".
        svg = self._render()

        outline = re.findall(r'<path d="([^"]+)"', svg)[0]

        numbers = [float(n) for n in re.findall(r"-?[\d.]+", outline)]

        xs, ys = numbers[0::2], numbers[1::2]

        # Three corners still at the frame's own edges...
        self.assertAlmostEqual(min(xs), 25.0)
        self.assertAlmostEqual(max(xs), 175.0)
        self.assertAlmostEqual(min(ys), 50.0)
        self.assertAlmostEqual(max(ys), 150.0)

        # ...and the notch vertex on the centre line, inside the right
        # edge, which is what makes it a pennant rather than a rectangle.
        self.assertIn(100.0, ys)

        notch_x = xs[ys.index(100.0)]

        self.assertLess(notch_x, 175.0)
        self.assertGreater(notch_x, 25.0)


    def test_it_carries_milsymbols_own_headquarters_mast(self):

        # Copied from a real HQ render rather than guessed - the same
        # path milsymbol emits for headquarters=True.
        real = nse.render_nonnato_unit_svg(
            "friend", "infantry", "unspecified", "present", None, None, False, True
        )

        mast = re.search(r'<path d="(M25,150 L25,250)"', real)

        self.assertIsNotNone(mast, "milsymbol's own mast path changed")

        self.assertIn('d="M25,150 L25,250"', self._render())


    def test_it_follows_the_affiliation_colour(self):

        for affiliation, colour in nse.AFFILIATION_COLOURS.items():

            with self.subTest(affiliation=affiliation):

                self.assertIn(colour, self._render(affiliation=affiliation))


    def test_it_takes_both_side_designations_on_the_frames_own_centre(self):

        svg = self._render("A", "1")

        for text in ("A", "1"):

            with self.subTest(designation=text):

                baseline = float(
                    re.search(
                        r'<text x="\S+" y="(\S+)"[^>]*>' + text + "</text>", svg
                    ).group(1)
                )

                cap = nse._SIDE_DESIGNATION_FONT_SIZE * nse._CAP_HEIGHT_RATIO

                self.assertAlmostEqual(
                    baseline - cap / 2, nse._UNIT_FRAME_CENTRE_Y, places=3
                )


class TestSideDesignationsCentreOnTheFrame(QgisTestCase):

    """
    "even in normal headquarters - the unique designations should be
    center of the rectangle and not the entire glyph" (2026-09-06). They
    used to centre on the icon's own measured ink, which the HQ mast and
    every echelon amplifier both move.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _baseline(self, svg, text):

        return float(
            re.search(
                r'<text x="\S+" y="(\S+)"[^>]*>' + text + "</text>", svg
            ).group(1)
        )


    def test_the_mast_no_longer_drags_them_down(self):

        plain = nse.render_nonnato_unit_svg(
            "friend", "infantry", "unspecified", "present", "A", "1", False
        )
        hq = nse.render_nonnato_unit_svg(
            "friend", "infantry", "unspecified", "present", "A", "1", False, True
        )

        self.assertEqual(self._baseline(plain, "A"), self._baseline(hq, "A"))


    def test_an_echelon_amplifier_no_longer_drags_them_up(self):

        # The same drift, present since long before the mast existed:
        # measured, a battalion's own amplifier moved the centre from
        # 100 to 82.6.
        baselines = {
            echelon: self._baseline(
                nse.render_nonnato_unit_svg(
                    "friend", "infantry", echelon, "present", "A", "1", False
                ),
                "A",
            )
            for echelon in ("unspecified", "battalion", "army_group")
        }

        self.assertEqual(len(set(baselines.values())), 1)


    def test_they_sit_on_the_frames_own_centre_for_every_entity(self):

        from MilitaryCartographyTools.military_symbology import (
            land_unit_layer_nonnato as layer_module,
        )

        cap = nse._SIDE_DESIGNATION_FONT_SIZE * nse._CAP_HEIGHT_RATIO

        for entity in layer_module.ENTITY_LABELS:

            with self.subTest(entity=entity):

                svg = nse.render_nonnato_unit_svg(
                    "friend", entity, "unspecified", "present", "A", "1", False
                )

                self.assertAlmostEqual(
                    self._baseline(svg, "A") - cap / 2,
                    nse._UNIT_FRAME_CENTRE_Y,
                    places=3,
                )


    def test_the_frame_really_is_where_this_says_it_is(self):

        # The constants are only safe because milsymbol's own frame path
        # never moves - pinned here so a milsymbol update cannot shift
        # it silently.
        svg = nse.render_nonnato_unit_svg("friend", "infantry")

        self.assertIn("M25,50 l150,0 0,100 -150,0 z", svg)

        self.assertEqual(nse._UNIT_FRAME_CENTRE_Y, 100)


class TestArtilleryVariants(QgisTestCase):

    """
    Self Propelled Artillery and Parachute Field Artillery, added
    2026-09-06 - both on the real `field_artillery` glyph.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _render(self, entity, left=None, right=None):

        return nse.render_nonnato_unit_svg(
            "friend", entity, "unspecified", "present", left, right, False
        )


    def test_both_keep_artillerys_own_filled_dot(self):

        artillery = self._render("field_artillery")

        dot = re.search(r"<circle[^>]*>", artillery).group(0)

        for entity in (
            nse.SELF_PROPELLED_ARTILLERY_ENTITY,
            nse.PARACHUTE_FIELD_ARTILLERY_ENTITY,
        ):

            with self.subTest(entity=entity):

                self.assertIn(dot, self._render(entity))


    def test_both_resolve_to_artillerys_own_real_sidc(self):

        for entity in (
            nse.SELF_PROPELLED_ARTILLERY_ENTITY,
            nse.PARACHUTE_FIELD_ARTILLERY_ENTITY,
        ):

            with self.subTest(entity=entity):

                self.assertEqual(
                    nse._UNIT_ENTITY_KEY_ALIASES[entity], "field_artillery"
                )


    def test_self_propelled_adds_three_wheels_on_the_apv_rule(self):

        # "add three wheels (same as APV wheeled)" - that icon's own
        # rule, applied to this frame: radius a third of the shape's
        # semi-minor axis, tops touching its bottom edge, outer two
        # inset one radius, middle centring the group.
        svg = self._render(nse.SELF_PROPELLED_ARTILLERY_ENTITY)

        wheels = [
            tuple(float(v) for v in w)
            for w in re.findall(r'<circle cx="(\S+?)" cy="(\S+?)" r="(\S+?)"', svg)
        ]

        # The artillery dot is a circle too, so four in total.
        self.assertEqual(len(wheels), 4)

        wheels = sorted(w for w in wheels if w[2] != 15)

        self.assertEqual(len(wheels), 3)

        radius = wheels[0][2]

        self.assertAlmostEqual(radius, (150 - 50) / 2 / 3, places=3)

        for x, y, r in wheels:

            self.assertAlmostEqual(r, radius, places=6)
            self.assertAlmostEqual(y - radius, 150, places=3)

        self.assertAlmostEqual(wheels[0][0] - radius, 25, places=3)
        self.assertAlmostEqual(wheels[2][0] + radius, 175, places=3)
        self.assertAlmostEqual(wheels[1][0], 100, places=3)


    def test_its_wheels_match_motorised_infantrys_own(self):

        # Same layer, same frame - the two must not draw wheels at
        # different sizes.
        def wheel_radii(entity):
            return {
                float(r)
                for r in re.findall(
                    r'<circle cx="\S+?" cy="\S+?" r="(\S+?)"', self._render(entity)
                )
            } - {15.0}

        self.assertEqual(
            wheel_radii(nse.SELF_PROPELLED_ARTILLERY_ENTITY),
            wheel_radii(nse.MOTORISED_INFANTRY_ENTITY),
        )


    def test_parachute_variant_reuses_the_parachute_units_own_glyph(self):

        # "add the parachute symbol (from the Parachute unit)" - the
        # same PATH, so it is visibly the same object. The transform
        # differs on purpose since 2026-09-06: the variant's own canopy
        # was resized to clear Artillery's dot, which the Parachute
        # unit's own placement had no reason to allow for.
        parachute_unit = self._render("parachute_rigger")
        variant = self._render(nse.PARACHUTE_FIELD_ARTILLERY_ENTITY)

        self.assertIn(nse._PARACHUTE_GLYPH_D, parachute_unit)
        self.assertIn(nse._PARACHUTE_GLYPH_D, variant)

        self.assertIn(f'transform="{nse._PARACHUTE_GLYPH_TRANSFORM}"', parachute_unit)
        self.assertNotIn(f'transform="{nse._PARACHUTE_GLYPH_TRANSFORM}"', variant)


    def test_the_parachute_variant_has_no_infantry_diagonals(self):

        # It is built on Artillery, not on Infantry - the Parachute
        # unit's own diagonals must not come with it.
        variant = self._render(nse.PARACHUTE_FIELD_ARTILLERY_ENTITY)

        self.assertNotIn("M25,50 L175,150", variant)


class TestSignalJaggedLineMirrored(QgisTestCase):

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_it_runs_from_the_other_two_corners(self):

        # "horizontally invert the jagged line - it should touch the
        # other two vertices of the rectangle" (2026-09-06). milsymbol
        # draws it top-LEFT to bottom-RIGHT.
        svg = nse.render_nonnato_unit_svg("friend", "signal")

        self.assertIn(f'd="{nse._SIGNAL_JAGGED_LINE_MIRRORED_D}"', svg)
        self.assertNotIn(f'd="{nse._SIGNAL_JAGGED_LINE_D}"', svg)


    def test_it_is_a_true_horizontal_mirror(self):

        def points(d):
            numbers = [float(n) for n in re.findall(r"[\d.]+", d)]
            return list(zip(numbers[0::2], numbers[1::2]))

        original = points(nse._SIGNAL_JAGGED_LINE_D)
        mirrored = points(nse._SIGNAL_JAGGED_LINE_MIRRORED_D)

        centre = (25 + 175) / 2

        self.assertEqual(
            [(2 * centre - x, y) for x, y in original], mirrored
        )


class TestMilitaryPoliceDerivedEntities(QgisTestCase):

    """
    Six entities on Military Police's own framed glyph, added
    2026-09-06 - three swapping its "MP" for other letters, three
    swapping it for a shape.
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def _render(self, entity, echelon="unspecified", headquarters=False):

        return nse.render_nonnato_unit_svg(
            "friend", entity, echelon, "present", None, None, False, headquarters
        )


    def test_the_lettered_three_change_only_the_letters(self):

        # "replace MP with IW, PO and I respectively".
        police = self._render("military_police")

        for entity, letters in nse._LETTERED_MILITARY_POLICE_ENTITIES.items():

            with self.subTest(entity=entity):

                svg = self._render(entity)

                self.assertEqual(svg, police.replace(">MP</text>", f">{letters}</text>"))


    def test_the_reglyphed_three_drop_the_lettering_entirely(self):

        for entity in nse._MILITARY_POLICE_REGLYPHED:

            with self.subTest(entity=entity):

                svg = self._render(entity)

                self.assertNotIn("</text>", svg)
                self.assertIn("M25,50 l150,0 0,100 -150,0 z", svg)


    def test_all_six_keep_echelon_status_and_headquarters(self):

        # The reason they are built on a real render rather than as
        # standalone SVGs.
        entities = list(nse._LETTERED_MILITARY_POLICE_ENTITIES) + list(
            nse._MILITARY_POLICE_REGLYPHED
        )

        for entity in entities:

            with self.subTest(entity=entity):

                plain = self._render(entity)

                self.assertNotEqual(plain, self._render(entity, echelon="battalion"))
                self.assertNotEqual(plain, self._render(entity, headquarters=True))


    def test_supplies_and_transports_diagonals_stop_at_the_circle(self):

        # "add a X (two diagonals) inside the circle only" - they must
        # not run out to the frame's own corners.
        svg = self._render(nse.SUPPLIES_TRANSPORT_ENTITY)

        radius = float(
            re.search(r'<circle[^>]*r="(\S+?)"', svg).group(1)
        )

        cross = re.findall(r'<path d="(M[^"]+)"', svg)[-1]

        numbers = [float(n) for n in re.findall(r"[\d.]+", cross)]

        for x, y in zip(numbers[0::2], numbers[1::2]):

            # Every endpoint sits on the circle, not beyond it.
            distance = ((x - 100) ** 2 + (y - 100) ** 2) ** 0.5

            self.assertAlmostEqual(distance, radius, places=3)


    def test_ordnance_uses_the_mines_layers_own_booby_trap_shape(self):

        # "its booby trap not decoy" - literally the same geometry the
        # Mines and Obstacles layer draws, not a copy of it. Compared on
        # the shapes rather than the raw markup, since the unit render
        # widens every stroke at the end (3 -> 3.9) and the mines layer
        # has its own colour.
        def shapes(svg):
            return (
                re.findall(r'<circle cx="(\S+?)" cy="(\S+?)" r="(\S+?)"', svg),
                re.findall(r'<path d="([^"]+)"', svg),
            )

        ordnance_circles, ordnance_paths = shapes(
            self._render(nse.ORDNANCE_ENTITY)
        )
        trap_circles, trap_paths = shapes(nse.booby_trap_control_measure_svg())

        self.assertEqual(ordnance_circles, trap_circles)
        self.assertEqual(len(trap_paths), 4)

        # Every horn, plus the frame the Ordnance version draws around
        # them.
        for horn in trap_paths:
            self.assertIn(horn, ordnance_paths)

        self.assertEqual(len(ordnance_paths), len(trap_paths) + 1)


    def test_ordnance_takes_the_affiliation_colour_not_mine_green(self):

        # "the colour affiliation remains standard as per land units and
        # not green" - MINE_GREEN is the mines layer's own rule, not a
        # property of the shape.
        for affiliation, colour in nse.AFFILIATION_COLOURS.items():

            with self.subTest(affiliation=affiliation):

                svg = nse.render_nonnato_unit_svg(
                    affiliation, nse.ORDNANCE_ENTITY, "unspecified", "present"
                )

                self.assertIn(colour, svg)
                self.assertNotIn(nse.MINE_GREEN, svg)


    def test_the_mines_layers_own_booby_trap_is_still_green(self):

        # The refactor must not leak Land Unit's colouring back the
        # other way.
        self.assertIn(nse.MINE_GREEN, nse.booby_trap_control_measure_svg())


    def test_remount_runs_from_the_top_corners_to_the_bottom_centre(self):

        svg = self._render(nse.REMOUNT_VETERINARY_ENTITY)

        mark = re.findall(r'<path d="(M[^"]+)"', svg)[-1]

        numbers = [float(n) for n in re.findall(r"[\d.]+", mark)]

        points = list(zip(numbers[0::2], numbers[1::2]))

        self.assertEqual(points, [(25.0, 50.0), (100.0, 150.0), (175.0, 50.0)])


class TestParachuteFieldArtillerySizing(QgisTestCase):

    """
    "reduce the size of the parachute canopy just enough that it is
    clear of the dot and clear from the rectangle" (2026-09-06).
    """

    def setUp(self):

        super().setUp()

        symbol_engine._svg_cache.clear()


    def test_the_canopy_clears_the_dot_and_the_frame(self):

        scale = nse._PARACHUTE_ARTILLERY_SCALE
        half_stroke = scale * nse._PARACHUTE_STROKE_WIDTH / 2

        top = (
            nse._PARACHUTE_ARTILLERY_TRANSLATE_Y
            + scale * nse._PARACHUTE_NATIVE_TOP
            - half_stroke
        )
        bottom = (
            nse._PARACHUTE_ARTILLERY_TRANSLATE_Y
            + scale * nse._PARACHUTE_NATIVE_BOTTOM
            + half_stroke
        )

        dot_bottom = 100 + nse._ARTILLERY_DOT_RADIUS + 3 / 2
        frame_inner = nse._UNIT_FRAME_BOTTOM - 4 / 2

        self.assertGreaterEqual(top, dot_bottom + nse._PARACHUTE_CLEARANCE - 0.001)
        self.assertLessEqual(bottom, frame_inner - nse._PARACHUTE_CLEARANCE + 0.001)


    def test_it_is_smaller_than_the_parachute_units_own(self):

        self.assertLess(nse._PARACHUTE_ARTILLERY_SCALE, 0.8)


    def test_it_stays_horizontally_centred(self):

        centre = (
            nse._PARACHUTE_ARTILLERY_TRANSLATE_X
            + nse._PARACHUTE_ARTILLERY_SCALE * nse._PARACHUTE_NATIVE_CENTRE_X
        )

        self.assertAlmostEqual(centre, 100.0, places=6)


class TestBoobyTrapStrokeMatchesItsNeighbours(QgisTestCase):

    def test_the_layer_render_is_stroke_scaled(self):

        # Drew at 3 where every neighbour on Mines and Obstacles draws at
        # 3.9 - found on the Office companion, fixed 2026-09-17.
        svg = nse.render_nonnato_booby_trap_svg()

        widths = set(re.findall(r'stroke-width="([\d.]+)"', svg))

        self.assertEqual(widths, {"3.9"})


    def test_it_matches_antitank_mine_booby_trapped(self):

        booby_trap = nse.render_nonnato_booby_trap_svg()
        trapped = nse.render_nonnato_equipment_svg(
            "friend", nse.ANTITANK_MINE_BOOBY_TRAPPED_ENTITY
        )

        self.assertEqual(
            set(re.findall(r'stroke-width="([\d.]+)"', booby_trap)),
            set(re.findall(r'stroke-width="([\d.]+)"', trapped)),
        )


    def test_the_shared_shape_is_left_unscaled(self):

        # Land Unit's Ordnance shares these marks and scales them itself.
        self.assertIn('stroke-width="3"', nse.booby_trap_control_measure_svg())


class TestEchelonTouchesFrame(QgisTestCase):

    """
    Every echelon marker sits on the frame (2026-09-17, decided on the
    Office companion 2026-09-16) - see seat_echelon_on_frame().
    """

    ECHELONS = (
        "squad", "platoon", "company", "battalion", "brigade",
        "division", "corps", "army", "army_group",
    )

    FRAME_TOP_INK = 50 - 5.2 / 2


    def _drop(self, svg):

        match = re.search(r'<g transform="translate\(0,([\d.]+)\)"', svg)

        return float(match.group(1)) if match else 0.0


    def _marker_bottom_ink(self, svg):

        group = re.search(
            r'<g transform="translate\(0,[\d.]+\)" stroke-width=[^>]*>.*?</g>',
            svg, re.S,
        ).group(0)

        return nse._lowest_echelon_point(group) + 5.2 / 2 + self._drop(svg)


    def test_every_echelon_marker_touches_the_frame(self):

        for echelon in self.ECHELONS:

            with self.subTest(echelon=echelon):

                svg = nse.render_nonnato_unit_svg(
                    "friend", "infantry", echelon=echelon
                )

                self.assertGreater(self._drop(svg), 0)
                self.assertAlmostEqual(
                    self._marker_bottom_ink(svg), self.FRAME_TOP_INK, places=3
                )


    def test_the_gaps_it_closes_are_the_measured_ones(self):

        company = nse.render_nonnato_unit_svg("friend", "infantry", echelon="company")
        section = nse.render_nonnato_unit_svg("friend", "infantry", echelon="squad")

        self.assertAlmostEqual(self._drop(company), 4.8, places=6)
        self.assertAlmostEqual(self._drop(section), 7.3, places=6)


    def test_only_the_translate_changes(self):

        # Nothing inside the group, and not the viewBox, moves: undoing
        # the translate and seating again gives the same markup back.
        for echelon in self.ECHELONS:

            with self.subTest(echelon=echelon):

                svg = nse.render_nonnato_unit_svg(
                    "friend", "infantry", echelon=echelon, combined_arms=True
                )
                unseated = re.sub(
                    r'translate\(0,[\d.]+\)', "translate(0,0)", svg, count=1
                )

                self.assertNotEqual(svg, unseated)
                self.assertEqual(nse.seat_echelon_on_frame(unseated), svg)


    def test_no_echelon_and_detachment_are_left_alone(self):

        for echelon in ("unspecified", "team_crew"):

            with self.subTest(echelon=echelon):

                svg = nse.render_nonnato_unit_svg(
                    "friend", "infantry", echelon=echelon
                )

                self.assertEqual(self._drop(svg), 0.0)


    def test_frameless_aviation_glyphs_are_left_alone(self):

        for entity in nse.AVIATION_ENTITIES:

            with self.subTest(entity=entity):

                svg = nse.render_nonnato_unit_svg(
                    "friend", entity, echelon="company"
                )

                self.assertEqual(self._drop(svg), 0.0)


    def test_administration_or_logistics_circle_counts_as_the_frame(self):

        # "fix the admin/log echelons also" (2026-09-18) - the first pass
        # matched only the rectangle. The circle's top is the same y=50.
        for echelon in self.ECHELONS:

            with self.subTest(echelon=echelon):

                svg = nse.render_nonnato_unit_svg(
                    "friend", nse.ADMIN_LOGISTICS_ENTITY, echelon=echelon
                )

                self.assertGreater(self._drop(svg), 0)
                self.assertAlmostEqual(
                    self._marker_bottom_ink(svg), self.FRAME_TOP_INK, places=3
                )


    def test_static_formation_headquarters_pennant_counts_as_the_frame(self):

        # "fix the static formation echelons also" (2026-09-18).
        for echelon in self.ECHELONS:

            with self.subTest(echelon=echelon):

                svg = nse.render_nonnato_unit_svg(
                    "friend", nse.STATIC_FORMATION_HQ_ENTITY, echelon=echelon
                )

                self.assertGreater(self._drop(svg), 0)
                self.assertAlmostEqual(
                    self._marker_bottom_ink(svg), self.FRAME_TOP_INK, places=3
                )


    def test_an_unknown_path_command_raises_rather_than_mismeasuring(self):

        with self.assertRaises(ValueError):
            nse._lowest_echelon_point('<g><path d="M100,40 C1,2 3,4 5,6"></path></g>')


class TestControlMeasurePoints(QgisTestCase):

    """render_nonnato_control_measure_svg() - see its own docstring."""

    AFFILIATIONS = ("friend", "hostile", "neutral", "unknown")


    def _milsymbol(self, affiliation, entity, status="present", designation=""):

        # The pipeline these entities used before 2026-09-17: the layer's
        # own mct_sidc_svg(mct_build_sidc(...)) at the default stroke
        # scale, with milsymbol's own designation slot.
        sidc = build_sidc(
            affiliation=affiliation, entity=entity,
            symbol_set="control_measure", echelon="unspecified",
            status=status, headquarters=False, edition="2525E",
        )
        options = {"uniqueDesignation": designation} if designation else None

        return nse.scale_svg_stroke_width(
            nse.render_symbol_svg(sidc, options), nse.DEFAULT_STROKE_SCALE
        )


    def _cases(self):

        for affiliation in self.AFFILIATIONS:
            for status in ("present", "planned"):
                for designation in ("", "A1"):
                    yield affiliation, status, designation


    def test_fort_and_the_shelters_are_unchanged_but_for_a_designation(self):

        # All three are in UNDESIGNATED_BY_MILSYMBOL: milsymbol draws
        # them no designation, so since 2026-09-24 one is injected
        # here. Undesignated they are still byte-for-byte milsymbol's
        # own; designated, the injected text and the room made for it
        # are the ONLY differences - verified by removal rather than by
        # rebuilding the expected markup.
        for entity in ("fort", "shelter_above_ground", "shelter_below_ground"):
            for affiliation, status, designation in self._cases():

                with self.subTest(entity=entity, affiliation=affiliation, status=status, designation=designation):

                    svg = nse.render_nonnato_control_measure_svg(
                        affiliation, entity, status, designation
                    )

                    if not designation:

                        self.assertEqual(
                            svg,
                            self._milsymbol(affiliation, entity, status, ""),
                        )

                        continue

                    assert_only_gained_a_designation(
                        self,
                        svg,
                        self._milsymbol(affiliation, entity, status, ""),
                        designation,
                    )


    def test_pill_box_is_unchanged(self):

        for affiliation, status, designation in self._cases():

            with self.subTest(affiliation=affiliation, status=status, designation=designation):

                self.assertEqual(
                    nse.render_nonnato_control_measure_svg(
                        affiliation, "shelter", status, designation
                    ),
                    nse.render_nonnato_pillbox_svg(
                        affiliation, status, designation or None
                    ),
                )


    def test_pill_box_gains_only_its_designation(self):

        for affiliation, status, _ in self._cases():

            with self.subTest(affiliation=affiliation, status=status):

                assert_only_gained_a_designation(
                    self,
                    nse.render_nonnato_control_measure_svg(
                        affiliation, "shelter", status, "A1"
                    ),
                    nse.render_nonnato_control_measure_svg(
                        affiliation, "shelter", status, ""
                    ),
                    "A1",
                )


    def test_the_six_take_the_affiliation_palette_and_nothing_else_changes(self):

        for entity in sorted(nse.CONTROL_MEASURE_PALETTE_ENTITIES):
            for affiliation, status, designation in self._cases():

                with self.subTest(entity=entity, affiliation=affiliation, status=status, designation=designation):

                    svg = nse.render_nonnato_control_measure_svg(
                        affiliation, entity, status, designation
                    )
                    colour = nse.AFFILIATION_COLOURS[affiliation]

                    self.assertIn(colour, svg)
                    self.assertNotIn('"black"', svg)
                    self.assertNotIn("rgb(255, 0, 0)", svg)

                    # Three of the six are also in
                    # UNDESIGNATED_BY_MILSYMBOL, so their designation
                    # is injected here rather than asked of milsymbol
                    # - compare against the undesignated render and
                    # take the text back off.
                    injected = (
                        designation
                        and entity in nse.UNDESIGNATED_BY_MILSYMBOL
                    )

                    before = self._milsymbol(
                        affiliation, entity, status,
                        "" if injected else designation,
                    )

                    expected = re.sub(
                        r'(stroke|fill)="(black|rgb\(255, 0, 0\))"',
                        r'\1="X"',
                        before,
                    )

                    if injected:

                        assert_only_gained_a_designation(
                            self,
                            svg.replace(colour, "X"),
                            expected,
                            designation,
                        )

                        continue

                    self.assertEqual(svg.replace(colour, "X"), expected)


    def test_nbc_shelter_is_a_hollow_shelter_below_ground(self):

        svg = nse.render_nonnato_control_measure_svg("friend", nse.NBC_SHELTER_ENTITY)
        shelter = self._milsymbol("friend", "shelter_below_ground")

        shelter_d = re.search(r' d="([^"]+)"', shelter).group(1)

        self.assertIn(f'd="{shelter_d}"', svg)
        self.assertIn('fill="none"', svg)
        self.assertNotIn('fill="black" ></path>', svg)


    def test_nbc_shelter_says_nbc_to_its_right_unless_told_otherwise(self):

        default = nse.render_nonnato_control_measure_svg("friend", nse.NBC_SHELTER_ENTITY)
        typed = nse.render_nonnato_control_measure_svg(
            "friend", nse.NBC_SHELTER_ENTITY, designation="a1"
        )
        bare = nse.render_nonnato_control_measure_svg(
            "friend", nse.NBC_SHELTER_ENTITY, default_designation=False
        )

        self.assertIn('text-anchor="start"', default)
        self.assertIn(">NBC</text>", default)
        self.assertIn(">A1</text>", typed)
        self.assertNotIn("NBC", typed)
        self.assertNotIn("<text", bare)

        # To the right of the ground line's far end (x=150).
        x = float(re.search(r'<text x="([\d.]+)"', default).group(1))
        self.assertGreater(x, 150)


    def test_nbc_shelter_keeps_milsymbols_colours(self):

        friend = nse.render_nonnato_control_measure_svg("friend", nse.NBC_SHELTER_ENTITY)
        hostile = nse.render_nonnato_control_measure_svg("hostile", nse.NBC_SHELTER_ENTITY)

        self.assertIn('stroke="black"', friend)
        self.assertIn('fill="black">NBC', friend)
        self.assertIn('stroke="rgb(255, 0, 0)"', hostile)
        self.assertIn('fill="rgb(255, 0, 0)">NBC', hostile)


    def test_command_post_is_military_police_relettered(self):

        for affiliation in self.AFFILIATIONS:

            with self.subTest(affiliation=affiliation):

                svg = nse.render_nonnato_control_measure_svg(
                    affiliation, nse.COMMAND_POST_ENTITY
                )
                police = nse.render_nonnato_unit_svg(affiliation, "military_police")

                self.assertEqual(svg, police.replace(">MP</text>", ">CP</text>"))
                self.assertIn(nse.AFFILIATION_COLOURS[affiliation], svg)


    def test_command_post_dashes_when_planned_and_designates_to_the_right(self):

        svg = nse.render_nonnato_control_measure_svg(
            "friend", nse.COMMAND_POST_ENTITY, "planned", "12"
        )

        self.assertIn("stroke-dasharray", svg)
        self.assertIn('text-anchor="start"', svg)
        self.assertIn(">12</text>", svg)


    def test_fire_trench_is_a_rectangle_open_at_the_bottom(self):

        svg = nse.render_nonnato_control_measure_svg("friend", nse.FIRE_TRENCH_ENTITY)

        self.assertEqual(svg.count("<path"), 1)
        self.assertIn('d="M55,122.5 L55,77.5 L145,77.5 L145,122.5"', svg)
        self.assertNotIn("z", re.search(r' d="([^"]+)"', svg).group(1).lower())
        self.assertIn('fill="none"', svg)
        self.assertIn('stroke-width="3.9"', svg)


    def test_fire_trench_is_coloured_like_its_fortification_neighbours(self):

        self.assertIn(
            'stroke="black"',
            nse.render_nonnato_control_measure_svg("neutral", nse.FIRE_TRENCH_ENTITY),
        )
        self.assertIn(
            'stroke="rgb(255, 0, 0)"',
            nse.render_nonnato_control_measure_svg("hostile", nse.FIRE_TRENCH_ENTITY),
        )


    def test_fire_trench_designates_to_the_right(self):

        svg = nse.render_nonnato_control_measure_svg(
            "friend", nse.FIRE_TRENCH_ENTITY, designation="3"
        )

        x = float(re.search(r'<text x="([\d.]+)"', svg).group(1))

        self.assertGreater(x, 145)
        self.assertIn(">3</text>", svg)



class TestForcesInDefence(QgisTestCase):

    """
    The open ellipse, and the echelon row that lies across its opening
    - see nonnato_symbol_engine's own Forces in Defence comments.
    """

    ECHELONS = (
        "unspecified",
        "team_crew",
        "squad",
        "platoon",
        "company",
        "battalion",
        "brigade",
        "division",
        "corps",
        "army",
        "army_group",
    )


    def render(self, affiliation="friend", **kwargs):

        return nse.render_nonnato_unit_svg(
            affiliation, nse.FORCES_IN_DEFENCE_ENTITY, **kwargs
        )


    def placement(self, svg):

        """The row's own (scale, offset x, offset y), as drawn."""

        match = re.search(
            r'<g transform="translate\(([-\d.]+),([-\d.]+)\)'
            r'(?: scale\(([\d.]+)\))?"',
            svg,
        )

        if match is None:
            return None

        return (
            float(match.group(3) or 1),
            float(match.group(1)),
            float(match.group(2)),
        )


    def shapes(self, svg):

        group = re.search(
            r'<g transform="translate[^"]*" stroke-width=[^>]*>.*?</g>',
            svg,
            re.S,
        )

        return nse._echelon_shapes(group.group(0)), nse._half_stroke(
            group.group(0)
        )


    def test_the_frame_is_one_arc_the_long_way_round(self):

        svg = self.render()

        self.assertIn(f'<path d="{nse._FID_ARC_D}"', svg)

        # large-arc AND sweep both 1: reversing either draws the
        # 60 degree OPENING instead of the 300 degree ellipse.
        self.assertIn("A75,50 0 1 1", nse._FID_ARC_D)

        self.assertNotIn(nse._UNIT_FRAME_PATH_D, svg)


    def test_the_opening_is_sixty_degrees_across_the_top(self):

        start_x, start_y = nse._FID_ARC_START
        end_x, end_y = nse._FID_ARC_END

        # Both ends level, symmetric about the ellipse's own centre
        # line, and above its widest point.
        self.assertAlmostEqual(start_y, end_y, places=6)
        self.assertAlmostEqual(
            (start_x + end_x) / 2, nse._FID_CENTRE_X, places=6
        )
        self.assertLess(start_y, nse._UNIT_FRAME_CENTRE_Y)

        # The gap they span, at the angle they span it.
        self.assertAlmostEqual(start_x - end_x, 75.0, places=4)


    def test_every_affiliation_keeps_its_own_colour(self):

        for affiliation, colour in nse.AFFILIATION_COLOURS.items():

            with self.subTest(affiliation=affiliation):

                self.assertIn(
                    f'stroke="{colour}"', self.render(affiliation=affiliation)
                )


    def test_planned_dashes_the_arc(self):

        svg = self.render(status="planned")

        arc = re.search(
            r'<path d="' + re.escape(nse._FID_ARC_D) + r'"([^>]*)>', svg
        )

        self.assertIn("stroke-dasharray", arc.group(1))


    def test_headquarters_and_combined_arms_are_refused_in_the_render(self):

        svg = self.render(
            echelon="battalion", headquarters=True, combined_arms=True
        )

        # The mast hangs off a bottom-left corner and Combined Arms
        # sits on a top edge; an ellipse has neither.
        self.assertNotIn(nse._HQ_MAST_D, svg)
        self.assertNotIn("<rect", svg)

        # Identical to the render that never asked for either.
        self.assertEqual(svg, self.render(echelon="battalion"))


    def test_no_echelon_leaves_the_arc_alone(self):

        self.assertIsNone(self.placement(self.render()))


    def test_every_echelon_row_is_centred_on_the_ellipses_top(self):

        for echelon in self.ECHELONS[1:]:

            with self.subTest(echelon=echelon):

                svg = self.render(echelon=echelon)

                shapes, _ = self.shapes(svg)

                scale, offset_x, offset_y = self.placement(svg)

                top = min(
                    shape[2] - shape[3] if shape[0] == "disc"
                    else min(shape[2], shape[4])
                    for shape in shapes
                )
                bottom = max(
                    shape[2] + shape[3] if shape[0] == "disc"
                    else max(shape[2], shape[4])
                    for shape in shapes
                )
                left = min(
                    shape[1] - shape[3] if shape[0] == "disc"
                    else min(shape[1], shape[3])
                    for shape in shapes
                )
                right = max(
                    shape[1] + shape[3] if shape[0] == "disc"
                    else max(shape[1], shape[3])
                    for shape in shapes
                )

                middle = (top + bottom) / 2 * scale + offset_y
                centre = (left + right) / 2 * scale + offset_x

                # On the ellipse's own topmost perimeter point, and
                # still centred on the symbol.
                self.assertAlmostEqual(middle, nse._UNIT_FRAME_TOP, places=3)
                self.assertAlmostEqual(centre, nse._FID_CENTRE_X, places=3)


    def test_no_row_is_rotated_or_larger_than_milsymbols_own(self):

        for echelon in self.ECHELONS[1:]:

            with self.subTest(echelon=echelon):

                svg = self.render(echelon=echelon)

                self.assertNotIn("rotate(", svg)

                self.assertLessEqual(self.placement(svg)[0], 1.0)


    def test_every_row_clears_the_arc(self):

        samples = nse._fid_arc_samples()

        for echelon in self.ECHELONS[1:]:

            with self.subTest(echelon=echelon):

                svg = self.render(echelon=echelon)

                shapes, half = self.shapes(svg)

                self.assertTrue(
                    nse._fid_row_clears(
                        shapes,
                        self.placement(svg),
                        half,
                        nse._half_stroke(
                            re.search(
                                r'<path d="'
                                + re.escape(nse._FID_ARC_D)
                                + r'"([^>]*)>',
                                svg,
                            ).group(1)
                        ),
                        samples,
                    )
                )


    def test_a_shrunk_row_was_shrunk_only_as_far_as_it_had_to_be(self):

        samples = nse._fid_arc_samples()

        shrunk = 0

        for echelon in self.ECHELONS[1:]:

            svg = self.render(echelon=echelon)

            scale, offset_x, offset_y = self.placement(svg)

            if scale == 1:
                continue

            shrunk += 1

            with self.subTest(echelon=echelon):

                shapes, half = self.shapes(svg)

                arc_half = nse._half_stroke(
                    re.search(
                        r'<path d="' + re.escape(nse._FID_ARC_D) + r'"([^>]*)>',
                        svg,
                    ).group(1)
                )

                # One per cent more would breach the arc - the row is
                # as large as it could be, not merely small enough.
                bigger = nse._fid_placement(
                    scale * 1.01, nse._FID_CENTRE_X, offset_y_centre(
                        shapes, scale, offset_y
                    )
                )

                self.assertFalse(
                    nse._fid_row_clears(shapes, bigger, half, arc_half, samples)
                )

        self.assertGreater(shrunk, 0)


    def test_the_viewbox_is_the_frames_own_width(self):

        for echelon in self.ECHELONS:

            with self.subTest(echelon=echelon):

                svg = self.render(echelon=echelon)

                x, _, width, _ = (
                    float(value)
                    for value in nse._VIEWBOX_PATTERN.search(svg).groups()
                )

                # Same declared width as every other Land Unit, so QGIS
                # - which scales a marker by that width - draws this
                # entity at the same size as its siblings.
                self.assertEqual(x, nse._FID_VIEWBOX_X)
                self.assertEqual(width, nse._FID_VIEWBOX_WIDTH)


    def test_the_viewbox_holds_every_row(self):

        for echelon in self.ECHELONS[1:]:

            with self.subTest(echelon=echelon):

                svg = self.render(echelon=echelon)

                _, vb_y, _, vb_height = (
                    float(value)
                    for value in nse._VIEWBOX_PATTERN.search(svg).groups()
                )

                shapes, half = self.shapes(svg)

                scale, offset_x, offset_y = self.placement(svg)

                ink_top = min(
                    shape[2] - shape[3] if shape[0] == "disc"
                    else min(shape[2], shape[4])
                    for shape in shapes
                ) * scale + offset_y - half * scale

                self.assertLessEqual(vb_y, ink_top + 1e-6)
                self.assertGreaterEqual(
                    vb_y + vb_height, nse._UNIT_FRAME_BOTTOM
                )


    def test_the_designations_still_hang_off_the_sides(self):

        svg = self.render(
            echelon="brigade", designation_left="7", designation_right="RAJ"
        )

        xs = [float(x) for x in re.findall(r'<text x="([-\d.]+)"', svg)]

        self.assertEqual(len(xs), 2)

        # One each side of the ellipse's own ink.
        self.assertLess(min(xs), nse._UNIT_FRAME_LEFT)
        self.assertGreater(max(xs), nse._UNIT_FRAME_RIGHT)


def offset_y_centre(shapes, scale, offset_y):

    """The row's own vertical centre in its untransformed coordinates."""

    top = min(
        shape[2] - shape[3] if shape[0] == "disc" else min(shape[2], shape[4])
        for shape in shapes
    )
    bottom = max(
        shape[2] + shape[3] if shape[0] == "disc" else max(shape[2], shape[4])
        for shape in shapes
    )

    return (top + bottom) / 2


class TestEllipseControlMeasurePoints(QgisTestCase):

    """
    The five added 2026-09-23 - three on Forces in Defence's own
    ellipse turned over, plus Vital Point and Vital Area.
    """

    ENTITIES = (
        nse.BEACH_HEAD_ENTITY,
        nse.BRIDGE_HEAD_ENTITY,
        nse.AIR_HEAD_ENTITY,
        nse.VITAL_POINT_ENTITY,
        nse.VITAL_AREA_ENTITY,
    )

    TURNED_OVER = (
        nse.BEACH_HEAD_ENTITY,
        nse.BRIDGE_HEAD_ENTITY,
        nse.AIR_HEAD_ENTITY,
    )


    def render(self, entity, affiliation="friend", **kwargs):

        return nse.render_nonnato_control_measure_svg(
            affiliation, entity, **kwargs
        )


    def test_the_opening_is_at_the_bottom(self):

        # "Use the same ellipse as Forces in defence but rotate it 180
        # deg" - same radii, same 60 degree opening, ends level and
        # BELOW the ellipse's own widest point.
        start_x, start_y = nse._CMP_ELLIPSE_ARC_START
        end_x, end_y = nse._CMP_ELLIPSE_ARC_END

        self.assertAlmostEqual(start_y, end_y, places=6)
        self.assertGreater(start_y, nse._UNIT_FRAME_CENTRE_Y)

        self.assertAlmostEqual(
            abs(start_x - end_x), abs(nse._FID_ARC_START[0] - nse._FID_ARC_END[0]),
            places=6,
        )

        # The same trap as its unflipped twin: both flags 1, the long
        # way round.
        self.assertIn("A75,50 0 1 1", nse._CMP_ELLIPSE_ARC_D)

        for entity in self.TURNED_OVER:

            with self.subTest(entity=entity):

                self.assertIn(nse._CMP_ELLIPSE_ARC_D, self.render(entity))


    def test_vital_point_keeps_the_opening_at_the_top(self):

        # "Start with the ellipse of Forces in Defence" - not turned.
        self.assertIn(nse._FID_ARC_D, self.render(nse.VITAL_POINT_ENTITY))


    def test_the_wave_is_milsymbols_own(self):

        amphibious = nse.render_nonnato_unit_svg("friend", "amphibious")

        self.assertIn(nse._AMPHIBIOUS_WAVE_D, amphibious)


    def test_the_bridge_is_milsymbols_own(self):

        bridge = nse.render_nonnato_equipment_svg("friend", "bridge")

        self.assertIn(nse._BRIDGE_GLYPH_D, bridge)


    def test_beach_head_takes_the_wave_and_not_the_stadium(self):

        svg = self.render(nse.BEACH_HEAD_ENTITY)

        self.assertIn(nse._AMPHIBIOUS_WAVE_D, svg)

        # Amphibious draws a stadium AND a wave; only the wave is
        # wanted.
        self.assertNotIn(nse._ARMOUR_OVAL_D, svg)


    def test_the_wave_is_the_one_glyph_that_shrinks(self):

        scales = {}

        for entity in self.TURNED_OVER:

            match = re.search(r"scale\(([\d.]+)\)", self.render(entity))

            scales[entity] = float(match.group(1)) if match else 1.0

        self.assertLess(scales[nse.BEACH_HEAD_ENTITY], 1.0)
        self.assertEqual(scales[nse.BRIDGE_HEAD_ENTITY], 1.0)
        self.assertEqual(scales[nse.AIR_HEAD_ENTITY], 1.0)


    def test_no_glyph_is_ever_drawn_larger_than_milsymbols_own(self):

        for entity in self.TURNED_OVER:

            with self.subTest(entity=entity):

                for scale in re.findall(
                    r"scale\(([\d.]+)\)", self.render(entity)
                ):
                    self.assertLessEqual(float(scale), 1.0)


    def test_every_glyph_clears_the_arc(self):

        for entity in self.TURNED_OVER:

            with self.subTest(entity=entity):

                svg = self.render(entity)

                # The glyph's own ink, measured the way it was fitted.
                bounds = nse._content_bounds(
                    re.sub(
                        r"<path d=\"" + re.escape(nse._CMP_ELLIPSE_ARC_D)
                        + r"\"[^>]*></path>",
                        "",
                        svg,
                    ),
                    None,
                )

                self.assertIsNotNone(bounds)

                x, y, width, height = bounds

                half_x = max(
                    abs(x - nse._FID_CENTRE_X),
                    abs(x + width - nse._FID_CENTRE_X),
                )
                half_y = max(
                    abs(y - nse._UNIT_FRAME_CENTRE_Y),
                    abs(y + height - nse._UNIT_FRAME_CENTRE_Y),
                )

                arc_half = (
                    nse._CMP_ELLIPSE_STROKE_WIDTH * nse.DEFAULT_STROKE_SCALE / 2
                )

                reach = (
                    (half_x / (nse._FID_RX - arc_half)) ** 2
                    + (half_y / (nse._FID_RY - arc_half)) ** 2
                )

                self.assertLess(reach, 1.0)


    def test_vital_points_circle_is_the_gap_itself(self):

        # "a circle with diameter same as the gap in the ellipse" - the
        # gap's two arc ends ARE its diameter, so both land on it.
        centre_x, centre_y = nse._VITAL_POINT_CIRCLE_CENTRE

        for end in (nse._FID_ARC_START, nse._FID_ARC_END):

            self.assertAlmostEqual(
                math.hypot(end[0] - centre_x, end[1] - centre_y),
                nse._VITAL_POINT_CIRCLE_RADIUS,
                places=4,
            )


    def test_vital_points_wedges_point_inward_without_meeting(self):

        svg = self.render(nse.VITAL_POINT_ENTITY)

        _, centre_y = nse._VITAL_POINT_CIRCLE_CENTRE

        apexes = []

        for d in re.findall(r'<path d="(M[^"]*Z)"', svg):

            # The base is an ARC OF THE INNER CIRCLE, not a chord: a
            # straight base leaves a crescent of white against the
            # circle it sits in.
            self.assertIn(
                f"A{nse._VITAL_POINT_CIRCLE_RADIUS:g},"
                f"{nse._VITAL_POINT_CIRCLE_RADIUS:g}",
                d,
            )

            points = [
                (float(x), float(y))
                for x, y in re.findall(r"[ML]([-\d.]+),([-\d.]+)", d)
            ]

            ends = [
                (float(x), float(y))
                for x, y in re.findall(r"[\d] ([-\d.]+),([-\d.]+) L", d)
            ]

            self.assertEqual(len(points), 2)
            self.assertEqual(len(ends), 1)

            # The base's two ends are level, and both lie on the
            # circle.
            self.assertAlmostEqual(points[0][1], ends[0][1], places=4)

            for end in (points[0], ends[0]):

                self.assertAlmostEqual(
                    math.hypot(
                        end[0] - nse._VITAL_POINT_CIRCLE_CENTRE[0],
                        end[1] - nse._VITAL_POINT_CIRCLE_CENTRE[1],
                    ),
                    nse._VITAL_POINT_CIRCLE_RADIUS,
                    places=3,
                )

            apexes.append(points[1][1])

        self.assertEqual(len(apexes), 2)

        # Both stop short of the centre rather than meeting there, one
        # each side of it.
        for apex in apexes:

            self.assertNotAlmostEqual(apex, centre_y, places=3)

            self.assertLess(
                abs(apex - centre_y), nse._VITAL_POINT_CIRCLE_RADIUS / 2
            )

        self.assertLess(min(apexes), centre_y)
        self.assertGreater(max(apexes), centre_y)


    def test_vital_points_triangles_are_filled(self):

        svg = self.render(nse.VITAL_POINT_ENTITY)

        colour = nse.AFFILIATION_COLOURS["friend"]

        self.assertEqual(svg.count(f'fill="{colour}"></path>'), 2)


    def test_the_viewbox_holds_vital_points_circle(self):

        svg = self.render(nse.VITAL_POINT_ENTITY)

        _, vb_y, vb_width, _ = (
            float(value) for value in nse._VIEWBOX_PATTERN.search(svg).groups()
        )

        _, centre_y = nse._VITAL_POINT_CIRCLE_CENTRE

        top = (
            centre_y
            - nse._VITAL_POINT_CIRCLE_RADIUS
            - nse._CMP_GLYPH_STROKE_WIDTH * nse.DEFAULT_STROKE_SCALE / 2
        )

        self.assertLessEqual(vb_y, top)

        # The WIDTH is what QGIS sizes a marker by, so it must not have
        # moved - this stays the size of its neighbours.
        self.assertEqual(vb_width, nse._FID_VIEWBOX_WIDTH)


    def test_vital_areas_circle_and_dot_are_borrowed_whole(self):

        svg = self.render(nse.VITAL_AREA_ENTITY)

        # Administration or Logistics' own circle...
        self.assertIn(f'r="{nse._ADMIN_LOGISTICS_RADIUS:g}"', svg)

        # ...and Artillery's own dot at 0.8.
        self.assertIn(
            f'r="{nse._VITAL_AREA_DOT_SCALE * nse._ARTILLERY_DOT_RADIUS:g}"',
            svg,
        )


    def test_vital_areas_arrows_stop_clear_of_the_dots_ink(self):

        svg = self.render(nse.VITAL_AREA_ENTITY)

        radius = nse._VITAL_AREA_DOT_SCALE * nse._ARTILLERY_DOT_RADIUS

        ink = radius + nse._CMP_GLYPH_STROKE_WIDTH * nse.DEFAULT_STROKE_SCALE / 2

        # A distinct gap, not merely "not touching".
        ink += nse._VITAL_AREA_ARROW_GAP

        tips = []

        for d in re.findall(r'<path d="(M100,[^"]*)"', svg):

            ys = [float(y) for _, y in re.findall(r"[ML]([-\d.]+),([-\d.]+)", d)]

            tips.append(min(ys, key=lambda y: abs(y - nse._UNIT_FRAME_CENTRE_Y)))

        self.assertEqual(len(tips), 2)

        for tip in tips:

            # Clear of the INK, not merely of the radius.
            self.assertGreater(abs(tip - nse._UNIT_FRAME_CENTRE_Y), ink)

        # One above the dot, one below.
        self.assertLess(min(tips), nse._UNIT_FRAME_CENTRE_Y)
        self.assertGreater(max(tips), nse._UNIT_FRAME_CENTRE_Y)


    def test_planned_dashes_the_frame_and_only_the_frame(self):

        for entity in self.ENTITIES:

            with self.subTest(entity=entity):

                svg = self.render(entity, status="planned")

                self.assertEqual(svg.count("stroke-dasharray"), 1)

                self.assertNotIn(
                    "stroke-dasharray", self.render(entity)
                )


    def test_every_affiliation_uses_the_schemes_own_palette(self):

        for affiliation in ("friend", "hostile", "neutral", "unknown"):

            colour = nse.AFFILIATION_COLOURS[affiliation]

            for entity in self.ENTITIES:

                with self.subTest(entity=entity, affiliation=affiliation):

                    svg = self.render(entity, affiliation=affiliation)

                    self.assertIn(f'stroke="{colour}"', svg)

                    # Not milsymbol's own black and red.
                    self.assertNotIn('stroke="black"', svg)
                    self.assertNotIn('stroke="rgb(255, 0, 0)"', svg)


    def test_each_one_designates_to_the_right(self):

        for entity in self.ENTITIES:

            with self.subTest(entity=entity):

                plain = self.render(entity)

                bounds = nse._content_bounds(plain, None)

                self.assertIsNotNone(bounds)

                svg = self.render(entity, designation="v1")

                x = float(re.search(r'<text x="([\d.]+)"', svg).group(1))

                # Clear of THIS symbol's own ink - Vital Area's circle
                # stops well short of where the ellipses reach.
                self.assertGreaterEqual(x, bounds[0] + bounds[2])
                self.assertIn(">V1</text>", svg)


def assert_only_gained_a_designation(case, designated, plain, designation):

    """
    Assert that `designated` is `plain` plus an injected side
    designation and nothing else.

    Checked by REMOVAL rather than by rebuilding the expected markup:
    the text is stripped back off and the declared box restored to the
    plain one's, and what is left must match byte for byte. That is the
    property that actually matters - the designation is added, the box
    makes room for it, and nothing else moves.
    """

    case.assertIn(f">{designation}</text>", designated)

    stripped = re.sub(r"<text\b.*?</text>", "", designated, flags=re.S)

    plain_box = nse._VIEWBOX_PATTERN.search(plain).group(0)
    grown_box = nse._VIEWBOX_PATTERN.search(stripped).group(0)

    plain_edges = [float(v) for v in nse._VIEWBOX_PATTERN.search(plain).groups()]
    grown_edges = [
        float(v) for v in nse._VIEWBOX_PATTERN.search(stripped).groups()
    ]

    # The box only ever grows, and only to hold text that hangs
    # outside the glyph.
    case.assertLessEqual(grown_edges[0], plain_edges[0])
    case.assertLessEqual(grown_edges[1], plain_edges[1])
    case.assertGreaterEqual(
        grown_edges[0] + grown_edges[2], plain_edges[0] + plain_edges[2]
    )
    case.assertGreaterEqual(
        grown_edges[1] + grown_edges[3], plain_edges[1] + plain_edges[3]
    )

    stripped = stripped.replace(grown_box, plain_box, 1)

    stripped = _WIDTH_HEIGHT.sub(
        _WIDTH_HEIGHT.search(plain).group(0) if _WIDTH_HEIGHT.search(plain)
        else "",
        stripped,
        count=1,
    )

    case.assertEqual(stripped, plain)


_WIDTH_HEIGHT = re.compile(r'width="[\d.]+" height="[\d.]+"')


class TestEntitiesMilsymbolWillNotDesignate(QgisTestCase):

    """
    Seven Control Measure Points that milsymbol draws no designation
    for, reported live 2026-09-24 against Artillery Observation Post
    and measured across the whole layer from there.
    """

    def test_the_set_is_what_milsymbol_actually_does(self):

        # Re-derived from live renders rather than trusted: a milsymbol
        # update that starts or stops drawing one of these fails here
        # instead of drifting.
        for entity in nse.UNDESIGNATED_BY_MILSYMBOL:

            with self.subTest(entity=entity):

                raw = symbol_engine.render_symbol_svg(
                    build_sidc(
                        affiliation="friend",
                        entity=entity,
                        symbol_set="control_measure",
                        echelon="unspecified",
                        status="present",
                        headquarters=False,
                        edition="2525E",
                    ),
                    {"uniqueDesignation": "A1"},
                )

                self.assertNotIn("<text", raw)


    def test_no_other_entity_on_the_layer_is_missing_from_it(self):

        from MilitaryCartographyTools.military_symbology.\
            control_measure_points_layer_nonnato import (
                ENTITY_LABELS,
                SYNTHETIC_ENTITIES,
            )

        for entity in set(ENTITY_LABELS) - SYNTHETIC_ENTITIES:

            with self.subTest(entity=entity):

                raw = symbol_engine.render_symbol_svg(
                    build_sidc(
                        affiliation="friend",
                        entity=entity,
                        symbol_set="control_measure",
                        echelon="unspecified",
                        status="present",
                        headquarters=False,
                        edition="2525E",
                    ),
                    {"uniqueDesignation": "A1"},
                )

                self.assertEqual(
                    "<text" not in raw,
                    entity in nse.UNDESIGNATED_BY_MILSYMBOL,
                )


    def test_every_one_of_them_now_draws_one(self):

        for entity in nse.UNDESIGNATED_BY_MILSYMBOL:

            with self.subTest(entity=entity):

                svg = nse.render_nonnato_control_measure_svg(
                    "friend", entity, designation="a1"
                )

                self.assertIn(">A1</text>", svg)


    def test_it_sits_right_of_the_ink_on_the_centre_line(self):

        for entity in nse.UNDESIGNATED_BY_MILSYMBOL:

            with self.subTest(entity=entity):

                plain = nse.render_nonnato_control_measure_svg(
                    "friend", entity
                )

                bounds = nse._content_bounds(plain, None)

                self.assertIsNotNone(bounds)

                svg = nse.render_nonnato_control_measure_svg(
                    "friend", entity, designation="a1"
                )

                text = re.search(
                    r'<text x="([-\d.]+)" y="([-\d.]+)"', svg
                )

                self.assertGreaterEqual(
                    float(text.group(1)), bounds[0] + bounds[2]
                )

                # Vertically centred on the symbol's own centre line,
                # give or take the font's own cap height.
                self.assertLess(
                    abs(float(text.group(2)) - nse._CONTROL_MEASURE_CENTRE_Y),
                    30,
                )


    def test_nothing_widens_the_box_for_text_milsymbol_never_draws(self):

        # Asking milsymbol for a designation it will not draw still
        # grows its declared viewBox, and the size stabiliser reads
        # that width - so the icon would shrink for nothing.
        for entity in nse.UNDESIGNATED_BY_MILSYMBOL:

            with self.subTest(entity=entity):

                raw = symbol_engine.render_symbol_svg(
                    build_sidc(
                        affiliation="friend",
                        entity=entity,
                        symbol_set="control_measure",
                        echelon="unspecified",
                        status="present",
                        headquarters=False,
                        edition="2525E",
                    ),
                    None,
                )

                plain = nse.render_nonnato_control_measure_svg(
                    "friend", entity
                )

                self.assertEqual(
                    nse._VIEWBOX_PATTERN.search(raw).groups(),
                    nse._VIEWBOX_PATTERN.search(plain).groups(),
                )


class TestObservationPostFamily(QgisTestCase):

    """
    The four added 2026-09-24, all built on Artillery Observation
    Post's own triangle.
    """

    ENTITIES = (
        nse.LISTENING_POST_ENTITY,
        nse.AIR_FORCE_OP_ENTITY,
        nse.AIR_DEFENCE_OP_ENTITY,
        nse.MOBILE_OP_ENTITY,
    )


    def render(self, entity, **kwargs):

        return nse.render_nonnato_control_measure_svg(
            kwargs.pop("affiliation", "friend"), entity, **kwargs
        )


    def test_the_donor_triangle_and_dot_are_milsymbols_own(self):

        donor = nse.render_nonnato_control_measure_svg(
            "friend", "observation_post_forward_observer"
        )

        self.assertIn(f'd="{nse._ARTILLERY_OP_TRIANGLE_D}"', donor)
        self.assertRegex(donor, nse._ARTILLERY_OP_DOT_PATTERN)


    def test_every_one_keeps_the_triangle(self):

        for entity in self.ENTITIES:

            with self.subTest(entity=entity):

                self.assertIn(
                    f'd="{nse._ARTILLERY_OP_TRIANGLE_D}"', self.render(entity)
                )


    def test_the_dot_is_replaced_except_on_air_defence(self):

        for entity in self.ENTITIES:

            with self.subTest(entity=entity):

                svg = self.render(entity)

                # milsymbol's own dot path is gone from all four; Air
                # Defence draws its own circle instead, above its
                # curve.
                self.assertNotRegex(svg, nse._ARTILLERY_OP_DOT_PATTERN)

                self.assertEqual(
                    "<circle" in svg, entity == nse.AIR_DEFENCE_OP_ENTITY
                )


    def test_listening_posts_strokes_are_true_altitudes(self):

        svg = self.render(nse.LISTENING_POST_ENTITY)

        strokes = re.findall(r'<path d="M([-\d.]+),([-\d.]+) L([-\d.]+),([-\d.]+)"', svg)

        self.assertEqual(len(strokes), 2)

        corners = {
            nse._ARTILLERY_OP_BOTTOM_LEFT: nse._ARTILLERY_OP_BOTTOM_RIGHT,
            nse._ARTILLERY_OP_BOTTOM_RIGHT: nse._ARTILLERY_OP_BOTTOM_LEFT,
        }

        for x1, y1, x2, y2 in strokes:

            start = (float(x1), float(y1))

            self.assertIn(start, corners)

            other = corners[start]

            # Perpendicular to the opposite side, not a line to the
            # opposite corner.
            side = (
                other[0] - nse._ARTILLERY_OP_APEX[0],
                other[1] - nse._ARTILLERY_OP_APEX[1],
            )
            stroke = (float(x2) - start[0], float(y2) - start[1])

            # Normalised, so this checks the ANGLE rather than a raw
            # product: the foot is written at six significant figures
            # like every other length here, which leaves the dot
            # product a hundredth off zero over a 96-unit side.
            cosine = (side[0] * stroke[0] + side[1] * stroke[1]) / (
                math.hypot(*side) * math.hypot(*stroke)
            )

            self.assertLess(abs(cosine), 1e-4)


    def test_the_air_defence_curve_is_a_construction_not_coordinates(self):

        inset = nse._air_defence_op_inset()

        # It had to come in off the corners at all, and not by much -
        # on a rectangle this curve cannot leave the frame; on a
        # triangle it leaves at once.
        self.assertGreater(inset, 0)
        self.assertLess(
            inset,
            (
                nse._ARTILLERY_OP_BOTTOM_RIGHT[0]
                - nse._ARTILLERY_OP_BOTTOM_LEFT[0]
            )
            / 4,
        )

        self.assertTrue(nse._air_defence_curve_clears(inset))

        # And it is the SMALLEST that clears, so the curve stays as
        # wide as it can.
        self.assertFalse(nse._air_defence_curve_clears(inset * 0.99))


    def test_the_air_defence_dot_grew_upward_from_where_it_fitted(self):

        svg = self.render(nse.AIR_DEFENCE_OP_ENTITY)

        circle = re.search(r'<circle cx="100" cy="([\d.]+)" r="([\d.]+)"', svg)

        centre = float(circle.group(1))
        radius = float(circle.group(2))

        # Doubled and lifted by exactly the radius it gained, so its
        # lower edge sits where the fitted dot's did.
        fitted = radius / 2

        self.assertAlmostEqual(centre + radius, 100 + fitted, places=3)
        self.assertLess(centre, 100)

        _, crest = nse._air_defence_curve(nse._air_defence_op_inset())

        self.assertLess(centre + radius, crest)


    def test_mobile_op_keeps_the_propeller_and_adds_a_mast_and_a_w(self):

        svg = self.render(nse.MOBILE_OP_ENTITY)

        self.assertIn(nse._ARMY_AVIATION_PROPELLER_SOLID_D, svg)

        apex_x, apex_y = nse._ARTILLERY_OP_APEX

        height = nse._ARTILLERY_OP_BOTTOM_LEFT[1] - apex_y

        tip = apex_y - height * nse._MOBILE_OP_MAST_FRACTION

        self.assertIn(f'M{apex_x:g},{apex_y:g} L{apex_x:g},{tip:g}', svg)

        # Five points, alternating, straddling the mast's own tip.
        w = [
            (float(x), float(y))
            for x, y in re.findall(r"[ML]([-\d.]+),([-\d.]+)", svg)
        ]

        above = [point for point in w if point[1] < tip]
        below = [point for point in w if point[1] > tip]

        self.assertTrue(above)
        self.assertTrue(below)


    def test_the_w_is_two_thirds_of_the_triangles_width(self):

        svg = self.render(nse.MOBILE_OP_ENTITY)

        width = nse._MOBILE_OP_W_FRACTION * (
            nse._ARTILLERY_OP_BOTTOM_RIGHT[0] - nse._ARTILLERY_OP_BOTTOM_LEFT[0]
        )

        centre = nse._ARTILLERY_OP_APEX[0]

        self.assertIn(f"M{nse._round_drawn(centre - width / 2):g},", svg)
        self.assertIn(f"L{nse._round_drawn(centre + width / 2):g},", svg)


    def test_every_one_takes_the_palette_and_a_right_side_designation(self):

        for entity in self.ENTITIES:

            for affiliation in ("friend", "hostile", "neutral", "unknown"):

                with self.subTest(entity=entity, affiliation=affiliation):

                    svg = self.render(
                        entity, affiliation=affiliation, designation="o1"
                    )

                    self.assertIn(
                        f'stroke="{nse.AFFILIATION_COLOURS[affiliation]}"', svg
                    )
                    self.assertNotIn('stroke="black"', svg)
                    self.assertIn(">O1</text>", svg)


class TestLetteredRadars(QgisTestCase):

    """LORROS and BFSR - the Radar with a lettered circle beside it."""

    def test_both_draw_the_radar_this_plugin_draws(self):

        radar = nse.render_nonnato_equipment_svg("friend", nse.SIGINT_RADAR_ENTITY)

        radar_d = re.findall(r' d="([^"]+)"', radar)

        for entity in (nse.LORROS_ENTITY, nse.BFSR_ENTITY):

            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                # The dish AND the mast this plugin adds to it.
                for d in radar_d:
                    self.assertIn(f'd="{d}"', svg)


    def test_the_circle_is_computed_from_its_own_letter(self):

        radii = {}

        for entity, letter in nse._LETTERED_RADAR_LETTERS.items():

            svg = nse.render_nonnato_equipment_svg("friend", entity)

            circle = re.search(r'<circle[^>]*r="([\d.]+)"', svg)

            self.assertIsNotNone(circle)

            radii[letter] = float(circle.group(1))

            self.assertIn(f">{letter}</text>", svg)

        # A fixed radius made it wider than the radar itself; each one
        # fits its own letter, so L and B differ.
        self.assertNotEqual(radii["L"], radii["B"])


    def test_the_circle_sits_on_the_radars_own_vertical_middle(self):

        radar = nse.render_nonnato_equipment_svg("friend", nse.SIGINT_RADAR_ENTITY)

        bounds = nse._content_bounds(radar, None)

        self.assertIsNotNone(bounds)

        middle = bounds[1] + bounds[3] / 2

        svg = nse.render_nonnato_equipment_svg("friend", nse.LORROS_ENTITY)

        circle = re.search(r'<circle[^>]*cy="([\d.]+)"', svg)

        # Not the frame's centre line.
        self.assertAlmostEqual(float(circle.group(1)), middle, places=2)


    def test_both_still_take_a_designation_below(self):

        for entity in (nse.LORROS_ENTITY, nse.BFSR_ENTITY):

            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg(
                    "friend", entity, designation="r2"
                )

                self.assertIn(">R2</text>", svg)


class TestEchelonMarkers(QgisTestCase):

    """The Echelons layer's own renders - one marker, alone, in a shared box."""

    def test_there_is_no_unspecified(self):

        # It has no marker.
        self.assertNotIn("unspecified", nse.ECHELON_MARKER_ENTITIES)
        self.assertEqual(len(nse.ECHELON_MARKER_ENTITIES), 10)


    def test_all_ten_share_one_box(self):

        boxes = {
            nse._VIEWBOX_PATTERN.search(
                nse.render_nonnato_echelon_svg("friend", echelon)
            ).group(0)
            for echelon in nse.ECHELON_MARKER_ENTITIES
        }

        self.assertEqual(len(boxes), 1)


    def test_the_box_is_the_union_of_every_marker(self):

        x, y, width, height = nse.echelon_shared_box()

        widest = tallest = False

        for echelon in nse.ECHELON_MARKER_ENTITIES:

            group = nse._echelon_marker_group("friend", echelon)

            half = nse._half_stroke(group)

            for shape in nse._echelon_shapes(group):

                if shape[0] == "disc":
                    edges = (
                        shape[1] - shape[3], shape[1] + shape[3],
                        shape[2] - shape[3], shape[2] + shape[3],
                    )
                else:
                    edges = (shape[1], shape[3], shape[2], shape[4])

                for edge in edges[:2]:
                    self.assertGreaterEqual(edge - half, x - 0.01)
                    self.assertLessEqual(edge + half, x + width + 0.01)

                for edge in edges[2:]:
                    self.assertGreaterEqual(edge - half, y - 0.01)
                    self.assertLessEqual(edge + half, y + height + 0.01)

                if edges[0] - half <= x + 0.01 or edges[1] + half >= x + width - 0.01:
                    widest = True

                if edges[2] - half <= y + 0.01 or edges[3] + half >= y + height - 0.01:
                    tallest = True

        # Both extremes actually touch it - it is the union, not a
        # round number with slack in it.
        self.assertTrue(widest)
        self.assertTrue(tallest)


    def test_detachments_slash_is_stripped_as_it_is_on_a_unit(self):

        svg = nse.render_nonnato_echelon_svg("friend", "team_crew")

        # One circle, no slash: the same echelon must not look like two
        # different things on two layers.
        self.assertEqual(svg.count("<circle"), 1)
        self.assertNotIn("<path", svg)


    def test_every_affiliation_colours_the_marker(self):

        for affiliation, colour in nse.AFFILIATION_COLOURS.items():

            with self.subTest(affiliation=affiliation):

                self.assertIn(
                    f'stroke="{colour}"',
                    nse.render_nonnato_echelon_svg(affiliation, "brigade"),
                )


    def test_an_echelon_with_no_marker_raises(self):

        with self.assertRaises(ValueError):
            nse.render_nonnato_echelon_svg("friend", "unspecified")


class TestNaiTaiAndDfSos(QgisTestCase):

    """
    The four NAI/TAI symbols and DF (SOS), added 2026-09-25 - the first
    four on Point of Interest's own render, DF (SOS) on the Target
    cross.
    """

    NAI_TAI = (
        nse.POINT_NAI_ENTITY,
        nse.POINT_TAI_ENTITY,
        nse.AREA_NAI_ENTITY,
        nse.AREA_TAI_ENTITY,
    )


    def render(self, entity, **kwargs):

        return nse.render_nonnato_control_measure_svg(
            kwargs.pop("affiliation", "friend"), entity, **kwargs
        )


    def test_the_donor_glyphs_are_milsymbols_own(self):

        poi = self.render("point_of_interest")

        self.assertIn(f'd="{nse._POI_POINTER_D}"', poi)
        self.assertRegex(poi, nse._POI_CIRCLE_PATTERN)

        self.assertIn(
            f'd="{nse._TARGET_CROSS_D}"', self.render("target_reference_point")
        )


    def test_point_of_interest_itself_is_untouched(self):

        # A rename was asked for and withdrawn the same day.
        from MilitaryCartographyTools.military_symbology.\
            control_measure_points_layer_nonnato import ENTITY_LABELS

        self.assertEqual(
            ENTITY_LABELS["point_of_interest"], "Point Of Interest"
        )


    def test_point_nai_is_the_donor_with_its_pointer_unfilled(self):

        svg = self.render(nse.POINT_NAI_ENTITY)

        pointer = nse._POI_POINTER_PATTERN.search(svg)

        self.assertIsNotNone(pointer)
        self.assertIn('fill="none"', pointer.group(0))

        # Its top follows the circle's ARC, so it still reads as one
        # clean pin - a straight-sided version put a visible chord
        # across the circle's base.
        self.assertIn("C ", nse._POI_POINTER_D)


    def test_the_two_area_symbols_carry_nothing_that_points(self):

        for entity in (nse.AREA_NAI_ENTITY, nse.AREA_TAI_ENTITY):

            with self.subTest(entity=entity):

                self.assertNotIn(nse._POI_POINTER_D, self.render(entity))


    def test_the_trapezium_is_built_from_the_donors_own_diameter(self):

        points = nse._trapezium_points(
            nse._POI_CIRCLE_CENTRE, 2 * nse._POI_CIRCLE_RADIUS, short_down=True
        )

        long_side = abs(points[1][0] - points[0][0])
        short_side = abs(points[2][0] - points[3][0])
        height = abs(points[2][1] - points[1][1])

        diameter = 2 * nse._POI_CIRCLE_RADIUS

        self.assertAlmostEqual(long_side, diameter)
        self.assertAlmostEqual(short_side, nse._TRAPEZIUM_SHORT_FACTOR * diameter)
        self.assertAlmostEqual(height, nse._TRAPEZIUM_HEIGHT_FACTOR * diameter)

        # A trapezium, not a parallelogram - "shorter side" only means
        # something on one of them.
        self.assertNotAlmostEqual(long_side, short_side)


    def test_point_tais_triangle_stands_on_the_short_side_and_reaches_the_tip(self):

        svg = self.render(nse.POINT_TAI_ENTITY)

        triangle = re.search(
            r'<path d="M([-\d.]+),([-\d.]+) L([-\d.]+),([-\d.]+) '
            r'L([-\d.]+),([-\d.]+) Z"',
            svg,
        )

        self.assertIsNotNone(triangle)

        numbers = [float(value) for value in triangle.groups()]

        # Middle point is the donor pointer's own tip.
        self.assertAlmostEqual(numbers[2], nse._POI_TIP[0], places=3)
        self.assertAlmostEqual(numbers[3], nse._POI_TIP[1], places=3)

        # Its two feet are the trapezium's own short side.
        points = nse._trapezium_points(
            nse._POI_CIRCLE_CENTRE, 2 * nse._POI_CIRCLE_RADIUS, short_down=True
        )

        self.assertAlmostEqual(numbers[1], points[3][1], places=3)
        self.assertAlmostEqual(numbers[5], points[2][1], places=3)


    def test_area_nais_short_side_ends_sit_on_the_circumference(self):

        svg = self.render(nse.AREA_NAI_ENTITY)

        path = re.search(r'<path d="(M[-\d.]+,[-\d.]+ L[^"]*)"', svg)

        points = [
            (float(x), float(y))
            for x, y in re.findall(r"[ML]([-\d.]+),([-\d.]+)", path.group(1))
        ]

        # Four corners, and the short side is NOT drawn - so the path
        # is open.
        self.assertEqual(len(points), 4)
        self.assertNotIn("Z", path.group(1))

        for end in (points[0], points[3]):

            self.assertAlmostEqual(
                math.hypot(
                    end[0] - nse._POI_CIRCLE_CENTRE[0],
                    end[1] - nse._POI_CIRCLE_CENTRE[1],
                ),
                nse._POI_CIRCLE_RADIUS,
                places=3,
            )


    def test_area_nai_is_wider_and_shorter_than_the_family(self):

        self.assertGreater(nse._AREA_NAI_WIDTH_FACTOR, 1)
        self.assertLess(nse._AREA_NAI_HEIGHT_FACTOR, 1)


    def test_the_designation_fits_the_shape_that_holds_it(self):

        for entity in self.NAI_TAI:

            with self.subTest(entity=entity):

                svg = self.render(entity, designation="tai12")

                size = float(re.search(r'font-size="([\d.]+)"', svg).group(1))

                # Never larger than the donor's own, and small enough
                # not to spill out of the shape.
                self.assertLessEqual(size, nse._POI_FONT_SIZE)

                width = nse._designation_text_width("TAI12", size)

                self.assertLessEqual(
                    width,
                    max(
                        nse._room_inside_circle(nse._POI_CIRCLE_RADIUS),
                        nse._room_inside_trapezium(2 * nse._POI_CIRCLE_RADIUS),
                    )
                    + 0.01,
                )


    def test_status_is_inert_on_all_four(self):

        # It is inert on their donor: milsymbol renders Point of
        # Interest identically for Present and Planned.
        for entity in self.NAI_TAI:

            with self.subTest(entity=entity):

                self.assertEqual(
                    self.render(entity, status="present"),
                    self.render(entity, status="planned"),
                )


    def test_df_sos_puts_its_letters_in_the_lower_right_quadrant(self):

        svg = self.render(nse.DF_SOS_ENTITY)

        self.assertIn(f'd="{nse._TARGET_CROSS_D}"', svg)

        text = re.search(
            r'<text x="([\d.]+)" y="([\d.]+)"[^>]*font-size="([\d.]+)"', svg
        )

        self.assertIsNotNone(text)
        self.assertIn(">SOS</text>", svg)

        self.assertEqual(float(text.group(3)), nse._DF_SOS_FONT_SIZE)

        # Clear of the upright's own ink, and on the cross's bottom
        # arm - it was anchored by its right edge first and reached
        # back across the upright at this size.
        self.assertGreater(
            float(text.group(1)), nse._CONTROL_MEASURE_CENTRE_Y
        )
        self.assertAlmostEqual(
            float(text.group(2)),
            nse._CONTROL_MEASURE_CENTRE_Y + nse._TARGET_CROSS_HALF,
            places=3,
        )
        self.assertIn('text-anchor="start"', svg)


    def test_df_sos_still_takes_its_own_designation(self):

        svg = self.render(nse.DF_SOS_ENTITY, designation="d4")

        self.assertIn(">SOS</text>", svg)
        self.assertIn(">D4</text>", svg)


    def test_all_five_take_the_schemes_palette(self):

        for entity in self.NAI_TAI + (nse.DF_SOS_ENTITY,):

            for affiliation in ("friend", "hostile", "neutral", "unknown"):

                with self.subTest(entity=entity, affiliation=affiliation):

                    svg = self.render(entity, affiliation=affiliation)

                    self.assertIn(
                        nse.AFFILIATION_COLOURS[affiliation], svg
                    )
                    self.assertNotIn('"black"', svg)
                    self.assertNotIn("rgb(255, 0, 0)", svg)
