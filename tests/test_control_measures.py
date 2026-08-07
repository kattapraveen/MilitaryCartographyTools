# -*- coding: utf-8 -*-

"""
Tests for military_symbology/control_measures.py - the control-measure
line/area layers (phase lines, boundaries, axis of advance, objectives,
NAIs) styled via a QgsRuleBasedRenderer keyed on "measure_type".

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsProject,
    QgsSymbolLayer,
    QgsVectorLayer,
    QgsVectorLayerUtils,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.control_measures import (
    AFFILIATION_LABELS,
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    add_control_measures_areas_layer,
    add_control_measures_lines_layer,
    create_control_measures_areas_layer,
    create_control_measures_lines_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import AFFILIATIONS


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


class TestCreateControlMeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_control_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["measure_type", "affiliation", "unique_designation", "length_km"]
        )


    def test_is_a_line_layer(self):

        layer = create_control_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_measure_type_uses_a_value_map_widget(self):

        layer = create_control_measures_lines_layer()

        idx = layer.fields().indexOf("measure_type")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )


    def test_affiliation_uses_a_value_map_widget_defaulting_to_unknown(self):

        layer = create_control_measures_lines_layer()

        idx = layer.fields().indexOf("affiliation")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'unknown'"
        )


    def test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_3(self):

        # Per the actual MIL-STD-2525D standard (Appendix H, section
        # H.5.3 Coloring): friendly control measures in black or blue,
        # hostile in red - scoped down to exactly friend=blue,
        # hostile=red, everything else=black ("black as standard").
        layer = create_control_measures_lines_layer()

        for measure_type in LINE_MEASURE_TYPE_LABELS:

            symbol = _rule_symbol_for(layer, measure_type)

            color, ok = _resolve_stroke_color(
                symbol.symbolLayer(0), layer, "friend"
            )
            self.assertTrue(ok, measure_type)
            self.assertEqual(color.name(), "#0000ff", measure_type)

            color, ok = _resolve_stroke_color(
                symbol.symbolLayer(0), layer, "hostile"
            )
            self.assertTrue(ok, measure_type)
            self.assertEqual(color.name(), "#ff0000", measure_type)

            for affiliation in ("neutral", "unknown"):

                color, ok = _resolve_stroke_color(
                    symbol.symbolLayer(0), layer, affiliation
                )
                self.assertTrue(ok, (measure_type, affiliation))
                self.assertEqual(color.name(), "#000000", (measure_type, affiliation))


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_control_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {
            rule.filterExpression() for rule in root.children()
        }

        expected = {
            f'"measure_type" = \'{measure_type}\''
            for measure_type in LINE_MEASURE_TYPE_LABELS
        }

        self.assertEqual(filters, expected)


    def test_labelling_is_enabled_on_the_designation_field(self):

        layer = create_control_measures_lines_layer()

        self.assertTrue(layer.labelsEnabled())

        self.assertEqual(
            layer.labeling().settings().fieldName,
            "unique_designation"
        )


    def test_axis_of_advance_arrowhead_has_a_visible_outline_width(self):

        # "arrowhead" is a stroke-only simple-marker shape (no fillable
        # interior) - createSimple()'s own default outline_width is 0,
        # which Qt draws as a barely-visible 1-device-pixel cosmetic
        # hairline. Guards against that regressing back to "too light"
        # (reported during manual smoke testing).
        layer = create_control_measures_lines_layer()

        root = layer.renderer().rootRule()

        axis_rule = next(
            rule for rule in root.children()
            if rule.filterExpression() == '"measure_type" = \'axis_of_advance\''
        )

        marker_line_layer = axis_rule.symbol().symbolLayer(1)

        outline_width = marker_line_layer.subSymbol().symbolLayer(0).strokeWidth()

        self.assertGreater(outline_width, 0)


    def test_length_km_default_value_recalculates_on_update(self):

        # Reported during manual smoke testing: mct_area_km2/
        # mct_perimeter_km/mct_length_km used to require an @layer
        # expression argument that doesn't reliably populate across
        # every QGIS expression entry point (confirmed: QGIS's
        # in-place attribute-table field calculator doesn't set it,
        # silently producing "nan"). length_km's default value must
        # not depend on @layer, and must actually recalculate
        # (applyOnUpdate) rather than being a one-shot default.
        military_symbology_functions.register()

        try:

            QgsProject.instance().setCrs(WGS84)

            layer = create_control_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            definition = layer.defaultValueDefinition(idx)

            self.assertEqual(
                definition.expression(),
                "mct_length_km($geometry)"
            )

            self.assertTrue(definition.applyOnUpdate())

            # A 0.01deg line along the equator - real reference value
            # already verified in tests/test_area_perimeter_functions.py:
            # ~1.1132 km.
            geometry = QgsGeometry.fromWkt("LINESTRING(0 0, 0.01 0)")

            feature = QgsVectorLayerUtils.createFeature(layer, geometry)

            self.assertAlmostEqual(
                feature["length_km"],
                1.1131949079327358,
                places=6
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["measure_type", "affiliation", "unique_designation", "area_km2", "perimeter_km"]
        )


    def test_is_a_polygon_layer(self):

        layer = create_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_affiliation_uses_a_value_map_widget_defaulting_to_unknown(self):

        layer = create_control_measures_areas_layer()

        idx = layer.fields().indexOf("affiliation")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'unknown'"
        )


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_3(self):

        # See the Lines layer's own
        # test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_3()
        # for the standard citation - areas only have an outline colour
        # (style: "no" fill), so only StrokeColor applies here.
        layer = create_control_measures_areas_layer()

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            symbol = _rule_symbol_for(layer, measure_type)

            color, ok = _resolve_stroke_color(
                symbol.symbolLayer(0), layer, "friend"
            )
            self.assertTrue(ok, measure_type)
            self.assertEqual(color.name(), "#0000ff", measure_type)

            color, ok = _resolve_stroke_color(
                symbol.symbolLayer(0), layer, "hostile"
            )
            self.assertTrue(ok, measure_type)
            self.assertEqual(color.name(), "#ff0000", measure_type)

            color, ok = _resolve_stroke_color(
                symbol.symbolLayer(0), layer, "unknown"
            )
            self.assertTrue(ok, measure_type)
            self.assertEqual(color.name(), "#000000", measure_type)


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_control_measures_areas_layer()

        root = layer.renderer().rootRule()

        filters = {
            rule.filterExpression() for rule in root.children()
        }

        expected = {
            f'"measure_type" = \'{measure_type}\''
            for measure_type in AREA_MEASURE_TYPE_LABELS
        }

        self.assertEqual(filters, expected)


    def test_labelling_is_enabled_on_the_designation_field(self):

        layer = create_control_measures_areas_layer()

        self.assertTrue(layer.labelsEnabled())


    def test_area_and_perimeter_default_values_recalculate_on_update(self):

        # See the Lines layer's own
        # test_length_km_default_value_recalculates_on_update() for why
        # this matters (no @layer dependency, applyOnUpdate=True).
        military_symbology_functions.register()

        try:

            QgsProject.instance().setCrs(WGS84)

            layer = create_control_measures_areas_layer()

            area_idx = layer.fields().indexOf("area_km2")
            perimeter_idx = layer.fields().indexOf("perimeter_km")

            area_definition = layer.defaultValueDefinition(area_idx)
            perimeter_definition = layer.defaultValueDefinition(perimeter_idx)

            self.assertEqual(
                area_definition.expression(),
                "mct_area_km2($geometry)"
            )
            self.assertTrue(area_definition.applyOnUpdate())

            self.assertEqual(
                perimeter_definition.expression(),
                "mct_perimeter_km($geometry)"
            )
            self.assertTrue(perimeter_definition.applyOnUpdate())

            # A 0.01deg x 0.01deg box at the equator - real reference
            # values already verified in
            # tests/test_area_perimeter_functions.py: ~1.2309 km^2 area,
            # ~4.4379 km perimeter.
            geometry = QgsGeometry.fromWkt(
                "POLYGON((0 0, 0 0.01, 0.01 0.01, 0.01 0, 0 0))"
            )

            feature = QgsVectorLayerUtils.createFeature(layer, geometry)

            self.assertAlmostEqual(
                feature["area_km2"],
                1.2309072049932537,
                places=6
            )

            self.assertAlmostEqual(
                feature["perimeter_km"],
                4.43787531568142,
                places=6
            )

        finally:

            military_symbology_functions.unregister()


class TestAddControlMeasuresLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        # Same safety property as unit_layer.py's own add_unit_layer() -
        # this layer's content is hand-drawn operational data, not
        # something safe to silently recreate.
        first = add_control_measures_lines_layer(self.iface)

        result = add_control_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())

        self.assertEqual(
            len(self.iface.messageBar().calls),
            1
        )


    def test_areas_layer_is_never_replaced_if_it_already_exists(self):

        first = add_control_measures_areas_layer(self.iface)

        result = add_control_measures_areas_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_control_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)


class TestAffiliationLabelsMatchSidc(QgisTestCase):

    # Same drift-guard as unit_layer.py's own
    # TestVocabularyLabelsMatchSidc - AFFILIATION_LABELS is this
    # module's presentation layer, sidc.py's AFFILIATIONS is the data
    # model; this only guards the two staying in sync, not that either
    # one's own values are correct.
    def test_affiliation_labels_cover_exactly_sidcs_affiliations(self):

        self.assertEqual(
            set(AFFILIATION_LABELS),
            set(AFFILIATIONS)
        )
