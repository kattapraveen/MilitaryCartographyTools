# -*- coding: utf-8 -*-

"""
Tests for military_symbology/land_sigint_layer_nonnato.py - the
"SIGINT (Non-NATO)" layer, built on nonnato_symbol_engine.py's own
rendering rather than _point_symbol_layer.py's shared NATO builder.

Military Cartography Tools
"""

import base64

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
from MilitaryCartographyTools.military_symbology import land_sigint_layer_nonnato
from MilitaryCartographyTools.military_symbology.land_sigint_layer_nonnato import (
    LAYER_NAME,
    ENTITY_LABELS,
    add_land_sigint_layer_nonnato,
    build_land_sigint_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    build_sidc,
    entities_for_edition,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestEntityLabelsMatchTheReviewedList(QgisTestCase):

    def test_every_key_is_a_valid_app6e_sigint_land_entity(self):

        real_keys = entities_for_edition("2525E")["sigint_land"]

        for key in ENTITY_LABELS:

            with self.subTest(entity=key):

                self.assertIn(key, real_keys)


    def test_count_matches_the_reviewed_list(self):

        # Jammer and Radar only - see the rules record's Part B: "Land
        # SIGINT: only Jammer and Radar are required."
        self.assertEqual(len(ENTITY_LABELS), 2)
        self.assertIn("jammer", ENTITY_LABELS)
        self.assertIn("radar", ENTITY_LABELS)


class TestBuildLandSigintLayerNonnato(QgisTestCase):

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

        layer = build_land_sigint_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["affiliation", "entity", "unique_designation", "rotation", "scale"]
        )


    def test_no_echelon_status_combined_arms_or_dimension_field(self):

        layer = build_land_sigint_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        for absent in ("echelon", "status", "combined_arms", "dimension"):
            self.assertNotIn(absent, field_names)


    def test_every_entity_renders_a_valid_symbol_path(self):

        layer = build_land_sigint_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                path = self._render_path_for(
                    layer, {"affiliation": "friend", "entity": entity}
                )

                self.assertTrue(path.startswith("base64:"))


    def test_every_affiliation_renders(self):

        layer = build_land_sigint_layer_nonnato()

        for affiliation in (
            "friend", "hostile", "neutral", "unknown",
            "friendly_paramilitary", "nonstate_hostile",
        ):

            with self.subTest(affiliation=affiliation):

                path = self._render_path_for(
                    layer, {"affiliation": affiliation, "entity": "radar"}
                )

                self.assertTrue(path.startswith("base64:"))


    def test_designation_reaches_the_render(self):

        layer = build_land_sigint_layer_nonnato()

        svg = self._decoded_svg_for(
            layer,
            {
                "affiliation": "friend", "entity": "radar",
                "unique_designation": "a1",
            },
        )

        self.assertIn("A1", svg)


    def test_a_typed_designation_does_not_shrink_the_icon(self):

        # Same fix, same reasoning as Land Unit's own regression test -
        # see that module's test file for the full "reported live"
        # story and why the raw Size property is EXPECTED to grow with
        # a designation, not stay flat.
        layer = build_land_sigint_layer_nonnato()

        without_designation = self._render_size_for(
            layer,
            {"affiliation": "friend", "entity": "radar", "unique_designation": ""},
        )
        with_designation = self._render_size_for(
            layer,
            {"affiliation": "friend", "entity": "radar", "unique_designation": "HQ 3"},
        )

        self.assertGreater(with_designation, without_designation)

        plain_width = QgsExpression(
            "mct_nonnato_sigint_svg_width('friend','radar','')"
        ).evaluate()

        amplified_width = QgsExpression(
            "mct_nonnato_sigint_svg_width('friend','radar','HQ 3')"
        ).evaluate()

        icon_footprint_without = without_designation
        icon_footprint_with = with_designation * plain_width / amplified_width

        self.assertAlmostEqual(
            icon_footprint_without, icon_footprint_with, places=3
        )


    def test_entity_keys_match_a_real_sigint_land_sidc(self):

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                build_sidc(
                    affiliation="friend", entity=entity,
                    symbol_set="sigint_land", edition="2525E",
                )


class TestAddLandSigintLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_adds_a_layer_named_sigint_nonnato(self):

        layer = add_land_sigint_layer_nonnato(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), layer.id())


    def test_guards_against_a_duplicate(self):

        first = add_land_sigint_layer_nonnato(self.iface)

        result = add_land_sigint_layer_nonnato(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
