# -*- coding: utf-8 -*-

"""
Tests for military_symbology/maneuver_control_measures_2.py - the
second "Maneuver control measure symbols" section (Table H-XII,
H.5.14, Mini-Phase H6). See that module's own docstring for why it has
a "_2" suffix, what's skipped (Attack By Fire Position, Ambush), and
why two of its own measure types live on the LINES layer despite the
standard's own "Area" SIDC prefix.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsExpressionContext,
    QgsFeature,
    QgsGeometry,
    QgsGeometryGeneratorSymbolLayer,
    QgsMarkerLineSymbolLayer,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.maneuver_control_measures_2 import (
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    add_maneuver_control_measures_2_areas_layer,
    add_maneuver_control_measures_2_lines_layer,
    create_maneuver_control_measures_2_areas_layer,
    create_maneuver_control_measures_2_lines_layer,
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


class TestCreateManeuverControlMeasures2LinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_maneuver_control_measures_2_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["measure_type", "affiliation", "status", "length_km"]
        )


    def test_is_a_line_layer(self):

        layer = create_maneuver_control_measures_2_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_maneuver_control_measures_2_lines_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in LINE_MEASURE_TYPE_LABELS
            }
        )


    def test_attack_by_fire_position_is_a_back_side_plus_a_midpoint_arrow(self):

        # 2026-08-12, built from the maintainer's own dictated rules:
        # "Point 1 is the tip arrowhead. Points 2 and 3 define the
        # endpoints of the straight line on the back side... The rear of
        # the arrow should connect to the midpoint of the line between
        # points 2 and 3." Deferred through all of Mini-Phase H6 for
        # exactly that midpoint connection, which no other construction
        # in this appendix needed - so BOTH drawn pieces come from
        # geometry generators over the one 3-point digitized line,
        # rather than the line being drawn as digitized.
        layer = create_maneuver_control_measures_2_lines_layer()

        symbol = _rule_symbol_for(layer, "attack_by_fire_position")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        for i in (0, 1):

            self.assertIsInstance(
                symbol.symbolLayer(i),
                QgsGeometryGeneratorSymbolLayer
            )

        self.assertIn(
            "mct_attack_by_fire_back",
            symbol.symbolLayer(0).geometryExpression()
        )

        # The arrowhead rides the shaft's own last vertex (PT1), so it
        # inherits the shaft's rotation instead of needing a hand-
        # computed angle.
        shaft = symbol.symbolLayer(1)

        arrow_layers = [
            shaft.subSymbol().symbolLayer(i)
            for i in range(shaft.subSymbol().symbolLayerCount())
            if isinstance(shaft.subSymbol().symbolLayer(i), QgsMarkerLineSymbolLayer)
        ]

        self.assertEqual(len(arrow_layers), 1)
        self.assertEqual(
            arrow_layers[0].placements(),
            Qgis.MarkerLinePlacement.LastVertex
        )


    def test_attack_by_fire_arrow_is_always_perpendicular_to_the_back_line(self):

        # 2026-08-12 correction: "the arrow is not perpendicular to the
        # base, especially when PT2 and PT3 are not equidistant from
        # PT1, make the arrow always perpendicular halfway between PT2
        # and PT3" - the maintainer's own words. The first version drew
        # midpoint -> PT1, which only comes out perpendicular in the
        # special case where PT1 sits directly over the midpoint.
        military_symbology_functions.register()

        try:

            expression = QgsExpression("mct_attack_by_fire_shaft($geometry)")

            def shaft_for(p1, p2, p3):

                feature = QgsFeature()
                feature.setGeometry(
                    QgsGeometry.fromPolylineXY([
                        QgsPointXY(*p1), QgsPointXY(*p2), QgsPointXY(*p3)
                    ])
                )

                context = QgsExpressionContext()
                context.setFeature(feature)

                result = expression.evaluate(context)

                self.assertFalse(
                    expression.hasEvalError(), expression.evalErrorString()
                )

                points = result.asPolyline()
                self.assertEqual(len(points), 2)

                return points

            # PT1 directly over the midpoint - the case that was always
            # correct, and must stay byte-for-byte unchanged.
            points = shaft_for((10, 40), (0, 0), (20, 0))

            self.assertAlmostEqual(points[0].x(), 10.0, places=6)
            self.assertAlmostEqual(points[0].y(), 0.0, places=6)
            self.assertAlmostEqual(points[1].x(), 10.0, places=6)
            self.assertAlmostEqual(points[1].y(), 40.0, places=6)

            # PT1 far off to one side - the case that used to skew. The
            # arrow must still rise straight from the midpoint, with
            # only PT1's own PERPENDICULAR distance setting its length.
            points = shaft_for((95, 40), (0, 0), (20, 0))

            self.assertAlmostEqual(points[0].x(), 10.0, places=6)
            self.assertAlmostEqual(points[0].y(), 0.0, places=6)
            self.assertAlmostEqual(points[1].x(), 10.0, places=6)
            self.assertAlmostEqual(points[1].y(), 40.0, places=6)

            # Same, on an oblique back line: the arrow's own direction
            # must stay exactly normal to PT2 -> PT3 whatever PT1 does.
            # None of these may sit ON the line y = x - a collinear PT1
            # has no "towards PT1" side at all, and is covered
            # separately below.
            for p1 in ((0, 30), (60, 5), (-10, 25)):

                points = shaft_for(p1, (0, 0), (20, 20))

                back_dx, back_dy = 20.0, 20.0
                arrow_dx = points[1].x() - points[0].x()
                arrow_dy = points[1].y() - points[0].y()

                self.assertAlmostEqual(points[0].x(), 10.0, places=6)
                self.assertAlmostEqual(points[0].y(), 10.0, places=6)
                self.assertAlmostEqual(
                    back_dx * arrow_dx + back_dy * arrow_dy, 0.0, places=6
                )

            # A PT1 lying ON the back line has no side to point
            # towards, so both halves fall back to returning the
            # digitized geometry untouched rather than inventing a
            # direction. Pinned because it is easy to trip over by
            # accident - this very test did, with a PT1 that happened
            # to sit on y = x.
            feature = QgsFeature()
            feature.setGeometry(
                QgsGeometry.fromPolylineXY([
                    QgsPointXY(30, 30), QgsPointXY(0, 0), QgsPointXY(20, 20)
                ])
            )

            context = QgsExpressionContext()
            context.setFeature(feature)

            self.assertEqual(len(expression.evaluate(context).asPolyline()), 3)

        finally:

            military_symbology_functions.unregister()


    def test_attack_by_fire_wings_always_sweep_away_from_point_1(self):

        # "The back side of the symbol encompasses the firing position
        # while the arrowhead typically points at the target" - so the
        # wings must open AWAY from PT1 no matter which side of the
        # back line PT1 sits on, and no matter which order PT2/PT3 were
        # digitized in. Both were caught as real risks by the
        # Encirclement winding bug earlier the same day.
        military_symbology_functions.register()

        try:

            expression = QgsExpression("mct_attack_by_fire_back($geometry)")

            def wing_ys(p1, p2, p3):

                feature = QgsFeature()
                feature.setGeometry(
                    QgsGeometry.fromPolylineXY([
                        QgsPointXY(*p1), QgsPointXY(*p2), QgsPointXY(*p3)
                    ])
                )

                context = QgsExpressionContext()
                context.setFeature(feature)

                result = expression.evaluate(context)

                self.assertFalse(
                    expression.hasEvalError(), expression.evalErrorString()
                )

                points = result.asPolyline()

                # wing tip, PT2, PT3, wing tip
                self.assertEqual(len(points), 4)

                return points[0].y(), points[3].y()

            # PT1 above the back line -> both wings below it
            for a, b in (wing_ys((10, 40), (0, 0), (20, 0)),):
                pass
            above = wing_ys((10, 40), (0, 0), (20, 0))
            self.assertLess(above[0], 0)
            self.assertLess(above[1], 0)

            # PT2/PT3 digitized in reverse -> unchanged behaviour
            reversed_order = wing_ys((10, 40), (20, 0), (0, 0))
            self.assertLess(reversed_order[0], 0)
            self.assertLess(reversed_order[1], 0)

            # PT1 below the back line -> both wings flip above it
            below = wing_ys((10, -40), (0, 0), (20, 0))
            self.assertGreater(below[0], 0)
            self.assertGreater(below[1], 0)

        finally:

            military_symbology_functions.unregister()


    def test_support_by_fire_position_has_an_arrowhead_at_each_end(self):

        layer = create_maneuver_control_measures_2_lines_layer()

        symbol = _rule_symbol_for(layer, "support_by_fire_position")

        self.assertEqual(symbol.symbolLayerCount(), 3)

        for i in (1, 2):

            self.assertIsInstance(
                symbol.symbolLayer(i),
                QgsMarkerLineSymbolLayer
            )


    def test_search_area_has_two_arrowheads_and_a_vertex_a_label(self):

        layer = create_maneuver_control_measures_2_lines_layer()

        symbol = _rule_symbol_for(layer, "search_area_reconnaissance_area")

        self.assertEqual(symbol.symbolLayerCount(), 4)

        vertex_label = symbol.symbolLayer(3)
        font_layer = vertex_label.subSymbol().symbolLayer(0)

        self.assertEqual(font_layer.character(), "A")


    def test_simple_end_labelled_lines_use_the_expected_fixed_characters(self):

        layer = create_maneuver_control_measures_2_lines_layer()

        cases = {
            "bridgehead_line": "BL",
            "holding_line": "HL",
            "release_line": "RL",
        }

        for measure_type, character in cases.items():

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 3)

                for i in (1, 2):

                    label_layer = symbol.symbolLayer(i)
                    font_layer = label_layer.subSymbol().symbolLayer(0)

                    self.assertEqual(font_layer.character(), character)


    def test_simple_end_labelled_lines_keep_their_labels_upright(self):

        # 2026-08-12: "the label on both ends should be straight, in our
        # case one of the labels is inverted" - the maintainer's own
        # words. With the marker line's own rotateSymbols flag on, a
        # line digitized right-to-left renders BOTH its labels
        # upside-down, and an angled end segment tilts its own label -
        # confirmed by render. Applied to Bridgehead Line first, then to
        # Holding Line and Release Line the same day ("fix holding line
        # and release line as well"), so all three now share the one
        # upright treatment.
        layer = create_maneuver_control_measures_2_lines_layer()

        for measure_type in ("bridgehead_line", "holding_line", "release_line"):

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                for i in (1, 2):

                    self.assertFalse(symbol.symbolLayer(i).rotateSymbols())


    def test_airhead_line_label_is_a_fixed_centred_string(self):

        layer = create_maneuver_control_measures_2_lines_layer()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", "airhead_line")

        settings = layer.labeling().settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)

        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        self.assertEqual(result, "AIRHEAD LINE")

        # Not repeating/end-anchored - a single Line placement, unlike
        # every other labelled line in this appendix so far.
        self.assertEqual(
            settings.placement,
            Qgis.LabelPlacement.Line
        )

        # 2026-08-12: "the text is overlapping the line, it should be
        # above the line" - the maintainer's own words. The shared
        # helper defaults to OnLine (which Boundary and every masked
        # Field T label need); this label has no mask of its own, so
        # OnLine drew the line straight through the glyphs.
        flags = settings.lineSettings().placementFlags()

        self.assertTrue(flags & Qgis.LabelLinePlacementFlag.AboveLine)
        self.assertFalse(flags & Qgis.LabelLinePlacementFlag.OnLine)

        # 2026-08-12, same round: "change the colour as per affiliation
        # for the airhead line also" - the label had been rendering
        # black beside an affiliation-coloured line. Same H.5.3 hue
        # rules the drawn line itself already follows.
        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for affiliation, hex_color in expected.items():

            with self.subTest(affiliation=affiliation):

                coloured = QgsFeature(layer.fields())
                coloured.setAttribute("measure_type", "airhead_line")
                coloured.setAttribute("affiliation", affiliation)

                colour_context = layer.createExpressionContext()
                colour_context.setFeature(coloured)

                colour, ok = settings.dataDefinedProperties().valueAsColor(
                    QgsPalLayerSettings.Property.Color,
                    colour_context,
                    QColor(1, 2, 3)
                )

                self.assertTrue(ok)
                self.assertEqual(colour.name(), hex_color)


    def test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_maneuver_control_measures_2_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in LINE_MEASURE_TYPE_LABELS:

            symbol = _rule_symbol_for(layer, measure_type)
            stroke_layer = symbol.symbolLayer(0)

            # Attack By Fire Position draws through a geometry
            # generator (its shape bears no resemblance to the
            # digitized path), so its stroke - and therefore its
            # affiliation colour - lives on that generator's own
            # SUB-symbol rather than directly on symbolLayer(0).
            if isinstance(stroke_layer, QgsGeometryGeneratorSymbolLayer):

                stroke_layer = stroke_layer.subSymbol().symbolLayer(0)

            for affiliation, hex_color in expected.items():

                with self.subTest(measure_type=measure_type, affiliation=affiliation):

                    color, ok = _resolve_stroke_color(stroke_layer, layer, affiliation)

                    self.assertTrue(ok)
                    self.assertEqual(color.name(), hex_color)


    def test_length_km_default_value_recalculates_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_maneuver_control_measures_2_lines_layer()

            idx = layer.fields().indexOf("length_km")

            self.assertTrue(
                layer.defaultValueDefinition(idx).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateManeuverControlMeasures2AreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_maneuver_control_measures_2_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["measure_type", "affiliation", "status", "area_km2", "perimeter_km"]
        )


    def test_is_a_polygon_layer(self):

        layer = create_maneuver_control_measures_2_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_maneuver_control_measures_2_areas_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in AREA_MEASURE_TYPE_LABELS
            }
        )


    def test_encirclement_has_a_toothed_outline(self):

        # 2026-08-12: "it is not ticks across the perimeter but
        # triangles placed with their base on the perimeter, with about
        # 60% of the triangle base length gap between the triangles" -
        # the maintainer's own words, replacing the original "line"-
        # shape tick marker. Same-day follow-up: "the triangles are
        # filled, make them hollow; increase size of triangles by 20%;
        # make the perimeter touch the base of the triangles... the
        # triangles need to be rotated 180 deg, the base is on
        # perimeter, not tip" - see _ENCIRCLEMENT_TRIANGLE_BASE_MM's own
        # comment for the rotation/offset maths this produced.
        #
        # Same-day third round: "in qgis, when i make this, the
        # triangles are pointing the other way" - the apex direction
        # turned out to depend on the polygon's own digitized winding
        # order. The marker line now sits inside a QgsGeometryGenerator
        # SymbolLayer that normalises that winding first (see
        # _encirclement_symbol()'s own comment), so it's one level
        # deeper in the symbol tree than it used to be.
        layer = create_maneuver_control_measures_2_areas_layer()

        symbol = _rule_symbol_for(layer, "encirclement")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        generator_layer = symbol.symbolLayer(1)

        self.assertIsInstance(generator_layer, QgsGeometryGeneratorSymbolLayer)

        # Winding normalised BEFORE the markers are placed, so the
        # triangles point outward no matter which way the user drew the
        # polygon.
        self.assertIn(
            "force_polygon_ccw",
            generator_layer.geometryExpression()
        )

        tooth_layer = generator_layer.subSymbol().symbolLayer(0)

        self.assertIsInstance(tooth_layer, QgsMarkerLineSymbolLayer)

        self.assertEqual(
            tooth_layer.placements(),
            Qgis.MarkerLinePlacement.Interval
        )

        triangle_layer = tooth_layer.subSymbol().symbolLayer(0)

        self.assertIsInstance(triangle_layer, QgsSimpleMarkerSymbolLayer)
        self.assertEqual(
            triangle_layer.shape(),
            QgsSimpleMarkerSymbolLayerBase.Shape.Triangle
        )

        # Hollow, not filled - transparent fill, stroke only.
        self.assertEqual(triangle_layer.color().alpha(), 0)

        # Rotated 180 degrees so the base (not the tip) faces outward,
        # and offset by half the triangle's own real height so the
        # base - not the shape's own bounding-box centre - lands on
        # the perimeter.
        self.assertAlmostEqual(triangle_layer.angle(), 180, places=5)
        self.assertAlmostEqual(
            triangle_layer.offset().y(),
            -1.905,
            places=5
        )
        self.assertAlmostEqual(triangle_layer.offset().x(), 0, places=5)

        base = triangle_layer.size()

        # +20% over the original 3.0mm base.
        self.assertAlmostEqual(base, 3.6, places=5)

        # Interval (base-to-base repeat spacing) = base + 60% gap.
        self.assertAlmostEqual(
            tooth_layer.interval(),
            base * 1.6,
            places=5
        )


    def test_penetration_box_is_a_plain_outline(self):

        layer = create_maneuver_control_measures_2_areas_layer()

        symbol = _rule_symbol_for(layer, "penetration_box")

        self.assertEqual(symbol.symbolLayerCount(), 1)


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_maneuver_control_measures_2_areas_layer()

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

            layer = create_maneuver_control_measures_2_areas_layer()

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


class TestAddManeuverControlMeasures2Layers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_maneuver_control_measures_2_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_maneuver_control_measures_2_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        first = add_maneuver_control_measures_2_lines_layer(self.iface)

        result = add_maneuver_control_measures_2_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_maneuver_control_measures_2_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)
