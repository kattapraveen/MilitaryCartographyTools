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


class TestContentBounds(QgisTestCase):

    """nonnato_symbol_engine._content_bounds() on its own - the Qt QSvgRenderer-based measurement inject_centered_designation_below() relies on."""

    def test_measures_tighter_than_the_declared_viewbox_for_a_padded_icon(self):

        svg = nse.render_nonnato_equipment_svg("friend", "jammer")

        match = re.search(r'viewBox="(\S+) (\S+) (\S+) (\S+)"', svg)
        vb_x, vb_y, vb_w, vb_h = (float(g) for g in match.groups())

        content_x, content_y, content_w, content_h = nse._content_bounds(
            svg, fallback=(vb_x, vb_y, vb_w, vb_h)
        )

        self.assertLess(content_y + content_h, vb_y + vb_h)


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
            "single_shot_rifle", "semiautomatic_rifle", "automatic_rifle",
        ):
            with self.subTest(entity=entity):

                svg = nse.render_nonnato_equipment_svg("friend", entity)

                self.assertTrue(svg.startswith("<svg"))


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
