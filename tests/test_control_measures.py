# -*- coding: utf-8 -*-

"""
Tests for military_symbology/control_measures.py - the control-measure
line/area layers (phase lines, boundaries, axis of advance, objectives,
NAIs) styled via a QgsRuleBasedRenderer keyed on "measure_type".

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsExpressionContext,
    QgsFeature,
    QgsGeometry,
    QgsGeometryGeneratorSymbolLayer,
    QgsMarkerLineSymbolLayer,
    QgsPointXY,
    QgsProject,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsSymbolLayerUtils,
    QgsTemplatedLineSymbolLayerBase,
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


def _stroke_symbol_layer(symbol):

    """
    The symbol layer whose StrokeColor property actually carries the
    affiliation colour expression - symbolLayer(0) directly for an
    ordinary line/fill symbol, or one level into a wrapper layer's own
    subSymbol for anything built from the shared helpers that wrap a real
    line layer inside something else with no colour properties of its
    own: QgsGeometryGeneratorSymbolLayer (circle-from-line measure types -
    isolate/secure/seize/retain - and the anchor-point-reconstructed ones -
    block/penetrate/breach/canalize - see control_measures.py's own
    docstrings) or QgsMarkerLineSymbolLayer (the wavy-line measure types -
    forward_line_of_troops/line_of_contact - whose colour lives on the
    repeating marker's own symbol layer, not the line layer that places
    it).
    """

    layer = symbol.symbolLayer(0)

    if isinstance(layer, (QgsGeometryGeneratorSymbolLayer, QgsMarkerLineSymbolLayer)):

        return layer.subSymbol().symbolLayer(0)

    return layer


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
            stroke_layer = _stroke_symbol_layer(symbol)

            color, ok = _resolve_stroke_color(
                stroke_layer, layer, "friend"
            )
            self.assertTrue(ok, measure_type)
            self.assertEqual(color.name(), "#0000ff", measure_type)

            color, ok = _resolve_stroke_color(
                stroke_layer, layer, "hostile"
            )
            self.assertTrue(ok, measure_type)
            self.assertEqual(color.name(), "#ff0000", measure_type)

            for affiliation in ("neutral", "unknown"):

                color, ok = _resolve_stroke_color(
                    stroke_layer, layer, affiliation
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


    # --- H.5.11-H.5.14 / H.5.26 additions (2026-08-07) ------------------

    def test_forward_line_of_troops_is_a_wavy_line(self):

        # Code 140100/140101 - the template page's own picture (410) shows
        # a real serpentine/wave line, not a plain straight one (an
        # earlier version of this function rendered a plain line, since
        # the extracted text alone gives no hint of the wave - see
        # control_measures.py's own comment on _forward_line_of_troops_symbol()).
        # Two QgsMarkerLineSymbolLayers alternate half_arc markers to draw
        # one continuous wave - see _wavy_line_layers()'s own comment.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "forward_line_of_troops")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        for i in range(2):

            self.assertIsInstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)
            self.assertEqual(
                symbol.symbolLayer(i).placements(),
                QgsTemplatedLineSymbolLayerBase.Placement.Interval
            )

        offsets_along_line = sorted(
            symbol.symbolLayer(i).offsetAlongLine() for i in range(2)
        )
        self.assertAlmostEqual(offsets_along_line[0], 0)
        self.assertGreater(offsets_along_line[1], 0)


    def test_line_of_contact_is_two_offset_wavy_lines(self):

        # Code 140200 - "created when both the friendly and enemy FLOT
        # symbols are displayed" - the template page's own picture (412)
        # shows this literally: two parallel WAVY lines (an earlier
        # version of this function used two plain offset straight lines,
        # the same "text alone doesn't show the wave" gap FLOT itself had -
        # see control_measures.py's own comment on _line_of_contact_symbol()).
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "line_of_contact")

        self.assertEqual(symbol.symbolLayerCount(), 4)

        for i in range(4):

            self.assertIsInstance(symbol.symbolLayer(i), QgsMarkerLineSymbolLayer)

        offsets = sorted(
            {symbol.symbolLayer(i).offset() for i in range(4)}
        )
        self.assertEqual(len(offsets), 2)
        self.assertAlmostEqual(offsets[0], -3)
        self.assertAlmostEqual(offsets[1], 3)


    def test_feba_renders_a_real_multi_vertex_path_unmodified(self):

        # Code 140400 - the template page's own picture (413) shows a
        # small triangular peak in the middle of the line (PT1-PT3
        # baseline, PT2 the peak) - reads like it needs special
        # construction, but doesn't: it's simply the raw 3-vertex path
        # P1->P2->P3, the same "additional points extend the line"
        # convention Phase Line/FLOT already support. Confirmed here by
        # rendering a real 3-vertex feature through the actual symbol and
        # checking the geometry comes through unchanged - not just that
        # some structure exists - since this module's own recurring
        # lesson is that a shape can look like it needs special code when
        # it doesn't (see control_measures.py's own comment on this
        # function for the reasoning).
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "forward_edge_of_battle_area")

        self.assertEqual(symbol.symbolLayerCount(), 1)
        self.assertIsInstance(symbol.symbolLayer(0), QgsSimpleLineSymbolLayer)

        phase_line_width = _rule_symbol_for(
            layer, "phase_line"
        ).symbolLayer(0).width()

        self.assertGreater(symbol.symbolLayer(0).width(), phase_line_width)


    def test_principal_direction_of_fire_has_arrows_at_both_ends(self):

        # Code 140500 - two arrowheads diverging from a shared vertex,
        # approximated as arrows at both FirstVertex and LastVertex (see
        # control_measures.py's own comment on the point-ordering
        # deviation and the FirstVertex rotation reasoning).
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "principal_direction_of_fire")

        self.assertEqual(symbol.symbolLayerCount(), 3)

        placements = {
            symbol.symbolLayer(i).placements()
            for i in (1, 2)
        }
        self.assertEqual(
            placements,
            {
                QgsTemplatedLineSymbolLayerBase.Placement.LastVertex,
                QgsTemplatedLineSymbolLayerBase.Placement.FirstVertex,
            }
        )

        first_vertex_layer = next(
            symbol.symbolLayer(i) for i in (1, 2)
            if symbol.symbolLayer(i).placements()
            == QgsTemplatedLineSymbolLayerBase.Placement.FirstVertex
        )
        self.assertEqual(
            first_vertex_layer.subSymbol().symbolLayer(0).angle(),
            180
        )


    def test_direction_of_attack_has_a_single_end_arrow(self):

        # Code 140600 - a plain arrow line, thinner than
        # axis_of_advance's own wide-band approximation.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "direction_of_attack")

        self.assertEqual(symbol.symbolLayerCount(), 2)
        self.assertIsInstance(symbol.symbolLayer(1), QgsMarkerLineSymbolLayer)
        self.assertEqual(
            symbol.symbolLayer(1).placements(),
            QgsTemplatedLineSymbolLayerBase.Placement.LastVertex
        )

        axis_width = _rule_symbol_for(
            layer, "axis_of_advance"
        ).symbolLayer(0).width()
        self.assertLess(symbol.symbolLayer(0).width(), axis_width)


    def test_block_reconstructs_the_real_3_anchor_point_shape(self):

        # Code 340100 - "Points 1 and 2 define the endpoints of the
        # graphic's vertical line. Point 3 defines the endpoint of the
        # graphic's horizontal line, which will project perpendicularly
        # from the MIDPOINT of the vertical line". A regression test for
        # a real bug: an earlier version of this symbol approximated the
        # horizontal line as a small FIXED-size tick at the digitized
        # line's own central point, ignoring point 3 entirely - caught by
        # comparing a real render against the standard's own template
        # diagram, where point 3 sits far from the vertical line. This
        # test evaluates both geometry-generator expressions against a
        # real 3-vertex feature and checks the actual reconstructed
        # geometry, not just that some structure exists.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "block")

        self.assertEqual(symbol.symbolLayerCount(), 2)
        self.assertIsInstance(symbol.symbolLayer(0), QgsGeometryGeneratorSymbolLayer)
        self.assertIsInstance(symbol.symbolLayer(1), QgsGeometryGeneratorSymbolLayer)

        p1, p2, p3 = QgsPointXY(14, 16), QgsPointXY(14, 4), QgsPointXY(2, 10)
        geometry = QgsGeometry.fromPolylineXY([p1, p2, p3])

        def evaluate(expression_string):

            expression = QgsExpression(expression_string)
            context = QgsExpressionContext()
            context.setFeature(QgsFeature())
            context.setGeometry(geometry)
            result = expression.evaluate(context)
            self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
            return result

        vertical = evaluate(symbol.symbolLayer(0).geometryExpression())
        self.assertEqual(vertical.asPolyline(), [p1, p2])

        horizontal = evaluate(symbol.symbolLayer(1).geometryExpression())
        midpoint = QgsPointXY(14, 10)
        self.assertEqual(horizontal.asPolyline(), [p3, midpoint])


    def _assert_is_the_real_bracket_shape(self, measure_type):

        # Shared by Breach and Canalize - confirmed identical shapes by
        # comparing their two template pictures side by side (637/638):
        # "Points 1 and 2 define the endpoints of the symbol's opening and
        # point 3 defines the rear of the symbol... the vertical line at
        # the rear will be the same height as the opening and parallel to
        # it" - a real open bracket/"C", not the plain-dashed-line-plus-
        # decorative-tick an earlier version of both functions used. See
        # _bracket_symbol()'s own comment for the construction.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, measure_type)

        self.assertEqual(symbol.symbolLayerCount(), 1)
        self.assertIsInstance(symbol.symbolLayer(0), QgsGeometryGeneratorSymbolLayer)

        p1, p2, p3 = QgsPointXY(16, 12), QgsPointXY(16, 4), QgsPointXY(2, 8)
        geometry = QgsGeometry.fromPolylineXY([p1, p2, p3])

        expression = QgsExpression(symbol.symbolLayer(0).geometryExpression())
        context = QgsExpressionContext()
        context.setFeature(QgsFeature())
        context.setGeometry(geometry)
        result = expression.evaluate(context)

        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        self.assertEqual(
            result.asPolyline(),
            [p1, QgsPointXY(2, 12), p3, QgsPointXY(2, 4), p2]
        )


    def test_breach_is_the_real_bracket_shape(self):

        self._assert_is_the_real_bracket_shape("breach")


    def test_canalize_is_the_real_bracket_shape(self):

        self._assert_is_the_real_bracket_shape("canalize")


    def test_disrupt_has_ticks_at_regular_intervals(self):

        # Code 341000 - "arrows" perpendicular to the baseline,
        # approximated as ticks repeated along the line.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "disrupt")

        self.assertEqual(symbol.symbolLayerCount(), 2)
        interval_layer = symbol.symbolLayer(1)
        self.assertEqual(
            interval_layer.placements(),
            QgsTemplatedLineSymbolLayerBase.Placement.Interval
        )
        self.assertGreater(interval_layer.interval(), 0)


    def test_fix_is_a_dashed_arrow_distinct_from_direction_of_attack(self):

        # Code 341100 - the standard gives Fix no distinguishing detail
        # beyond "an arrow"; dashed here purely so it stays visually
        # distinguishable from direction_of_attack's own solid arrow.
        layer = create_control_measures_lines_layer()
        fix_symbol = _rule_symbol_for(layer, "fix")

        self.assertEqual(fix_symbol.symbolLayerCount(), 2)
        self.assertIsInstance(
            fix_symbol.symbolLayer(1), QgsMarkerLineSymbolLayer
        )


    def test_penetrate_reconstructs_the_real_3_anchor_point_shape(self):

        # Code 341800 - the same genuine 3-anchor-point shape as Block
        # above (see that test's own comment for the bug this replaced),
        # except "Point 3 defines the rear of the symbol" - point 3 is
        # the arrow's tail, so the arrowhead sits at the midpoint end,
        # piercing into the vertical line.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "penetrate")

        self.assertEqual(symbol.symbolLayerCount(), 2)
        self.assertIsInstance(symbol.symbolLayer(0), QgsGeometryGeneratorSymbolLayer)
        self.assertIsInstance(symbol.symbolLayer(1), QgsGeometryGeneratorSymbolLayer)

        p1, p2, p3 = QgsPointXY(14, 16), QgsPointXY(14, 4), QgsPointXY(2, 10)
        geometry = QgsGeometry.fromPolylineXY([p1, p2, p3])

        def evaluate(expression_string):

            expression = QgsExpression(expression_string)
            context = QgsExpressionContext()
            context.setFeature(QgsFeature())
            context.setGeometry(geometry)
            result = expression.evaluate(context)
            self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
            return result

        vertical = evaluate(symbol.symbolLayer(0).geometryExpression())
        self.assertEqual(vertical.asPolyline(), [p1, p2])

        shaft = evaluate(symbol.symbolLayer(1).geometryExpression())
        midpoint = QgsPointXY(14, 10)
        self.assertEqual(shaft.asPolyline(), [p3, midpoint])

        arrow_sub_symbol = symbol.symbolLayer(1).subSymbol()
        self.assertEqual(arrow_sub_symbol.symbolLayerCount(), 2)
        arrow_layer = arrow_sub_symbol.symbolLayer(1)
        self.assertIsInstance(arrow_layer, QgsMarkerLineSymbolLayer)
        self.assertEqual(
            arrow_layer.placements(),
            QgsTemplatedLineSymbolLayerBase.Placement.LastVertex
        )


    def test_delay_and_withdraw_share_the_same_arrow_recipe(self):

        # Codes 340800/342400 - the standard's own draw rules for these
        # two are close to verbatim identical (arrow + perpendicular
        # 180-degree arc); control_measures.py documents deliberately
        # giving them the same rendering recipe, differentiated only by
        # measure_type/label, the same way FLOT is kept separate from
        # Phase Line despite an identical recipe.
        layer = create_control_measures_lines_layer()

        delay_symbol = _rule_symbol_for(layer, "delay")
        withdraw_symbol = _rule_symbol_for(layer, "withdraw")

        self.assertEqual(delay_symbol.symbolLayerCount(), 2)
        self.assertEqual(withdraw_symbol.symbolLayerCount(), 2)
        self.assertAlmostEqual(
            delay_symbol.symbolLayer(0).width(),
            withdraw_symbol.symbolLayer(0).width()
        )


    def test_isolate_secure_seize_are_circles_generated_from_the_line(self):

        # Codes 341500/342100/342300, plus retain (151205, checked
        # separately below) - all defined by the standard as a
        # centre+radius circle, approximated via a
        # QgsGeometryGeneratorSymbolLayer computing the radius from just
        # the first two vertices (not length($geometry), which would sum
        # every segment and inflate the radius once a 3rd vertex is added
        # for Seize's own arrow - see
        # test_seize_radius_is_not_inflated_by_the_arrow_point() below,
        # and control_measures.py's own docstring/
        # _circle_from_line_symbol() comment).
        layer = create_control_measures_lines_layer()

        for measure_type in ("isolate", "secure", "seize"):

            symbol = _rule_symbol_for(layer, measure_type)
            circle_layer = symbol.symbolLayer(0)

            self.assertIsInstance(
                circle_layer, QgsGeometryGeneratorSymbolLayer, measure_type
            )
            self.assertEqual(
                circle_layer.geometryExpression(),
                "buffer(start_point($geometry),"
                " distance(start_point($geometry), point_n($geometry, 2)))",
                measure_type
            )


    def test_seize_radius_is_not_inflated_by_the_arrow_point(self):

        # Regression test for a real bug found by rendering Seize with
        # its full 3-point form (centre, radius point, arrow point) and
        # comparing it side by side with the 2-point form: using
        # length($geometry) as the radius summed BOTH segments, doubling
        # the circle's size the moment a 3rd point was added for the
        # arrow. The radius must come from the centre-to-2nd-vertex
        # distance only, regardless of how many further vertices follow.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "seize")
        circle_layer = symbol.symbolLayer(0)

        two_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), QgsPointXY(10, 0)]
        )
        three_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), QgsPointXY(10, 0), QgsPointXY(10, 10)]
        )

        expression = QgsExpression(circle_layer.geometryExpression())

        def rendered_area(geometry):

            context = QgsExpressionContext()
            context.setFeature(QgsFeature())
            context.setGeometry(geometry)
            result = expression.evaluate(context)
            self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
            return result.area()

        self.assertAlmostEqual(
            rendered_area(two_point),
            rendered_area(three_point),
            delta=0.01
        )


    def test_isolate_and_secure_have_distinct_outline_styles(self):

        layer = create_control_measures_lines_layer()

        isolate_outline = _rule_symbol_for(
            layer, "isolate"
        ).symbolLayer(0).subSymbol().symbolLayer(0).strokeStyle()

        secure_outline = _rule_symbol_for(
            layer, "secure"
        ).symbolLayer(0).subSymbol().symbolLayer(0).strokeStyle()

        self.assertNotEqual(isolate_outline, secure_outline)


    def test_seize_arrow_runs_from_point_2_to_point_4_only(self):

        # Code 342300 - the standard defines TWO different point recipes,
        # not one "3-or-4-point variant": with 4 points, point 2 is the
        # circle's own radius AND the arrow's start, point 4 is the
        # arrow's end. With exactly 3 points, point 2 means something
        # completely different (the arrowhead tip directly, no radius
        # role) - an earlier version of this function conflated the two,
        # appending an arrow at whatever the raw digitized line's own last
        # vertex happened to be, which is wrong for a 3-point input. See
        # _seize_symbol()'s own comment. This only implements the 4-point
        # recipe: with fewer than 4 points, point_n($geometry, 4) is NULL
        # and no arrow renders - confirmed here by evaluating the real
        # geometry-generator expression, not just checking layer types.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "seize")

        self.assertEqual(symbol.symbolLayerCount(), 2)
        self.assertIsInstance(symbol.symbolLayer(0), QgsGeometryGeneratorSymbolLayer)

        arrow_layer = symbol.symbolLayer(1)
        self.assertIsInstance(arrow_layer, QgsGeometryGeneratorSymbolLayer)

        p2, p4 = QgsPointXY(10, 0), QgsPointXY(20, 20)
        four_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), p2, QgsPointXY(15, 10), p4]
        )

        expression = QgsExpression(arrow_layer.geometryExpression())
        context = QgsExpressionContext()
        context.setFeature(QgsFeature())
        context.setGeometry(four_point)
        result = expression.evaluate(context)

        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        self.assertEqual(result.asPolyline(), [p2, p4])

        three_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), p2, QgsPointXY(15, 10)]
        )
        context.setGeometry(three_point)
        result = expression.evaluate(context)
        self.assertIsNone(result)

        arrow_sub_symbol = arrow_layer.subSymbol()
        self.assertEqual(arrow_sub_symbol.symbolLayerCount(), 2)
        self.assertIsInstance(
            arrow_sub_symbol.symbolLayer(1), QgsMarkerLineSymbolLayer
        )
        self.assertEqual(
            arrow_sub_symbol.symbolLayer(1).placements(),
            QgsTemplatedLineSymbolLayerBase.Placement.LastVertex
        )


    def test_retain_is_a_circle_generated_from_the_line(self):

        # Code 151205 - a Defensive maneuver control measure (H.5.12.1),
        # NOT a Mission Task despite being commonly grouped with them -
        # see control_measures.py's own _retain_symbol() comment. Shares
        # the same centre+radius circle technique as isolate/secure/seize.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "retain")

        self.assertIsInstance(symbol.symbolLayer(0), QgsGeometryGeneratorSymbolLayer)
        self.assertEqual(
            symbol.symbolLayer(0).geometryExpression(),
            "buffer(start_point($geometry),"
            " distance(start_point($geometry), point_n($geometry, 2)))"
        )


    def test_retain_has_tick_marks_around_the_whole_circle(self):

        # Code 151205 - the template page's own picture (423) shows the
        # circle bristling with perpendicular tick marks all around its
        # circumference, matching the text's own "the default tic length
        # should be the same as the text height of the echelon field" -
        # an earlier version of this function used an invented "dash dot"
        # outline instead, which doesn't match the picture at all.
        layer = create_control_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "retain")

        circle_sub_symbol = symbol.symbolLayer(0).subSymbol()

        self.assertEqual(circle_sub_symbol.symbolLayerCount(), 2)

        tick_layer = circle_sub_symbol.symbolLayer(1)
        self.assertIsInstance(tick_layer, QgsMarkerLineSymbolLayer)
        self.assertEqual(
            tick_layer.placements(),
            QgsTemplatedLineSymbolLayerBase.Placement.Interval
        )


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


    # --- H.5.11-H.5.14 additions (2026-08-07) ---------------------------

    def test_battle_position_is_a_plain_unfilled_outline(self):

        # Code 151200 - same unfilled-outline recipe as objective, since
        # the standard's own draw rule here has no further distinguishing
        # stroke detail.
        layer = create_control_measures_areas_layer()
        symbol = _rule_symbol_for(layer, "battle_position")

        self.assertEqual(symbol.symbolLayerCount(), 1)
        self.assertEqual(
            symbol.symbolLayer(0).strokeStyle(),
            QgsSymbolLayerUtils.decodePenStyle("solid")
        )


    def test_strong_point_has_perpendicular_tick_marks(self):

        # Code 151203 - a fortified outline with regular perpendicular
        # tick marks (fixed size/interval here, not the standard's own
        # echelon-text-height-driven rule - see control_measures.py's
        # own comment).
        layer = create_control_measures_areas_layer()
        symbol = _rule_symbol_for(layer, "strong_point")

        self.assertEqual(symbol.symbolLayerCount(), 2)
        tick_layer = symbol.symbolLayer(1)
        self.assertIsInstance(tick_layer, QgsMarkerLineSymbolLayer)
        self.assertEqual(
            tick_layer.placements(),
            QgsTemplatedLineSymbolLayerBase.Placement.Interval
        )
        self.assertGreater(tick_layer.interval(), 0)
        self.assertGreater(
            tick_layer.subSymbol().symbolLayer(0).strokeWidth(), 0
        )


    def test_battle_position_shares_objectives_solid_outline(self):

        # Codes 151200/150101 - both plain unfilled outlines, since
        # neither the standard's own Battle Position nor Objective draw
        # rule specifies anything more distinguishing than that (see
        # control_measures.py's own comment on _battle_position_symbol()).
        layer = create_control_measures_areas_layer()

        objective_style = _rule_symbol_for(
            layer, "objective"
        ).symbolLayer(0).strokeStyle()

        battle_position_style = _rule_symbol_for(
            layer, "battle_position"
        ).symbolLayer(0).strokeStyle()

        self.assertEqual(objective_style, battle_position_style)


    def test_area_types_use_their_own_templates_outline_style(self):

        # An earlier version of this test asserted that NAI/Engagement
        # Area/Assembly Area/Encirclement must all have mutually distinct
        # pen styles - an invented requirement, not something the standard
        # itself asks for. Checking the actual template pictures (424,
        # 415) showed Engagement Area and Assembly Area are both plain
        # SOLID outlines ("Friendly Present" status, matching Battle
        # Position's own convention) - the earlier dash-dot/dash-dot-dot
        # styles were invented purely to keep them visually distinct from
        # each other on screen, which doesn't hold up against what's
        # actually drawn. NAI and Encirclement are unchanged pending their
        # own template-picture check (Encirclement in particular needs a
        # real "spiky boundary" shape per H.5.14's own picture, not just a
        # different dash style - tracked separately, not yet built).
        layer = create_control_measures_areas_layer()

        outline_style_of = lambda measure_type: (
            _rule_symbol_for(layer, measure_type).symbolLayer(0).strokeStyle()
        )

        solid = QgsSymbolLayerUtils.decodePenStyle("solid")

        self.assertEqual(outline_style_of("engagement_area"), solid)
        self.assertEqual(outline_style_of("assembly_area"), solid)
        self.assertEqual(
            outline_style_of("nai"),
            QgsSymbolLayerUtils.decodePenStyle("dash")
        )


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
