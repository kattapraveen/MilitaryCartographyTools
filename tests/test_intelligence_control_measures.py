# -*- coding: utf-8 -*-

"""
Tests for military_symbology/intelligence_control_measures.py - the
Intelligence Control Measures Lines layer (Table H-XXV, Mini-Phase
H22). One drawable symbol, the Intelligence Coordination Line, built
as the same both-ends-labelled line the Battlefield and Restrictive
Fire Lines of Table H-XVI already use.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsProject,
    QgsSymbolLayer,
)
from qgis.PyQt.QtCore import Qt

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.intelligence_control_measures import (
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_CODES,
    LINE_MEASURE_TYPE_LABELS,
    TABLE_H_XXV_NOT_A_SYMBOL,
    add_intelligence_control_measures_lines_layer,
    create_intelligence_control_measures_lines_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestIntelligenceVocabulary(QgisTestCase):

    def test_the_table_is_one_drawable_symbol_plus_its_parent_row(self):

        # Table H-XXV is the whole of H.5.27, printed page 656: two
        # rows, of which 300000 draws nothing at all. Recorded rather
        # than dropped, so the arithmetic is checkable without
        # re-reading the printed table.
        self.assertEqual(LINE_MEASURE_TYPE_CODES, {"icl": "300100"})

        self.assertEqual(set(TABLE_H_XXV_NOT_A_SYMBOL), {"300000"})

        self.assertEqual(
            set(LINE_MEASURE_TYPE_LABELS), set(LINE_MEASURE_TYPE_CODES)
        )


class TestIntelligenceLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _label_rules(self, layer):

        """
        Two rules, appended start-anchored then end-anchored.

        NOTE a rule's own settings() returns BY VALUE - hold it in its
        own variable rather than chaining, or the temporary's C++
        object can be collected mid-expression and segfault the
        interpreter.
        """

        root = layer.labeling().rootRule()

        children = root.children()

        self.assertEqual(len(children), 2)

        return children


    def _evaluate_label(self, layer, unique_designation=""):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", "icl")
        feature.setAttribute("unique_designation", unique_designation)

        settings = self._label_rules(layer)[0].settings()

        expression = QgsExpression(settings.fieldName)

        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def test_has_the_expected_fields(self):

        layer = create_intelligence_control_measures_lines_layer()

        self.assertTrue(layer.isValid())

        self.assertEqual(
            [field.name() for field in layer.fields()],
            [
                "measure_type",
                "affiliation",
                "status",
                "unique_designation",
                "length_km",
            ]
        )


    def test_the_label_puts_the_designation_after_the_abbreviation(self):

        # The standard's own example: "ICL EUSTIS" - the NFL/BCL/RFL
        # order, not FSCL's own designation-first one.
        layer = create_intelligence_control_measures_lines_layer()

        self.assertEqual(
            self._evaluate_label(layer, "EUSTIS"), "ICL EUSTIS"
        )


    def test_designations_are_upper_cased_per_h_5_4(self):

        layer = create_intelligence_control_measures_lines_layer()

        self.assertEqual(
            self._evaluate_label(layer, "eustis"), "ICL EUSTIS"
        )


    def test_a_blank_designation_leaves_no_trailing_space(self):

        # Without trim() a blank field gives "ICL ", and the mask would
        # then cut a hole in the line for the trailing space.
        layer = create_intelligence_control_measures_lines_layer()

        self.assertEqual(self._evaluate_label(layer), "ICL")


    def test_the_label_is_drawn_at_both_ends_clear_of_the_line(self):

        # AboveRight at the start and AboveLeft at the end, so a long
        # designation is pushed INWARD from each end vertex rather than
        # hanging off past it - the same pair the BCL/RFL family uses.
        layer = create_intelligence_control_measures_lines_layer()

        start_rule, end_rule = self._label_rules(layer)

        start_settings = start_rule.settings()

        self.assertEqual(
            start_settings.placement, Qgis.LabelPlacement.OverPoint
        )
        self.assertTrue(start_settings.geometryGeneratorEnabled)
        self.assertEqual(
            start_settings.geometryGenerator, "start_point($geometry)"
        )
        self.assertEqual(
            start_settings.quadOffset,
            Qgis.LabelQuadrantPosition.AboveRight
        )

        end_settings = end_rule.settings()

        self.assertEqual(
            end_settings.geometryGenerator, "end_point($geometry)"
        )
        self.assertEqual(
            end_settings.quadOffset,
            Qgis.LabelQuadrantPosition.AboveLeft
        )


    def test_both_labels_mask_the_line_they_sit_on(self):

        # Both rules must declare the SAME list - masking is per QGIS
        # layer, and differing lists make QGIS keep one arbitrarily and
        # log a warning.
        layer = create_intelligence_control_measures_lines_layer()

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

        self.assertEqual(declared[0], ["icl_line"])
        self.assertEqual(declared[1], declared[0])


    def test_the_masked_id_is_the_id_the_line_actually_carries(self):

        # A QgsSymbolLayerReference pointing at an id no symbol layer
        # has masks nothing at all, silently.
        layer = create_intelligence_control_measures_lines_layer()

        rule = next(
            rule for rule in layer.renderer().rootRule().children()
            if rule.filterExpression() == '"measure_type" = \'icl\''
        )

        symbol = rule.symbol()

        self.assertEqual(symbol.symbolLayerCount(), 1)

        self.assertEqual(symbol.symbolLayer(0).id(), "icl_line")


    def test_the_line_is_solid_when_present_and_dashed_when_planned(self):

        layer = create_intelligence_control_measures_lines_layer()

        rule = next(
            rule for rule in layer.renderer().rootRule().children()
            if rule.filterExpression() == '"measure_type" = \'icl\''
        )

        symbol_layer = rule.symbol().symbolLayer(0)

        for status, expected in (
            ("present", Qt.PenStyle.SolidLine),
            ("planned", Qt.PenStyle.DashLine),
        ):

            with self.subTest(status=status):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("measure_type", "icl")
                feature.setAttribute("status", status)

                context = layer.createExpressionContext()
                context.setFeature(feature)

                properties = symbol_layer.dataDefinedProperties()

                value, ok = properties.valueAsString(
                    QgsSymbolLayer.Property.StrokeStyle, context
                )

                self.assertTrue(ok)

                self.assertEqual(
                    value,
                    "solid" if expected == Qt.PenStyle.SolidLine else "dash"
                )


    def test_the_line_takes_its_colour_from_the_affiliation(self):

        layer = create_intelligence_control_measures_lines_layer()

        rule = next(
            rule for rule in layer.renderer().rootRule().children()
            if rule.filterExpression() == '"measure_type" = \'icl\''
        )

        symbol_layer = rule.symbol().symbolLayer(0)

        for affiliation, expected in (
            ("friend", "#0000ff"),
            ("hostile", "#ff0000"),
        ):

            with self.subTest(affiliation=affiliation):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("measure_type", "icl")
                feature.setAttribute("affiliation", affiliation)

                context = layer.createExpressionContext()
                context.setFeature(feature)

                properties = symbol_layer.dataDefinedProperties()

                color, ok = properties.valueAsColor(
                    QgsSymbolLayer.Property.StrokeColor, context
                )

                self.assertTrue(ok)

                self.assertEqual(color.name(), expected)


    def test_adding_the_layer_inserts_exactly_one(self):

        layer = add_intelligence_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)), 1
        )


    def test_a_second_add_warns_instead_of_replacing(self):

        first = add_intelligence_control_measures_lines_layer(self.iface)

        self.assertIsNone(
            add_intelligence_control_measures_lines_layer(self.iface)
        )

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
        self.assertEqual(len(self.iface.messageBar().calls), 1)
