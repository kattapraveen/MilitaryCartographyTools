# -*- coding: utf-8 -*-

"""
Tests for military_symbology/sea_surface_layer.py - "Sea Surface"
(MIL-STD-2525D Appendix E). Single-domain layer, no
missile-family companion to merge in (unlike Space/Air) - Table A-III
has no separate "Sea Surface Missile" symbol set.

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
from MilitaryCartographyTools.military_symbology import sea_surface_layer
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES, MODIFIERS
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
)
from MilitaryCartographyTools.military_symbology.sea_surface_layer import (
    OUTPUT_LAYER_NAME,
    add_sea_surface_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    def test_entity_labels_cover_every_sea_surface_entity(self):

        self.assertEqual(
            set(sea_surface_layer._ENTITY_LABELS),
            set(ENTITIES["sea_surface"])
        )


    def test_sector_labels_cover_every_sea_surface_modifier(self):

        self.assertEqual(
            set(sea_surface_layer._SECTOR1_LABELS),
            set(MODIFIERS["sea_surface"]["sector1"])
        )
        self.assertEqual(
            set(sea_surface_layer._SECTOR2_LABELS),
            set(MODIFIERS["sea_surface"]["sector2"])
        )


class TestBuildSeaSurfaceLayer(QgisTestCase):

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
            "sea_surface",
            sea_surface_layer._ENTITY_LABELS,
            sea_surface_layer.DEFAULT_ENTITY,
            include_echelon=False,
            include_headquarters=False,
            sector1_labels=sea_surface_layer._SECTOR1_LABELS,
            sector2_labels=sea_surface_layer._SECTOR2_LABELS,
        )


    def test_has_the_expected_fields_no_symbol_set_no_echelon_no_headquarters(self):

        # Table E-II (Appendix E's own amplifier table) lists neither
        # Field B (Echelon) nor Field S (Headquarters Staff Indicator).
        layer = self._build()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "affiliation",
                "entity",
                "status",
                "sector1_modifier",
                "sector2_modifier",
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


    def _resolve_svg_path(self, layer, entity, sector1_modifier="", sector2_modifier=""):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", entity)
        feature.setAttribute("status", "present")
        feature.setAttribute("sector1_modifier", sector1_modifier)
        feature.setAttribute("sector2_modifier", sector2_modifier)

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

        path, ok = self._resolve_svg_path(layer, "frigate")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_own_ship_and_fused_track_resolve(self):

        # Table E-VI/E-VII's own special entries - own_ship and
        # fused_track - included in the full vocabulary this session.
        layer = self._build()

        for entity in ("own_ship", "fused_track"):

            with self.subTest(entity=entity):

                path, ok = self._resolve_svg_path(layer, entity)

                self.assertTrue(ok)
                self.assertTrue(path.startswith("base64:"))


    def test_an_entity_with_sector_modifiers_resolves(self):

        layer = self._build()

        path, ok = self._resolve_svg_path(
            layer,
            "destroyer",
            sector1_modifier="antiair_warfare",
            sector2_modifier="nuclear_powered",
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


class TestAddSeaSurfaceLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_creates_and_adds_the_layer(self):

        layer = add_sea_surface_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(edition_layer_name(OUTPUT_LAYER_NAME))

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        first = add_sea_surface_layer(self.iface)

        result = add_sea_surface_layer(self.iface)

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

        add_sea_surface_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], edition_layer_name(OUTPUT_LAYER_NAME))
