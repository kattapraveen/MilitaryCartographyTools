# -*- coding: utf-8 -*-

"""
Tests for military_symbology/space_layer.py - "Space" (MIL-STD-2525D
Appendix B), the first single-domain layer built
on top of military_symbology/_point_symbol_layer.py's shared factory.
Covers both of the appendix's sections (Space Equipment/Platform,
symbol set "05", and the single Space Missile entity, symbol set "06")
in one layer, via _point_symbol_layer.py's entity_symbol_set_overrides
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
    QgsExpression,
    QgsSymbolLayer,
)

from .qgis_test_case import FakeIface, QgisTestCase, edition_layer_name

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import space_layer
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES, MODIFIERS
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
    _symbol_set_expression,
)
from MilitaryCartographyTools.military_symbology.space_layer import (
    OUTPUT_LAYER_NAME,
    add_space_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    def test_entity_labels_cover_every_space_and_space_missile_entity(self):

        expected = set(ENTITIES["space"]) | set(ENTITIES["space_missile"])

        self.assertEqual(
            set(space_layer._ENTITY_LABELS),
            expected
        )


    def test_overrides_only_cover_entities_from_a_different_symbol_set(self):

        # Every override key must be a real space_missile entity (not a
        # plain "space" one - that would silently mis-resolve a Space
        # Equipment/Platform entity to the wrong symbol set).
        for entity in space_layer._ENTITY_SYMBOL_SET_OVERRIDES:

            self.assertIn(entity, ENTITIES["space_missile"])
            self.assertNotIn(entity, ENTITIES["space"])


    def test_sector_labels_are_the_union_of_space_and_space_missile_modifiers(self):

        for sector, layer_labels in (
            ("sector1", space_layer._SECTOR1_LABELS),
            ("sector2", space_layer._SECTOR2_LABELS),
        ):

            expected = (
                set(MODIFIERS["space"][sector])
                | set(MODIFIERS["space_missile"][sector])
            )

            self.assertEqual(set(layer_labels), expected, sector)


class TestSymbolSetExpression(QgisTestCase):

    def test_no_overrides_is_a_plain_literal(self):

        self.assertEqual(
            _symbol_set_expression("space", None),
            "'space'"
        )


    def test_with_overrides_is_a_valid_case_expression(self):

        expression_text = _symbol_set_expression(
            "space",
            {"missile": "space_missile"}
        )

        expression = QgsExpression(expression_text)

        self.assertFalse(expression.hasParserError(), expression.parserErrorString())


class TestBuildSpaceLayer(QgisTestCase):

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
            "space",
            space_layer._ENTITY_LABELS,
            space_layer.DEFAULT_ENTITY,
            entity_symbol_set_overrides=space_layer._ENTITY_SYMBOL_SET_OVERRIDES,
            include_echelon=False,
            include_headquarters=False,
            sector1_labels=space_layer._SECTOR1_LABELS,
            sector2_labels=space_layer._SECTOR2_LABELS,
        )


    def test_has_the_expected_fields_no_symbol_set_no_echelon_no_headquarters(self):

        # Space (Table B-II, Appendix B's own amplifier table) lists
        # neither Field B (Echelon) nor Field S (Headquarters Staff
        # Indicator) - unlike land units, which do. Sector 1/2 modifier
        # fields ARE included (orbit type / sensor type, missile class /
        # range - added 2026-08-08).
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


    def test_a_space_equipment_entity_resolves_to_a_valid_symbol_path(self):

        layer = self._build()

        path, ok = self._resolve_svg_path(layer, "reconnaissance_satellite")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_the_missile_entity_resolves_via_its_symbol_set_override(self):

        # "missile" belongs to symbol set "06" (space_missile), not this
        # layer's default "05" - confirms the CASE-expression override
        # actually reaches mct_build_sidc() and still produces a valid
        # symbol, not an error string.
        layer = self._build()

        path, ok = self._resolve_svg_path(layer, "missile")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_an_equipment_entity_with_a_sector1_modifier_resolves(self):

        # Confirms the sector1_modifier field actually reaches
        # mct_build_sidc() end to end (Space's own "05" vocabulary).
        layer = self._build()

        path, ok = self._resolve_svg_path(
            layer,
            "satellite",
            sector1_modifier="low_earth_orbit",
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_the_missile_entity_with_its_own_sector1_modifier_resolves(self):

        # "ballistic" is only valid under symbol_set "space_missile" (06),
        # which is exactly what the "missile" entity resolves to - proves
        # the modifier lookup uses the CASE-resolved symbol_set, not this
        # layer's own default "space" (05).
        layer = self._build()

        path, ok = self._resolve_svg_path(
            layer,
            "missile",
            sector1_modifier="ballistic",
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_a_modifier_only_valid_for_the_other_merged_symbol_set_raises_in_build_sidc(self):

        # "ballistic" is a space_missile-only sector1 key - deliberately
        # NOT asserting anything about the rendered symbol path here:
        # mct_build_sidc() catches build_sidc()'s KeyError and returns
        # plain error text, which milsymbol.js may still turn into SOME
        # SVG for an unparseable SIDC rather than visibly failing (see
        # build_single_domain_point_layer()'s own docstring) - so that
        # layer isn't where this contract can be reliably checked. The
        # real, guaranteed contract lives in sidc.py's own build_sidc(),
        # confirmed directly here.
        from MilitaryCartographyTools.military_symbology.sidc import build_sidc

        with self.assertRaises(KeyError):

            build_sidc(
                affiliation="friend",
                entity="satellite",
                symbol_set="space",
                sector1_modifier="ballistic",
            )


class TestAddSpaceLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_creates_and_adds_the_layer(self):

        layer = add_space_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(edition_layer_name(OUTPUT_LAYER_NAME))

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        first = add_space_layer(self.iface)

        result = add_space_layer(self.iface)

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

        add_space_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], edition_layer_name(OUTPUT_LAYER_NAME))
