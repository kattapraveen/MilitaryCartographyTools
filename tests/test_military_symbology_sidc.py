# -*- coding: utf-8 -*-

"""
Tests for military_symbology/sidc.py's build_sidc() - constructing a
20-character MIL-STD-2525D/APP-6D SIDC from named components, per the field
positions/codes read directly from the vendored milsymbol.js's own parsing
logic (see sidc.py's own module docstring for the exact source files).

Military Cartography Tools
"""

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.military_symbology.sidc import build_sidc, MODIFIERS


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
