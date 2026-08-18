# -*- coding: utf-8 -*-

"""
Tests for military_symbology/sidc.py's build_sidc() - constructing a
20-character MIL-STD-2525D/APP-6D SIDC from named components, per the field
positions/codes read directly from the vendored milsymbol.js's own parsing
logic (see sidc.py's own module docstring for the exact source files).

Military Cartography Tools
"""

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.military_symbology.sidc import (
    build_sidc,
    ENTITIES,
    MODIFIERS,
)
from MilitaryCartographyTools.military_symbology.sidc_2525e import (
    MODIFIERS_SECTOR1_2525E,
)


class TestBuildSidc(QgisTestCase):

    def test_default_friendly_infantry(self):

        sidc = build_sidc(
            affiliation="friend",
            entity="infantry"
        )

        self.assertEqual(len(sidc), 20)
        self.assertEqual(sidc, "10031000001211000000")


    def test_affiliation_occupies_position_4(self):

        hostile = build_sidc(affiliation="hostile", entity="armor")
        neutral = build_sidc(affiliation="neutral", entity="armor")
        unknown = build_sidc(affiliation="unknown", entity="armor")

        self.assertEqual(hostile[3], "6")
        self.assertEqual(neutral[3], "4")
        self.assertEqual(unknown[3], "1")


    def test_symbol_set_occupies_positions_5_6(self):

        sidc = build_sidc(affiliation="friend", entity="infantry")

        self.assertEqual(sidc[4:6], "10")


    def test_entity_base_code_occupies_positions_11_16(self):

        sidc = build_sidc(affiliation="friend", entity="armor")

        self.assertEqual(sidc[10:16], "120500")


    def test_broader_vocabulary_entity_codes(self):

        # Spot-checks a few of the entities added in the broader
        # common-vocabulary pass, against the same real
        # src/numbersidc/sidc/landunit.js codes as the original seven.
        expected = {
            "air_defense": "130100",
            "air_defense_missile": "130102",
            "field_artillery_self_propelled": "130301",
            "military_intelligence": "151000",
            "medical": "161300",
        }

        for entity, code in expected.items():

            sidc = build_sidc(affiliation="friend", entity=entity)

            self.assertEqual(
                sidc[10:16],
                code,
                f"entity={entity}"
            )


    def test_air_sea_surface_subsurface_symbol_sets(self):

        # Spot-checks the air/sea_surface/subsurface symbol sets added
        # 2026-08-07 - real codes from milsymbol-3.0.4's own
        # src/numbersidc/sidc/air.js, sea.js, subsurface.js.
        cases = [
            ("air", "fighter", "01", "110104"),
            ("air", "cargo", "01", "110107"),
            ("air", "military_rotary_wing", "01", "110200"),
            ("sea_surface", "destroyer", "30", "120203"),
            ("sea_surface", "carrier", "30", "120100"),
            ("subsurface", "submarine", "35", "110100"),
        ]

        for symbol_set, entity, symbol_set_code, entity_code in cases:

            sidc = build_sidc(
                affiliation="friend",
                entity=entity,
                symbol_set=symbol_set
            )

            self.assertEqual(
                sidc[4:6],
                symbol_set_code,
                f"symbol_set={symbol_set}"
            )

            self.assertEqual(
                sidc[10:16],
                entity_code,
                f"symbol_set={symbol_set}, entity={entity}"
            )


    def test_control_measure_symbol_set(self):

        # Spot-checks the "control_measure" symbol set (Appendix H's
        # own point control measures) added 2026-08-07 - real codes
        # from milsymbol-3.0.4's own
        # src/numbersidc/sidc/control-measure.js.
        cases = [
            ("checkpoint", "130300"),
            ("decision_point", "130700"),
            ("observation_post", "160100"),
            ("ammunition_supply_point", "320200"),
        ]

        for entity, entity_code in cases:

            sidc = build_sidc(
                affiliation="friend",
                entity=entity,
                symbol_set="control_measure"
            )

            self.assertEqual(
                sidc[4:6],
                "25",
                f"entity={entity}"
            )

            self.assertEqual(
                sidc[10:16],
                entity_code,
                f"entity={entity}"
            )


    def test_status_planned_occupies_position_7(self):

        sidc = build_sidc(
            affiliation="friend",
            entity="infantry",
            status="planned"
        )

        self.assertEqual(sidc[6], "1")


    def test_headquarters_occupies_position_8(self):

        with_hq = build_sidc(
            affiliation="friend",
            entity="infantry",
            headquarters=True
        )

        without_hq = build_sidc(
            affiliation="friend",
            entity="infantry",
            headquarters=False
        )

        self.assertEqual(with_hq[7], "2")
        self.assertEqual(without_hq[7], "0")


    def test_echelon_occupies_positions_9_10(self):

        sidc = build_sidc(
            affiliation="friend",
            entity="infantry",
            echelon="battalion"
        )

        self.assertEqual(sidc[8:10], "16")


    def test_unknown_affiliation_raises(self):

        with self.assertRaises(KeyError):

            build_sidc(affiliation="martian", entity="infantry")


    def test_unknown_entity_raises(self):

        with self.assertRaises(KeyError):

            build_sidc(affiliation="friend", entity="starfighter")


    def test_unknown_echelon_raises(self):

        with self.assertRaises(KeyError):

            build_sidc(
                affiliation="friend",
                entity="infantry",
                echelon="platoon_of_giants"
            )


    def test_unknown_status_raises(self):

        with self.assertRaises(KeyError):

            build_sidc(
                affiliation="friend",
                entity="infantry",
                status="destroyed_and_forgotten"
            )


    def test_no_modifiers_occupies_positions_17_20_with_zeros(self):

        # Default behaviour, unchanged from before sector1_modifier/
        # sector2_modifier existed as parameters.
        sidc = build_sidc(affiliation="friend", entity="infantry")

        self.assertEqual(sidc[16:20], "0000")


    def test_sector1_and_sector2_modifiers_occupy_positions_17_20(self):

        # Space's own orbit-type (sector1) and sensor-type (sector2)
        # modifiers - real codes from milsymbol-3.0.4's own
        # src/numbersidc/sidc/space.js (sIdm1/sIdm2).
        sidc = build_sidc(
            affiliation="friend",
            entity="satellite",
            symbol_set="space",
            sector1_modifier="low_earth_orbit",
            sector2_modifier="optical",
        )

        self.assertEqual(sidc[16:18], "01")
        self.assertEqual(sidc[18:20], "01")


    def test_empty_string_modifier_is_treated_as_none(self):

        # A UI field defaulting to "" (the "(None)" ValueMap option -
        # see _point_symbol_layer.py) must resolve the same as omitting
        # the argument entirely, not raise.
        sidc = build_sidc(
            affiliation="friend",
            entity="satellite",
            symbol_set="space",
            sector1_modifier="",
            sector2_modifier="",
        )

        self.assertEqual(sidc[16:20], "0000")


    def test_unknown_sector1_modifier_raises(self):

        with self.assertRaises(KeyError):

            build_sidc(
                affiliation="friend",
                entity="satellite",
                symbol_set="space",
                sector1_modifier="warp_drive",
            )


    def test_modifier_for_a_symbol_set_with_no_modifiers_defined_raises(self):

        # "ground_unit" has no MODIFIERS entry at all yet - passing a
        # real (non-empty) modifier for it must fail loudly, not
        # silently produce "00".
        with self.assertRaises(KeyError):

            build_sidc(
                affiliation="friend",
                entity="infantry",
                sector1_modifier="anything",
            )


    def test_every_modifiers_entry_has_two_digit_string_codes(self):

        # Sanity guard on the MODIFIERS data itself - every code must be
        # exactly 2 digits (SIDC positions 17-18/19-20), and unique
        # within its own symbol_set/sector (no two modifier keys
        # silently mapping to the same code).
        for symbol_set, sectors in MODIFIERS.items():

            for sector, codes in sectors.items():

                for key, code in codes.items():

                    self.assertEqual(
                        len(code),
                        2,
                        f"{symbol_set}/{sector}/{key} = {code!r}"
                    )
                    self.assertTrue(
                        code.isdigit(),
                        f"{symbol_set}/{sector}/{key} = {code!r}"
                    )

                self.assertEqual(
                    len(set(codes.values())),
                    len(codes),
                    f"duplicate code in {symbol_set}/{sector}"
                )


