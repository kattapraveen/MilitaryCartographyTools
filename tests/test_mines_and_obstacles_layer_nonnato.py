# -*- coding: utf-8 -*-

"""
Tests for military_symbology/mines_and_obstacles_layer_nonnato.py -
the "Mines and Obstacles (Non-NATO)" layer, new 2026-09-03: the mine
family moved here from Land Equipment (Non-NATO), and Booby Trap moved
here from Control Measure Points (Non-NATO) - see that module's own
docstring for the full "let's move all the mines to a different layer
- say mines and obstacles; shift booby trap also into this new layer"
request.

Military Cartography Tools
"""

import base64

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
from MilitaryCartographyTools.military_symbology.mines_and_obstacles_layer_nonnato import (
    BRIDGE_ENTITIES,
    BOOBY_TRAP_ENTITY,
    LAYER_NAME,
    ENTITY_LABELS,
    add_mines_and_obstacles_layer_nonnato,
    build_mines_and_obstacles_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY,
    BAR_MINE_ENTITY,
    DIRECTIONAL_MINE_ENTITY,
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
    DIRECTIONAL_MINE_ENTITY,
})

REAL_MINE_ENTITIES = frozenset({
    "land_mine", "antitank_mine", "antipersonnel_land_mine",
})


class TestEntityLabelsMatchTheReviewedList(QgisTestCase):

    def test_every_real_mine_key_is_a_valid_app6e_land_equipment_entity(self):

        real_keys = entities_for_edition("2525E")["land_equipment"]

        for key in REAL_MINE_ENTITIES:

            with self.subTest(entity=key):

                self.assertIn(key, real_keys)


    def test_booby_trap_is_a_valid_app6e_control_measure_entity(self):

        real_keys = entities_for_edition("2525E")["control_measure"]

        self.assertIn(BOOBY_TRAP_ENTITY, real_keys)


    def test_count_matches_the_reviewed_list(self):

        # 3 real mine entities + 6 synthetic mine icons (moved from
        # Land Equipment) + Booby Trap (moved from Control Measure
        # Points) - see this module's own docstring.
        self.assertEqual(len(ENTITY_LABELS), 16)

        for entity in SYNTHETIC_ENTITIES | REAL_MINE_ENTITIES:
            self.assertIn(entity, ENTITY_LABELS)

        self.assertIn(BOOBY_TRAP_ENTITY, ENTITY_LABELS)


