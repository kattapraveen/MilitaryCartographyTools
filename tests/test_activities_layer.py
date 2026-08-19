# -*- coding: utf-8 -*-

"""
Tests for military_symbology/activities_layer.py - "Activities"
(MIL-STD-2525D Appendix G). Single-domain layer, sector 1
modifiers only - no sector 2 field, per Appendix G's own explicit text
("Note: There are no sector 2 modifiers in activities symbols.").

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
from MilitaryCartographyTools.military_symbology import activities_layer
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES, MODIFIERS
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
)
from MilitaryCartographyTools.military_symbology.activities_layer import (
    OUTPUT_LAYER_NAME,
    add_activities_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    def test_entity_labels_cover_every_activities_entity(self):

        self.assertEqual(
            set(activities_layer._ENTITY_LABELS),
            set(ENTITIES["activities"])
        )


    def test_sector1_labels_cover_every_activities_modifier(self):

        self.assertEqual(
            set(activities_layer._SECTOR1_LABELS),
            set(MODIFIERS["activities"]["sector1"])
        )


class TestBuildActivitiesLayer(QgisTestCase):

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
            "activities",
            activities_layer._ENTITY_LABELS,
            activities_layer.DEFAULT_ENTITY,
            include_echelon=False,
            include_headquarters=False,
            sector1_labels=activities_layer._SECTOR1_LABELS,
        )


    def test_has_the_expected_fields_no_sector2_no_echelon_no_headquarters(self):

        # Table G-II (Appendix G's own amplifier table) lists neither
        # Field B (Echelon) nor Field S (Headquarters Staff Indicator);
        # G.5.3.1 step 3 explicitly says there are no sector 2 modifiers.
        layer = self._build()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "affiliation",
                "entity",
                "status",
                "sector1_modifier",
                "unique_designation",
                "rotation",
                "scale",
            ]
        )


    def test_entity_field_uses_a_plain_value_map(self):

        layer = self._build()

        idx = layer.fields().indexOf("entity")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )


    def _resolve_svg_path(self, layer, entity, sector1_modifier=""):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", entity)
        feature.setAttribute("status", "present")
        feature.setAttribute("sector1_modifier", sector1_modifier)

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

        path, ok = self._resolve_svg_path(layer, activities_layer.DEFAULT_ENTITY)

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_a_hierarchy_only_generic_entity_resolves(self):

        # "criminal_activity_incident" (110000) has no icon in milsymbol's
        # own source - frame-only, per Table G-III's own remarks column.
        layer = self._build()

        path, ok = self._resolve_svg_path(layer, "criminal_activity_incident")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_an_entity_with_a_sector1_modifier_resolves(self):

        layer = self._build()

        path, ok = self._resolve_svg_path(
            layer,
            "ied",
            sector1_modifier="hoax_decoy",
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


class TestAddActivitiesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_creates_and_adds_the_layer(self):

        layer = add_activities_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(edition_layer_name(OUTPUT_LAYER_NAME))

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        first = add_activities_layer(self.iface)

        result = add_activities_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(edition_layer_name(OUTPUT_LAYER_NAME))

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())

        self.assertEqual(
            len(self.iface.messageBar().calls),
            1
        )


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_activities_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], edition_layer_name(OUTPUT_LAYER_NAME))
