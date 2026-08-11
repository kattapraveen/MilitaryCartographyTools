# -*- coding: utf-8 -*-

"""
Tests for military_symbology/target_control_measures.py - the Target
Control Measures line/area layers (Table H-XVII, Mini-Phase H12),
styled via a QgsRuleBasedRenderer keyed on "measure_type". See that
module's own docstring for what's already covered by the pre-existing
point vocabulary and for what's skipped (Rectangular Target - Single
Target, AEGIS only).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsMarkerLineSymbolLayer,
    QgsProject,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.target_control_measures import (
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    add_target_control_measures_areas_layer,
    add_target_control_measures_lines_layer,
    create_target_control_measures_areas_layer,
    create_target_control_measures_lines_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


def _rule_symbol_for(layer, measure_type):

    root = layer.renderer().rootRule()

    rule = next(
        rule for rule in root.children()
        if rule.filterExpression() == f'"measure_type" = \'{measure_type}\''
    )

    return rule.symbol()


def _resolve_stroke_color(symbol_layer, layer, affiliation):

    feature = QgsFeature(layer.fields())
    feature.setAttribute("affiliation", affiliation)

    context = layer.createExpressionContext()
    context.setFeature(feature)

    color, ok = symbol_layer.dataDefinedProperties().valueAsColor(
        QgsSymbolLayer.Property.StrokeColor,
        context,
        QColor(1, 2, 3)
    )

    return color, ok


class TestCreateTargetControlMeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _evaluate_label(self, layer, measure_type, **attrs):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)

        for key, value in attrs.items():

            feature.setAttribute(key, value)

        settings = layer.labeling().settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def test_has_the_expected_fields(self):

        layer = create_target_control_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "length_km",
            ]
        )


    def test_is_a_line_layer(self):

        layer = create_target_control_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_target_control_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in LINE_MEASURE_TYPE_LABELS
            }
        )


    def test_every_line_type_has_end_ticks(self):

        layer = create_target_control_measures_lines_layer()

        for measure_type in LINE_MEASURE_TYPE_LABELS:

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 3)

                for i in (1, 2):

                    self.assertIsInstance(
                        symbol.symbolLayer(i),
                        QgsMarkerLineSymbolLayer
                    )


    def test_linear_target_label_is_the_bare_designation(self):

        layer = create_target_control_measures_lines_layer()

        self.assertEqual(
            self._evaluate_label(
                layer, "linear_target", unique_designation="la2961"
            ),
            "LA2961"
        )

        self.assertEqual(
            self._evaluate_label(layer, "linear_target"),
            ""
        )


    def test_linear_smoke_target_label_appends_smoke(self):

        layer = create_target_control_measures_lines_layer()

        self.assertEqual(
            self._evaluate_label(
                layer, "linear_smoke_target", unique_designation="vb1910"
            ),
            "VB1910\nSMOKE"
        )

        self.assertEqual(
            self._evaluate_label(layer, "linear_smoke_target"),
            "SMOKE"
        )


    def test_final_protective_fire_label_is_fixed(self):

        layer = create_target_control_measures_lines_layer()

        self.assertEqual(
            self._evaluate_label(layer, "final_protective_fire"),
            "FPF"
        )


    def test_lines_follow_the_shared_status_field(self):

        layer = create_target_control_measures_lines_layer()

        for measure_type in LINE_MEASURE_TYPE_LABELS:

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)
                base_line = symbol.symbolLayer(0)

                self.assertTrue(
                    base_line.dataDefinedProperties().hasProperty(
                        QgsSymbolLayer.Property.StrokeStyle
                    )
                )


    def test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_target_control_measures_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        symbol = _rule_symbol_for(layer, "linear_target")
        stroke_layer = symbol.symbolLayer(0)

        for affiliation, hex_color in expected.items():

            with self.subTest(affiliation=affiliation):

                color, ok = _resolve_stroke_color(stroke_layer, layer, affiliation)

                self.assertTrue(ok)
                self.assertEqual(color.name(), hex_color)


    def test_length_km_default_value_recalculates_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_target_control_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            self.assertTrue(
                layer.defaultValueDefinition(idx).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateTargetControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _evaluate_label(self, layer, measure_type, **attrs):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)

        for key, value in attrs.items():

            feature.setAttribute(key, value)

        settings = layer.labeling().settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def test_has_the_expected_fields(self):

        layer = create_target_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_target_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_target_control_measures_areas_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in AREA_MEASURE_TYPE_LABELS
            }
        )


    def test_area_target_and_series_labels_are_bare_designations(self):

        layer = create_target_control_measures_areas_layer()

        for measure_type in ("area_target", "series_or_group_of_targets"):

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, unique_designation="pc9008"
                    ),
                    "PC9008"
                )


    def test_smoke_label_appends_smoke(self):

        layer = create_target_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_label(
                layer, "smoke", unique_designation="dt4877"
            ),
            "DT4877\nSMOKE"
        )

        self.assertEqual(
            self._evaluate_label(layer, "smoke"),
            "SMOKE"
        )


    def test_bomb_area_label_is_fixed(self):

        layer = create_target_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_label(layer, "bomb_area"),
            "BOMB"
        )


    def test_fire_support_area_label_prefixes_fsa(self):

        layer = create_target_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_label(
                layer, "fire_support_area", unique_designation="green"
            ),
            "FSA GREEN"
        )

        self.assertEqual(
            self._evaluate_label(layer, "fire_support_area"),
            "FSA"
        )


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_target_control_measures_areas_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            symbol = _rule_symbol_for(layer, measure_type)
            outline_layer = symbol.symbolLayer(0)

            for affiliation, hex_color in expected.items():

                with self.subTest(measure_type=measure_type, affiliation=affiliation):

                    color, ok = _resolve_stroke_color(outline_layer, layer, affiliation)

                    self.assertTrue(ok)
                    self.assertEqual(color.name(), hex_color)


    def test_area_and_perimeter_default_values_recalculate_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_target_control_measures_areas_layer()

            self.assertTrue(
                layer.defaultValueDefinition(
                    layer.fields().indexOf("area_km2")
                ).applyOnUpdate()
            )

            self.assertTrue(
                layer.defaultValueDefinition(
                    layer.fields().indexOf("perimeter_km")
                ).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestAddTargetControlMeasuresLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_target_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_target_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        first = add_target_control_measures_lines_layer(self.iface)

        result = add_target_control_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_target_control_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)
