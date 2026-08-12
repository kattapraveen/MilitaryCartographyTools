# -*- coding: utf-8 -*-

"""
Tests for military_symbology/fire_support_coordination_measures.py -
the Fire Support Coordination Measures line/area layers (Table H-XVI,
Mini-Phase H11), styled via a QgsRuleBasedRenderer keyed on
"measure_type". See that module's own docstring for which Irregular/
Rectangle/Circular code triples were folded into each area type, and
for why CFL/MFP use a centred label while FSCL/NFL/BCL/RFL use a
fixed label at each end.

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
from qgis.PyQt.QtCore import Qt

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.fire_support_coordination_measures import (
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    add_fire_support_coordination_measures_areas_layer,
    add_fire_support_coordination_measures_lines_layer,
    create_fire_support_coordination_measures_areas_layer,
    create_fire_support_coordination_measures_lines_layer,
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


class TestCreateFireSupportCoordinationMeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _label_rules(self, layer):

        """
        This layer went from QgsVectorLayerSimpleLabeling to
        QgsRuleBasedLabeling 2026-08-12, when each measure type's label
        stopped sharing one placement - so there is no single
        layer.labeling().settings() any more. Four rules, appended in
        this order: the two end-anchored ones (start, then end), then
        CFL, then MFP.

        NOTE a rule's own settings() returns BY VALUE - hold it in its
        own variable rather than chaining, or the temporary's C++ object
        can be collected mid-expression and segfault the interpreter.
        See test_offensive_control_measures.py's own note on the trap.
        """

        root = layer.labeling().rootRule()

        children = root.children()

        self.assertEqual(len(children), 4)

        return children


    def _evaluate_label(self, layer, measure_type, unique_designation=""):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)
        feature.setAttribute("unique_designation", unique_designation)

        settings = self._label_rules(layer)[0].settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def test_has_the_expected_fields(self):

        layer = create_fire_support_coordination_measures_lines_layer()

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

        layer = create_fire_support_coordination_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_fire_support_coordination_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in LINE_MEASURE_TYPE_LABELS
            }
        )


    def test_line_labels_place_the_designation_per_the_template(self):

        # 2026-08-12, from the maintainer's own live testing. FSCL puts
        # the designation FIRST - its template reads "[T] FSCL" and its
        # example "MND(S) FSCL" - while NFL/BCL/RFL/CFL all put it LAST
        # ("NFL [T]", example "NFL II CORPS"). MFP has no Field T box in
        # its template at all. Getting these backwards is invisible
        # until someone reads the map, so each is pinned separately.
        layer = create_fire_support_coordination_measures_lines_layer()

        cases = {
            "fscl": "MND(S) FSCL",
            "nfl": "NFL II CORPS",
            "bcl": "BCL III MEF",
            "rfl": "RFL II CORPS",
            "cfl": "CFL 52ID (M)",
            "mfp": "MFP",
        }

        designations = {
            "fscl": "MND(S)",
            "nfl": "II CORPS",
            "bcl": "III MEF",
            "rfl": "II CORPS",
            "cfl": "52ID (M)",
            "mfp": "IGNORED",
        }

        for measure_type, expected in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, designations[measure_type]
                    ),
                    expected
                )


    def test_a_blank_designation_leaves_no_trailing_space(self):

        # trim() in _line_label_expression(): without it a blank field
        # gives "NFL " / " FSCL", and the mask would then cut a hole in
        # the line for the trailing space.
        layer = create_fire_support_coordination_measures_lines_layer()

        for measure_type, expected in (
            ("fscl", "FSCL"),
            ("nfl", "NFL"),
            ("bcl", "BCL"),
            ("rfl", "RFL"),
            ("cfl", "CFL"),
        ):

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    expected
                )


    def test_designations_are_upper_cased_per_h_5_4(self):

        layer = create_fire_support_coordination_measures_lines_layer()

        self.assertEqual(
            self._evaluate_label(layer, "nfl", "ii corps"),
            "NFL II CORPS"
        )


    def test_end_labelled_lines_label_both_ends_clear_of_the_line(self):

        # These four used to draw their abbreviation as a pair of fixed-
        # character font markers, which could never carry a per-feature
        # designation (a marker's character is fixed at build time). They
        # are real PAL labels now: one anchored on the line's own start
        # vertex, one on its end. AboveRight/AboveLeft rather than a
        # plain Above at both, so a long designation is pushed INWARD
        # from each end instead of hanging off past it.
        layer = create_fire_support_coordination_measures_lines_layer()

        start_rule, end_rule = self._label_rules(layer)[:2]

        expected_filter = (
            '"measure_type" = \'fscl\' OR "measure_type" = \'nfl\''
            ' OR "measure_type" = \'bcl\' OR "measure_type" = \'rfl\''
        )

        for rule in (start_rule, end_rule):

            self.assertEqual(rule.filterExpression(), expected_filter)

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

        # The old font-marker pair is gone - a plain line, nothing else.
        for measure_type in ("fscl", "nfl", "bcl", "rfl"):

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 1)


    def test_cfl_sits_above_the_centre_and_mfp_stays_on_the_line(self):

        # CFL's own draw rules: "the line information will be posted
        # once at the center of the line" - and the maintainer asked for
        # it above the line specifically. MFP was already placed
        # correctly and only needed the mask, so it keeps the shared
        # OnLine default its template draws.
        layer = create_fire_support_coordination_measures_lines_layer()

        cfl_rule, mfp_rule = self._label_rules(layer)[2:]

        self.assertEqual(cfl_rule.filterExpression(), '"measure_type" = \'cfl\'')
        self.assertEqual(mfp_rule.filterExpression(), '"measure_type" = \'mfp\'')

        cfl_settings = cfl_rule.settings()

        self.assertEqual(cfl_settings.placement, Qgis.LabelPlacement.Line)
        self.assertEqual(
            cfl_settings.lineSettings().placementFlags(),
            Qgis.LabelLinePlacementFlag.AboveLine
        )

        mfp_settings = mfp_rule.settings()

        self.assertEqual(mfp_settings.placement, Qgis.LabelPlacement.Line)
        self.assertEqual(
            mfp_settings.lineSettings().placementFlags(),
            Qgis.LabelLinePlacementFlag.OnLine
        )


    def test_every_line_label_masks_its_own_line(self):

        # "not overlapping line" for the end-labelled four, and the
        # maintainer's only ask for MFP ("needs to be masked so that
        # line is not overlapping it"). All four rules must declare the
        # SAME list - masking is per QGIS layer, and differing lists
        # make QGIS keep one arbitrarily and log a warning.
        layer = create_fire_support_coordination_measures_lines_layer()

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
            ["cfl_line", "fscl_family_line", "mfp_line"]
        )

        for other in declared[1:]:

            self.assertEqual(other, declared[0])


    def test_cfl_is_always_dashed(self):

        layer = create_fire_support_coordination_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "cfl")
        base_line = symbol.symbolLayer(0)

        self.assertEqual(base_line.penStyle(), Qt.PenStyle.DashLine)

        has_override = base_line.dataDefinedProperties().hasProperty(
            QgsSymbolLayer.Property.StrokeStyle
        )

        self.assertFalse(has_override)


    def test_other_lines_follow_the_shared_status_field(self):

        layer = create_fire_support_coordination_measures_lines_layer()

        for measure_type in LINE_MEASURE_TYPE_LABELS:

            if measure_type == "cfl":
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

        layer = create_fire_support_coordination_measures_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in ("fscl", "cfl"):

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

            layer = create_fire_support_coordination_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            self.assertTrue(
                layer.defaultValueDefinition(idx).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateFireSupportCoordinationMeasuresAreasLayer(QgisTestCase):

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

        layer = create_fire_support_coordination_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_fire_support_coordination_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_fire_support_coordination_measures_areas_layer()

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

        layer = create_fire_support_coordination_measures_areas_layer()

        cases = {
            "aca": ("ACA", "1", "ACA\n1"),
            "ffa": ("FFA", "x corps", "FFA\nX CORPS"),
            "nfa": ("NFA", "x corps", "NFA\nX CORPS"),
            "rfa": ("RFA", "x corps", "RFA\nX CORPS"),
            "paa": ("PAA", "1-6 fa", "PAA\n1-6 FA"),
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


    def test_nfa_has_a_hatched_fill_layer(self):

        layer = create_fire_support_coordination_measures_areas_layer()

        symbol = _rule_symbol_for(layer, "nfa")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        hatch_layer = symbol.symbolLayer(1)

        self.assertEqual(
            hatch_layer.layerType(),
            "LinePatternFill"
        )


    def test_other_areas_are_a_plain_unfilled_outline(self):

        layer = create_fire_support_coordination_measures_areas_layer()

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            if measure_type == "nfa":
                continue

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 1)


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_fire_support_coordination_measures_areas_layer()

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

            layer = create_fire_support_coordination_measures_areas_layer()

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


class TestAddFireSupportCoordinationMeasuresLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_fire_support_coordination_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_fire_support_coordination_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        first = add_fire_support_coordination_measures_lines_layer(self.iface)

        result = add_fire_support_coordination_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_fire_support_coordination_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)
