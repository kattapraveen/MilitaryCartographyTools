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

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import land_layer
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES
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

            matching = QgsProject.instance().mapLayersByName(name)

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

                matching = QgsProject.instance().mapLayersByName(name)

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
                len(QgsProject.instance().mapLayersByName(name)),
                1
            )


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_land_unit_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], UNIT_LAYER_NAME)


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
