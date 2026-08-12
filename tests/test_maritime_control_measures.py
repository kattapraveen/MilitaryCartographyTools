# -*- coding: utf-8 -*-

"""
Tests for military_symbology/maritime_control_measures.py - the
Maritime Control Measures Bearing Line family (Table H-XIV, Mini-Phase
H8/H9), styled via a QgsRuleBasedRenderer keyed on "measure_type". See
that module's own docstring for why this is a Lines-only layer and for
the much larger AEGIS-specific/ASW-sonar/Sonobuoy family deliberately
left out (added instead, where curated in, to control_measure_points.py).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsProject,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.maritime_control_measures import (
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    add_maritime_control_measures_lines_layer,
    create_maritime_control_measures_lines_layer,
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


class TestCreateMaritimeControlMeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _label_rules(self, layer):

        """
        This layer went from QgsVectorLayerSimpleLabeling to
        QgsRuleBasedLabeling 2026-08-12, when the unique designation
        became a second, separately-placed label - so there is no
        single layer.labeling().settings() any more. Returns the two
        rules in the order they are appended: abbreviation first,
        designation second.

        NOTE each rule's own settings() returns BY VALUE - hold it in
        its own variable before touching anything on it. Chaining lets
        the temporary's C++ object be collected mid-expression and
        segfaults the interpreter outright; see
        test_offensive_control_measures.py's own note on the same trap.
        """

        root = layer.labeling().rootRule()

        children = root.children()

        self.assertEqual(len(children), 2)

        return children


    def _evaluate_label(self, layer, measure_type, unique_designation=""):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)
        feature.setAttribute("unique_designation", unique_designation)

        abbreviation_rule = self._label_rules(layer)[0]

        settings = abbreviation_rule.settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def test_has_the_expected_fields(self):

        layer = create_maritime_control_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type",
                "affiliation",
                "status",
                "unique_designation",
                "length_km",
            ]
        )


    def test_is_a_line_layer(self):

        layer = create_maritime_control_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_maritime_control_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in LINE_MEASURE_TYPE_LABELS
            }
        )


    def test_bearing_line_labels_use_the_expected_fixed_characters(self):

        layer = create_maritime_control_measures_lines_layer()

        cases = {
            "bearing_line": "B",
            "bearing_line_electronic": "E",
            "bearing_line_electronic_warfare": "EW",
            "bearing_line_acoustic": "A",
            "bearing_line_acoustic_ambiguous": "A",
            "bearing_line_torpedo": "T",
            "bearing_line_electro_optical_intercept": "O",
            "bearing_line_jammer": "J",
            "bearing_line_rdf": "RDF",
        }

        for measure_type, character in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    character
                )


    def test_bearing_line_labels_stay_upright(self):

        # 2026-08-12, the maintainer's own first point on this table:
        # "the orientation has to be straight at all times and not
        # along the line". Qgis.LabelPlacement.Line rotates its label
        # to follow the feature, which on a right-to-left or steeply
        # descending bearing renders it upside-down; .Horizontal is
        # QGIS's own "along the line, text stays level" mode. Both
        # rules must avoid .Line - the designation uses OverPoint
        # against the line's own end vertex instead.
        layer = create_maritime_control_measures_lines_layer()

        abbreviation_rule, designation_rule = self._label_rules(layer)

        abbreviation_settings = abbreviation_rule.settings()

        self.assertEqual(
            abbreviation_settings.placement,
            Qgis.LabelPlacement.Horizontal
        )

        designation_settings = designation_rule.settings()

        self.assertEqual(
            designation_settings.placement,
            Qgis.LabelPlacement.OverPoint
        )


    def test_bearing_line_labels_mask_the_line_they_sit_on(self):

        # The maintainer's own second point: "should be masked so that
        # the line is not cutting through the letter". Both symbol
        # builders' ids have to be in the list - a type whose id is
        # missing would keep drawing through its own label - and BOTH
        # rules must declare the SAME list, or QGIS logs "Different
        # sets of symbol layers are masked by different sources!" and
        # silently keeps only one of them.
        layer = create_maritime_control_measures_lines_layer()

        declared = []

        for rule in self._label_rules(layer):

            settings = rule.settings()

            text_format = settings.format()

            mask = text_format.mask()

            self.assertTrue(mask.enabled())

            declared.append(
                sorted(
                    reference.symbolLayerIdV2()
                    for reference in mask.maskedSymbolLayers()
                )
            )

        self.assertEqual(
            declared[0],
            ["bearing_line", "bearing_line_acoustic_ambiguous"]
        )

        self.assertEqual(declared[0], declared[1])


    def test_unique_designation_labels_the_lines_end_below_right(self):

        # The maintainer's own third point: "there should be an option
        # for unique designator which will be place at the end - bottom
        # right of the line, also oriented straight". The standard's own
        # template puts its "H" box just ABOVE the PT2 end instead;
        # below-right is the maintainer's explicit call.
        layer = create_maritime_control_measures_lines_layer()

        designation_rule = self._label_rules(layer)[1]

        settings = designation_rule.settings()

        self.assertTrue(settings.geometryGeneratorEnabled)

        self.assertEqual(
            settings.geometryGenerator,
            "end_point($geometry)"
        )

        self.assertEqual(
            settings.quadOffset,
            Qgis.LabelQuadrantPosition.BelowRight
        )

        # Upper-cased per H.5.4, and a blank field must not reserve the
        # empty label's own space.
        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", "bearing_line_jammer")
        feature.setAttribute("unique_designation", "pat-1")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        expression = QgsExpression(settings.fieldName)

        self.assertEqual(expression.evaluate(context), "PAT-1")

        filter_expression = QgsExpression(designation_rule.filterExpression())

        self.assertTrue(filter_expression.evaluate(context))

        blank = QgsFeature(layer.fields())
        blank.setAttribute("measure_type", "bearing_line_jammer")

        blank_context = layer.createExpressionContext()
        blank_context.setFeature(blank)

        self.assertFalse(filter_expression.evaluate(blank_context))


    def test_acoustic_ambiguous_is_always_dashed(self):

        layer = create_maritime_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "bearing_line_acoustic_ambiguous")
        base_line = symbol.symbolLayer(0)

        self.assertEqual(base_line.penStyle(), Qt.PenStyle.DashLine)

        # No data-defined StrokeStyle override - always dashed
        # regardless of the "status" field.
        has_override = base_line.dataDefinedProperties().hasProperty(
            QgsSymbolLayer.Property.StrokeStyle
        )

        self.assertFalse(has_override)


    def test_other_bearing_lines_follow_the_shared_status_field(self):

        layer = create_maritime_control_measures_lines_layer()

        for measure_type in LINE_MEASURE_TYPE_LABELS:

            if measure_type == "bearing_line_acoustic_ambiguous":
                continue

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)
                base_line = symbol.symbolLayer(0)

                self.assertTrue(
                    base_line.dataDefinedProperties().hasProperty(
                        QgsSymbolLayer.Property.StrokeStyle
                    )
                )


    def test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_maritime_control_measures_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in ("bearing_line", "bearing_line_acoustic_ambiguous"):

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

            layer = create_maritime_control_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            self.assertTrue(
                layer.defaultValueDefinition(idx).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestAddMaritimeControlMeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_maritime_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        first = add_maritime_control_measures_lines_layer(self.iface)

        result = add_maritime_control_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_maritime_control_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)
