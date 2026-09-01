# -*- coding: utf-8 -*-

"""
Tests for military_symbology/land_equipment_layer_nonnato.py - the
"Land Equipment (Non-NATO)" layer, built on nonnato_symbol_engine.py's
own rendering rather than _point_symbol_layer.py's shared NATO builder.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpression,
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
from MilitaryCartographyTools.military_symbology import land_equipment_layer_nonnato
from MilitaryCartographyTools.military_symbology.land_equipment_layer_nonnato import (
    LAYER_NAME,
    ENTITY_LABELS,
    add_land_equipment_layer_nonnato,
    build_land_equipment_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY,
    BAR_MINE_ENTITY,
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY,
    INFLUENCE_MINE_ANTI_TANK_ENTITY,
    MINE_GREEN,
    UNKNOWN_MINE_ENTITY,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    build_sidc,
    entities_for_edition,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

SYNTHETIC_ENTITIES = frozenset({
    UNKNOWN_MINE_ENTITY,
    INFLUENCE_MINE_ANTI_TANK_ENTITY,
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY,
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY,
    BAR_MINE_ENTITY,
})


class TestEntityLabelsMatchTheReviewedList(QgisTestCase):

    def test_every_real_key_is_a_valid_app6e_land_equipment_entity(self):

        real_keys = entities_for_edition("2525E")["land_equipment"]

        for key in ENTITY_LABELS:

            if key in SYNTHETIC_ENTITIES:
                continue

            with self.subTest(entity=key):

                self.assertIn(key, real_keys)


    def test_count_matches_the_reviewed_list(self):

        # 53 real entities (11 non-tiered + 39 weapon-tier siblings +
        # 3 repurposed Machine Gun tiers) plus 5 synthetic mine icons -
        # see the rules record's "Required entities" section.
        self.assertEqual(len(ENTITY_LABELS), 58)

        for entity in SYNTHETIC_ENTITIES:
            self.assertIn(entity, ENTITY_LABELS)


class TestBuildLandEquipmentLayerNonnato(QgisTestCase):

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


    def _decoded_svg_for(self, layer, attributes):

        import base64

        path = self._render_path_for(layer, attributes)

        self.assertTrue(path.startswith("base64:"))

        return base64.b64decode(path[len("base64:"):]).decode("utf-8")


    def _render_size_for(self, layer, attributes):

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

        size, ok = svg_layer.dataDefinedProperties().valueAsDouble(
            QgsSymbolLayer.Property.Size, expr_context, 0.0
        )

        self.assertTrue(ok, "size expression failed to evaluate")

        return size


    def test_every_field_exists_with_the_right_type(self):

        layer = build_land_equipment_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["affiliation", "entity", "unique_designation", "rotation", "scale"]
        )


    def test_no_echelon_status_or_combined_arms_field(self):

        layer = build_land_equipment_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        for absent in ("echelon", "status", "combined_arms"):
            self.assertNotIn(absent, field_names)


    def test_every_entity_renders_a_valid_symbol_path(self):

        layer = build_land_equipment_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                path = self._render_path_for(
                    layer, {"affiliation": "friend", "entity": entity}
                )

                self.assertTrue(path.startswith("base64:"))


    def test_every_affiliation_renders(self):

        layer = build_land_equipment_layer_nonnato()

        for affiliation in (
            "friend", "hostile", "neutral", "unknown",
            "friendly_paramilitary", "nonstate_hostile",
        ):

            with self.subTest(affiliation=affiliation):

                path = self._render_path_for(
                    layer, {"affiliation": affiliation, "entity": "tank"}
                )

                self.assertTrue(path.startswith("base64:"))


    def test_every_mine_entity_renders_green_regardless_of_affiliation(self):

        layer = build_land_equipment_layer_nonnato()

        for entity in SYNTHETIC_ENTITIES | {
            "land_mine", "antitank_mine", "antipersonnel_land_mine"
        }:

            with self.subTest(entity=entity):

                svg = self._decoded_svg_for(
                    layer, {"affiliation": "hostile", "entity": entity}
                )

                self.assertIn(MINE_GREEN, svg)


    def test_designation_reaches_the_render(self):

        layer = build_land_equipment_layer_nonnato()

        svg = self._decoded_svg_for(
            layer,
            {
                "affiliation": "friend", "entity": "tank",
                "unique_designation": "a1",
            },
        )

        self.assertIn("A1", svg)


    def test_a_typed_designation_does_not_shrink_the_icon(self):

        # Same fix, same reasoning as Land Unit's own regression test -
        # see that module's test file for the full "reported live"
        # story and why the raw Size property is EXPECTED to grow with
        # a designation, not stay flat.
        layer = build_land_equipment_layer_nonnato()

        without_designation = self._render_size_for(
            layer,
            {"affiliation": "friend", "entity": "tank", "unique_designation": ""},
        )
        with_designation = self._render_size_for(
            layer,
            {"affiliation": "friend", "entity": "tank", "unique_designation": "HQ 3"},
        )

        self.assertGreater(with_designation, without_designation)

        plain_width = QgsExpression(
            "mct_nonnato_equipment_svg_width('friend','tank','')"
        ).evaluate()

        amplified_width = QgsExpression(
            "mct_nonnato_equipment_svg_width('friend','tank','HQ 3')"
        ).evaluate()

        icon_footprint_without = without_designation
        icon_footprint_with = with_designation * plain_width / amplified_width

        self.assertAlmostEqual(
            icon_footprint_without, icon_footprint_with, places=3
        )


    def test_entity_keys_match_a_real_land_equipment_sidc(self):

        # Confirms ENTITY_LABELS' keys are exactly what
        # render_nonnato_equipment_svg()'s own build_sidc() call
        # expects - not just present in the 2525E vocabulary (already
        # checked above) but resolving with no KeyError for every one.
        for entity in ENTITY_LABELS:

            if entity in SYNTHETIC_ENTITIES:
                continue

            with self.subTest(entity=entity):

                build_sidc(
                    affiliation="friend", entity=entity,
                    symbol_set="land_equipment", edition="2525E",
                )


class TestAddLandEquipmentLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_adds_a_layer_named_land_equipment_nonnato(self):

        layer = add_land_equipment_layer_nonnato(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), layer.id())


    def test_guards_against_a_duplicate(self):

        first = add_land_equipment_layer_nonnato(self.iface)

        result = add_land_equipment_layer_nonnato(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
