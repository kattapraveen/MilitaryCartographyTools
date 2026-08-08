# -*- coding: utf-8 -*-

"""
Tests for military_symbology/cyberspace_layer.py - "Tactical Graphics -
Cyberspace" (MIL-STD-2525D Appendix L). Single-domain layer, no modifier
fields at all - L.5.3.2's own text: "There are no modifiers in
cyberspace symbols."

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
from MilitaryCartographyTools.military_symbology import cyberspace_layer
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES, MODIFIERS
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
)
from MilitaryCartographyTools.military_symbology.cyberspace_layer import (
    OUTPUT_LAYER_NAME,
    add_cyberspace_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    def test_entity_labels_cover_every_cyberspace_entity(self):

        self.assertEqual(
            set(cyberspace_layer._ENTITY_LABELS),
            set(ENTITIES["cyberspace"])
        )


    def test_no_modifiers_entry_exists_at_all(self):

        self.assertNotIn("cyberspace", MODIFIERS)


class TestBuildCyberspaceLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _build(self):

        return build_single_domain_point_layer(
            OUTPUT_LAYER_NAME,
            "cyberspace",
            cyberspace_layer._ENTITY_LABELS,
            cyberspace_layer.DEFAULT_ENTITY,
            include_echelon=False,
            include_headquarters=False,
        )


    def test_has_only_the_core_fields(self):

        # Table L-II lists no Field B (Echelon)/Field S (Headquarters),
        # and there are no sector 1/2 modifier fields at all.
        layer = self._build()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "affiliation",
                "entity",
                "status",
                "unique_designation",
            ]
        )


    def _resolve_svg_path(self, layer, entity):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", entity)
        feature.setAttribute("status", "present")

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

        return svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name,
            expr_context,
            ""
        )


    def test_a_plain_entity_resolves_to_a_valid_symbol_path(self):

        layer = self._build()

        path, ok = self._resolve_svg_path(layer, cyberspace_layer.DEFAULT_ENTITY)

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_a_hierarchy_only_generic_entity_resolves(self):

        # "botnet" (110000) has no icon in milsymbol's own D-edition
        # source - frame-only, per Table L-II's own remarks column.
        layer = self._build()

        path, ok = self._resolve_svg_path(layer, "botnet")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_entities_sharing_a_name_but_different_codes_both_resolve(self):

        # "Network Outage" appears twice in the standard under different
        # categories (130200 Health and Status, 160700 Effect) - both
        # kept as distinct entities, confirm both actually resolve.
        layer = self._build()

        for entity in ("network_outage_health_status", "network_outage_effect"):

            with self.subTest(entity=entity):

                path, ok = self._resolve_svg_path(layer, entity)

                self.assertTrue(ok)
                self.assertTrue(path.startswith("base64:"))


class TestAddCyberspaceLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_creates_and_adds_the_layer(self):

        layer = add_cyberspace_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        first = add_cyberspace_layer(self.iface)

        result = add_cyberspace_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())

        self.assertEqual(
            len(self.iface.messageBar().calls),
            1
        )


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_cyberspace_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], OUTPUT_LAYER_NAME)