class TestBuildMinesAndObstaclesLayerNonnato(QgisTestCase):

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

        layer = build_mines_and_obstacles_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                # "affiliation" arrived 2026-09-09 with the bridges.
                "affiliation",
                "entity",
                # "mine_type" arrived 2026-09-09 with Gap/Safe Lane and
                # Minefield.
                "mine_type",
                "unique_designation", "rotation", "scale",
            ]
        )


    def test_no_echelon_status_or_combined_arms_field(self):

        # This layer had no "affiliation" field either until 2026-09-09,
        # when the bridge family arrived - the first thing here whose
        # colour is not fixed. Echelon, status and Combined Arms remain
        # meaningless for everything on it.
        layer = build_mines_and_obstacles_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        for absent in ("echelon", "status", "combined_arms"):
            self.assertNotIn(absent, field_names)


    def test_only_the_bridges_read_the_affiliation_field(self):

        # Every other entity overrides it internally - the mine family
        # to MINE_GREEN, Booby Trap to its own green - so the field is
        # inert for them rather than absent.
        from MilitaryCartographyTools.military_symbology import (
            nonnato_symbol_engine as nse,
        )

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                if entity in BRIDGE_ENTITIES:

                    friend = nse.render_nonnato_equipment_svg("friend", entity)
                    hostile = nse.render_nonnato_equipment_svg("hostile", entity)

                    self.assertNotEqual(friend, hostile)
                    self.assertIn(
                        nse.AFFILIATION_COLOURS["hostile"], hostile
                    )

                elif entity != BOOBY_TRAP_ENTITY:

                    self.assertEqual(
                        nse.render_nonnato_equipment_svg("friend", entity),
                        nse.render_nonnato_equipment_svg("hostile", entity),
                    )


    def test_every_entity_renders_a_valid_symbol_path(self):

        layer = build_mines_and_obstacles_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                path = self._render_path_for(layer, {"entity": entity})

                self.assertTrue(path.startswith("base64:"))


    def test_every_mine_entity_renders_green(self):

        layer = build_mines_and_obstacles_layer_nonnato()

        for entity in SYNTHETIC_ENTITIES | REAL_MINE_ENTITIES:

            with self.subTest(entity=entity):

                svg = self._decoded_svg_for(layer, {"entity": entity})

                self.assertIn(MINE_GREEN, svg)


    def test_booby_trap_uses_the_custom_green_icon(self):

        layer = build_mines_and_obstacles_layer_nonnato()

        svg = self._decoded_svg_for(layer, {"entity": BOOBY_TRAP_ENTITY})

        # Green, and NOT a milsymbol-rendered ellipse-plus-triangle (no
        # monoColor use here at all, since booby_trap_control_measure_
        # svg() takes no affiliation).
        self.assertIn(MINE_GREEN, svg)
        self.assertEqual(svg.count("<circle"), 1)


    def test_designation_reaches_a_mine_entity(self):

        layer = build_mines_and_obstacles_layer_nonnato()

        svg = self._decoded_svg_for(
            layer,
            {"entity": "antitank_mine", "unique_designation": "a1"},
        )

        self.assertIn("A1", svg)


    def test_booby_trap_never_carries_a_designation(self):

        layer = build_mines_and_obstacles_layer_nonnato()

        without = self._decoded_svg_for(
            layer, {"entity": BOOBY_TRAP_ENTITY, "unique_designation": ""}
        )
        with_designation = self._decoded_svg_for(
            layer,
            {"entity": BOOBY_TRAP_ENTITY, "unique_designation": "HQ 3"},
        )

        self.assertEqual(without, with_designation)


    def test_a_typed_designation_does_not_shrink_a_mine_icon(self):

        layer = build_mines_and_obstacles_layer_nonnato()

        without_designation = self._render_size_for(
            layer, {"entity": "antitank_mine", "unique_designation": ""}
        )
        with_designation = self._render_size_for(
            layer,
            {"entity": "antitank_mine", "unique_designation": "HQ 3"},
        )

        self.assertAlmostEqual(without_designation, with_designation, places=3)


    def test_booby_trap_size_is_stable(self):

        layer = build_mines_and_obstacles_layer_nonnato()

        without_designation = self._render_size_for(
            layer, {"entity": BOOBY_TRAP_ENTITY, "unique_designation": ""}
        )
        with_designation = self._render_size_for(
            layer,
            {"entity": BOOBY_TRAP_ENTITY, "unique_designation": "HQ 3"},
        )

        self.assertAlmostEqual(without_designation, with_designation, places=3)


    def test_entity_keys_match_a_real_sidc_where_one_exists(self):

        for entity in REAL_MINE_ENTITIES:

            with self.subTest(entity=entity):

                build_sidc(
                    affiliation="friend", entity=entity,
                    symbol_set="land_equipment", edition="2525E",
                )

        build_sidc(
            affiliation="friend", entity=BOOBY_TRAP_ENTITY,
            symbol_set="control_measure", edition="2525E",
        )


class TestAddMinesAndObstaclesLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_adds_a_layer_named_mines_and_obstacles_nonnato(self):

        layer = add_mines_and_obstacles_layer_nonnato(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), layer.id())


    def test_guards_against_a_duplicate(self):

        first = add_mines_and_obstacles_layer_nonnato(self.iface)

        result = add_mines_and_obstacles_layer_nonnato(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
