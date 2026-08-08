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
