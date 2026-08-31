# -*- coding: utf-8 -*-

"""
Tests for military_symbology/control_measure_points_layer_nonnato.py -
the "Control Measure Points (Non-NATO)" layer. Unlike Land Unit/Land
Equipment/SIGINT, ten of its eleven entities render through the plain
existing mct_sidc_svg()/mct_build_sidc() pipeline (no non-NATO-specific
colour treatment - see the rules record's Part C); only Booby Trap gets
a custom icon.

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

from MilitaryCartographyTools.expressions import (
    military_symbology_functions,
    nonnato_symbology_functions,
)
from MilitaryCartographyTools.military_symbology.control_measure_points_layer_nonnato import (
    BOOBY_TRAP_ENTITY,
    LAYER_NAME,
    ENTITY_LABELS,
    add_control_measure_points_layer_nonnato,
    build_control_measure_points_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    build_sidc,
    entities_for_edition,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestEntityLabelsMatchTheReviewedList(QgisTestCase):

    def test_every_key_is_a_valid_app6e_control_measure_entity(self):

        real_keys = entities_for_edition("2525E")["control_measure"]

        for key in ENTITY_LABELS:

            with self.subTest(entity=key):

                self.assertIn(key, real_keys)


    def test_count_matches_the_reviewed_list(self):

        # 11 of 241 - see the rules record's "Control Measure Points"
        # section.
        self.assertEqual(len(ENTITY_LABELS), 11)


    def test_the_three_renames_are_in_place(self):

        self.assertEqual(ENTITY_LABELS["target_reference_point"], "Target")
        self.assertEqual(ENTITY_LABELS["shelter"], "Pill Box")
        self.assertEqual(
            ENTITY_LABELS["observation_post_forward_observer"],
            "Artillery Observation Post",
        )


class TestBuildControlMeasurePointsLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()
        nonnato_symbology_functions.register()


    def tearDown(self):

        nonnato_symbology_functions.unregister()
        military_symbology_functions.unregister()

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


    def test_every_field_exists_with_the_right_type(self):

        layer = build_control_measure_points_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["affiliation", "entity", "status", "unique_designation",
             "rotation", "scale"]
        )


    def test_no_echelon_or_headquarters_field(self):

        layer = build_control_measure_points_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        for absent in ("echelon", "headquarters", "combined_arms"):
            self.assertNotIn(absent, field_names)


    def test_every_entity_renders_a_valid_symbol_path(self):

        layer = build_control_measure_points_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                path = self._render_path_for(
                    layer,
                    {
                        "affiliation": "friend", "entity": entity,
                        "status": "present",
                    }
                )

                self.assertTrue(path.startswith("base64:"))


    def test_booby_trap_uses_the_custom_green_icon(self):

        layer = build_control_measure_points_layer_nonnato()

        svg = self._decoded_svg_for(
            layer,
            {
                "affiliation": "hostile", "entity": BOOBY_TRAP_ENTITY,
                "status": "present",
            }
        )

        # Green regardless of affiliation, and NOT a milsymbol-rendered
        # ellipse-plus-triangle (no monoColor use here at all, since
        # booby_trap_control_measure_svg() takes no affiliation).
        self.assertIn("#009b00", svg)
        self.assertEqual(svg.count("<circle"), 1)


    def test_every_other_entity_uses_the_real_nato_affiliation_colours(self):

        layer = build_control_measure_points_layer_nonnato()

        # NATO's own four-colour scheme (H.5.3), NOT the six-colour
        # non-NATO palette - Part C's own settled "no non-NATO-specific
        # treatment" rule.
        for affiliation in ("friend", "hostile"):

            with self.subTest(affiliation=affiliation):

                svg = self._decoded_svg_for(
                    layer,
                    {
                        "affiliation": affiliation, "entity": "decision_point",
                        "status": "present",
                    },
                )

                self.assertTrue(svg.startswith("<svg"))


    def test_designation_reaches_a_plain_milsymbol_entity(self):

        layer = build_control_measure_points_layer_nonnato()

        svg = self._decoded_svg_for(
            layer,
            {
                "affiliation": "friend", "entity": "target_reference_point",
                "status": "present", "unique_designation": "a1",
            },
        )

        self.assertIn("A1", svg)


    def test_entity_keys_match_a_real_control_measure_sidc(self):

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                build_sidc(
                    affiliation="friend", entity=entity,
                    symbol_set="control_measure", edition="2525E",
                )


class TestAddControlMeasurePointsLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()
        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()
        military_symbology_functions.unregister()

        super().tearDown()


    def test_adds_a_layer_named_control_measure_points_nonnato(self):

        layer = add_control_measure_points_layer_nonnato(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), layer.id())


    def test_guards_against_a_duplicate(self):

        first = add_control_measure_points_layer_nonnato(self.iface)

        result = add_control_measure_points_layer_nonnato(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
