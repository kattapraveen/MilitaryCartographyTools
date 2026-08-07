# -*- coding: utf-8 -*-

"""
Tests for military_symbology/sidc.py's build_sidc() - constructing a
20-character MIL-STD-2525D/APP-6D SIDC from named components, per the field
positions/codes read directly from the vendored milsymbol.js's own parsing
logic (see sidc.py's own module docstring for the exact source files).

Military Cartography Tools
"""

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.military_symbology.sidc import build_sidc


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
            ("air", "rotary_wing", "01", "110200"),
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
