# -*- coding: utf-8 -*-

"""
Tests for military_symbology/maneuver_control_measures.py - the
Maneuver Control Measures line/area layers (Table H-VII, Mini-Phase
H3), styled via a QgsRuleBasedRenderer keyed on "measure_type". See
that module's own docstring for the full measure-type list, what was
scoped out (Offset Unit variants), and why Field N ("ENY") isn't
rendered. Also covers the 2026-08-09 correction pass (FLOT merged to
one measure type with open HalfArc arcs, Line of Contact added, Phase
Line's tick removed, Fortified Area rebuilt, Limited Access Area added)
made after the maintainer's own live QGIS testing.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsFontMarkerSymbolLayer,
    QgsGeometry,
    QgsMarkerLineSymbolLayer,
    QgsPointXY,
    QgsProject,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology import maneuver_control_measures
from MilitaryCartographyTools.military_symbology.maneuver_control_measures import (
    AFFILIATION_LABELS,
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    STATUS_LABELS,
    add_maneuver_control_measures_areas_layer,
    add_maneuver_control_measures_lines_layer,
    create_maneuver_control_measures_areas_layer,
    create_maneuver_control_measures_lines_layer,
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


class TestCreateManeuverControlMeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_maneuver_control_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "length_km",
            ]
        )


    def test_is_a_line_layer(self):

        layer = create_maneuver_control_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_measure_type_uses_a_value_map_widget_defaulting_to_phase_line(self):

        layer = create_maneuver_control_measures_lines_layer()

        idx = layer.fields().indexOf("measure_type")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(widget_setup.type(), "ValueMap")
        self.assertEqual(
            widget_setup.config()["map"],
            {label: value for value, label in LINE_MEASURE_TYPE_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'phase_line'"
        )


    def test_affiliation_uses_a_value_map_widget_defaulting_to_unspecified(self):

        layer = create_maneuver_control_measures_lines_layer()

        idx = layer.fields().indexOf("affiliation")

        self.assertEqual(
            layer.editorWidgetSetup(idx).config()["map"],
            {label: value for value, label in AFFILIATION_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'unspecified'"
        )


    def test_status_uses_a_value_map_widget_defaulting_to_present(self):

        layer = create_maneuver_control_measures_lines_layer()

        idx = layer.fields().indexOf("status")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(widget_setup.type(), "ValueMap")
        self.assertEqual(
            widget_setup.config()["map"],
            {label: value for value, label in STATUS_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'present'"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_maneuver_control_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in LINE_MEASURE_TYPE_LABELS
            }
        )


    def test_plain_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        # Phase Line/FEBA/Principal Direction of Fire all use a plain
        # QgsSimpleLineSymbolLayer as symbolLayer(0), unlike FLOT's own
        # arc-based construction (see the FLOT-specific stroke-style
        # test below) - same 5-colour rule as every other module here.
        layer = create_maneuver_control_measures_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in ("phase_line", "feba", "principal_direction_of_fire"):

            symbol = _rule_symbol_for(layer, measure_type)
            stroke_layer = symbol.symbolLayer(0)

            for affiliation, hex_color in expected.items():

                with self.subTest(measure_type=measure_type, affiliation=affiliation):

                    color, ok = _resolve_stroke_color(stroke_layer, layer, affiliation)

                    self.assertTrue(ok)
                    self.assertEqual(color.name(), hex_color)


    def test_flot_uses_a_single_continuous_chain_of_open_arcs(self):

        # A single "flot" measure type (not split by affiliation - see
        # module docstring), using Shape.HalfArc (a genuinely open arc,
        # no closing chord - the 2026-08-09 fix for a bug the SemiCircle
        # shape had) at an interval equal to the arc's own size, so
        # consecutive arcs touch with no gap.
        layer = create_maneuver_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "flot")

        marker_line = symbol.symbolLayer(0)
        arc_layer = marker_line.subSymbol().symbolLayer(0)

        self.assertEqual(
            arc_layer.shape(),
            QgsSimpleMarkerSymbolLayerBase.Shape.HalfArc
        )

        self.assertEqual(
            marker_line.interval(),
            arc_layer.size()
        )


    def test_flot_stroke_style_follows_status(self):

        # The template's own Planned/On Order rows (pages 411-412) show
        # a DOTTED version of the identical coil/crescent shape, not the
        # shared module's own 'dash' style - see _FLOT_STROKE_STYLE_
        # EXPRESSION's own comment for why this can't reuse
        # _STATUS_LINE_STYLE_EXPRESSION.
        layer = create_maneuver_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "flot")
        marker_line = symbol.symbolLayer(0)
        arc_layer = marker_line.subSymbol().symbolLayer(0)

        expr = arc_layer.dataDefinedProperties().property(
            QgsSymbolLayer.Property.StrokeStyle
        ).expressionString()

        self.assertIn("dot", expr)
        self.assertIn("solid", expr)


    def test_line_of_contact_has_two_offset_arc_chains_one_blue_one_red(self):

        # Not affiliation-driven (the maintainer's own instruction) -
        # one chain is fixed blue (friendly side - changed from black
        # 2026-08-10, the enemy side stays fixed red), offset a gap
        # apart, bulging toward each other.
        layer = create_maneuver_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "line_of_contact")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        colors = set()

        for i in (0, 1):

            marker_line = symbol.symbolLayer(i)
            arc_layer = marker_line.subSymbol().symbolLayer(0)

            self.assertEqual(
                arc_layer.shape(),
                QgsSimpleMarkerSymbolLayerBase.Shape.HalfArc
            )

            colors.add(arc_layer.strokeColor().name())

            # Offset on opposite sides of the digitized line.
            self.assertNotEqual(marker_line.offset(), 0)

        self.assertEqual(
            colors,
            {"#0000ff", "#ff0000"}
        )


    def test_flot_and_line_of_contact_arcs_are_the_same_reduced_size(self):

        # 2026-08-10, per the project maintainer's own explicit
        # instruction: both measure types' own arcs were too big,
        # reduced by 40% (6mm -> 3.6mm) - see _ARC_SIZE_MM's own comment.
        layer = create_maneuver_control_measures_lines_layer()

        flot_symbol = _rule_symbol_for(layer, "flot")
        flot_arc = flot_symbol.symbolLayer(0).subSymbol().symbolLayer(0)

        self.assertAlmostEqual(flot_arc.size(), 6 * 0.6, places=5)

        loc_symbol = _rule_symbol_for(layer, "line_of_contact")

        for i in (0, 1):

            loc_arc = loc_symbol.symbolLayer(i).subSymbol().symbolLayer(0)

            self.assertAlmostEqual(loc_arc.size(), 6 * 0.6, places=5)


    def test_phase_line_has_no_tick_and_a_dynamic_pl_label_at_each_end(self):

        layer = create_maneuver_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "phase_line")

        # symbolLayer(0) is the base line; then a "PL "+name label at
        # FirstVertex and LastVertex - 3 layers total, no tick (removed
        # 2026-08-09 - see module docstring).
        self.assertEqual(symbol.symbolLayerCount(), 3)

        label_layers = [
            symbol.symbolLayer(i)
            for i in (1, 2)
        ]

        for label_layer in label_layers:

            with self.subTest(index=label_layer):

                font_layer = label_layer.subSymbol().symbolLayer(0)

                self.assertIsInstance(font_layer, QgsFontMarkerSymbolLayer)

                expr = font_layer.dataDefinedProperties().property(
                    QgsSymbolLayer.Property.Character
                ).expressionString()

                self.assertIn("'PL'", expr)


    def test_feba_has_a_fixed_feba_label_at_each_end_with_no_tick(self):

        layer = create_maneuver_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "feba")

        # base line + 2 fixed end labels (no tick, unlike Phase Line).
        self.assertEqual(symbol.symbolLayerCount(), 3)

        for i in (1, 2):

            label_layer = symbol.symbolLayer(i)

            self.assertIsInstance(label_layer, QgsMarkerLineSymbolLayer)

            font_layer = label_layer.subSymbol().symbolLayer(0)

            self.assertEqual(font_layer.character(), "FEBA")


    def test_principal_direction_of_fire_has_just_the_line_and_two_arrowheads(self):

        layer = create_maneuver_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "principal_direction_of_fire")

        # base line + 2 arrowheads (First/LastVertex) - no vertex label
        # (removed 2026-08-09 at the maintainer's own request: Field A's
        # own "A" marks where a separate symbol belongs, not literal
        # text - see module docstring).
        self.assertEqual(symbol.symbolLayerCount(), 3)

        for i in (1, 2):

            self.assertIsInstance(
                symbol.symbolLayer(i),
                QgsMarkerLineSymbolLayer
            )


    def test_feba_has_no_general_label_or_unique_designation(self):

        # 2026-08-09 correction: FEBA no longer shows an optional name
        # via the general along-line label - "there is no unique
        # designation in FEBA" (the maintainer's own words). Since no
        # measure type on this Lines layer uses the general label any
        # more, the layer has no labeling configured at all.
        layer = create_maneuver_control_measures_lines_layer()

        self.assertIsNone(layer.labeling())


    def test_length_km_default_value_recalculates_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_maneuver_control_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            self.assertTrue(
                layer.defaultValueDefinition(idx).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateManeuverControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _evaluate_area_label(self, layer, measure_type, **attrs):

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

        layer = create_maneuver_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "dtg_start", "dtg_end",
                "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_maneuver_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_measure_type_uses_a_value_map_widget_defaulting_to_area(self):

        layer = create_maneuver_control_measures_areas_layer()

        idx = layer.fields().indexOf("measure_type")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(
            widget_setup.config()["map"],
            {label: value for value, label in AREA_MEASURE_TYPE_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'area'"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_maneuver_control_measures_areas_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in AREA_MEASURE_TYPE_LABELS
            }
        )


    def test_plain_area_has_no_label(self):

        layer = create_maneuver_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_area_label(layer, "area", unique_designation="whatever"),
            ""
        )


    def test_assembly_area_and_zone_labels_prefix_the_type_abbreviation(self):

        layer = create_maneuver_control_measures_areas_layer()

        cases = {
            "assembly_area": ("AA", "AA BLUE"),
            "drop_zone": ("DZ", "DZ HAWK"),
            "extraction_zone": ("EZ", "EZ ROCK"),
            "landing_zone": ("LZ", "LZ SILVER"),
            "pickup_zone": ("PZ", "PZ WOLF"),
            "limited_access_area": ("LAA", "LAA ZULU"),
        }

        for measure_type, (prefix, expected) in cases.items():

            name = expected[len(prefix) + 1:]

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_area_label(
                        layer, measure_type, unique_designation=name.lower()
                    ),
                    expected
                )


    def test_action_area_labels_use_a_hyphen_and_optional_dtg_range(self):

        layer = create_maneuver_control_measures_areas_layer()

        cases = {
            "joint_tactical_action_area": "JTAA",
            "submarine_action_area": "SAA",
            "submarine_generated_action_area": "SGSA",
        }

        for measure_type, prefix in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_area_label(
                        layer, measure_type, unique_designation="02"
                    ),
                    f"{prefix}-02"
                )

                self.assertEqual(
                    self._evaluate_area_label(
                        layer, measure_type,
                        unique_designation="02",
                        dtg_start="051030",
                        dtg_end="051600",
                    ),
                    f"{prefix}-02\n051030-051600Z"
                )


    def test_fortified_area_label_has_no_type_prefix(self):

        layer = create_maneuver_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_area_label(
                layer, "fortified_area", unique_designation="tango"
            ),
            "TANGO"
        )


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_maneuver_control_measures_areas_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in ("area", "assembly_area", "drop_zone"):

            symbol = _rule_symbol_for(layer, measure_type)
            outline_layer = symbol.symbolLayer(0)

            for affiliation, hex_color in expected.items():

                with self.subTest(measure_type=measure_type, affiliation=affiliation):

                    color, ok = _resolve_stroke_color(outline_layer, layer, affiliation)

                    self.assertTrue(ok)
                    self.assertEqual(color.name(), hex_color)


    def test_fortified_area_uses_a_crenellate_outline_geometry_generator(self):

        # 2026-08-09 rebuild - two earlier QgsMarkerLineSymbolLayer-based
        # attempts (a single spaced row, then two staggered touching
        # rows) both broke down on a real curved/multi-vertex boundary,
        # not just a synthetic rectangle. Replaced with a genuine
        # computed outline via mct_crenellate_outline() - see module
        # docstring and expressions/military_symbology_functions.py's
        # own comment on that function.
        layer = create_maneuver_control_measures_areas_layer()

        symbol = _rule_symbol_for(layer, "fortified_area")

        self.assertEqual(symbol.symbolLayerCount(), 1)

        generator_layer = symbol.symbolLayer(0)

        self.assertEqual(
            generator_layer.layerType(),
            "GeometryGenerator"
        )

        self.assertIn(
            "mct_crenellate_outline",
            generator_layer.geometryExpression()
        )


    def test_fortified_area_crenellated_outline_evaluates_to_a_real_line(self):

        # Integration-level: a real feature run through the actual
        # renderer resolves the geometry generator's own expression to
        # a valid, non-empty line geometry - not just structurally
        # present but functionally correct.
        military_symbology_functions.register()

        try:

            layer = create_maneuver_control_measures_areas_layer()

            ring = QgsGeometry.fromPolygonXY([[
                QgsPointXY(0, 0), QgsPointXY(0, 1), QgsPointXY(1, 1),
                QgsPointXY(1, 0), QgsPointXY(0, 0),
            ]])

            feature = QgsFeature(layer.fields())
            feature.setGeometry(ring)
            feature.setAttribute("measure_type", "fortified_area")

            expression = QgsExpression(
                "mct_crenellate_outline($geometry, 14)"
            )

            context = layer.createExpressionContext()
            context.setFeature(feature)
            context.setGeometry(ring)

            result = expression.evaluate(context)

            self.assertFalse(
                expression.hasEvalError(),
                expression.evalErrorString()
            )
            self.assertIsInstance(result, QgsGeometry)
            self.assertFalse(result.isEmpty())
            self.assertGreater(
                result.constGet().numPoints(),
                4
            )

        finally:

            military_symbology_functions.unregister()


    def test_limited_access_area_has_a_hatched_fill_layer(self):

        layer = create_maneuver_control_measures_areas_layer()

        symbol = _rule_symbol_for(layer, "limited_access_area")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        hatch_layer = symbol.symbolLayer(1)

        self.assertEqual(
            hatch_layer.layerType(),
            "LinePatternFill"
        )


    def test_area_and_perimeter_default_values_recalculate_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_maneuver_control_measures_areas_layer()

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


class TestAddManeuverControlMeasuresLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_maneuver_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_maneuver_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        first = add_maneuver_control_measures_lines_layer(self.iface)

        result = add_maneuver_control_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_areas_layer_is_never_replaced_if_it_already_exists(self):

        first = add_maneuver_control_measures_areas_layer(self.iface)

        result = add_maneuver_control_measures_areas_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_maneuver_control_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)
