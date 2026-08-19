# -*- coding: utf-8 -*-

"""
Tests for military_symbology/air_layer.py - "Air"
(MIL-STD-2525D Appendix C), the second single-domain layer built on top
of military_symbology/_point_symbol_layer.py's shared factory (after
Space). Covers both of the appendix's sections (Air Equipment/Platform,
symbol set "01", and the single Air Missile entity, symbol set "02") in
one layer, via _point_symbol_layer.py's entity_symbol_set_overrides
mechanism.

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

from .qgis_test_case import FakeIface, QgisTestCase, edition_layer_name

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import air_layer
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES, MODIFIERS
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
)
from MilitaryCartographyTools.military_symbology.air_layer import (
    OUTPUT_LAYER_NAME,
    add_air_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    def test_entity_labels_cover_every_air_and_air_missile_entity(self):

        expected = set(ENTITIES["air"]) | set(ENTITIES["air_missile"])

        self.assertEqual(
            set(air_layer._ENTITY_LABELS),
            expected
        )


    def test_overrides_only_cover_entities_from_a_different_symbol_set(self):

        for entity in air_layer._ENTITY_SYMBOL_SET_OVERRIDES:

            self.assertIn(entity, ENTITIES["air_missile"])
            self.assertNotIn(entity, ENTITIES["air"])


    def test_sector_labels_are_the_union_of_air_and_air_missile_modifiers(self):

        for sector, layer_labels in (
            ("sector1", air_layer._SECTOR1_LABELS),
            ("sector2", air_layer._SECTOR2_LABELS),
        ):

            expected = (
                set(MODIFIERS["air"][sector])
                | set(MODIFIERS["air_missile"][sector])
            )

            self.assertEqual(set(layer_labels), expected, sector)


class TestBuildAirLayer(QgisTestCase):

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
            "air",
            air_layer._ENTITY_LABELS,
            air_layer.DEFAULT_ENTITY,
            entity_symbol_set_overrides=air_layer._ENTITY_SYMBOL_SET_OVERRIDES,
            include_echelon=False,
            include_headquarters=False,
            sector1_labels=air_layer._SECTOR1_LABELS,
            sector2_labels=air_layer._SECTOR2_LABELS,
        )


    def test_has_the_expected_fields_no_symbol_set_no_echelon_no_headquarters(self):

        # Table C-II (Appendix C's own amplifier table) lists neither
        # Field B (Echelon) nor Field S (Headquarters Staff Indicator)
        # for air symbols - same finding as Space's own Table B-II.
        # Sector 1/2 modifier fields ARE included (role/mission class,
        # missile class/range - added 2026-08-08).
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


    def test_entity_field_uses_a_plain_value_map_not_a_cascading_relation(self):

        layer = self._build()

        idx = layer.fields().indexOf("entity")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )


    def _resolve_svg_path(
        self,
        layer,
        entity,
        sector1_modifier="",
        sector2_modifier="",
    ):

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


    def test_an_air_equipment_entity_resolves_to_a_valid_symbol_path(self):

        layer = self._build()

        path, ok = self._resolve_svg_path(layer, "fighter")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_the_missile_entity_resolves_via_its_symbol_set_override(self):

        # "missile" belongs to symbol set "02" (air_missile), not this
        # layer's default "01".
        layer = self._build()

        path, ok = self._resolve_svg_path(layer, "missile")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_an_equipment_entity_with_a_sector1_modifier_resolves(self):

        layer = self._build()

        path, ok = self._resolve_svg_path(
            layer,
            "tanker",
            sector1_modifier="tanker",
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_the_missile_entity_with_its_own_sector1_modifier_resolves(self):

        # "anti_ballistic" is only valid under symbol_set "air_missile"
        # (02), which is exactly what the "missile" entity resolves to.
        layer = self._build()

        path, ok = self._resolve_svg_path(
            layer,
            "missile",
            sector1_modifier="anti_ballistic",
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_a_modifier_only_valid_for_the_other_merged_symbol_set_raises_in_build_sidc(self):

        # "anti_ballistic" is an air_missile-only sector1 key - see
        # test_space_layer.py's own version of this test for why the
        # real contract is checked at build_sidc() directly, not via a
        # rendered symbol path.
        from MilitaryCartographyTools.military_symbology.sidc import build_sidc

        with self.assertRaises(KeyError):

            build_sidc(
                affiliation="friend",
                entity="fighter",
                symbol_set="air",
                sector1_modifier="anti_ballistic",
            )


class TestAddAirLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_creates_and_adds_the_layer(self):

        layer = add_air_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(edition_layer_name(OUTPUT_LAYER_NAME))

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        first = add_air_layer(self.iface)

        result = add_air_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(edition_layer_name(OUTPUT_LAYER_NAME))

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

        add_air_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], edition_layer_name(OUTPUT_LAYER_NAME))
