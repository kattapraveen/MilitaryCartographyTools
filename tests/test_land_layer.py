# -*- coding: utf-8 -*-

"""
Tests for military_symbology/land_layer.py - the four "Tactical
Graphics - Land <Domain>" layers (MIL-STD-2525D Appendix D: Unit,
Civilian, Equipment, Installation), each a genuinely separate
single-domain layer built on _point_symbol_layer.py's shared factory -
unlike Space/Air, not merged via entity_symbol_set_overrides (see
land_layer.py's own module docstring for why).

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRenderContext,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from .qgis_test_case import FakeIface, QgisTestCase, edition_layer_name

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import land_layer
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES, MODIFIERS
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
)
from MilitaryCartographyTools.military_symbology.land_layer import (
    UNIT_LAYER_NAME,
    CIVILIAN_LAYER_NAME,
    EQUIPMENT_LAYER_NAME,
    INSTALLATION_LAYER_NAME,
    add_land_layers,
    add_land_unit_layer,
    add_land_civilian_layer,
    add_land_equipment_layer,
    add_land_installation_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

# (symbol_set, entity_labels attr, default_entity attr, include_echelon,
# a real entity to render-test with) - one row per domain, driving every
# generic test below via subTest() rather than four near-duplicate test
# classes.
_DOMAINS = [
    ("ground_unit", "_UNIT_ENTITY_LABELS", "DEFAULT_UNIT_ENTITY", True, "infantry"),
    ("land_civilian", "_CIVILIAN_ENTITY_LABELS", "DEFAULT_CIVILIAN_ENTITY", False, "civilian"),
    ("land_equipment", "_EQUIPMENT_ENTITY_LABELS", "DEFAULT_EQUIPMENT_ENTITY", False, "tank"),
    ("land_installation", "_INSTALLATION_ENTITY_LABELS", "DEFAULT_INSTALLATION_ENTITY", False, "military"),
]


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    def test_entity_labels_cover_every_entity_for_each_domain(self):

        for symbol_set, labels_attr, _, _, _ in _DOMAINS:

            with self.subTest(symbol_set=symbol_set):

                self.assertEqual(
                    set(getattr(land_layer, labels_attr)),
                    set(ENTITIES[symbol_set])
                )


class TestBuildLandLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_echelon_and_headquarters_applicability_per_domain(self):

        # Table VII (Ch 5): Field B (Echelon) applies only to Units;
        # Field S (Headquarters) applies to Units/Equipment/
        # Installations - all four Land layers here get headquarters,
        # only Land Unit gets echelon too.
        for symbol_set, labels_attr, default_attr, include_echelon, _ in _DOMAINS:

            with self.subTest(symbol_set=symbol_set):

                layer = build_single_domain_point_layer(
                    "Test Layer",
                    symbol_set,
                    getattr(land_layer, labels_attr),
                    getattr(land_layer, default_attr),
                    include_echelon=include_echelon,
                    include_headquarters=True,
                )

                field_names = [field.name() for field in layer.fields()]

                self.assertEqual("echelon" in field_names, include_echelon)
                self.assertIn("headquarters", field_names)


    def test_a_real_feature_resolves_to_a_valid_symbol_path_per_domain(self):

        for symbol_set, labels_attr, default_attr, include_echelon, entity in _DOMAINS:

            with self.subTest(symbol_set=symbol_set):

                layer = build_single_domain_point_layer(
                    "Test Layer",
                    symbol_set,
                    getattr(land_layer, labels_attr),
                    getattr(land_layer, default_attr),
                    include_echelon=include_echelon,
                    include_headquarters=True,
                )

                feature = QgsFeature(layer.fields())
                feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
                feature.setAttribute("affiliation", "friend")
                feature.setAttribute("entity", entity)
                feature.setAttribute("status", "present")
                feature.setAttribute("headquarters", False)

                if include_echelon:
                    feature.setAttribute("echelon", "unspecified")

                expr_context = QgsExpressionContext()
                expr_context.appendScope(
                    QgsExpressionContextUtils.layerScope(layer)
                )
                expr_context.setFeature(feature)

                render_context = QgsRenderContext()
                render_context.setExpressionContext(expr_context)

                symbol = layer.renderer().symbol().clone()
                symbol.startRender(render_context, layer.fields())

                svg_layer = symbol.symbolLayer(0)

                path, ok = svg_layer.dataDefinedProperties().valueAsString(
                    QgsSymbolLayer.Property.Name,
                    expr_context,
                    ""
                )

                self.assertTrue(ok)
                self.assertTrue(path.startswith("base64:"))


class TestAddLandLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_add_land_layers_creates_all_four(self):

        result = add_land_layers(self.iface)

        for name in (
            UNIT_LAYER_NAME,
            CIVILIAN_LAYER_NAME,
            EQUIPMENT_LAYER_NAME,
            INSTALLATION_LAYER_NAME,
        ):

            self.assertIsNotNone(result[name])

            matching = QgsProject.instance().mapLayersByName(edition_layer_name(name))

            self.assertEqual(len(matching), 1)


    def test_each_individual_adder_guards_against_a_duplicate(self):

        for adder, name in (
            (add_land_unit_layer, UNIT_LAYER_NAME),
            (add_land_civilian_layer, CIVILIAN_LAYER_NAME),
            (add_land_equipment_layer, EQUIPMENT_LAYER_NAME),
            (add_land_installation_layer, INSTALLATION_LAYER_NAME),
        ):

            with self.subTest(name=name):

                first = adder(self.iface)

                result = adder(self.iface)

                self.assertIsNone(result)

                matching = QgsProject.instance().mapLayersByName(edition_layer_name(name))

                self.assertEqual(len(matching), 1)
                self.assertEqual(matching[0].id(), first.id())


    def test_calling_add_land_layers_twice_only_fills_in_whats_missing(self):

        add_land_unit_layer(self.iface)

        result = add_land_layers(self.iface)

        # Unit was already there (None, warned) - the other three are new.
        self.assertIsNone(result[UNIT_LAYER_NAME])
        self.assertIsNotNone(result[CIVILIAN_LAYER_NAME])
        self.assertIsNotNone(result[EQUIPMENT_LAYER_NAME])
        self.assertIsNotNone(result[INSTALLATION_LAYER_NAME])

        for name in (
            UNIT_LAYER_NAME,
            CIVILIAN_LAYER_NAME,
            EQUIPMENT_LAYER_NAME,
            INSTALLATION_LAYER_NAME,
        ):

            self.assertEqual(
                len(QgsProject.instance().mapLayersByName(edition_layer_name(name))),
                1
            )


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_land_unit_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], edition_layer_name(UNIT_LAYER_NAME))


class TestLandEquipmentLawEnforcementFamily(QgisTestCase):

    """
    MIL-STD-2525D Table A-XXV's law-enforcement family for Land
    Equipment (symbol set 15), which shipped truncated through 1.0.3 -
    generic + Border Patrol + Customs + DEA only, four of twelve.

    The codes below are written out longhand, transcribed from the
    printed table rather than generated, so this test disagrees with
    the source when the source is wrong rather than agreeing with it
    by construction.
    """

    # Table A-XXV, printed page 73.
    LAW_ENFORCEMENT = {
        "law_enforcement": "170000",
        "bureau_of_alcohol_tobacco_firearms_and_explosives": "170100",
        "border_patrol": "170200",
        "customs_service": "170300",
        "drug_enforcement_agency": "170400",
        "department_of_justice": "170500",
        "federal_bureau_of_investigation": "170600",
        "police": "170700",
        "united_states_secret_service": "170800",  # nosec B105 # pragma: allowlist secret
        "transportation_security_administration": "170900",
        "coast_guard": "171000",
        "us_marshals_service": "171100",
    }


    def test_every_law_enforcement_entity_is_present_with_the_right_code(self):

        for entity, code in self.LAW_ENFORCEMENT.items():

            with self.subTest(entity=entity):

                self.assertEqual(ENTITIES["land_equipment"].get(entity), code)


    def test_the_family_has_no_extra_members(self):

        # Guards the other direction: nothing invented, and nothing
        # copied in from the Activities or Land Installation families,
        # whose tails differ (Prison, Law Enforcement Vessel).
        in_range = {
            entity: code
            for entity, code in ENTITIES["land_equipment"].items()
            if code.startswith("17")
        }

        self.assertEqual(in_range, self.LAW_ENFORCEMENT)


    def test_land_equipment_has_no_prison(self):

        # Prison exists in Activities (131508) and Land Installation
        # (112108) but NOT in Land Equipment, which is what shifts this
        # set's tail by one relative to those two: Police is followed
        # directly by USSS here. Recorded so nobody "completes" the
        # family by copying another set's list.
        self.assertNotIn("prison", ENTITIES["land_equipment"])


    def test_coast_guard_is_present_and_is_not_called_a_vessel(self):

        # 171000 is Coast Guard in Table A-XXV. Worth pinning because
        # sidc.py calls the SAME position in two other sets
        # "law_enforcement_vessel" (land_installation 112111, activities
        # 131511) - both of which the standard also prints as Coast
        # Guard, so those two are mislabelled and this one must not be
        # "corrected" to match them. The standard's real Law Enforcement
        # Vessel is Sea Surface 140300, which sidc.py has right.
        self.assertEqual(ENTITIES["land_equipment"]["coast_guard"], "171000")
        self.assertNotIn("law_enforcement_vessel", ENTITIES["land_equipment"])
        self.assertEqual(ENTITIES["sea_surface"]["law_enforcement_vessel"], "140300")


    def test_every_law_enforcement_entity_renders_a_real_icon(self):

        # milsymbol falls back to a bare frame for a code it doesn't
        # know, and every unknown code yields the SAME frame - so an
        # entity whose SVG matches the bogus control's is one milsymbol
        # cannot actually draw.
        from MilitaryCartographyTools.military_symbology import symbol_engine
        from MilitaryCartographyTools.military_symbology.sidc import build_sidc

        bare_frame = symbol_engine.render_symbol_svg(
            "10031500001799000000"
        )

        for entity in self.LAW_ENFORCEMENT:

            with self.subTest(entity=entity):

                svg = symbol_engine.render_symbol_svg(
                    build_sidc("friend", entity, symbol_set="land_equipment")
                )

                self.assertNotEqual(svg, bare_frame)


    def test_dea_label_uses_the_standards_own_wording(self):

        # Table A-XXV reads "Drug Enforcement Administration (DEA)".
        # The KEY stays "..._agency" - it shipped in 1.0.3 and is
        # written into saved features - but the label a user reads is
        # the standard's.
        self.assertEqual(
            land_layer._EQUIPMENT_ENTITY_LABELS["drug_enforcement_agency"],
            "Drug Enforcement Administration (DEA)"
        )


class TestLandInstallationLawEnforcementFamily(QgisTestCase):

    """
    MIL-STD-2525D Table A-XXVII's law-enforcement family for Land
    Installation (symbol set 20). Codes transcribed longhand from the
    printed table, same reasoning as the Land Equipment class above.
    """

    # Table A-XXVII, printed page 77.
    LAW_ENFORCEMENT = {
        "law_enforcement": "112100",
        "bureau_of_alcohol_tobacco_firearms_and_explosives": "112101",
        "border_patrol": "112102",
        "customs_service": "112103",
        "drug_enforcement_agency": "112104",
        "department_of_justice": "112105",
        "federal_bureau_of_investigation": "112106",
        "police": "112107",
        "prison": "112108",
        "secret_service": "112109",  # nosec B105 # pragma: allowlist secret
        "transportation_security_agency": "112110",
        "law_enforcement_vessel": "112111",
        "us_marshals_service": "112112",
    }


    def test_every_law_enforcement_entity_is_present_with_the_right_code(self):

        for entity, code in self.LAW_ENFORCEMENT.items():

            with self.subTest(entity=entity):

                self.assertEqual(
                    ENTITIES["land_installation"].get(entity), code
                )


    def test_the_family_has_no_extra_members(self):

        in_range = {
            entity: code
            for entity, code in ENTITIES["land_installation"].items()
            if code.startswith("1121")
        }

        self.assertEqual(in_range, self.LAW_ENFORCEMENT)


    def test_every_law_enforcement_entity_renders_a_real_icon(self):

        from MilitaryCartographyTools.military_symbology import symbol_engine
        from MilitaryCartographyTools.military_symbology.sidc import build_sidc

        bare_frame = symbol_engine.render_symbol_svg(
            "10032000001199000000"
        )

        for entity in self.LAW_ENFORCEMENT:

            with self.subTest(entity=entity):

                svg = symbol_engine.render_symbol_svg(
                    build_sidc(
                        "friend", entity, symbol_set="land_installation"
                    )
                )

                self.assertNotEqual(svg, bare_frame)


class TestCoastGuardIsNotLabelledAVessel(QgisTestCase):

    """
    `law_enforcement_vessel` is a milsymbol-ism sitting on the code the
    standard prints as Coast Guard, in two symbol sets. The KEY is
    deliberately left wrong - it is written into saved features - so
    these tests pin the LABEL, which is the only thing a user reads.

    The standard's genuine Law Enforcement Vessel is Sea Surface 140300
    and must keep its name.
    """

    def test_land_installation_112111_reads_coast_guard(self):

        self.assertEqual(
            ENTITIES["land_installation"]["law_enforcement_vessel"],
            "112111"
        )

        self.assertEqual(
            land_layer._INSTALLATION_ENTITY_LABELS["law_enforcement_vessel"],
            "Coast Guard"
        )


    def test_activities_131511_reads_coast_guard(self):

        from MilitaryCartographyTools.military_symbology import activities_layer

        self.assertEqual(
            ENTITIES["activities"]["law_enforcement_vessel"], "131511"
        )

        self.assertEqual(
            activities_layer._ENTITY_LABELS["law_enforcement_vessel"],
            "Coast Guard"
        )


    def test_sea_surface_keeps_the_real_law_enforcement_vessel(self):

        from MilitaryCartographyTools.military_symbology import sea_surface_layer

        self.assertEqual(
            ENTITIES["sea_surface"]["law_enforcement_vessel"], "140300"
        )

        self.assertEqual(
            sea_surface_layer._ENTITY_LABELS["law_enforcement_vessel"],
            "Law Enforcement Vessel"
        )


    def test_the_agency_wording_is_gone_from_every_land_dropdown(self):

        # The maintainer found "Drug Enforcement Agency" in the live
        # dropdown after a fix that corrected the identical wording one
        # dict higher in the same file. Assert across BOTH label dicts
        # so a one-set fix cannot pass again.
        for labels in (
            land_layer._EQUIPMENT_ENTITY_LABELS,
            land_layer._INSTALLATION_ENTITY_LABELS,
        ):

            with self.subTest(labels=len(labels)):

                self.assertNotIn(
                    "Drug Enforcement Agency", set(labels.values())
                )

                self.assertNotIn(
                    "Transportation Security Agency (TSA)",
                    set(labels.values())
                )


class TestLandInstallationVocabulary(QgisTestCase):

    """
    D-3: Land Installation's vocabulary against MIL-STD-2525D Table
    A-XXVII, completed 2026-08-18 (99 -> 130 entities).
    """

    # Every code milsymbol's landinstallation.js draws that the standard
    # does NOT print anywhere in its text. Kept because they shipped and
    # are in users' saved features; marked in the label so they cannot be
    # mistaken for standard entities.
    NON_STANDARD = {"home": "112300", "airport": "120803"}


    def test_every_entity_renders_a_real_icon(self):

        from MilitaryCartographyTools.military_symbology import symbol_engine
        from MilitaryCartographyTools.military_symbology.sidc import build_sidc

        bare_frame = symbol_engine.render_symbol_svg("10032000001199000000")

        for entity in ENTITIES["land_installation"]:

            with self.subTest(entity=entity):

                svg = symbol_engine.render_symbol_svg(
                    build_sidc(
                        "friend", entity, symbol_set="land_installation"
                    )
                )

                self.assertNotEqual(svg, bare_frame)


    def test_codes_are_in_ascending_order(self):

        # Not cosmetic: the dict is maintained by inserting each new code
        # next to its neighbours, and a code out of order is the visible
        # symptom of an entry filed under the wrong group.
        codes = list(ENTITIES["land_installation"].values())

        self.assertEqual(codes, sorted(codes))


    def test_non_standard_entities_say_so_in_their_label(self):

        for entity, code in self.NON_STANDARD.items():

            with self.subTest(entity=entity):

                self.assertEqual(ENTITIES["land_installation"][entity], code)

                self.assertIn(
                    "non-standard",
                    land_layer._INSTALLATION_ENTITY_LABELS[entity]
                )


    def test_group_headers_are_not_named_after_their_children(self):

        # Two parent codes carried a child's name until 2026-08-18, which
        # would have put the same text on two different entries once the
        # children were added. Table A-XXVII's own wording for each.
        labels = land_layer._INSTALLATION_ENTITY_LABELS

        self.assertEqual(ENTITIES["land_installation"]["electric_power"], "120500")
        self.assertIn("Energy Facility Infrastructure", labels["electric_power"])

        self.assertEqual(
            ENTITIES["land_installation"]["electric_power_facility"], "120501"
        )
        self.assertEqual(labels["electric_power_facility"], "Electric Power")

        self.assertEqual(ENTITIES["land_installation"]["water"], "121400")
        self.assertIn("Water Supply Infrastructure", labels["water"])

        self.assertEqual(
            ENTITIES["land_installation"]["water_facility"], "121410"
        )
        self.assertEqual(labels["water_facility"], "Water")


    def test_no_label_is_used_twice(self):

        # The whole point of the two fixes above: a dropdown that offers
        # the same words on two rows is unusable.
        labels = list(land_layer._INSTALLATION_ENTITY_LABELS.values())

        self.assertEqual(len(labels), len(set(labels)))


class TestLandSectorModifiers(QgisTestCase):

    """
    D-4 (part one), 2026-08-18: sector 1/2 modifiers for Land Civilian,
    Equipment and Installation. Land Unit's own is a separate pass.

    Counts are transcribed from the standard's own tables, so a code
    quietly added from milsymbol's larger 2525E lists fails here.
    """

    # (symbol_set, sector, code count in MIL-STD-2525D, table)
    EXPECTED = [
        ("land_civilian", "sector1", 24, "A-XXIII"),
        ("land_civilian", "sector2", 1, "A-XXIV"),
        ("land_equipment", "sector1", 9, "A-XXVI"),
        ("land_installation", "sector1", 13, "A-XXVIII"),
        ("land_installation", "sector2", 8, "A-XXIX"),
    ]

    LABEL_ATTRS = {
        ("land_civilian", "sector1"): "_CIVILIAN_SECTOR1_LABELS",
        ("land_civilian", "sector2"): "_CIVILIAN_SECTOR2_LABELS",
        ("land_equipment", "sector1"): "_EQUIPMENT_SECTOR1_LABELS",
        ("land_installation", "sector1"): "_INSTALLATION_SECTOR1_LABELS",
        ("land_installation", "sector2"): "_INSTALLATION_SECTOR2_LABELS",
    }


    def test_each_sector_has_exactly_the_standards_codes(self):

        for symbol_set, sector, count, table in self.EXPECTED:

            with self.subTest(symbol_set=symbol_set, sector=sector):

                codes = MODIFIERS[symbol_set][sector]

                self.assertEqual(len(codes), count, table)

                # Contiguous 01..NN, which is how every one of these
                # tables is printed - a gap means a dropped row.
                self.assertEqual(
                    sorted(codes.values()),
                    ["%02d" % n for n in range(1, count + 1)]
                )


    def test_labels_match_the_modifier_keys(self):

        for (symbol_set, sector), attr in self.LABEL_ATTRS.items():

            with self.subTest(symbol_set=symbol_set, sector=sector):

                self.assertEqual(
                    set(getattr(land_layer, attr)),
                    set(MODIFIERS[symbol_set][sector])
                )


    def test_land_equipment_has_no_sector_2(self):

        # MIL-STD-2525D has D.8.3 (Land equipment sector 1) and no
        # D.8.4 - confirmed in the table of contents and the body.
        # milsymbol's nine sIdm2 codes for symbol set 15 are mobility
        # indicators, which the standard encodes elsewhere. Pinned so
        # nobody "completes" the pair from milsymbol.
        self.assertIn("sector1", MODIFIERS["land_equipment"])
        self.assertNotIn("sector2", MODIFIERS["land_equipment"])

        self.assertFalse(
            hasattr(land_layer, "_EQUIPMENT_SECTOR2_LABELS")
        )


    def test_every_modifier_actually_changes_the_symbol(self):

        # A modifier that renders identically to the plain symbol is a
        # dropdown entry that does nothing - the user picks it, nothing
        # happens, and no test would otherwise notice.
        from MilitaryCartographyTools.military_symbology import symbol_engine
        from MilitaryCartographyTools.military_symbology.sidc import build_sidc

        probes = [
            ("land_civilian", "civilian", "sector1"),
            ("land_civilian", "civilian", "sector2"),
            ("land_equipment", "tank", "sector1"),
            ("land_installation", "military", "sector1"),
            ("land_installation", "military", "sector2"),
        ]

        for symbol_set, entity, sector in probes:

            plain = symbol_engine.render_symbol_svg(
                build_sidc("friend", entity, symbol_set=symbol_set)
            )

            for key in MODIFIERS[symbol_set][sector]:

                with self.subTest(symbol_set=symbol_set, modifier=key):

                    svg = symbol_engine.render_symbol_svg(
                        build_sidc(
                            "friend",
                            entity,
                            symbol_set=symbol_set,
                            **{sector + "_modifier": key}
                        )
                    )

                    self.assertNotEqual(svg, plain)


    def test_the_three_layers_offer_the_dropdowns(self):

        for adder, symbol_set in (
            (add_land_civilian_layer, "land_civilian"),
            (add_land_equipment_layer, "land_equipment"),
            (add_land_installation_layer, "land_installation"),
        ):

            with self.subTest(symbol_set=symbol_set):

                QgsProject.instance().clear()
                QgsProject.instance().setCrs(WGS84)

                layer = adder(FakeIface())

                names = [f.name() for f in layer.fields()]

                self.assertIn("sector1_modifier", names)

                if "sector2" in MODIFIERS[symbol_set]:
                    self.assertIn("sector2_modifier", names)
                else:
                    self.assertNotIn("sector2_modifier", names)


class TestLandUnitSectorModifiers(QgisTestCase):

    """
    D-4b, 2026-08-18: Land Unit's own sector 1/2 modifiers (MIL-STD-2525D
    Tables D-VI/D-VII) - the fourth and largest of the Land layers'
    modifier passes, and the one that took real verification.

    Both milsymbol's landunit.js and the most easily available "2525d"
    TSV source turned out to be unsafe to use directly here - see
    sidc.py's own MODIFIERS["ground_unit"] comment for the two distinct
    failures found. Every code below is transcribed from the printed
    standard, longhand, for exactly that reason.
    """

    # Table D-VI, printed pages 206-214. 76 codes: 01-78 with 30 and 38
    # reserved. The 8 marked below are where milsymbol's own _STD2525
    # ternary picks the wrong branch relative to what 2525D prints -
    # see the vendored-file patch in military_symbology/vendor/
    # milsymbol.js and THIRD_PARTY_NOTICES.md.
    SECTOR1 = {
        "airmobile_air_assault": "01",   # corrected - was Tactical Satellite Communications
        "area": "02", "attack": "03", "biological": "04", "border": "05",
        "bridging": "06", "chemical": "07", "close_protection": "08",
        "combat": "09", "command_and_control": "10",
        "communications_contingency_package": "11", "construction": "12",
        "cross_cultural_communication": "13", "crowd_and_riot_control": "14",
        "decontamination": "15", "detention": "16",
        "direct_communications": "17", "diving": "18", "division": "19",
        "dog": "20", "drilling": "21", "electro_optical": "22",
        "enhanced": "23", "explosive_ordnance_disposal": "24",
        "fire_direction_center": "25", "force": "26", "forward": "27",
        "ground_station_module": "28", "landing_support": "29",
        "maintenance": "31", "meteorological": "32",
        "mine_countermeasure": "33", "missile": "34",
        "mobile_advisor_and_support": "35",
        "mobile_subscriber_equipment": "36", "mobility_support": "37",
        "multinational": "39", "multinational_specialized_unit": "40",
        "multiple_rocket_launcher": "41", "nato_medical_role_1": "42",
        "nato_medical_role_2": "43", "nato_medical_role_3": "44",
        "nato_medical_role_4": "45", "naval": "46",
        "node_center": "47",             # corrected - was Unmanned Aerial Vehicle
        "nuclear": "48", "operations": "49", "radar": "50",
        "radio_frequency_identification_interrogator_sensor": "51",
        "radiological": "52", "search_and_rescue": "53", "security": "54",
        "sensor": "55",
        "sensor_control_module": "56",   # corrected - was Weapon
        "signals_intelligence": "57",
        "single_shelter_switch": "58",   # corrected - was Armored
        "single_rocket_launcher": "59", "smoke": "60", "sniper": "61",
        "sound_ranging": "62", "special_operations_forces": "63",
        "special_weapons_and_tactics": "64", "survey": "65",
        "tactical_exploitation": "66", "target_acquisition": "67",
        "topographic_geospatial": "68", "utility": "69",
        "video_imagery": "70",
        "accident": "71",                # corrected - was Mobility Assault
        "other": "72",                   # corrected - was Amphibious Warfare Ship
        "civilian": "73",                # corrected - was Load Handling System
        "antisubmarine_warfare": "74",   # corrected - was Palletized Load System
        "medevac": "75", "ranger": "76", "support": "77", "aviation": "78",
    }

    # Table D-VII, printed pages 216-222. 57 codes: 01-57, contiguous.
    SECTOR2 = {
        "airborne": "01", "arctic": "02", "battle_damage_repair": "03",
        "bicycle_equipped": "04", "casualty_staging": "05",
        "clearing": "06", "close_range": "07", "control": "08",
        "decontamination": "09", "demolition": "10", "dental": "11",
        "digital": "12",
        "enhanced_position_location_reporting_system": "13",
        "equipment": "14", "heavy": "15", "high_altitude": "16",
        "intermodal": "17", "intensive_care": "18", "light": "19",
        "laboratory": "20", "launcher": "21", "long_range": "22",
        "low_altitude": "23", "medium": "24", "medium_altitude": "25",
        "medium_range": "26", "mountain": "27",
        "high_to_medium_altitude": "28", "multi_channel": "29",
        "optical": "30", "pack_animal": "31",
        "patient_evacuation_coordination": "32",
        "preventive_maintenance": "33", "psychological": "34",
        "radio_relay_line_of_sight": "35", "railroad": "36",
        "recovery_unmanned_systems": "37", "recovery_maintenance": "38",
        "rescue_coordination_center": "39", "riverine": "40",
        "single_channel": "41", "ski": "42", "short_range": "43",
        "strategic": "44", "support": "45", "tactical": "46",
        "towed": "47", "troop": "48",
        "vertical_or_short_take_off_and_landing": "49", "veterinary": "50",
        "wheeled": "51", "high_to_low_altitude": "52",
        "medium_to_low_altitude": "53", "attack": "54", "refuel": "55",
        "utility": "56", "combat_search_and_rescue": "57",
    }


    def test_sector1_matches_table_d_vi_exactly(self):

        self.assertEqual(MODIFIERS["ground_unit"]["sector1"], self.SECTOR1)


    def test_sector2_matches_table_d_vii_exactly(self):

        self.assertEqual(MODIFIERS["ground_unit"]["sector2"], self.SECTOR2)


    def test_table_d_vi_does_not_extend_to_milsymbols_full_range(self):

        # milsymbol's own landunit.js defines sIdm1 codes up to 99;
        # the printed standard's Table D-VI stops at 78. Codes 79-98
        # (Tilt-Rotor, Command Post Node, Joint Network Node among them)
        # are 2525E-only and must not appear here.
        codes = set(MODIFIERS["ground_unit"]["sector1"].values())

        for code in ("79", "80", "81", "82", "98", "99"):
            self.assertNotIn(code, codes)


    def test_table_d_vii_does_not_extend_past_its_real_57_codes(self):

        # The standard's own Table D-VII prints "Reserved for future
        # use" for 79-99, but the commonly available TSV source (and
        # milsymbol) both carry entries up to 78 - 21 more 2525E-only
        # codes that do not exist in 2525D's own table at all.
        codes = set(MODIFIERS["ground_unit"]["sector2"].values())

        for code in ("58", "60", "70", "78"):
            self.assertNotIn(code, codes)


    def test_reserved_sector1_codes_are_absent(self):

        codes = set(MODIFIERS["ground_unit"]["sector1"].values())

        self.assertNotIn("30", codes)
        self.assertNotIn("38", codes)


    def test_labels_match_the_modifier_keys(self):

        self.assertEqual(
            set(land_layer._UNIT_SECTOR1_LABELS),
            set(MODIFIERS["ground_unit"]["sector1"])
        )

        self.assertEqual(
            set(land_layer._UNIT_SECTOR2_LABELS),
            set(MODIFIERS["ground_unit"]["sector2"])
        )


    def test_every_modifier_renders_and_changes_the_symbol(self):

        from MilitaryCartographyTools.military_symbology import symbol_engine
        from MilitaryCartographyTools.military_symbology.sidc import build_sidc

        plain = symbol_engine.render_symbol_svg(
            build_sidc("friend", "infantry", symbol_set="ground_unit")
        )

        for sector in ("sector1", "sector2"):

            for key in MODIFIERS["ground_unit"][sector]:

                with self.subTest(sector=sector, modifier=key):

                    svg = symbol_engine.render_symbol_svg(
                        build_sidc(
                            "friend", "infantry", symbol_set="ground_unit",
                            **{sector + "_modifier": key}
                        )
                    )

                    self.assertNotEqual(svg, plain)


    def test_the_layer_offers_both_sector_dropdowns(self):

        layer = add_land_unit_layer(FakeIface())

        names = [f.name() for f in layer.fields()]

        self.assertIn("sector1_modifier", names)
        self.assertIn("sector2_modifier", names)


class TestVendoredMilsymbolPatch(QgisTestCase):

    """
    The 8 Land Unit sector-1 codes where milsymbol's own _STD2525
    ternary was found to select the wrong icon for MIL-STD-2525D - fixed
    by patching military_symbology/vendor/milsymbol.js directly, since
    ms.setStandard() is a single global flag and could not be flipped
    for just these 8 codes without affecting every other symbol that
    also branches on it. See THIRD_PARTY_NOTICES.md for the full
    reasoning and evidence.

    These pin the RENDERED glyph, not just the label - the whole point
    of patching rather than just relabelling was to make the two agree.
    """

    # (code, a fragment unique to the correct (post-patch) glyph)
    PATCHED = [
        ("01", "M85,55 L100,75 115,55"),  # Airmobile/Air Assault arrow
        ("47", ">NC<"),                    # Node Center
        ("56", ">SCM<"),                   # Sensor Control Module
        ("58", ">SSS<"),                   # Single Shelter Switch
        ("71", ">ACC<"),                   # Accident
        ("72", ">OTH<"),                   # Other
        ("73", ">CIV<"),                   # Civilian
        ("74", ">P<"),                     # Antisubmarine Warfare
    ]


    def test_the_patched_codes_render_the_2525d_glyph(self):

        from MilitaryCartographyTools.military_symbology import symbol_engine

        for code, fragment in self.PATCHED:

            with self.subTest(code=code):

                svg = symbol_engine.render_symbol_svg(
                    "1003100000121100%s00" % code
                )

                self.assertIn(fragment, svg)


    def test_the_wrong_pre_patch_glyphs_are_gone(self):

        # The exact glyph fragments that used to render before the
        # patch - milsymbol's default (_STD2525=true) branch, which did
        # not match Table D-VI.
        from MilitaryCartographyTools.military_symbology import symbol_engine

        wrong = {
            "01": "m 105,65 10,0",  # Tactical Satellite Communications
            "47": "m 80,65 20,13 20,-13 0,-5 -20,10 -20,-10 z",  # UAV path
            "56": ">WPN<",
            "71": ">MA<",
        }

        for code, fragment in wrong.items():

            with self.subTest(code=code):

                svg = symbol_engine.render_symbol_svg(
                    "1003100000121100%s00" % code
                )

                self.assertNotIn(fragment, svg)
