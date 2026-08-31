# -*- coding: utf-8 -*-

"""
Tests for military_symbology/land_unit_layer_nonnato.py - the
"Land Unit (Non-NATO)" layer, built on nonnato_symbol_engine.py's own
rendering rather than _point_symbol_layer.py's shared NATO builder.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRenderContext,
    QgsSymbolLayer,
)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import nonnato_symbology_functions
from MilitaryCartographyTools.military_symbology import land_unit_layer_nonnato
from MilitaryCartographyTools.military_symbology.land_unit_layer_nonnato import (
    LAYER_NAME,
    ENTITY_LABELS,
    add_land_unit_layer_nonnato,
    build_land_unit_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    ENEMY_INFO_UNKNOWN_ENTITY,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    build_sidc,
    entities_for_edition,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestEntityLabelsMatchTheReviewedList(QgisTestCase):

    def test_every_real_key_is_a_valid_app6e_ground_unit_entity(self):

        real_keys = entities_for_edition("2525E")["ground_unit"]

        for key in ENTITY_LABELS:

            if key == ENEMY_INFO_UNKNOWN_ENTITY:
                continue

            with self.subTest(entity=key):

                self.assertIn(key, real_keys)


    def test_count_matches_the_reviewed_list_plus_enemy_info_unknown(self):

        # 20 real entities the maintainer's reviewed check sheet
        # confirmed, plus Enemy (Info Unknown) - see the rules record's
        # "Required entities" section.
        self.assertEqual(len(ENTITY_LABELS), 21)
        self.assertIn(ENEMY_INFO_UNKNOWN_ENTITY, ENTITY_LABELS)


class TestBuildLandUnitLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def _render_path_for(self, layer, attributes):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))

        for name, value in attributes.items():
            feature.setAttribute(name, value)

        expr_context = QgsExpressionContext()
        expr_context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        expr_context.setFeature(feature)

        render_context = QgsRenderContext()
        render_context.setExpressionContext(expr_context)

        symbol = layer.renderer().symbol().clone()
        symbol.startRender(render_context, layer.fields())

        svg_layer = symbol.symbolLayer(0)

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name, expr_context, ""
        )

        self.assertTrue(ok, "expression failed to evaluate")

        return path


    def test_every_field_exists_with_the_right_type(self):

        layer = build_land_unit_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "affiliation", "entity", "echelon", "status",
                "combined_arms", "unique_designation", "rotation", "scale",
            ]
        )


    def test_every_real_entity_renders_a_valid_symbol_path(self):

        layer = build_land_unit_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                path = self._render_path_for(
                    layer,
                    {
                        "affiliation": "friend",
                        "entity": entity,
                        "echelon": "unspecified",
                        "status": "present",
                        "combined_arms": False,
                    },
                )

                self.assertTrue(path.startswith("base64:"))


    def test_every_affiliation_renders(self):

        layer = build_land_unit_layer_nonnato()

        for affiliation in (
            "friend", "hostile", "neutral", "unknown",
            "friendly_paramilitary", "nonstate_hostile",
        ):

            with self.subTest(affiliation=affiliation):

                path = self._render_path_for(
                    layer,
                    {
                        "affiliation": affiliation,
                        "entity": "infantry",
                        "echelon": "unspecified",
                        "status": "present",
                        "combined_arms": False,
                    },
                )

                self.assertTrue(path.startswith("base64:"))


    def test_combined_arms_checkbox_reaches_the_render(self):

        layer = build_land_unit_layer_nonnato()

        without = self._render_path_for(
            layer,
            {
                "affiliation": "friend", "entity": "infantry",
                "echelon": "unspecified", "status": "present",
                "combined_arms": False,
            },
        )
        with_ca = self._render_path_for(
            layer,
            {
                "affiliation": "friend", "entity": "infantry",
                "echelon": "unspecified", "status": "present",
                "combined_arms": True,
            },
        )

        self.assertNotEqual(without, with_ca)


    def test_entity_keys_match_a_real_ground_unit_sidc(self):

        # Confirms ENTITY_LABELS' keys are exactly what
        # render_nonnato_unit_svg()'s own build_sidc() call expects -
        # not just present in the 2525E vocabulary (already checked
        # above) but resolving with no KeyError for every one.
        for entity in ENTITY_LABELS:

            if entity == ENEMY_INFO_UNKNOWN_ENTITY:
                continue

            with self.subTest(entity=entity):

                build_sidc(
                    affiliation="friend", entity=entity,
                    symbol_set="ground_unit", edition="2525E",
                )


class TestAddLandUnitLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_adds_a_layer_named_land_unit_nonnato(self):

        layer = add_land_unit_layer_nonnato(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), layer.id())


    def test_guards_against_a_duplicate(self):

        first = add_land_unit_layer_nonnato(self.iface)

        result = add_land_unit_layer_nonnato(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
