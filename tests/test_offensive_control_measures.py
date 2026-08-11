# -*- coding: utf-8 -*-

"""
Tests for military_symbology/offensive_control_measures.py - the
Offensive Control Measures line/area/point layers (Tables H-X/H-XI,
Mini-Phase H5), styled via a QgsRuleBasedRenderer keyed on
"measure_type" (lines/areas) or milsymbol.js (points). See that
module's own docstring for what's approximated (Table H-X's own Axis
of Advance family) and what's built for real (Table H-XI's Direction
of Attack family, Infiltration Lane, and the simple lines/areas/point).

Military Cartography Tools
"""

import base64
import math
import re

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsExpressionContext,
    QgsFeature,
    QgsFontMarkerSymbolLayer,
    QgsGeometry,
    QgsGeometryGeneratorSymbolLayer,
    QgsLabelLineSettings,
    QgsMarkerLineSymbolLayer,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QPointF, Qt

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.offensive_control_measures import (
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    POINTS_LAYER_NAME,
    POINT_ENTITY_LABELS,
    add_offensive_control_measures_areas_layer,
    add_offensive_control_measures_lines_layer,
    add_offensive_control_measures_points_layer,
    create_offensive_control_measures_areas_layer,
    create_offensive_control_measures_lines_layer,
    create_offensive_control_measures_points_layer,
)


def _font_marker_layers(symbol):

    """Every QgsFontMarkerSymbolLayer nested inside symbol's own
    QgsMarkerLineSymbolLayer sub-symbols - used to find the Field T/
    Field W-W1 data-defined-Character markers regardless of their own
    index (which varies per sub-type - see module docstring)."""

    found = []

    for i in range(symbol.symbolLayerCount()):

        layer = symbol.symbolLayer(i)

        sub_symbol = layer.subSymbol() if hasattr(layer, "subSymbol") else None

        if sub_symbol is None:
            continue

        for j in range(sub_symbol.symbolLayerCount()):

            sub_layer = sub_symbol.symbolLayer(j)

            if isinstance(sub_layer, QgsFontMarkerSymbolLayer):
                found.append(sub_layer)

    return found


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


class TestCreateOffensiveControlMeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_offensive_control_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "dtg_start", "dtg_end", "length_km",
            ]
        )


    def test_is_a_line_layer(self):

        layer = create_offensive_control_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_measure_type_uses_a_value_map_widget_defaulting_to_line_of_departure(self):

        layer = create_offensive_control_measures_lines_layer()

        idx = layer.fields().indexOf("measure_type")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(
            widget_setup.config()["map"],
            {label: value for value, label in LINE_MEASURE_TYPE_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'line_of_departure'"
        )


    def test_affiliation_defaults_to_friend_not_the_shared_unspecified_default(self):

        # 2026-08-10, per the project maintainer's own observation while
        # smoke-testing Friendly Airborne: nearly every measure type on
        # this layer is an inherently friendly, own-force graphic, so
        # this layer overrides _configure_affiliation_field()'s own
        # shared cross-appendix default ("unspecified"/black) - see
        # create_offensive_control_measures_lines_layer()'s own comment.
        layer = create_offensive_control_measures_lines_layer()

        idx = layer.fields().indexOf("affiliation")

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'friend'"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_offensive_control_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in LINE_MEASURE_TYPE_LABELS
            }
        )


    def test_master_arrow_variants_use_the_non_crossed_ribbon(self):

        # 2026-08-10, per the project maintainer's own explicit
        # instruction ("this arrow is similar except the lines do not
        # crossover, further the width of the shaft is constant -
        # render the arrow for now"): Main Attack moved off the old
        # doubled-outline approximation onto the real ribbon
        # construction too, but with `crossed=false` (see
        # mct_axis_of_advance_ribbon()'s own docstring), later finalised
        # (20%-wider double-lined arrowhead, Field T on the shaft at 1/3
        # distance with horizontal text, no DTG) and named "the master
        # arrow" by the maintainer. 2026-08-11: Supporting Attack moved
        # off its own doubled-outline-free approximation onto the SAME
        # construction, MINUS the double-lined arrowhead ("main attack
        # requires the inner chevron, supporting attack does not
        # require it" - the maintainer's own words, after an earlier
        # over-broad edit removed it from both) - see
        # _MASTER_ARROW_VARIANTS's own comment and
        # _DOUBLE_LINED_ARROWHEAD_VARIANTS's own comment for the one
        # part that's genuinely NOT shared between the two. Axis of
        # Advance - Enemy joined the same way 2026-08-11 ("just use the
        # master arrow and default colour to red" - see
        # test_enemy_variants_render_red_regardless_of_affiliation for
        # the colour side of that).
        layer = create_offensive_control_measures_lines_layer()

        expected_ribbon_expression_by_type = {
            "axis_of_advance_main_attack": "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2, true)",
            "axis_of_advance_supporting_attack": "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2)",
            "axis_of_advance_enemy": "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2)",
        }

        for measure_type, expected_expression in expected_ribbon_expression_by_type.items():

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 2)

                ribbon_layer = symbol.symbolLayer(0)

                self.assertIsInstance(
                    ribbon_layer,
                    QgsGeometryGeneratorSymbolLayer
                )

                self.assertEqual(
                    ribbon_layer.geometryExpression(),
                    expected_expression
                )

                label_layer = symbol.symbolLayer(1)

                self.assertIsInstance(
                    label_layer,
                    QgsGeometryGeneratorSymbolLayer
                )

                self.assertEqual(
                    label_layer.symbolType(),
                    Qgis.SymbolType.Marker
                )

                self.assertIn(
                    "line_interpolate_point",
                    label_layer.geometryExpression()
                )

                label_symbol = label_layer.subSymbol()

                self.assertIsInstance(
                    label_symbol.symbolLayer(0),
                    QgsFontMarkerSymbolLayer
                )

                # No QgsMarkerLineSymbolLayer at all now - Field T no
                # longer rotates with the line, and Field W-W1 is gone.
                marker_line_layers = [
                    symbol.symbolLayer(i)
                    for i in range(symbol.symbolLayerCount())
                    if isinstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
                ]

                self.assertEqual(len(marker_line_layers), 0)


    def test_main_attacks_arrowhead_is_20_percent_wider_than_its_shaft(self):

        # 2026-08-10, per the project maintainer's own explicit
        # instruction ("the arrowhead is of the same width as the
        # shaft, increase the arrowhead width by 20%"). Compares the
        # shaft's own width (the perpendicular distance between the two
        # edges' own FIRST points, at Point 1 - unaffected by
        # `arrow_width_ratio`) against the arrowhead's own base width
        # (the distance between its two back corners) - the latter
        # should be exactly 1.2x the former.
        military_symbology_functions.register()

        try:

            feature = QgsFeature()
            feature.setGeometry(
                QgsGeometry.fromPolylineXY([
                    QgsPointXY(0, 0), QgsPointXY(30, 70), QgsPointXY(90, 85),
                ])
            )

            expression = QgsExpression(
                "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2)"
            )

            context = QgsExpressionContext()
            context.setFeature(feature)

            result = expression.evaluate(context)

            self.assertFalse(expression.hasEvalError(), expression.evalErrorString())

            left_edge = result.constGet().geometryN(0)
            right_edge = result.constGet().geometryN(1)
            arrowhead = result.constGet().geometryN(2)

            shaft_width = left_edge.pointN(0).distance(right_edge.pointN(0))
            arrowhead_base_width = arrowhead.pointN(0).distance(arrowhead.pointN(2))

            self.assertAlmostEqual(
                arrowhead_base_width, shaft_width * 1.2, places=6
            )

        finally:

            military_symbology_functions.unregister()


    def test_non_crossed_ribbon_edges_terminate_at_the_arrowheads_own_corners(self):

        # Direct coverage of mct_axis_of_advance_ribbon()'s own
        # `crossed=false` branch - the geometry math itself, independent
        # of how the symbol layer wires it up. Each edge's own LAST
        # point should be exactly the arrowhead's own corner on the
        # SAME side (corner_left for the left edge, corner_right for
        # the right edge) - the opposite of the crossed variant, where
        # each edge ends up on the OPPOSITE side's attachment point.
        # With `arrow_width_ratio=1.2` this now happens via an extra
        # straight gap-closing segment (the shaft's own narrower corner
        # first, then out to the arrowhead's own wider one) rather than
        # landing there directly, but the edge's own LAST point should
        # still be exactly the arrowhead's own corner either way.
        military_symbology_functions.register()

        try:

            feature = QgsFeature()
            feature.setGeometry(
                QgsGeometry.fromPolylineXY([
                    QgsPointXY(0, 0), QgsPointXY(30, 70), QgsPointXY(90, 85),
                ])
            )

            expression = QgsExpression(
                "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2)"
            )

            context = QgsExpressionContext()
            context.setFeature(feature)

            result = expression.evaluate(context)

            self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
            self.assertEqual(result.wkbType(), QgsWkbTypes.MultiLineString)
            self.assertEqual(result.constGet().numGeometries(), 3)

            left_edge = result.constGet().geometryN(0)
            right_edge = result.constGet().geometryN(1)
            arrowhead = result.constGet().geometryN(2)

            arrowhead_corner_left = arrowhead.pointN(0)
            arrowhead_corner_right = arrowhead.pointN(2)

            left_edge_end = left_edge.pointN(left_edge.numPoints() - 1)
            right_edge_end = right_edge.pointN(right_edge.numPoints() - 1)

            self.assertAlmostEqual(
                left_edge_end.distance(arrowhead_corner_left), 0, places=6
            )
            self.assertAlmostEqual(
                right_edge_end.distance(arrowhead_corner_right), 0, places=6
            )

        finally:

            military_symbology_functions.unregister()


    def test_double_lined_arrowhead_adds_a_fourth_inset_chevron_piece(self):

        # 2026-08-10, per the project maintainer's own explicit
        # instruction ("add another line connecting the two edges of
        # the shaft near the triangle following the shape of the
        # triangle keeping the same distance - in effect the arrow tip
        # is double lined"), Main Attack's own only (see
        # _DOUBLE_LINED_ARROWHEAD_VARIANTS's own comment in
        # offensive_control_measures.py for why Supporting Attack does
        # NOT get this despite otherwise replicating the master arrow).
        # `double_lined_arrowhead=true` should add a 4th piece (the
        # inner chevron) whose own two base points are EXACTLY
        # `shaft_corner_left`/`shaft_corner_right` - "touching the tip
        # of the arrow shaft, where the small line joining the triangle
        # begins", the maintainer's own correction after a first
        # attempt placed them further back along the shaft's own long
        # straight run instead - and whose own middle point (the inner
        # tip) is set back from the real tip - a true constant-distance
        # parallel offset, not a scaled-down copy (which would touch
        # the real tip with a zero gap instead).
        military_symbology_functions.register()

        try:

            feature = QgsFeature()
            feature.setGeometry(
                QgsGeometry.fromPolylineXY([
                    QgsPointXY(0, 0), QgsPointXY(30, 70), QgsPointXY(90, 85),
                ])
            )

            expression = QgsExpression(
                "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2, true)"
            )

            context = QgsExpressionContext()
            context.setFeature(feature)

            result = expression.evaluate(context)

            self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
            self.assertEqual(result.wkbType(), QgsWkbTypes.MultiLineString)
            self.assertEqual(result.constGet().numGeometries(), 4)

            left_edge = QgsGeometry(result.constGet().geometryN(0).clone())
            right_edge = QgsGeometry(result.constGet().geometryN(1).clone())
            arrowhead = result.constGet().geometryN(2)
            inner_chevron = result.constGet().geometryN(3)

            self.assertEqual(inner_chevron.numPoints(), 3)

            inner_base_left = inner_chevron.pointN(0)
            inner_tip = inner_chevron.pointN(1)
            inner_base_right = inner_chevron.pointN(2)

            # The inner chevron's own base points land on the real
            # shaft edges (within the polyline's own bounding
            # tolerance), not just somewhere near them.
            self.assertAlmostEqual(
                QgsGeometry.fromPointXY(QgsPointXY(inner_base_left)).distance(left_edge),
                0, places=4
            )
            self.assertAlmostEqual(
                QgsGeometry.fromPointXY(QgsPointXY(inner_base_right)).distance(right_edge),
                0, places=4
            )

            # More precisely: they're exactly the shaft's own corner
            # point (second-to-last vertex of each edge, right before
            # the short gap-closing segment to the arrowhead's own
            # wider corner) - not merely somewhere else on the edge.
            shaft_corner_left = left_edge.constGet().pointN(left_edge.constGet().numPoints() - 2)
            shaft_corner_right = right_edge.constGet().pointN(right_edge.constGet().numPoints() - 2)

            self.assertAlmostEqual(
                inner_base_left.distance(shaft_corner_left), 0, places=6
            )
            self.assertAlmostEqual(
                inner_base_right.distance(shaft_corner_right), 0, places=6
            )

            # The inner tip is set back from the real tip along the
            # centreline, not coincident with it.
            arrowhead_tip = arrowhead.pointN(1)
            self.assertGreater(inner_tip.distance(arrowhead_tip), 0)

            # 2026-08-11 correction: the inner chevron's own two edges
            # must be truly PARALLEL to the real arrowhead's own edges
            # (same azimuth), not merely touching the shaft's own
            # corner point at some other angle - the maintainer's own
            # direct observation ("the inner chevron is slanting
            # slightly with respect to the main triangle") after an
            # earlier version anchored the base point but kept an
            # independently-chosen offset distance/direction instead.
            arrowhead_corner_left = arrowhead.pointN(0)
            arrowhead_corner_right = arrowhead.pointN(2)

            real_az_left = math.atan2(
                arrowhead_tip.x() - arrowhead_corner_left.x(),
                arrowhead_tip.y() - arrowhead_corner_left.y(),
            )
            inner_az_left = math.atan2(
                inner_tip.x() - inner_base_left.x(),
                inner_tip.y() - inner_base_left.y(),
            )

            real_az_right = math.atan2(
                arrowhead_tip.x() - arrowhead_corner_right.x(),
                arrowhead_tip.y() - arrowhead_corner_right.y(),
            )
            inner_az_right = math.atan2(
                inner_tip.x() - inner_base_right.x(),
                inner_tip.y() - inner_base_right.y(),
            )

            self.assertAlmostEqual(real_az_left, inner_az_left, places=6)
            self.assertAlmostEqual(real_az_right, inner_az_right, places=6)

        finally:

            military_symbology_functions.unregister()


    def test_feint_has_the_master_arrow_base_plus_a_dashed_outer_chevron(self):

        # 2026-08-11, per the project maintainer's own explicit
        # instruction ("use the arrow and unique identification of
        # supporting attack as the base, now add an outer chevron,
        # outside the arrowhead, made of dashed line with adequate gap
        # between the arrowhead and the new outer chevron"). Feint
        # should have the SAME 2-layer master arrow base as Supporting
        # Attack (ribbon + horizontal Field T label, no double-lined
        # arrowhead - see _DOUBLE_LINED_ARROWHEAD_VARIANTS's own
        # comment), plus a THIRD layer: a separate geometry-generator
        # line layer for the outer chevron, fixed dashed regardless of
        # status.
        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "axis_of_advance_feint")

        self.assertEqual(symbol.symbolLayerCount(), 3)

        ribbon_layer = symbol.symbolLayer(0)

        self.assertEqual(
            ribbon_layer.geometryExpression(),
            "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2)"
        )

        outer_chevron_layer = symbol.symbolLayer(2)

        self.assertIsInstance(
            outer_chevron_layer,
            QgsGeometryGeneratorSymbolLayer
        )

        self.assertEqual(
            outer_chevron_layer.symbolType(),
            Qgis.SymbolType.Line
        )

        self.assertIn(
            "mct_axis_of_advance_outer_chevron",
            outer_chevron_layer.geometryExpression()
        )

        outer_chevron_symbol = outer_chevron_layer.subSymbol()
        outer_chevron_outline = outer_chevron_symbol.symbolLayer(0)

        self.assertEqual(
            outer_chevron_outline.penStyle(),
            Qt.PenStyle.DashLine
        )


    def test_outer_chevron_function_produces_a_chevron_outside_the_arrowhead(self):

        # Direct coverage of expressions/military_symbology_functions.py's
        # own mct_axis_of_advance_outer_chevron() - the geometry math
        # itself, independent of how the symbol layer wires it up. Each
        # of its own 3 points should sit strictly farther from the
        # centreline than the real arrowhead's own corresponding corner
        # (i.e. genuinely OUTSIDE, not overlapping or inside it).
        military_symbology_functions.register()

        try:

            feature = QgsFeature()
            feature.setGeometry(
                QgsGeometry.fromPolylineXY([
                    QgsPointXY(0, 0), QgsPointXY(30, 70), QgsPointXY(90, 85),
                ])
            )

            context = QgsExpressionContext()
            context.setFeature(feature)

            ribbon_expression = QgsExpression(
                "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2)"
            )
            ribbon = ribbon_expression.evaluate(context)

            self.assertFalse(
                ribbon_expression.hasEvalError(),
                ribbon_expression.evalErrorString()
            )

            arrowhead = ribbon.constGet().geometryN(2)
            arrowhead_corner_left = arrowhead.pointN(0)
            arrowhead_corner_right = arrowhead.pointN(2)

            outer_expression = QgsExpression(
                "mct_axis_of_advance_outer_chevron($geometry, 0.08, 1.2, 0.8)"
            )
            outer = outer_expression.evaluate(context)

            self.assertFalse(
                outer_expression.hasEvalError(),
                outer_expression.evalErrorString()
            )
            self.assertEqual(outer.wkbType(), QgsWkbTypes.LineString)
            self.assertEqual(outer.constGet().numPoints(), 3)

            outer_left = outer.constGet().pointN(0)
            outer_right = outer.constGet().pointN(2)

            self.assertGreater(
                outer_left.distance(arrowhead_corner_left), 0
            )
            self.assertGreater(
                outer_right.distance(arrowhead_corner_right), 0
            )

        finally:

            military_symbology_functions.unregister()


    def test_airborne_and_aviation_use_the_real_ribbon_construction(self):

        # 2026-08-10: "Friendly Airborne" and "Friendly Aviation" split
        # from one combined dropdown entry into two (they share a single
        # SIDC, 151401, but are "two different tasks" per the project
        # maintainer's own request) and moved to a real geometry-
        # generator ribbon construction (mct_axis_of_advance_ribbon())
        # rather than the rest of the Axis of Advance family's own
        # single-thick-line approximation - see module docstring and
        # _axis_of_advance_ribbon_symbol()'s own comment.
        layer = create_offensive_control_measures_lines_layer()

        # Both variants carry the same layer count - a unit-context icon
        # at the shaft's own start (see _unit_context_icon_layer()),
        # Infantry+Airborne-modifier for Airborne, Aviation Rotary Wing
        # (no modifier) for Aviation, added to Airborne first then
        # brought over to Aviation 2026-08-10 per the maintainer's own
        # explicit request. Field W-W1 (DTG) was tried, then dropped
        # from this and every other Axis of Advance/Direction of Attack
        # variant - see module docstring's 2026-08-10 entry.
        expected_layer_count_by_type = {
            "axis_of_advance_airborne": 3,
            "axis_of_advance_aviation": 3,
        }

        for measure_type, expected_layer_count in expected_layer_count_by_type.items():

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), expected_layer_count)

                generator_layer = symbol.symbolLayer(0)

                self.assertIsInstance(
                    generator_layer,
                    QgsGeometryGeneratorSymbolLayer
                )

                self.assertEqual(
                    generator_layer.geometryExpression(),
                    "mct_axis_of_advance_ribbon($geometry)"
                )

                font_layers = _font_marker_layers(symbol)

                self.assertEqual(len(font_layers), 1)


    def test_airborne_has_a_unit_context_icon_at_the_shafts_own_start(self):

        # 2026-08-10, per the project maintainer's own explicit layout
        # instruction: a real Infantry SVG icon (see
        # _unit_context_icon_layer()'s own docstring for why it's the
        # real milsymbol.js render, not a hand-built approximation) plus
        # the Airborne modifier glyph at Point 1 (the shaft's own
        # start), with Field T moved to sit near it too (rather than its
        # own usual place near the tip - see _axis_of_advance_ribbon_
        # symbol()'s own comment). Field W-W1 (DTG) was tried at this
        # same spot, then dropped entirely - see module docstring's
        # 2026-08-10 entry.
        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "axis_of_advance_airborne")

        marker_line_layers = [
            symbol.symbolLayer(i)
            for i in range(symbol.symbolLayerCount())
            if isinstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
        ]

        icon_layers = [
            layer for layer in marker_line_layers
            if layer.placements() == Qgis.MarkerLinePlacement.FirstVertex
            and layer.subSymbol().symbolLayerCount() == 3
        ]

        self.assertEqual(len(icon_layers), 1)

        # 2026-08-12: "the symbol at the base of the shaft... should not
        # be rotated but be straight" - the project maintainer's own
        # words. Unlike Field T's own end marker (still rotate-with-
        # line), this icon now stays upright regardless of the arrow's
        # own direction.
        self.assertFalse(icon_layers[0].rotateSymbols())

        icon_symbol = icon_layers[0].subSymbol()

        # 2026-08-12 follow-up: the fixed 90-degree correction was only
        # ever right for the rotate-with-line case - "all three icons
        # are 90 deg off, rotate them counter clockwise by 90 deg" once
        # rotate=False landed, confirmed by render. 0 is that correction
        # for the non-rotating case.
        self.assertEqual(icon_symbol.symbolLayer(0).angle(), 0)

        self.assertIsInstance(
            icon_symbol.symbolLayer(0),
            QgsSvgMarkerSymbolLayer
        )

        self.assertIn(
            "'infantry'",
            icon_symbol.symbolLayer(0).dataDefinedProperties().property(
                QgsSymbolLayer.Property.Name
            ).expressionString()
        )

        for i in (1, 2):

            self.assertEqual(
                icon_symbol.symbolLayer(i).shape(),
                QgsSimpleMarkerSymbolLayerBase.Shape.HalfArc
            )

        # Field T is anchored at FirstVertex now (not LastVertex, its
        # usual placement for every other Axis of Advance variant).
        text_layers = [
            layer for layer in marker_line_layers
            if layer.placements() == Qgis.MarkerLinePlacement.FirstVertex
            and layer.subSymbol().symbolLayerCount() == 1
            and isinstance(layer.subSymbol().symbolLayer(0), QgsFontMarkerSymbolLayer)
        ]

        self.assertEqual(len(text_layers), 1)


    def test_aviation_has_a_rotary_wing_context_icon_with_no_airborne_modifier(self):

        # 2026-08-10, per the project maintainer's own explicit request:
        # brought Friendly Aviation over to the same unit-context-icon +
        # Field T layout Friendly Airborne got first, but swapping the
        # icon's own entity to Aviation Rotary Wing (sidc.py's own
        # ENTITIES["ground_unit"]["aviation_rotary_wing"]) and dropping
        # the Airborne modifier's own humps entirely - the Aviation
        # Rotary Wing icon's own rotor-blade glyph already identifies
        # the unit type on its own ("remove the infantry symbol and the
        # 'm'... replace with the aviation symbol... rest remains same").
        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "axis_of_advance_aviation")

        marker_line_layers = [
            symbol.symbolLayer(i)
            for i in range(symbol.symbolLayerCount())
            if isinstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
        ]

        icon_layers = [
            layer for layer in marker_line_layers
            if layer.placements() == Qgis.MarkerLinePlacement.FirstVertex
            and layer.subSymbol().symbolLayerCount() == 1
            and isinstance(layer.subSymbol().symbolLayer(0), QgsSvgMarkerSymbolLayer)
        ]

        self.assertEqual(len(icon_layers), 1)

        # 2026-08-12: same "should not be rotated but be straight"
        # correction as Friendly Airborne's own icon above.
        self.assertFalse(icon_layers[0].rotateSymbols())

        icon_symbol = icon_layers[0].subSymbol()

        # See test_airborne_has_a_unit_context_icon_at_the_shafts_own_
        # start()'s own comment - the fixed angle flips to 0 once the
        # icon stops rotating with the line.
        self.assertEqual(icon_symbol.symbolLayer(0).angle(), 0)

        self.assertIn(
            "'aviation_rotary_wing'",
            icon_symbol.symbolLayer(0).dataDefinedProperties().property(
                QgsSymbolLayer.Property.Name
            ).expressionString()
        )

        text_layers = [
            layer for layer in marker_line_layers
            if layer.placements() == Qgis.MarkerLinePlacement.FirstVertex
            and layer.subSymbol().symbolLayerCount() == 1
            and isinstance(layer.subSymbol().symbolLayer(0), QgsFontMarkerSymbolLayer)
        ]

        self.assertEqual(len(text_layers), 1)


    def test_attack_helicopter_has_the_rotary_wing_icon_and_crossing_glyph(self):

        # 2026-08-10, per the project maintainer's own explicit request:
        # Attack Helicopter (151402) moved off the approximated single-
        # thick-line-plus-crossbar construction onto the same real
        # ribbon construction Airborne/Aviation already use, reusing
        # Aviation's own Aviation Rotary Wing base icon ("base of the
        # shaft remains same - aviation rotary wing icon") and adding
        # its own crossing-point glyph - see
        # _attack_helicopter_direction_glyph_layer()'s own docstring for
        # why it's a fixed-content inline SVG (exact path data supplied
        # by the maintainer, not derived) rather than a hand-built
        # QGIS-native shape.
        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "axis_of_advance_attack_helicopter")

        self.assertEqual(symbol.symbolLayerCount(), 4)

        generator_layers = [
            symbol.symbolLayer(i)
            for i in range(symbol.symbolLayerCount())
            if isinstance(symbol.symbolLayer(i), QgsGeometryGeneratorSymbolLayer)
        ]

        self.assertEqual(len(generator_layers), 2)

        ribbon_layer = generator_layers[0]

        self.assertEqual(
            ribbon_layer.geometryExpression(),
            "mct_axis_of_advance_ribbon($geometry)"
        )

        glyph_layer = generator_layers[1]

        self.assertEqual(
            glyph_layer.symbolType(),
            Qgis.SymbolType.Marker
        )

        self.assertEqual(
            glyph_layer.geometryExpression(),
            "mct_axis_of_advance_crossing_point($geometry)"
        )

        glyph_symbol = glyph_layer.subSymbol()

        self.assertIsInstance(
            glyph_symbol.symbolLayer(0),
            QgsSvgMarkerSymbolLayer
        )

        marker_line_layers = [
            symbol.symbolLayer(i)
            for i in range(symbol.symbolLayerCount())
            if isinstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
        ]

        icon_layers = [
            layer for layer in marker_line_layers
            if layer.placements() == Qgis.MarkerLinePlacement.FirstVertex
            and layer.subSymbol().symbolLayerCount() == 1
            and isinstance(layer.subSymbol().symbolLayer(0), QgsSvgMarkerSymbolLayer)
        ]

        self.assertEqual(len(icon_layers), 1)

        # 2026-08-12: "same is the case for... attack helicopter" - the
        # project maintainer's own words, extending the "should not be
        # rotated but be straight" correction from Airborne/Aviation to
        # this base icon too. The crossing-point glyph above was already
        # fixed-orientation by construction and is unaffected.
        self.assertFalse(icon_layers[0].rotateSymbols())

        base_icon_symbol = icon_layers[0].subSymbol()

        # See test_airborne_has_a_unit_context_icon_at_the_shafts_own_
        # start()'s own comment - the fixed angle flips to 0 once the
        # icon stops rotating with the line.
        self.assertEqual(base_icon_symbol.symbolLayer(0).angle(), 0)

        self.assertIn(
            "'aviation_rotary_wing'",
            base_icon_symbol.symbolLayer(0).dataDefinedProperties().property(
                QgsSymbolLayer.Property.Name
            ).expressionString()
        )

        text_layers = [
            layer for layer in marker_line_layers
            if layer.placements() == Qgis.MarkerLinePlacement.FirstVertex
            and layer.subSymbol().symbolLayerCount() == 1
            and isinstance(layer.subSymbol().symbolLayer(0), QgsFontMarkerSymbolLayer)
        ]

        self.assertEqual(len(text_layers), 1)


    def test_ribbon_expression_function_produces_a_three_piece_outline(self):

        # Direct coverage of expressions/military_symbology_functions.py's
        # own mct_axis_of_advance_ribbon() - the geometry math itself,
        # independent of how the symbol layer wires it up.
        military_symbology_functions.register()

        try:

            feature = QgsFeature()
            feature.setGeometry(
                QgsGeometry.fromPolylineXY([
                    QgsPointXY(0, 0), QgsPointXY(30, 70), QgsPointXY(90, 85),
                ])
            )

            expression = QgsExpression("mct_axis_of_advance_ribbon($geometry)")

            context = QgsExpressionContext()
            context.setFeature(feature)

            result = expression.evaluate(context)

            self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
            self.assertEqual(result.wkbType(), QgsWkbTypes.MultiLineString)
            self.assertEqual(result.constGet().numGeometries(), 3)

        finally:

            military_symbology_functions.unregister()


    def test_crossing_point_function_lies_on_both_ribbon_edges(self):

        # 2026-08-10, per the project maintainer's own correction: an
        # earlier version of Attack Helicopter's own crossing-point
        # glyph used a plain Point-2/Point-3 midpoint, which the
        # maintainer found consistently placed the glyph "slightly
        # right and above the point of intersection" across several
        # different arrow geometries - a systematic offset, not a
        # fluke, because the ribbon's own real crossing point is a
        # function of `width`/`attach_ratio`, not simply the arithmetic
        # midpoint. This checks the REAL fix directly: the point
        # mct_axis_of_advance_crossing_point() returns should lie
        # (near-)exactly ON both of the ribbon's own two edges (not
        # just somewhere near them), for more than one geometry, so a
        # regression back to the midpoint approximation would fail this
        # even though it'd still return "a point somewhere in the
        # middle".
        military_symbology_functions.register()

        try:

            for points in (
                [QgsPointXY(0, 0), QgsPointXY(30, 70), QgsPointXY(90, 85)],
                [QgsPointXY(0, 0), QgsPointXY(50, 20), QgsPointXY(120, 90)],
            ):

                with self.subTest(points=points):

                    feature = QgsFeature()
                    feature.setGeometry(QgsGeometry.fromPolylineXY(points))

                    context = QgsExpressionContext()
                    context.setFeature(feature)

                    ribbon_expression = QgsExpression(
                        "mct_axis_of_advance_ribbon($geometry)"
                    )
                    ribbon = ribbon_expression.evaluate(context)

                    self.assertFalse(
                        ribbon_expression.hasEvalError(),
                        ribbon_expression.evalErrorString()
                    )

                    left_edge = QgsGeometry(ribbon.constGet().geometryN(0).clone())
                    right_edge = QgsGeometry(ribbon.constGet().geometryN(1).clone())

                    crossing_expression = QgsExpression(
                        "mct_axis_of_advance_crossing_point($geometry)"
                    )
                    crossing = crossing_expression.evaluate(context)

                    self.assertFalse(
                        crossing_expression.hasEvalError(),
                        crossing_expression.evalErrorString()
                    )

                    self.assertLess(crossing.distance(left_edge), 1e-6)
                    self.assertLess(crossing.distance(right_edge), 1e-6)

        finally:

            military_symbology_functions.unregister()


    def test_ribbon_arrowhead_is_equilateral(self):

        # 2026-08-10, per the project maintainer's own explicit
        # correction ("make it equilateral instead of isosceles") -
        # the arrowhead's own height is derived from its own base
        # width (width * sqrt(3)) rather than an independent ratio, so
        # this should hold for any width_ratio, not just the default.
        military_symbology_functions.register()

        try:

            feature = QgsFeature()
            feature.setGeometry(
                QgsGeometry.fromPolylineXY([
                    QgsPointXY(0, 0), QgsPointXY(30, 70), QgsPointXY(90, 85),
                ])
            )

            expression = QgsExpression("mct_axis_of_advance_ribbon($geometry)")

            context = QgsExpressionContext()
            context.setFeature(feature)

            result = expression.evaluate(context)

            self.assertFalse(expression.hasEvalError(), expression.evalErrorString())

            arrowhead = result.constGet().geometryN(2)

            corner_left = arrowhead.pointN(0)
            tip = arrowhead.pointN(1)
            corner_right = arrowhead.pointN(2)

            side_a = corner_left.distance(tip)
            side_b = tip.distance(corner_right)
            side_c = corner_right.distance(corner_left)

            self.assertAlmostEqual(side_a, side_b, places=6)
            self.assertAlmostEqual(side_b, side_c, places=6)

        finally:

            military_symbology_functions.unregister()


    def test_direction_of_attack_variants_are_a_thin_line_with_an_open_chevron(self):

        # 2026-08-10: every variant also carries Field T/Field W-W1, and
        # Friendly Aviation carries two more layers of its own (the
        # bowtie glyph and its own unit icon) - see module docstring.
        # 2026-08-11: Friendly Aviation's own Field T moved off its font-
        # marker layer onto a real, masked PAL label (see
        # create_offensive_control_measures_lines_layer()'s own
        # labelling call) - so it has only ONE font-marker layer left
        # (Field W-W1/DTG), unlike every other variant's two.
        layer = create_offensive_control_measures_lines_layer()

        # 2026-08-12: Field W-W1 (DTG) split into two separate marker
        # layers, one per line (see _DTG_START_LINE_EXPRESSION's own
        # comment) - one more layer/font-marker per variant than before.
        # Friendly Aviation also gained a separate decorative stub layer
        # (_direction_of_attack_bowtie_stub_layer()) the same day.
        # 2026-08-12: Main Attack's own Field T moved off the shared
        # font-marker layer entirely (onto a masked PAL label, like
        # Friendly Aviation's own) - one fewer symbol/font-marker layer
        # than the other still-untouched variants. Supporting Attack got
        # the same treatment the same day ("start with the friendly
        # aviation symbol, drop the milsymbol, horizontal stub and bow
        # tie") - masked PAL Field T, no unit icon/bowtie/stub. Enemy got
        # the same treatment again the same day ("start with the
        # supporting attack, default the colour to red, that's all"),
        # and Friendly Ground Axis once more ("replicate the supporting
        # attack symbol for friendly ground axis, that's all"). Feint
        # got the same base plus one extra layer - its own dashed outer
        # chevron (_direction_of_attack_feint_outer_chevron_layer()).
        # Main Attack was then rebuilt the same day on Feint's own
        # chevron technique ("start with the symbol for feint; change
        # the outer chevron to solid line, add line segments to join
        # ends of both the stubs") - it now goes through the SAME real
        # single-chevron construction as every other variant, plus its
        # own solid outer chevron+struts layer
        # (_direction_of_attack_main_attack_outer_chevron_layer()) - so
        # Main Attack and Feint are both 5 base layers, everyone else 4.
        base_layer_count_by_type = {
            "direction_of_attack_aviation": 7,
            "direction_of_attack_main": 5,
            "direction_of_attack_supporting": 4,
            "direction_of_attack_ground_axis": 4,
            "direction_of_attack_feint": 5,
            "direction_of_attack_enemy": 4,
        }

        expected_font_layer_count_by_type = {
            "direction_of_attack_aviation": 2,
            "direction_of_attack_main": 2,
            "direction_of_attack_supporting": 2,
            "direction_of_attack_ground_axis": 2,
            "direction_of_attack_feint": 2,
            "direction_of_attack_enemy": 2,
        }

        for measure_type, expected_layer_count in base_layer_count_by_type.items():

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), expected_layer_count)

                base_line = symbol.symbolLayer(0)

                self.assertLess(base_line.width(), 1.0)

                chevron_layer = symbol.symbolLayer(1)
                self.assertIsInstance(chevron_layer, QgsMarkerLineSymbolLayer)

                font_layers = _font_marker_layers(symbol)

                self.assertEqual(
                    len(font_layers),
                    expected_font_layer_count_by_type[measure_type]
                )


    def test_direction_of_attack_aviation_has_a_bowtie_glyph(self):

        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "direction_of_attack_aviation")

        marker_line_layers = [
            symbol.symbolLayer(i)
            for i in range(symbol.symbolLayerCount())
            if isinstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
        ]

        bowtie_layers = [
            layer for layer in marker_line_layers
            if layer.subSymbol().symbolLayerCount() == 2
            and all(
                isinstance(layer.subSymbol().symbolLayer(i), QgsSimpleMarkerSymbolLayer)
                for i in range(2)
            )
        ]

        self.assertEqual(len(bowtie_layers), 1)

        # 2026-08-12: "it is filled instead of being an outline only" -
        # the maintainer's own words, comparing against the standard's
        # own hollow bowtie. Both triangles must be transparent-filled,
        # stroke-only now.
        for i in range(2):

            triangle_layer = bowtie_layers[0].subSymbol().symbolLayer(i)
            self.assertEqual(triangle_layer.color(), QColor(0, 0, 0, 0))


    def test_direction_of_attack_aviation_has_a_unit_icon_before_the_origin(self):

        # 2026-08-11: "the aviation symbol should be before the line
        # origin, and should be bounded in a rectangle" - the real
        # "Aviation - Fixed Wing" Ground Unit SIDC icon (already
        # rectangle-framed by construction), offset off the FirstVertex
        # anchor rather than sitting on top of it like the bowtie does.
        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "direction_of_attack_aviation")

        marker_line_layers = [
            symbol.symbolLayer(i)
            for i in range(symbol.symbolLayerCount())
            if isinstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
        ]

        icon_layers = [
            layer for layer in marker_line_layers
            if layer.subSymbol().symbolLayerCount() >= 1
            and isinstance(layer.subSymbol().symbolLayer(0), QgsSvgMarkerSymbolLayer)
        ]

        self.assertEqual(len(icon_layers), 1)

        icon_frame_layer = icon_layers[0].subSymbol().symbolLayer(0)

        self.assertEqual(icon_layers[0].placements(), Qgis.MarkerLinePlacement.FirstVertex)
        self.assertNotEqual(icon_frame_layer.offset(), QPointF(0, 0))

        # 2026-08-12 same-day follow-up: "like axis of advance, the
        # symbol for aviation should be straight" - the maintainer's own
        # words, extending the earlier Axis of Advance "should not be
        # rotated" correction to this icon too (it wasn't part of that
        # first round - see test_airborne_has_a_unit_context_icon_at_
        # the_shafts_own_start()'s own comment for that original fix).
        self.assertFalse(icon_layers[0].rotateSymbols())
        self.assertEqual(icon_frame_layer.angle(), 0)

        # No other Direction of Attack variant gets this icon. Filtered
        # by FirstVertex placement specifically (not just "any SVG
        # marker") - Main Attack's own outer chevron
        # (_direction_of_attack_main_attack_outer_chevron_layer()) and
        # Feint's own (_direction_of_attack_feint_outer_chevron_layer())
        # are ALSO SVG markers, but at LastVertex, not this icon's own
        # FirstVertex.
        for measure_type in (
            "direction_of_attack_main",
            "direction_of_attack_supporting",
            "direction_of_attack_ground_axis",
            "direction_of_attack_feint",
            "direction_of_attack_enemy",
        ):

            with self.subTest(measure_type=measure_type):

                other_symbol = _rule_symbol_for(layer, measure_type)

                other_icon_layers = [
                    other_symbol.symbolLayer(i)
                    for i in range(other_symbol.symbolLayerCount())
                    if isinstance(other_symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
                    and other_symbol.symbolLayer(i).placements() == Qgis.MarkerLinePlacement.FirstVertex
                    and other_symbol.symbolLayer(i).subSymbol().symbolLayerCount() >= 1
                    and isinstance(
                        other_symbol.symbolLayer(i).subSymbol().symbolLayer(0),
                        QgsSvgMarkerSymbolLayer
                    )
                ]

                self.assertEqual(len(other_icon_layers), 0)


    def test_direction_of_attack_aviation_designation_is_a_masked_pal_label(self):

        # 2026-08-11: "the unique designation should be just behind the
        # arrow head with suitable masking, in line with the arrow
        # shaft" - real masking needs a genuine PAL label (see
        # _control_measure_shared.py's own _build_pal_layer_settings()
        # comment), unlike every other Direction of Attack/Axis of
        # Advance variant's own font-marker Field T.
        #
        # 2026-08-12: this layer's own labelling moved to
        # QgsRuleBasedLabeling (Main Attack's own Field T got the same
        # masked-PAL treatment the same day - see
        # test_direction_of_attack_main_attack_designation_is_a_masked_
        # pal_label()) - the aviation rule is still the FIRST child.
        layer = create_offensive_control_measures_lines_layer()

        labeling = layer.labeling()
        settings = labeling.rootRule().children()[0].settings()

        self.assertTrue(settings.isExpression)
        self.assertIn("direction_of_attack_aviation", settings.fieldName)
        self.assertEqual(settings.placement, Qgis.LabelPlacement.Line)

        # `text_format` is held in its own variable, not chained
        # straight into `.mask()` - QgsPalLayerSettings.format() returns
        # a QgsTextFormat BY VALUE, and a temporary's own C++ object can
        # be garbage-collected out from under a value later read off of
        # it (mask()) if nothing keeps the temporary itself alive - the
        # same "wrapped C/C++ object has been deleted" class of bug this
        # project's own test suite has hit before (see module docstring/
        # roadmap's own 2026-08-11 entries), confirmed here directly: the
        # chained form segfaulted the whole interpreter, not merely
        # raised a Python exception.
        text_format = settings.format()
        mask_settings = text_format.mask()
        self.assertTrue(mask_settings.enabled())

        masked_ids = [
            ref.symbolLayerIdV2() for ref in mask_settings.maskedSymbolLayers()
        ]
        self.assertIn("direction_of_attack_aviation_line", masked_ids)

        line_settings = settings.lineSettings()
        self.assertEqual(
            line_settings.anchorType(),
            QgsLabelLineSettings.AnchorType.Strict
        )
        # 2026-08-12: "that clears all chapter X/XI - cross check
        # please" - the maintainer's own words. Cross-checked directly
        # against the standard's own Table H-XI (pages 432-433): every
        # real template/example there clusters Field T near PT2 (the
        # line's own START), not near the tip the way this anchor
        # (0.9, EndOfText) was originally built without ever checking
        # the standard - see _DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT's
        # own comment for the full story and the maintainer's own "go
        # ahead and fix the DTG and Field T" instruction once shown it.
        self.assertAlmostEqual(line_settings.lineAnchorPercent(), 0.12)
        self.assertEqual(
            line_settings.anchorTextPoint(),
            QgsLabelLineSettings.AnchorTextPoint.StartOfText
        )

        # No other measure type on this layer gets a real label - every
        # other feature's own expression resolves to '' (see the CASE
        # guard in offensive_control_measures.py's own
        # _DIRECTION_OF_ATTACK_AVIATION_DESIGNATION_LABEL_EXPRESSION).
        expr = QgsExpression(settings.fieldName)

        feature = QgsFeature()
        feature.setFields(layer.fields())
        feature.setAttribute("measure_type", "direction_of_attack_main")
        feature.setAttribute("unique_designation", "SHOULD NOT APPEAR")

        context = QgsExpressionContext()
        context.setFeature(feature)

        self.assertEqual(expr.evaluate(context), "")


    def test_direction_of_attack_main_attack_designation_is_a_masked_pal_label(self):

        # 2026-08-12: "Field T - unique designator should have a mask
        # so that line is not seen below it" - the maintainer's own
        # words, once Field T moved to the centre of the shaft, right
        # on top of the drawn line. The second rule on this layer's own
        # QgsRuleBasedLabeling (see test_direction_of_attack_aviation_
        # designation_is_a_masked_pal_label()'s own comment) - a third
        # was added the same day for Supporting Attack, a fourth for
        # Enemy ("start with the supporting attack, default the colour
        # to red, that's all"), a fifth for Friendly Ground Axis
        # ("replicate the supporting attack symbol for friendly ground
        # axis, that's all, no change to the symbol required"), and a
        # sixth for Feint ("start with the supporting attack symbol,
        # add a dashed chevron outside the main arrowhead...").
        layer = create_offensive_control_measures_lines_layer()

        labeling = layer.labeling()
        rules = labeling.rootRule().children()

        self.assertEqual(len(rules), 6)

        settings = rules[1].settings()

        self.assertTrue(settings.isExpression)
        self.assertIn("direction_of_attack_main", settings.fieldName)
        self.assertEqual(settings.placement, Qgis.LabelPlacement.Line)

        text_format = settings.format()
        mask_settings = text_format.mask()
        self.assertTrue(mask_settings.enabled())

        masked_ids = [
            ref.symbolLayerIdV2() for ref in mask_settings.maskedSymbolLayers()
        ]
        self.assertIn("direction_of_attack_main_line", masked_ids)

        # 2026-08-12: Main Attack's own former CENTRE-of-shaft anchor
        # (0.5) was retired the same "cross check" round as Friendly
        # Aviation's own near-tip 0.9 - both replaced by the SAME
        # shared near-start anchor once the standard's own Table H-XI
        # showed Field T clustering at PT2, not the tip or the centre -
        # see _DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT's own comment.
        line_settings = settings.lineSettings()
        self.assertEqual(
            line_settings.anchorType(),
            QgsLabelLineSettings.AnchorType.Strict
        )
        self.assertAlmostEqual(line_settings.lineAnchorPercent(), 0.12)
        self.assertEqual(
            line_settings.anchorTextPoint(),
            QgsLabelLineSettings.AnchorTextPoint.StartOfText
        )

        # Still affiliation-coloured, not the shared text format's own
        # default black - preserving the font-marker technique's own
        # existing behaviour (_designation_font_marker() already
        # applied this), not a new request.
        color_property = settings.dataDefinedProperties().property(
            QgsPalLayerSettings.Property.Color
        )
        self.assertTrue(color_property.isActive())


    def test_direction_of_attack_main_attack_line_layer_has_a_stable_id(self):

        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "direction_of_attack_main")

        self.assertEqual(symbol.symbolLayer(0).id(), "direction_of_attack_main_line")


    def test_direction_of_attack_main_attack_has_no_font_marker_field_t(self):

        # Field T moved off the shared font-marker technique entirely
        # for Main Attack (onto the masked PAL label above) - unlike
        # every other non-aviation variant, which still has one.
        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "direction_of_attack_main")

        font_layers = _font_marker_layers(symbol)

        # Field W-W1 (DTG) still uses two font-marker layers - just no
        # THIRD one for Field T.
        self.assertEqual(len(font_layers), 2)


    def test_direction_of_attack_main_attack_has_a_solid_outer_chevron_with_struts(self):

        # 2026-08-12: "start with the symbol for feint; change the
        # outer chevron to solid line, add line segments to join ends
        # of both the stubs" - the maintainer's own words. Main Attack
        # now uses the SAME real QgsSimpleMarkerSymbolLayer(Shape.
        # ArrowHead) every other variant does as its own inner chevron
        # (unlike the old fully hand-authored double-chevron SVG this
        # test used to check for), plus one extra SVG marker at
        # LastVertex - see _DIRECTION_OF_ATTACK_MAIN_ATTACK_OUTER_
        # CHEVRON_SVG's own comment.
        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "direction_of_attack_main")

        marker_line_layers = [
            symbol.symbolLayer(i)
            for i in range(symbol.symbolLayerCount())
            if isinstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
        ]

        # Narrow to the chevron-shaped ones only (Simple/SVG marker
        # submarkers) - Field W-W1 (DTG) moved to FirstVertex during
        # the "cross check" round (see _DIRECTION_OF_ATTACK_LABEL_
        # ANCHOR_PERCENT's own comment), so it no longer shows up here
        # at all, but this filter stays defensive rather than assuming.
        last_vertex_layers = [
            layer for layer in marker_line_layers
            if layer.placements() == Qgis.MarkerLinePlacement.LastVertex
            and isinstance(
                layer.subSymbol().symbolLayer(0),
                (QgsSimpleMarkerSymbolLayer, QgsSvgMarkerSymbolLayer)
            )
        ]

        self.assertEqual(len(last_vertex_layers), 2)

        real_chevron_layers = [
            layer for layer in last_vertex_layers
            if isinstance(layer.subSymbol().symbolLayer(0), QgsSimpleMarkerSymbolLayer)
        ]

        outer_chevron_layers = [
            layer for layer in last_vertex_layers
            if isinstance(layer.subSymbol().symbolLayer(0), QgsSvgMarkerSymbolLayer)
        ]

        self.assertEqual(len(real_chevron_layers), 1)
        self.assertEqual(len(outer_chevron_layers), 1)

        svg_layer = outer_chevron_layers[0].subSymbol().symbolLayer(0)

        svg_data = base64.b64decode(
            svg_layer.path().split("base64:", 1)[1]
        ).decode("utf-8")

        # Solid, not Feint's own dashed - the one delta the maintainer
        # named for the chevron's own stroke.
        self.assertNotIn("stroke-dasharray", svg_data)

        segments = re.findall(
            r"M\s*([\d.]+),([\d.]+)\s*L\s*([\d.]+),([\d.]+)",
            svg_data
        )

        # Two long chevron arms plus two short struts (one per side)
        # connecting the outer chevron's own back corners to the real
        # inner chevron's own back corners - "join ends of both the
        # stubs".
        self.assertEqual(len(segments), 4)

        def length(segment):
            x1, y1, x2, y2 = (float(v) for v in segment)
            return math.hypot(x2 - x1, y2 - y1)

        lengths = sorted(length(segment) for segment in segments)

        # The two struts are short (each exactly the gap distance,
        # ~0.81mm); the two arms are long (~5.7mm, the real chevron's
        # own side length plus the same gap's own along-axis reach -
        # see _direction_of_attack_feint_outer_chevron_layer()'s own
        # comment for that derivation). A wide margin either side of
        # the real numbers, since this is checking the shape didn't
        # regress into a straight combined pair, not re-deriving exact
        # geometry the source code comments already document.
        self.assertLess(lengths[0], 2.0)
        self.assertLess(lengths[1], 2.0)
        self.assertGreater(lengths[2], 4.0)
        self.assertGreater(lengths[3], 4.0)

        # Colour-driven like every other line/chevron in this
        # construction, not the plain default.
        color_property = svg_layer.dataDefinedProperties().property(
            QgsSymbolLayer.Property.StrokeColor
        )
        self.assertTrue(color_property.isActive())

        # No other Direction of Attack variant gets a second LastVertex
        # SVG marker of this kind - Feint is deliberately excluded from
        # this loop: it also has one now (its own dashed outer chevron,
        # see test_direction_of_attack_feint_has_a_dashed_outer_chevron)
        # - a real, distinct construction, not this one, so it would
        # trip this specific check for the wrong reason.
        for measure_type in (
            "direction_of_attack_aviation",
            "direction_of_attack_supporting",
            "direction_of_attack_ground_axis",
            "direction_of_attack_enemy",
        ):

            with self.subTest(measure_type=measure_type):

                other_symbol = _rule_symbol_for(layer, measure_type)

                other_chevron_layers = [
                    other_symbol.symbolLayer(i)
                    for i in range(other_symbol.symbolLayerCount())
                    if isinstance(other_symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
                    and other_symbol.symbolLayer(i).placements() == Qgis.MarkerLinePlacement.LastVertex
                    and other_symbol.symbolLayer(i).subSymbol().symbolLayerCount() >= 1
                    and isinstance(
                        other_symbol.symbolLayer(i).subSymbol().symbolLayer(0),
                        QgsSvgMarkerSymbolLayer
                    )
                ]

                self.assertEqual(len(other_chevron_layers), 0)


    def test_direction_of_attack_feint_has_a_dashed_outer_chevron(self):

        # 2026-08-12: "start with the supporting attack symbol, add a
        # dashed chevron outside the main arrowhead, at a gap 1/6 of
        # the length of arrowhead side, the new chevron being parallel
        # to the existing arrowhead" - the maintainer's own words. See
        # _direction_of_attack_feint_outer_chevron_layer()'s own
        # comment for the real-chevron probe measurements (half-angle
        # ~43.727 degrees, side length ~4.8505mm) this glyph's own
        # coordinates were computed from.
        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "direction_of_attack_feint")

        marker_line_layers = [
            symbol.symbolLayer(i)
            for i in range(symbol.symbolLayerCount())
            if isinstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
        ]

        outer_chevron_layers = [
            layer for layer in marker_line_layers
            if layer.placements() == Qgis.MarkerLinePlacement.LastVertex
            and layer.subSymbol().symbolLayerCount() >= 1
            and isinstance(layer.subSymbol().symbolLayer(0), QgsSvgMarkerSymbolLayer)
        ]

        self.assertEqual(len(outer_chevron_layers), 1)

        svg_layer = outer_chevron_layers[0].subSymbol().symbolLayer(0)

        svg_data = base64.b64decode(
            svg_layer.path().split("base64:", 1)[1]
        ).decode("utf-8")

        self.assertIn("stroke-dasharray", svg_data)

        # Parse the two "M x,y L x,y" arms and confirm each is parallel
        # to the real chevron's own arm at that same half-angle (~43.727
        # degrees from the horizontal centreline) - the same "compute
        # both arms' own slopes directly" verification this project's
        # other hand-authored chevrons (Main Attack) were confirmed
        # with, not just a visual check.
        segments = re.findall(
            r"M\s*([\d.]+),([\d.]+)\s*L\s*([\d.]+),([\d.]+)",
            svg_data
        )

        self.assertEqual(len(segments), 2)

        real_half_angle = math.radians(43.727)

        for x1, y1, x2, y2 in segments:

            dx = float(x2) - float(x1)
            dy = float(y2) - float(y1)

            # Angle from the horizontal centreline, independent of
            # which quadrant the arm vector points into (both arms
            # point back-and-outward, not along +x).
            arm_angle = math.atan2(abs(dy), abs(dx))

            self.assertAlmostEqual(arm_angle, real_half_angle, places=2)

        # Colour-driven like every other line/chevron in this
        # construction, not the plain default.
        color_property = svg_layer.dataDefinedProperties().property(
            QgsSymbolLayer.Property.StrokeColor
        )
        self.assertTrue(color_property.isActive())


    def test_direction_of_attack_aviation_line_layer_has_a_stable_id(self):

        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "direction_of_attack_aviation")

        self.assertEqual(symbol.symbolLayer(0).id(), "direction_of_attack_aviation_line")

        # Every other Direction of Attack variant's own line layer is
        # untouched - no id EXPLICITLY set (masking is scoped to
        # aviation only), so it keeps whatever auto-generated UUID QGIS
        # itself assigns rather than this project's own stable id.
        for measure_type in (
            "direction_of_attack_main",
            "direction_of_attack_supporting",
            "direction_of_attack_ground_axis",
            "direction_of_attack_feint",
            "direction_of_attack_enemy",
        ):

            with self.subTest(measure_type=measure_type):

                other_symbol = _rule_symbol_for(layer, measure_type)
                self.assertNotEqual(
                    other_symbol.symbolLayer(0).id(),
                    "direction_of_attack_aviation_line"
                )


    def test_enemy_variants_render_red_regardless_of_affiliation(self):

        # 2026-08-10: per the project maintainer's own report, an Enemy-
        # flagged Axis of Advance/Direction of Attack must render red
        # even if "affiliation" was left at a non-hostile value.
        # 2026-08-11: Axis of Advance - Enemy moved onto the master
        # arrow's own ribbon construction ("just use the master arrow
        # and default colour to red" - already true by construction,
        # not a new colour rule) - its own colour now lives on the
        # geometry generator's own SUB-symbol, not symbolLayer(0)
        # directly, the same relocation Main Attack/Supporting Attack/
        # Feint already went through. Direction of Attack - Enemy is
        # unaffected here (colour still directly on symbolLayer(0),
        # the plain QgsSimpleLineSymbolLayer shaft) even after
        # 2026-08-12's "start with the supporting attack" rebuild -
        # it's still a plain QgsLineSymbol, not a ribbon geometry
        # generator, so this test's own assertion shape didn't need to
        # change, only the base construction it now points at.
        layer = create_offensive_control_measures_lines_layer()

        for measure_type in ("axis_of_advance_enemy", "direction_of_attack_enemy"):

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                if measure_type == "axis_of_advance_enemy":

                    base_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)

                else:

                    base_line = symbol.symbolLayer(0)

                feature = QgsFeature(layer.fields())
                feature.setAttribute("measure_type", measure_type)
                feature.setAttribute("affiliation", "friend")

                context = layer.createExpressionContext()
                context.setFeature(feature)

                color, ok = base_line.dataDefinedProperties().valueAsColor(
                    QgsSymbolLayer.Property.StrokeColor,
                    context,
                    QColor(1, 2, 3)
                )

                self.assertTrue(ok)
                self.assertEqual(color.name(), "#ff0000")


    def test_infiltration_lane_is_two_parallel_lines_with_a_centred_designation(self):

        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "infiltration_lane")

        self.assertEqual(symbol.symbolLayerCount(), 3)

        self.assertAlmostEqual(symbol.symbolLayer(0).offset(), 2.0, places=5)
        self.assertAlmostEqual(symbol.symbolLayer(1).offset(), -2.0, places=5)

        label_layer = symbol.symbolLayer(2)

        self.assertEqual(
            label_layer.placements(),
            Qgis.MarkerLinePlacement.CentralPoint
        )

        font_layer = label_layer.subSymbol().symbolLayer(0)

        feature = QgsFeature(layer.fields())
        feature.setAttribute("unique_designation", "green")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        character, ok = font_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Character,
            context,
            ""
        )

        self.assertTrue(ok)
        self.assertEqual(character, "GREEN")


    def test_simple_end_labelled_lines_use_the_expected_fixed_characters(self):

        layer = create_offensive_control_measures_lines_layer()

        cases = {
            "final_coordination_line": "FCL",
            "limit_of_advance": "LOA",
            "line_of_departure": "LD",
            "line_of_departure_and_contact": "LD/LC",
            "probable_line_of_deployment": "PLD",
        }

        for measure_type, character in cases.items():

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 3)

                for i in (1, 2):

                    label_layer = symbol.symbolLayer(i)
                    font_layer = label_layer.subSymbol().symbolLayer(0)

                    self.assertEqual(font_layer.character(), character)


    def test_probable_line_of_deployment_is_always_dashed(self):

        layer = create_offensive_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "probable_line_of_deployment")

        base_line = symbol.symbolLayer(0)

        self.assertEqual(base_line.penStyle(), Qt.PenStyle.DashLine)

        # No data-defined StrokeStyle override - always dashed
        # regardless of the "status" field.
        has_override = base_line.dataDefinedProperties().hasProperty(
            QgsSymbolLayer.Property.StrokeStyle
        )

        self.assertFalse(has_override)


    def test_other_simple_lines_follow_the_shared_status_field(self):

        layer = create_offensive_control_measures_lines_layer()

        for measure_type in (
            "final_coordination_line", "limit_of_advance",
            "line_of_departure", "line_of_departure_and_contact",
        ):

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)
                base_line = symbol.symbolLayer(0)

                self.assertTrue(
                    base_line.dataDefinedProperties().hasProperty(
                        QgsSymbolLayer.Property.StrokeStyle
                    )
                )


    def test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_offensive_control_measures_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        # "axis_of_advance_main_attack" was this test's own original
        # representative Axis of Advance measure type, until it moved
        # to the real (non-crossed) "master arrow" ribbon construction
        # 2026-08-10 - its own colour now lives on the geometry
        # generator's own SUB-symbol, not symbol.symbolLayer(0)
        # directly. Supporting Attack and Feint followed the same move
        # 2026-08-11 ("just replicate the master arrow"/"use the arrow
        # ... of supporting attack as the base"), leaving only Enemy in
        # the old approximated Axis of Advance family - and Enemy's own
        # colour is hardcoded red regardless of affiliation (see
        # test_enemy_variants_render_red_regardless_of_affiliation), so
        # it can't stand in for this test's own affiliation-mapping
        # check either. Picks Final Coordination Line instead (Table
        # H-XI's own simple end-labelled line) - the intent here is
        # just "one representative measure type whose colour sits
        # directly on symbolLayer(0)", not any specific sub-type.
        for measure_type in ("final_coordination_line", "direction_of_attack_main"):

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

            layer = create_offensive_control_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            self.assertTrue(
                layer.defaultValueDefinition(idx).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateOffensiveControlMeasuresAreasLayer(QgisTestCase):

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

        layer = create_offensive_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_offensive_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_labels_prefix_the_type_abbreviation(self):

        layer = create_offensive_control_measures_areas_layer()

        cases = {
            "assault_position": ("ASLT", "danube", "ASLT DANUBE"),
            "attack_position": ("ATK", "nile", "ATK NILE"),
            "objective_area": ("OBJ", "five", "OBJ FIVE"),
        }

        for measure_type, (prefix, name, expected) in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, unique_designation=name
                    ),
                    expected
                )


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_offensive_control_measures_areas_layer()

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


class TestCreateOffensiveControlMeasuresPointsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()


    def test_has_the_expected_fields(self):

        layer = create_offensive_control_measures_points_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["affiliation", "entity", "status", "unique_designation"]
        )


    def test_is_a_point_layer(self):

        layer = create_offensive_control_measures_points_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Point"
        )


    def test_entity_uses_a_value_map_widget_defaulting_to_point_of_departure(self):

        layer = create_offensive_control_measures_points_layer()

        idx = layer.fields().indexOf("entity")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(
            widget_setup.config()["map"],
            {label: value for value, label in POINT_ENTITY_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'point_of_departure'"
        )


    def test_svg_layer_is_anchored_at_the_tip(self):

        # Point of Departure shares the box+cone construction (and its
        # own tip-anchoring draw rule) already established for Table
        # H-VI/H-IX's own point families - see module docstring.
        layer = create_offensive_control_measures_points_layer()

        symbol = layer.renderer().symbol()
        svg_layer = symbol.symbolLayer(0)

        value, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.VerticalAnchor,
            layer.createExpressionContext(),
            ""
        )

        self.assertTrue(ok)
        self.assertEqual(value, "bottom")


    def test_a_real_feature_resolves_to_a_valid_symbol_path(self):

        layer = create_offensive_control_measures_points_layer()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", "point_of_departure")
        feature.setAttribute("status", "present")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        symbol = layer.renderer().symbol()
        svg_layer = symbol.symbolLayer(0)

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name,
            context,
            ""
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_unique_designation_is_labeled_beside_the_box(self):

        # 2026-08-12 rebuild: "same construction of symbol as Fly-To-
        # Point... the unique designation is outside the symbol on top
        # right as in the Fly-To symbol" - the maintainer's own words.
        # A direct probe render (SIDC 10032500001604000000 with
        # {"uniqueDesignation": "1"}) showed milsymbol.js's own native
        # `uniqueDesignation` text-modifier slot already places the
        # designation at (x=150, y=-30) - the SAME y as the "PD" text
        # itself (also y=-30) and just past the box's own right edge
        # (x=140) - disproving the original build's own claim that both
        # of milsymbol's text slots were wrong for this SIDC. No
        # separate QGIS label needed any more - see c2_measures.py's
        # own _POINT_SIDC_EXPRESSION for the identical pattern this now
        # mirrors for Fly-To Point and the rest of that shared family.
        layer = create_offensive_control_measures_points_layer()

        self.assertIsNone(layer.labeling())

        feature = QgsFeature(layer.fields())
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", "point_of_departure")
        feature.setAttribute("status", "present")
        feature.setAttribute("unique_designation", "alpha")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        symbol = layer.renderer().symbol()
        svg_layer = symbol.symbolLayer(0)

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name,
            context,
            ""
        )

        self.assertTrue(ok)

        svg_data = base64.b64decode(path.split("base64:", 1)[1]).decode("utf-8")

        # Upper-cased per H.5.4's "all text labeling in upper case" rule.
        self.assertIn("ALPHA", svg_data)
        self.assertNotIn("alpha", svg_data)


class TestAddOffensiveControlMeasuresLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_offensive_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_offensive_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_points_layer_is_created_and_added(self):

        layer = add_offensive_control_measures_points_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        first = add_offensive_control_measures_lines_layer(self.iface)

        result = add_offensive_control_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_offensive_control_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)