class TestCommonModifiers(QgisTestCase):

    """
    E-8: 2525E's COMMON sector 1/2 modifier tables, selected by SIDC
    digits 21/22 rather than scoped to one symbol_set - see
    sidc.py's common_modifiers_for_edition()/_resolve_modifier() and
    sidc_2525e.py's own header comment on the mechanism. Confirmed by
    hand against a rendered symbol before this was wired up (see
    docs/roadmap.md's Phase 12 entry); these pin that finding down.
    """

    def test_common_sector1_modifier_sets_the_digit_21_flag(self):

        # Command Post Node (code 116 in the common table) on Land
        # Equipment - the exact case confirmed by hand-rendering before
        # this was wired into build_sidc().
        sidc = build_sidc(
            affiliation="friend",
            entity="rifle",
            symbol_set="land_equipment",
            sector1_modifier="command_post_node",
            edition="2525E",
        )

        self.assertEqual(len(sidc), 22)
        self.assertEqual(sidc[16:18], "16")
        self.assertEqual(sidc[20], "1")
        self.assertEqual(sidc[21], "0")


    def test_common_sector2_modifier_sets_the_digit_22_flag(self):

        sidc = build_sidc(
            affiliation="friend",
            entity="rifle",
            symbol_set="land_equipment",
            sector2_modifier="airborne",
            edition="2525E",
        )

        self.assertEqual(len(sidc), 22)
        self.assertEqual(sidc[20], "0")
        self.assertEqual(sidc[21], "1")


    def test_both_sectors_common_sets_both_flags(self):

        sidc = build_sidc(
            affiliation="friend",
            entity="rifle",
            symbol_set="land_equipment",
            sector1_modifier="command_post_node",
            sector2_modifier="airborne",
            edition="2525E",
        )

        self.assertEqual(len(sidc), 22)
        self.assertEqual(sidc[20:22], "11")


    def test_no_common_modifier_keeps_the_plain_20_character_sidc(self):

        # Every pre-existing call site, and every 2525E call that
        # never resolves a common modifier, must keep producing the
        # SIDC length it always has - this is additive, not a format
        # change.
        sidc = build_sidc(
            affiliation="friend",
            entity="rifle",
            symbol_set="land_equipment",
            edition="2525E",
        )

        self.assertEqual(len(sidc), 20)


    def test_own_set_modifier_wins_on_a_name_collision(self):

        # "biological" exists in both land_equipment's own sector1
        # table and the common one, same label, different code - the
        # own-set entry must win, matching what the merged dropdown
        # offers (see _point_symbol_layer.py's _merge_common_labels()).
        sidc = build_sidc(
            affiliation="friend",
            entity="rifle",
            symbol_set="land_equipment",
            sector1_modifier="biological",
            edition="2525E",
        )

        self.assertEqual(len(sidc), 20)
        self.assertEqual(
            sidc[16:18],
            MODIFIERS_SECTOR1_2525E["land_equipment"]["biological"],
        )


    def test_unknown_modifier_still_raises_with_common_available(self):

        with self.assertRaises(KeyError):

            build_sidc(
                affiliation="friend",
                entity="rifle",
                symbol_set="land_equipment",
                sector1_modifier="warp_drive",
                edition="2525E",
            )


    def test_2525d_has_no_common_modifiers(self):

        # common_modifiers_for_edition() is 2525E-only; a 2525D call
        # must not resolve a common-table key even if it happens to
        # exist in 2525E's common table.
        with self.assertRaises(KeyError):

            build_sidc(
                affiliation="friend",
                entity="infantry",
                sector1_modifier="command_post_node",
            )


