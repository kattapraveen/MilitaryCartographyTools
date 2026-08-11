# -*- coding: utf-8 -*-

"""
Tests for military_symbology/airspace_control_measures.py - the
Airspace Control Measures line/area layers (Table H-XIII, Mini-Phase
H7), styled via a QgsRuleBasedRenderer keyed on "measure_type". See that
module's own docstring for what's approximated (the corridor/route
family), what's built for real (the zone/area family, IFF Off/On Line),
and what's skipped (the 25-entry point vocabulary, added instead to
control_measure_points.py, and Base Defense Zone).

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

from MilitaryCartographyTools.military_symbology.airspace_control_measures import (
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    add_airspace_control_measures_areas_layer,
    add_airspace_control_measures_lines_layer,
    create_airspace_control_measures_areas_layer,
    create_airspace_control_measures_lines_layer,
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


class TestCreateAirspaceControlMeasuresLinesLayer(QgisTestCase):

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

        layer = create_airspace_control_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "length_km",
            ]
        )


    def test_is_a_line_layer(self):

        layer = create_airspace_control_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_airspace_control_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in LINE_MEASURE_TYPE_LABELS
            }
        )


    def test_corridor_family_labels_prefix_the_type_abbreviation(self):

        layer = create_airspace_control_measures_lines_layer()

        cases = {
            "air_corridor": ("AC", "gold", "AC GOLD"),
            "low_level_transit_route": ("LLTR", "cobra", "LLTR COBRA"),
            "minimum_risk_route": ("MRR", "red", "MRR RED"),
            "safe_lane": ("SL", "lion", "SL LION"),
            "saafr": ("SAAFR", "blue", "SAAFR BLUE"),
            "transit_corridor": ("TC", "king", "TC KING"),
            "unmanned_aircraft_route": ("UA", "dragon", "UA DRAGON"),
        }

        for measure_type, (prefix, name, expected) in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, unique_designation=name
                    ),
                    expected
                )

                # Prefix alone when no name is given.
                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    prefix
                )


    def test_corridor_family_is_a_moderately_thick_status_driven_line(self):

        layer = create_airspace_control_measures_lines_layer()

        for measure_type in (
            "air_corridor", "low_level_transit_route", "minimum_risk_route",
            "safe_lane", "saafr", "transit_corridor", "unmanned_aircraft_route",
        ):

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 1)

                base_line = symbol.symbolLayer(0)

                self.assertGreaterEqual(base_line.width(), 1.0)

                self.assertTrue(
                    base_line.dataDefinedProperties().hasProperty(
                        QgsSymbolLayer.Property.StrokeStyle
                    )
                )


    def test_iff_lines_use_the_expected_fixed_end_labels(self):

        layer = create_airspace_control_measures_lines_layer()

        cases = {
            "iff_off_line": "IFF OFF",
            "iff_on_line": "IFF ON",
        }

        for measure_type, character in cases.items():

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 3)

                for i in (1, 2):

                    label_layer = symbol.symbolLayer(i)

                    self.assertIsInstance(label_layer, QgsMarkerLineSymbolLayer)

                    font_layer = label_layer.subSymbol().symbolLayer(0)

                    self.assertEqual(font_layer.character(), character)

                # IFF lines carry no general designation label - they
                # rely entirely on the fixed end markers above.
                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    ""
                )


    def test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_airspace_control_measures_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in ("air_corridor", "iff_off_line"):

            symbol = _rule_symbol_for(layer, measure_type)
            stroke_layer = symbol.symbolLayer(0)

            for affiliation, hex_color in expected.items():

                with self.subTest(measure_type=measure_type, affiliation=affiliation):

                    color, ok = _resolve_stroke_color(stroke_layer, layer, affiliation)

                    self.assertTrue(ok)
                    self.assertEqual(color.name(), hex_color)


    def test_length_km_default_value_recalculates_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_airspace_control_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            self.assertTrue(
                layer.defaultValueDefinition(idx).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateAirspaceControlMeasuresAreasLayer(QgisTestCase):

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

        layer = create_airspace_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_airspace_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_airspace_control_measures_areas_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in AREA_MEASURE_TYPE_LABELS
            }
        )


    def test_labels_prefix_the_type_abbreviation(self):

        layer = create_airspace_control_measures_areas_layer()

        cases = {
            "hidacz": ("HIDACZ", "32aadc", "HIDACZ\n32AADC"),
            "roz": ("ROZ", "11 ada bde", "ROZ\n11 ADA BDE"),
            "aarroz": ("AARROZ", "2id", "AARROZ\n2ID"),
            "ua_roz": ("UA-ROZ", "mnd(n)", "UA-ROZ\nMND(N)"),
            "wez": ("WEZ", "21 ada bn", "WEZ\n21 ADA BN"),
            "fez": ("FEZ", "atf", "FEZ\nATF"),
            "jez": ("JEZ", "atf", "JEZ\nATF"),
            "mez": ("MEZ", "2-4 ada bn", "MEZ\n2-4 ADA BN"),
            "lomez": ("LOMEZ", "aacc", "LOMEZ\nAACC"),
            "himez": ("HIMEZ", "aacc", "HIMEZ\nAACC"),
            "shoradez": ("SHORADEZ", "atf", "SHORADEZ\nATF"),
            "weapons_free_zone": ("WFZ", "atf", "WFZ\nATF"),
        }

        for measure_type, (prefix, name, expected) in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, unique_designation=name
                    ),
                    expected
                )

                # Prefix alone when no name is given.
                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    prefix
                )


    def test_weapons_free_zone_has_a_hatched_fill_layer(self):

        layer = create_airspace_control_measures_areas_layer()

        symbol = _rule_symbol_for(layer, "weapons_free_zone")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        hatch_layer = symbol.symbolLayer(1)

        self.assertEqual(
            hatch_layer.layerType(),
            "LinePatternFill"
        )


    def test_other_areas_are_a_plain_unfilled_outline(self):

        layer = create_airspace_control_measures_areas_layer()

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            if measure_type == "weapons_free_zone":
                continue

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 1)


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_airspace_control_measures_areas_layer()

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

            layer = create_airspace_control_measures_areas_layer()

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


class TestAddAirspaceControlMeasuresLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_airspace_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_airspace_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        first = add_airspace_control_measures_lines_layer(self.iface)

        result = add_airspace_control_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_airspace_control_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)
