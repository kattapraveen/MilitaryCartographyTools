# -*- coding: utf-8 -*-

"""
Tests for military_symbology/target_acquisition_control_measures.py -
the Target Acquisition Control Measures Areas layer (Table H-XVIII,
Mini-Phase H13/H14), styled via a QgsRuleBasedRenderer keyed on
"measure_type". See that module's own docstring for what's skipped
(both Weapon/Sensor Range Fan variants).

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

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.target_acquisition_control_measures import (
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    add_target_acquisition_control_measures_areas_layer,
    create_target_acquisition_control_measures_areas_layer,
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


class TestCreateTargetAcquisitionControlMeasuresAreasLayer(QgisTestCase):

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

        layer = create_target_acquisition_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_covers_every_measure_type_the_table_lists(self):

        # Was a bare `len(...) == 11` count until 2026-08-12, which is
        # exactly the check that let Terminally Guided Munition
        # Footprint (242000) go missing: it was never added, so the
        # count agreed with itself and stayed green. Pinned against the
        # standard's OWN code list now, so an absent measure type fails
        # by name rather than passing quietly.
        #
        # Codes are given as the table gives them - most entries are an
        # Irregular/Rectangle/Circular TRIPLE folded into one measure
        # type here, TGMF is a lone code, and the two Kill Boxes share
        # one 2423xx run between them. That mixture is very likely why a
        # pass reading the table in triples skipped the one entry that
        # isn't one.
        self.assertEqual(
            set(AREA_MEASURE_TYPE_LABELS),
            {
                "ati",            # 241101/102/103
                "cffz",           # 241201/202/203
                "censor_zone",    # 241301/302/303
                "cfz",            # 241401/402/403
                "dead_space_area",  # 241501/502/503
                "sensor_zone",    # 241601/602/603
                "tba",            # 241701/702/703
                "tvar",           # 241801/802/803
                "zor",            # 241901/902/903
                "tgmf",           # 242000 - single code, no triple
                "blue_kill_box",  # 242301/302/303
                "purple_kill_box",  # 242304/305/306
            }
        )

        # Weapon/Sensor Range Fan (242100 Circular, 242200 Sector) are
        # deliberately still absent - genuinely computed geometry from
        # one anchor point, not a digitized boundary. Tracked to build
        # rather than curated out.
        self.assertNotIn("weapon_sensor_range_fan_circular", AREA_MEASURE_TYPE_LABELS)
        self.assertNotIn("weapon_sensor_range_fan_sector", AREA_MEASURE_TYPE_LABELS)


    def test_terminally_guided_munition_footprint_labels_tgmf(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        self.assertEqual(self._evaluate_label(layer, "tgmf"), "TGMF")

        self.assertEqual(
            self._evaluate_label(
                layer, "tgmf", unique_designation="alpha"
            ),
            "TGMF\nALPHA"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_target_acquisition_control_measures_areas_layer()

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

        layer = create_target_acquisition_control_measures_areas_layer()

        cases = {
            "ati": ("ATI", "mnd(n)", "ATI\nMND(N)"),
            "cffz": ("CFF ZONE", "3bde 4id", "CFF ZONE\n3BDE 4ID"),
            "censor_zone": ("CENSOR ZONE", "school", "CENSOR ZONE\nSCHOOL"),
            "cfz": ("CF ZONE", "green", "CF ZONE\nGREEN"),
            "dead_space_area": ("DA", "1/7 fa", "DA\n1/7 FA"),
            "sensor_zone": ("SENSOR ZONE", "q37", "SENSOR ZONE\nQ37"),
            "tba": ("TBA", "tank", "TBA\nTANK"),
            "tvar": ("TVAR", "scud", "TVAR\nSCUD"),
            "zor": ("ZOR", "3bde 4id", "ZOR\n3BDE 4ID"),
            "blue_kill_box": ("BKB", "x corps", "BKB\nX CORPS"),
            "purple_kill_box": ("PKB", "x corps", "PKB\nX CORPS"),
        }

        for measure_type, (prefix, name, expected) in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, unique_designation=name
                    ),
                    expected
                )

                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    prefix
                )


    def test_every_area_is_a_plain_unfilled_outline(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 1)


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_target_acquisition_control_measures_areas_layer()

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

            layer = create_target_acquisition_control_measures_areas_layer()

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


class TestAddTargetAcquisitionControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_areas_layer_is_created_and_added(self):

        layer = add_target_acquisition_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_never_replaced_if_it_already_exists(self):

        first = add_target_acquisition_control_measures_areas_layer(self.iface)

        result = add_target_acquisition_control_measures_areas_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_target_acquisition_control_measures_areas_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], AREAS_LAYER_NAME)