class TestNoAegisOnlySymbols(QgisTestCase):

    """
    This project ships no AEGIS-only symbols - naval combat-system
    display constructs, not general-purpose military symbology.

    The rule was applied per-table as each mini-phase was built, which
    let two slip through: Airfield (131900, Table H-VI) and
    Target-Recorded (240603, Table H-XVII) were both kept on their own
    first pass, each with its own local reasoning. A sweep of every
    "(AEGIS only)" marking across the whole of Appendix H removed both
    2026-08-12. This test is that sweep's result, so the rule is
    enforced in one place rather than re-argued per table.

    Codes below are every AEGIS-only entry in Appendix H, read off the
    standard's own CONTROL MEASURE cells.
    """

    AEGIS_ONLY_CODES = (
        "131900",  # H-VI   Airfield
        "200101",  # H-XIV  Launch Area - Ellipse
        "200102",  # H-XIV  Launch Area - Rectangle
        "200201",  # H-XIV  Defended Area - Ellipse
        "200202",  # H-XIV  Defended Area - Rectangle
        "200300",  # H-XIV  No Attack (NOTACK) Zone
        "200400",  # H-XIV  Ship Area of Interest
        "200401",  # H-XIV  Ship Area of Interest - Ellipse
        "200402",  # H-XIV  Ship Area of Interest - Rectangle
        "200500",  # H-XIV  Active Maneuver Area
        "200600",  # H-XIV  Cued Acquisition Doctrine
        "200700",  # H-XIV  Radar Search Doctrine
        "211000",  # H-XIV  Launched Torpedo
        "211200",  # H-XIV  Acoustic Countermeasure (Decoy)
        "211300",  # H-XIV  Electronic Countermeasures (ECM) Decoy
        "240603",  # H-XVII Target-Recorded
        "240804",  # H-XVII Rectangular Target - Single Target
    )

    def test_no_aegis_only_code_is_in_the_control_measure_vocabulary(self):

        # Scoped to ENTITIES["control_measure"] deliberately: SIDC codes
        # are only unique WITHIN a symbol set, so checking the whole of
        # sidc.py would false-positive on Land Equipment entries that
        # happen to reuse 200400-200700.
        shipped = ENTITIES["control_measure"]

        offenders = {
            entity: code
            for entity, code in shipped.items()
            if code in self.AEGIS_ONLY_CODES
        }

        self.assertEqual(offenders, {})


    def test_the_two_that_were_removed_stay_removed(self):

        shipped = ENTITIES["control_measure"]

        self.assertNotIn("airfield", shipped)
        self.assertNotIn("target_recorded", shipped)
