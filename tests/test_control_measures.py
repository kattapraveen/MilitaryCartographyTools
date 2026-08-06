# -*- coding: utf-8 -*-

"""
Tests for military_symbology/control_measures.py - the control-measure
line/area layers (phase lines, boundaries, axis of advance, objectives,
NAIs) styled via a QgsRuleBasedRenderer keyed on "measure_type".

Military Cartography Tools
"""

from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsVectorLayer

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.military_symbology.control_measures import (
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    add_control_measures_areas_layer,
    add_control_measures_lines_layer,
    create_control_measures_areas_layer,
    create_control_measures_lines_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestCreateControlMeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_control_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["measure_type", "unique_designation"]
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


class TestCreateControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["measure_type", "unique_designation"]
        )


    def test_is_a_polygon_layer(self):

        layer = create_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


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
