# -*- coding: utf-8 -*-

"""
Tests for military_symbology/unit_layer.py - the "Tactical Graphics -
Units" point layer: fields, attribute form, and the renderer that
computes each feature's own MIL-STD-2525/APP-6 symbol live from its own
attributes.

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
)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import unit_layer
from MilitaryCartographyTools.military_symbology.sidc import (
    AFFILIATIONS,
    ECHELONS,
    ENTITIES,
    STATUS,
)
from MilitaryCartographyTools.military_symbology.unit_layer import (
    OUTPUT_LAYER_NAME,
    add_unit_layer,
    create_unit_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    """
    Regression guard: unit_layer.py's own display-label dicts are kept
    separate from sidc.py's vocabulary (presentation vs. data model,
    see unit_layer.py's own comment on this), which means they could
    silently drift apart - a new entity added to sidc.py without a
    matching label here would just be missing from the dropdown, not a
    crash. Asserting the key sets match exactly turns that into a
    loud test failure instead.
    """

    def test_affiliation_labels_cover_every_sidc_affiliation(self):

        self.assertEqual(
            set(unit_layer._AFFILIATION_LABELS),
            set(AFFILIATIONS)
        )


    def test_entity_labels_cover_every_ground_unit_entity(self):

        self.assertEqual(
            set(unit_layer._ENTITY_LABELS),
            set(ENTITIES[unit_layer.DEFAULT_SYMBOL_SET])
        )


    def test_echelon_labels_cover_every_sidc_echelon(self):

        self.assertEqual(
            set(unit_layer._ECHELON_LABELS),
            set(ECHELONS)
        )


    def test_status_labels_cover_every_sidc_status(self):

        self.assertEqual(
            set(unit_layer._STATUS_LABELS),
            set(STATUS)
        )


class TestCreateUnitLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_has_the_expected_fields(self):

        layer = create_unit_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "affiliation",
                "entity",
                "echelon",
                "status",
                "headquarters",
                "unique_designation",
            ]
        )


    def test_uses_the_projects_own_crs(self):

        layer = create_unit_layer()

        self.assertEqual(layer.crs().authid(), WGS84.authid())


    def test_dropdown_fields_use_value_map_widgets(self):

        layer = create_unit_layer()

        for field_name in ("affiliation", "entity", "echelon", "status"):

            idx = layer.fields().indexOf(field_name)

            self.assertEqual(
                layer.editorWidgetSetup(idx).type(),
                "ValueMap"
            )


    def test_headquarters_uses_a_checkbox_widget(self):

        layer = create_unit_layer()

        idx = layer.fields().indexOf("headquarters")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "CheckBox"
        )


    def test_renderers_svg_layer_has_a_data_defined_name(self):

        layer = create_unit_layer()

        symbol = layer.renderer().symbol()
        svg_layer = symbol.symbolLayer(0)

        self.assertTrue(
            svg_layer.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.Name
            )
        )


    def test_a_real_feature_resolves_to_a_valid_symbol_path(self):

        # Integration-level: not just checking the expression string is
        # set, but that a real feature run through the actual renderer
        # resolves to a valid base64: SVG path - confirmed live during
        # design that QGIS's own data-defined property evaluation,
        # mct_build_sidc(), and mct_sidc_svg() all connect correctly.
        layer = create_unit_layer()

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature.setAttribute("affiliation", "hostile")
        feature.setAttribute("entity", "armor")
        feature.setAttribute("echelon", "battalion")
        feature.setAttribute("status", "present")
        feature.setAttribute("headquarters", False)

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


class TestAddUnitLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_creates_and_adds_the_layer(self):

        layer = add_unit_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        # The critical safety property this feature needs, unlike every
        # other generate_*() in this plugin: a second click must NEVER
        # remove/replace an existing layer, since its content is
        # hand-placed operational data, not something safe to recreate.
        first = add_unit_layer(self.iface)

        result = add_unit_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)

        self.assertEqual(matching[0].id(), first.id())

        self.assertEqual(
            len(self.iface.messageBar().calls),
            1
        )


    def test_default_insert_position_lands_at_top_of_tree(self):

        from qgis.core import QgsVectorLayer

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_unit_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], OUTPUT_LAYER_NAME)
