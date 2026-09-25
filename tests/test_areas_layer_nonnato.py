# -*- coding: utf-8 -*-

"""
Tests for military_symbology/areas_layer_nonnato.py - the "Areas
(Non-NATO)" layer, the branch's only POLYGON layer and, with the
minefield line layer, one of only two whose symbols are built from
QGIS primitives rather than from an SVG.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsLinePatternFillSymbolLayer,
    QgsProject,
    QgsRuleBasedRenderer,
    QgsSimpleLineSymbolLayer,
    QgsWkbTypes,
)

from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.military_symbology.areas_layer_nonnato import (
    AREA_COLOUR,
    BOGGY_TERRAIN_ENTITY,
    DEFAULT_ENTITY,
    ENTITY_LABELS,
    KEY_TERRAIN_FEATURE_ENTITY,
    LAYER_NAME,
    RESTRICTED_TERRAIN_ENTITY,
    SEVERELY_RESTRICTED_TERRAIN_ENTITY,
    _BACKSLASH_ANGLE,
    _HORIZONTAL_ANGLE,
    _VERTICAL_ANGLE,
    add_areas_layer_nonnato,
    build_areas_layer_nonnato,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestBuildAreasLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.layers = []


    def symbol_for(self, entity):

        """The one rule's symbol whose filter matches `entity`."""

        # Kept, not just held: letting a layer fall out of scope takes
        # its renderer's C++ object - and every symbol layer already
        # handed out from it - with it, mid-test. A test that asks
        # about two entities needs BOTH layers still alive.
        layer = build_areas_layer_nonnato()

        self.layers.append(layer)

        for rule in layer.renderer().rootRule().children():

            if f"'{entity}'" in rule.filterExpression():
                return rule.symbol()

        self.fail(f"no rule for {entity}")


    def hatches(self, entity):

        symbol = self.symbol_for(entity)

        return [
            symbol.symbolLayer(index)
            for index in range(symbol.symbolLayerCount())
            if isinstance(
                symbol.symbolLayer(index), QgsLinePatternFillSymbolLayer
            )
        ]


    def test_it_is_a_polygon_layer(self):

        # The whole reason it is a layer of its own: a QGIS vector
        # layer carries one geometry type, and no other non-NATO layer
        # is polygons.
        layer = build_areas_layer_nonnato()

        self.assertTrue(layer.isValid())
        self.assertEqual(
            layer.geometryType(), QgsWkbTypes.GeometryType.PolygonGeometry
        )
        self.assertEqual(layer.name(), LAYER_NAME)


    def test_the_only_field_is_the_entity(self):

        # Terrain is terrain whoever holds it: no affiliation, and no
        # status either - the boundary is always solid.
        self.assertEqual(
            [field.name() for field in build_areas_layer_nonnato().fields()],
            ["entity"],
        )


    def test_the_four_entities(self):

        self.assertEqual(
            list(ENTITY_LABELS.values()),
            [
                "Key Terrain Feature",
                "Boggy Terrain",
                "Restricted Terrain",
                "Severely Restricted Terrain",
            ],
        )

        self.assertIn(DEFAULT_ENTITY, ENTITY_LABELS)


    def test_the_entity_dropdown_offers_all_four(self):

        layer = build_areas_layer_nonnato()

        setup = layer.editorWidgetSetup(layer.fields().indexOf("entity"))

        self.assertEqual(setup.type(), "ValueMap")
        self.assertEqual(
            sorted(setup.config()["map"]), sorted(ENTITY_LABELS.values())
        )


    def test_one_rule_per_entity(self):

        layer = build_areas_layer_nonnato()

        self.assertIsInstance(layer.renderer(), QgsRuleBasedRenderer)
        self.assertEqual(
            len(layer.renderer().rootRule().children()), len(ENTITY_LABELS)
        )


    def test_every_entity_has_a_solid_black_boundary(self):

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                boundary = self.symbol_for(entity).symbolLayer(0)

                self.assertIsInstance(boundary, QgsSimpleLineSymbolLayer)
                self.assertEqual(boundary.color(), QColor(AREA_COLOUR))

                # No status field on this layer, so nothing can ever
                # dash it.
                self.assertFalse(
                    boundary.dataDefinedProperties().hasActiveProperties()
                )


    def test_key_terrain_feature_slants_like_a_backslash(self):

        hatches = self.hatches(KEY_TERRAIN_FEATURE_ENTITY)

        self.assertEqual(len(hatches), 1)

        # 45, not 135: the angle is measured clockwise, so the other
        # value mirrors the hatch. See the constant's own comment.
        self.assertEqual(hatches[0].lineAngle(), _BACKSLASH_ANGLE)
        self.assertEqual(_BACKSLASH_ANGLE, 45)


    def test_boggy_terrain_is_horizontal_and_broken(self):

        hatches = self.hatches(BOGGY_TERRAIN_ENTITY)

        self.assertEqual(len(hatches), 1)
        self.assertEqual(hatches[0].lineAngle(), _HORIZONTAL_ANGLE)

        line = hatches[0].subSymbol().symbolLayer(0)

        self.assertTrue(line.useCustomDashPattern())
        self.assertTrue(len(line.customDashVector()) >= 2)


    def test_restricted_terrain_is_horizontal_and_unbroken(self):

        hatches = self.hatches(RESTRICTED_TERRAIN_ENTITY)

        self.assertEqual(len(hatches), 1)
        self.assertEqual(hatches[0].lineAngle(), _HORIZONTAL_ANGLE)
        self.assertFalse(
            hatches[0].subSymbol().symbolLayer(0).useCustomDashPattern()
        )


    def test_severely_restricted_terrain_crosses_two_runs(self):

        hatches = self.hatches(SEVERELY_RESTRICTED_TERRAIN_ENTITY)

        self.assertEqual(len(hatches), 2)
        self.assertEqual(
            sorted(hatch.lineAngle() for hatch in hatches),
            [_HORIZONTAL_ANGLE, _VERTICAL_ANGLE],
        )

        # Restricted Terrain's own hatch, plus one crossing it, so the
        # two read as a progression.
        restricted = self.hatches(RESTRICTED_TERRAIN_ENTITY)[0]

        self.assertEqual(hatches[0].distance(), restricted.distance())


    def test_every_hatch_paints_through_its_own_sub_symbol(self):

        # A QgsLinePatternFillSymbolLayer paints through a SUB-symbol,
        # so a colour set only on the fill layer itself never reaches
        # the map - the trap that left every Weapons Free Zone hatched
        # black in 2026-08-12.
        for entity in ENTITY_LABELS:

            for hatch in self.hatches(entity):

                with self.subTest(entity=entity, angle=hatch.lineAngle()):

                    self.assertEqual(
                        hatch.subSymbol().symbolLayer(0).color(),
                        QColor(AREA_COLOUR),
                    )


class TestAddAreasLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)
        QgsProject.instance().removeAllMapLayers()


    def test_it_adds_the_layer_once(self):

        iface = FakeIface()

        first = add_areas_layer_nonnato(iface)
        second = add_areas_layer_nonnato(iface)

        # The second click warns and adds nothing - a hand-drawn layer
        # is never silently replaced.
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(
            len(
                [
                    layer
                    for layer in QgsProject.instance().mapLayers().values()
                    if layer.name() == LAYER_NAME
                ]
            ),
            1,
        )
