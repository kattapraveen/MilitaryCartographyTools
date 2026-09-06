# -*- coding: utf-8 -*-

"""
Tests for military_symbology/nonnato_symbol_engine.py - the SVG
post-processing non-NATO symbology needs on top of milsymbol.js's own
output (frame/fill/monoColor themselves need no fixup, see
symbol_engine.py's tests for that half of the pipeline).

Military Cartography Tools
"""

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
            f'<circle cx="100" cy="100" r="15" ', merged
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

        self.assertIn(f'fill="none"', svg)
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
        self.assertEqual(svg.count('stroke-dasharray="4,3"'), 4)

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
            "machine_gun", "light", "medium",
        ):
            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                self.assertTrue(svg.startswith("<svg"))


    def test_machine_gun_tiers_have_the_right_number_of_horizontal_lines(self):

        # Regression test for a real bug: Machine Gun's tiers were
        # briefly mapped onto the Rifle fire-mode family (single_shot/
        # semiautomatic/automatic_rifle) after an investigation wrongly
        # concluded Machine Gun had no real Light/Medium/Heavy siblings
        # in the 2525E table - it does, just bare-keyed "light"/
        # "medium"/"heavy" rather than "machine_gun_light" etc. (see
        # sidc.py's own 2525D table, which has the same codes correctly
        # prefixed). "light has no horizontal line in center, medium
        # has one line and heavy two lines - same as all other" -
        # matching every other weapon-tier family's own base/Light/
        # Medium shift (e.g. howitzer/howitzer_light/howitzer_medium).
        light = nse.render_nonnato_equipment_svg("friend", "machine_gun")
        medium = nse.render_nonnato_equipment_svg("friend", "light")
        heavy = nse.render_nonnato_equipment_svg("friend", "medium")

        # Each tier line is a "30,0" horizontal segment - Light has
        # none, Medium's own extra <path> carries one, Heavy's own
        # extra <path> carries two (drawn as one multi-segment path,
        # not two separate <path> elements).
        self.assertEqual(light.count("30,0"), 0)
        self.assertEqual(medium.count("30,0"), 1)
        self.assertEqual(heavy.count("30,0"), 2)


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


    def test_apv_wheeled_svg_is_the_plain_apv_glyph(self):

        # The three wheels are NOT drawn into the SVG - an SVG-internal
        # circle below milsymbol's own declared draw area gets clipped
        # by QGIS's own marker rendering whatever the viewBox says (a
        # real bug, caught by a smoke test: "the circles below the
        # ellipse are not visible... circles are being cropped"). They
        # are their own simple-marker symbol layers instead - see
        # land_equipment_layer_nonnato._wheel_symbol_layers() and its
        # own tests - so this entity's own SVG is byte-identical to the
        # plain APV render it aliases to.
        wheeled = nse.render_nonnato_equipment_svg(
            "friend", nse.APV_WHEELED_ENTITY
        )
        apv = nse.render_nonnato_equipment_svg(
            "friend", "armored_protected_vehicle"
        )

        self.assertEqual(wheeled, apv)
        self.assertEqual(wheeled.count("<circle"), 0)


    def test_apv_wheel_geometry_constants_sit_on_the_ovals_own_edges(self):

        # "three circles below the oval, slightly inside the edges,
        # touching the oval, radii size can be 1/3 of semi-minor axis" -
        # the oval spans x 75..125 and y 80..120, so the semi-minor axis
        # is 20 and the radius 20/3. Each wheel's own top touches the
        # oval's own straight bottom edge, and the outer two are inset
        # exactly one radius from its own straight left/right edges.
        radius = nse.APV_WHEEL_DIAMETER / 2

        self.assertAlmostEqual(radius, 20 / 3)
        self.assertAlmostEqual(nse.APV_WHEEL_CENTRE_Y - radius, 120)

        left, middle, right = nse.APV_WHEEL_CENTRE_XS

        self.assertAlmostEqual(left - radius, 75)
        self.assertAlmostEqual(right + radius, 125)
        self.assertAlmostEqual(middle, (left + right) / 2)


    def test_apv_wheeled_designation_clears_the_wheels(self):

        # The wheels are separate symbol layers, so this SVG's own
        # measured content stops at the hull - without being told where
        # the wheels really end, the designation tucks straight under
        # the hull and through them. Reported live, 2026-09-03, right
        # after the wheels themselves were fixed.
        wheel_bottom = nse.APV_WHEEL_CENTRE_Y + nse.APV_WHEEL_DIAMETER / 2

        wheeled = nse.render_nonnato_equipment_svg(
            "friend", nse.APV_WHEELED_ENTITY, designation="a1"
        )
        plain = nse.render_nonnato_equipment_svg(
            "friend", "armored_protected_vehicle", designation="a1"
        )

        def baseline(svg):
            match = re.search(r'<text x="\S+" y="(\S+)"[^>]*>A1</text>', svg)
            return float(match.group(1))

        # The text's own top edge (baseline minus roughly a cap height)
        # has to sit below the lowest point the wheels reach.
        font_size = nse._DESIGNATION_FONT_SIZE

        self.assertGreater(baseline(wheeled) - font_size, wheel_bottom)

        # ...and it is pushed down purely because of the wheels - the
        # plain APV, same glyph without them, sits higher.
        self.assertGreater(baseline(wheeled), baseline(plain))


    def test_designation_min_content_bottom_never_pulls_text_up(self):

        # The override only ever lowers the text - an icon that already
        # draws below the given floor keeps its own measured position.
        base_svg = nse.render_nonnato_equipment_svg("friend", "tank")

        without = nse.inject_centered_designation_below(base_svg, "a1", _FRIEND)
        with_low_floor = nse.inject_centered_designation_below(
            base_svg, "a1", _FRIEND, min_content_bottom=-999
        )

        self.assertEqual(without, with_low_floor)


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


    def test_designation_is_accepted_but_milsymbol_draws_nothing_for_it(self):

        # Confirmed live: `shelter`'s own milsymbol icon defines NO
        # designation slot at all - uniqueDesignation/uniqueDesignation1
        # /additionalInformation/additionalInformation1 all draw
        # identically with or without one. Not a regression from the
        # fill fixup - the plain mct_sidc_svg() pipeline every other
        # entity on this layer uses would hit the exact same milsymbol
        # limitation for this one entity. Documented here as the
        # current, accepted behaviour rather than silently assumed.
        without = nse.render_nonnato_pillbox_svg("friend")
        with_designation = nse.render_nonnato_pillbox_svg("friend", designation="a1")

        self.assertEqual(without, with_designation)


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

        # These wheels ARE in the SVG (unlike Armoured Protection
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

        # Booby Trap never carries a designation at all.
        entities = [
            entity for entity in layer_module.ENTITY_LABELS
            if entity != layer_module.BOOBY_TRAP_ENTITY
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
