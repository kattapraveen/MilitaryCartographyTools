# -*- coding: utf-8 -*-

"""
Tests for military_symbology/airspace_control_measures.py - the
Airspace Control Measures line/area/point layers (Table H-XIII,
Mini-Phase H7). The lines and areas are styled via a
QgsRuleBasedRenderer keyed on "measure_type"; the 26-entry point
vocabulary is milsymbol-rendered instead, on its own third layer. See
that module's own docstring for what's approximated (the corridor/route
family) and what's built for real (the zone/area family, IFF Off/On
Line, Base Defense Zone, and the points).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsExpressionContext,
    QgsFeature,
    QgsGeometry,
    QgsMarkerLineSymbolLayer,
    QgsPointXY,
    QgsProject,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.airspace_control_measures import (
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    POINTS_LAYER_NAME,
    POINT_ENTITY_LABELS,
    add_airspace_control_measures_areas_layer,
    add_airspace_control_measures_lines_layer,
    add_airspace_control_measures_points_layer,
    create_airspace_control_measures_areas_layer,
    create_airspace_control_measures_lines_layer,
    create_airspace_control_measures_points_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES


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


class TestCreateAirspaceControlMeasuresLinesLayer(QgisTestCase):

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

        layer = create_airspace_control_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "length_km",
            ]
        )


    def test_is_a_line_layer(self):

        layer = create_airspace_control_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_airspace_control_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in LINE_MEASURE_TYPE_LABELS
            }
        )


    def test_corridor_family_labels_prefix_the_type_abbreviation(self):

        layer = create_airspace_control_measures_lines_layer()

        cases = {
            "air_corridor": ("AC", "gold", "AC GOLD"),
            "low_level_transit_route": ("LLTR", "cobra", "LLTR COBRA"),
            "minimum_risk_route": ("MRR", "red", "MRR RED"),
            "safe_lane": ("SL", "lion", "SL LION"),
            "saafr": ("SAAFR", "blue", "SAAFR BLUE"),
            "transit_corridor": ("TC", "king", "TC KING"),
            "unmanned_aircraft_route": ("UA", "dragon", "UA DRAGON"),
        }

        for measure_type, (prefix, name, expected) in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, unique_designation=name
                    ),
                    expected
                )

                # Prefix alone when no name is given.
                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    prefix
                )


    def test_corridor_family_is_two_parallel_lines(self):

        # 2026-08-12: "it is two parallel lines with the unique
        # designation within the parallel lines" - the maintainer's own
        # words. This family had been a single thick line approximating
        # the standard's own ribbon; Table H-XIII (printed page 448)
        # draws two parallel lines with the label centred between them,
        # PT1/PT2 defining the CENTRELINE the user digitizes.
        layer = create_airspace_control_measures_lines_layer()

        for measure_type in (
            "air_corridor", "low_level_transit_route", "minimum_risk_route",
            "safe_lane", "saafr", "transit_corridor", "unmanned_aircraft_route",
        ):

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 2)

                offsets = []

                for index in range(2):

                    line_layer = symbol.symbolLayer(index)

                    offsets.append(line_layer.offset())

                    self.assertTrue(
                        line_layer.dataDefinedProperties().hasProperty(
                            QgsSymbolLayer.Property.StrokeStyle
                        )
                    )

                # Equal and opposite about the digitized centreline, so
                # the label sitting ON that centreline lands between
                # them.
                self.assertAlmostEqual(offsets[0], -offsets[1], places=6)
                self.assertNotAlmostEqual(offsets[0], 0.0, places=6)


    def test_corridor_labels_sit_between_the_lines_and_repeat(self):

        # The label rides the digitized centreline (OnLine placement),
        # which is exactly between the two offset lines. It repeats so
        # that "in case of multiple line segments the AC+unique_
        # designator should be in all segments if it fits" - PAL places
        # a repeat only where the text actually fits, so short segments
        # go unlabelled rather than overprinting.
        layer = create_airspace_control_measures_lines_layer()

        settings = layer.labeling().settings()

        self.assertEqual(settings.placement, Qgis.LabelPlacement.Line)
        self.assertGreater(settings.repeatDistance, 0)
        self.assertEqual(
            settings.repeatDistanceUnit,
            Qgis.RenderUnit.Millimeters
        )

        self.assertTrue(
            settings.lineSettings().placementFlags()
            & Qgis.LabelLinePlacementFlag.OnLine
        )


    def test_base_defense_zone_is_a_two_point_circle(self):

        # 2026-08-12: "make it a two point circle, one for the center
        # and other for radius" - the maintainer's own words. This
        # DEPARTS from the standard, which says the symbol "requires
        # one anchor point" and is "Static" (a fixed-size circle) -
        # which is exactly why it had been skipped when this module was
        # first built. A second point for the radius makes it sizable.
        layer = create_airspace_control_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "base_defense_zone")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        expression = symbol.symbolLayer(0).geometryExpression()

        self.assertIn("make_circle", expression)
        self.assertIn("point_n($geometry, 1)", expression)
        self.assertIn("point_n($geometry, 2)", expression)

        # "BDZ" rides the centre vertex as a marker, not this layer's
        # own shared labelling - that is set up for the corridors'
        # along-the-line repeating labels.
        centre = symbol.symbolLayer(1)

        self.assertEqual(
            centre.placements(),
            Qgis.MarkerLinePlacement.FirstVertex
        )
        self.assertFalse(centre.rotateSymbols())


    def test_base_defense_zone_circle_is_centred_and_sized_by_its_points(self):

        military_symbology_functions.register()

        try:

            layer = create_airspace_control_measures_lines_layer()
            symbol = _rule_symbol_for(layer, "base_defense_zone")

            feature = QgsFeature(layer.fields())
            feature.setGeometry(
                QgsGeometry.fromPolylineXY([
                    QgsPointXY(10, 20),   # centre
                    QgsPointXY(13, 24),   # radius point - distance 5
                ])
            )

            context = QgsExpressionContext()
            context.setFeature(feature)

            circle = QgsExpression(
                symbol.symbolLayer(0).geometryExpression()
            ).evaluate(context)

            box = circle.boundingBox()

            self.assertAlmostEqual(box.center().x(), 10.0, places=3)
            self.assertAlmostEqual(box.center().y(), 20.0, places=3)
            self.assertAlmostEqual(box.width(), 10.0, places=2)
            self.assertAlmostEqual(box.height(), 10.0, places=2)


        finally:

            military_symbology_functions.unregister()


    def test_weapons_free_zone_hatch_is_tightened_coloured_and_maskable(self):

        # 2026-08-12: "the hashing can be a bit closer say by 30%, and
        # the text inside needs to have a mask so that it is readable".
        # The colour fix came out of the same round: a data-defined
        # StrokeColor set on the FILL layer is silently ignored - a
        # QgsLinePatternFillSymbolLayer paints through a sub-symbol -
        # so every WFZ had been hatched black beside its own correctly
        # coloured outline.
        layer = create_airspace_control_measures_areas_layer()

        symbol = _rule_symbol_for(layer, "weapons_free_zone")

        hatch = symbol.symbolLayer(symbol.symbolLayerCount() - 1)

        self.assertAlmostEqual(hatch.distance(), 2.5 * 0.7, places=6)

        self.assertTrue(
            hatch.subSymbol().symbolLayer(0).dataDefinedProperties().hasProperty(
                QgsSymbolLayer.Property.StrokeColor
            )
        )

        # Stable id so the label can cut a real gap in the hatch.
        self.assertEqual(hatch.id(), "weapons_free_zone_hatch")

        # Each of settings()/format() returns BY VALUE, so every
        # intermediate is held in its own variable. Chaining them lets
        # the temporary's C++ object be collected out from under the
        # next call and SEGFAULTS the interpreter - the same trap
        # already documented in test_offensive_control_measures.py, and
        # walked straight into again here.
        settings = layer.labeling().settings()
        text_format = settings.format()
        mask = text_format.mask()

        self.assertTrue(mask.enabled())
        self.assertIn(
            "weapons_free_zone_hatch",
            [ref.symbolLayerIdV2() for ref in mask.maskedSymbolLayers()]
        )


    def test_iff_line_labels_stay_upright(self):

        # 2026-08-12: "the text is inverted depending on how the line is
        # made, it should be right way up" - the maintainer's own words.
        # The same defect already fixed for Bridgehead/Holding/Release
        # Line: with the marker line's own rotateSymbols flag on, a line
        # digitized right-to-left renders BOTH end labels upside-down.
        layer = create_airspace_control_measures_lines_layer()

        for measure_type in ("iff_on_line", "iff_off_line"):

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                for index in (1, 2):

                    self.assertFalse(symbol.symbolLayer(index).rotateSymbols())


    def test_zone_labels_anchor_inside_the_polygons_top_left(self):

        # 2026-08-12: "the zones names and unique identifier ... just
        # need to be on to top left corner of polygon, within it" - the
        # maintainer's own words. The label content was already right;
        # only its position was, defaulting to the polygon's centre.
        layer = create_airspace_control_measures_areas_layer()

        settings = layer.labeling().settings()

        self.assertTrue(settings.geometryGeneratorEnabled)
        self.assertIn("mct_area_label_anchor", settings.geometryGenerator)
        self.assertEqual(settings.geometryGeneratorType, Qgis.GeometryType.Point)

        # Hangs down-and-right off the anchor, so it stays inside
        # rather than straddling the polygon's own top edge.
        self.assertEqual(
            settings.pointSettings().quadrant(),
            Qgis.LabelQuadrantPosition.BelowRight
        )


    def test_area_label_anchor_stays_inside_awkward_polygons(self):

        # A bounding-box corner is NOT usable directly - for anything
        # non-rectangular it falls outside the shape, which would put
        # the label off the polygon entirely. Every anchor must be
        # WITHIN its own polygon, however awkward the outline.
        military_symbology_functions.register()

        try:

            expression = QgsExpression("mct_area_label_anchor($geometry)")

            shapes = {
                "square": [(0, 0), (10, 0), (10, 10), (0, 10)],
                # L-shape whose own bbox top-left is a notch, not solid
                "L": [(0, 0), (10, 0), (10, 4), (4, 4), (4, 10), (0, 10)],
                # triangle with an empty top-left
                "triangle": [(0, 0), (10, 0), (10, 10)],
                # concave arrowhead
                "concave": [(0, 0), (10, 5), (0, 10), (3, 5)],
            }

            for name, ring in shapes.items():

                with self.subTest(shape=name):

                    polygon = QgsGeometry.fromPolygonXY(
                        [[QgsPointXY(*point) for point in ring]]
                    )

                    feature = QgsFeature()
                    feature.setGeometry(polygon)

                    context = QgsExpressionContext()
                    context.setFeature(feature)

                    anchor = expression.evaluate(context)

                    self.assertFalse(
                        expression.hasEvalError(), expression.evalErrorString()
                    )

                    # Inside the polygon...
                    self.assertTrue(
                        polygon.contains(anchor),
                        f"{name}: anchor fell outside the polygon"
                    )

                    # ...and in its upper-left half, not at the centre.
                    box = polygon.boundingBox()
                    point = anchor.asPoint()

                    self.assertGreater(point.y(), box.center().y())

        finally:

            military_symbology_functions.unregister()


    def test_iff_lines_use_the_expected_fixed_end_labels(self):

        layer = create_airspace_control_measures_lines_layer()

        cases = {
            "iff_off_line": "IFF OFF",
            "iff_on_line": "IFF ON",
        }

        for measure_type, character in cases.items():

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 3)

                for i in (1, 2):

                    label_layer = symbol.symbolLayer(i)

                    self.assertIsInstance(label_layer, QgsMarkerLineSymbolLayer)

                    font_layer = label_layer.subSymbol().symbolLayer(0)

                    self.assertEqual(font_layer.character(), character)

                # IFF lines carry no general designation label - they
                # rely entirely on the fixed end markers above.
                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    ""
                )


    def test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_airspace_control_measures_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in ("air_corridor", "iff_off_line"):

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

            layer = create_airspace_control_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            self.assertTrue(
                layer.defaultValueDefinition(idx).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateAirspaceControlMeasuresAreasLayer(QgisTestCase):

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

        layer = create_airspace_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_airspace_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_airspace_control_measures_areas_layer()

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

        layer = create_airspace_control_measures_areas_layer()

        cases = {
            "hidacz": ("HIDACZ", "32aadc", "HIDACZ\n32AADC"),
            "roz": ("ROZ", "11 ada bde", "ROZ\n11 ADA BDE"),
            "aarroz": ("AARROZ", "2id", "AARROZ\n2ID"),
            "ua_roz": ("UA-ROZ", "mnd(n)", "UA-ROZ\nMND(N)"),
            "wez": ("WEZ", "21 ada bn", "WEZ\n21 ADA BN"),
            "fez": ("FEZ", "atf", "FEZ\nATF"),
            "jez": ("JEZ", "atf", "JEZ\nATF"),
            "mez": ("MEZ", "2-4 ada bn", "MEZ\n2-4 ADA BN"),
            "lomez": ("LOMEZ", "aacc", "LOMEZ\nAACC"),
            "himez": ("HIMEZ", "aacc", "HIMEZ\nAACC"),
            "shoradez": ("SHORADEZ", "atf", "SHORADEZ\nATF"),
            "weapons_free_zone": ("WFZ", "atf", "WFZ\nATF"),
        }

        for measure_type, (prefix, name, expected) in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, unique_designation=name
                    ),
                    expected
                )

                # Prefix alone when no name is given.
                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    prefix
                )


    def test_weapons_free_zone_has_a_hatched_fill_layer(self):

        layer = create_airspace_control_measures_areas_layer()

        symbol = _rule_symbol_for(layer, "weapons_free_zone")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        hatch_layer = symbol.symbolLayer(1)

        self.assertEqual(
            hatch_layer.layerType(),
            "LinePatternFill"
        )


    def test_other_areas_are_a_plain_unfilled_outline(self):

        layer = create_airspace_control_measures_areas_layer()

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            if measure_type == "weapons_free_zone":
                continue

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 1)


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_airspace_control_measures_areas_layer()

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

            layer = create_airspace_control_measures_areas_layer()

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


class TestAddAirspaceControlMeasuresLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_airspace_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_airspace_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        first = add_airspace_control_measures_lines_layer(self.iface)

        result = add_airspace_control_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_airspace_control_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)


    def test_points_layer_is_created_and_added(self):

        layer = add_airspace_control_measures_points_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


class TestCreateAirspaceControlMeasuresPointsLayer(QgisTestCase):

    """
    Table H-XIII's own "Points" sub-section (printed pages 459-464),
    moved here 2026-08-12 out of the shared control_measure_points.py
    layer at the project maintainer's own request.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()


    def test_has_the_expected_fields(self):

        layer = create_airspace_control_measures_points_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["affiliation", "entity", "status", "unique_designation"]
        )


    def test_is_a_point_layer(self):

        layer = create_airspace_control_measures_points_layer()

        self.assertEqual(layer.geometryType().name, "Point")


    def test_covers_every_code_the_table_lists_from_180000_to_182500(self):

        # The table's own point codes run in an unbroken 100-step
        # sequence, so the vocabulary can be checked against the
        # standard directly rather than against itself. 180000 (the
        # generic "Airspace Control Points" parent) was missing from
        # sidc.py entirely until this move.
        codes = sorted(
            ENTITIES["control_measure"][entity]
            for entity in POINT_ENTITY_LABELS
        )

        self.assertEqual(
            codes,
            [f"18{step:02d}00" for step in range(0, 26)]
        )


    def test_entity_uses_a_value_map_widget_defaulting_to_air_control_point(self):

        layer = create_airspace_control_measures_points_layer()

        idx = layer.fields().indexOf("entity")

        self.assertEqual(
            layer.editorWidgetSetup(idx).config()["map"],
            {label: value for value, label in POINT_ENTITY_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'air_control_point'"
        )


    def test_only_the_downed_aircrew_pickup_point_is_anchored_at_its_tip(self):

        # Its own draw rules: "The point defines the tip of the
        # inverted cone" - every other entry in this table is a
        # "Center Point". Confirmed by probe render: 180300's own
        # rendered viewBox (56 -64 88 168) is identical to Point of
        # Departure's, which offensive_control_measures.py already
        # anchors "bottom" for exactly this reason.
        layer = create_airspace_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        anchors = {}

        for entity in POINT_ENTITY_LABELS:

            feature = QgsFeature(layer.fields())
            feature.setAttribute("affiliation", "friend")
            feature.setAttribute("entity", entity)
            feature.setAttribute("status", "present")

            context = layer.createExpressionContext()
            context.setFeature(feature)

            value, ok = svg_layer.dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.VerticalAnchor,
                context,
                ""
            )

            self.assertTrue(ok)

            anchors[entity] = value

        self.assertEqual(anchors.pop("downed_aircrew_pickup_point"), "bottom")

        self.assertEqual(set(anchors.values()), {"center"})


    def test_only_pop_up_point_is_drawn_at_a_multiplied_size(self):

        # 180400's own "PUP" text sits outside the circle, widening its
        # viewBox to 198x108 against the bars family's 88x148 - and
        # QGIS reads a marker's size as its WIDTH, so at a fixed 8mm it
        # draws at roughly half its siblings' scale. Doubled on the
        # maintainer's own instruction ("pop up point can be doubled in
        # size"); every other entry stays at the base size.
        layer = create_airspace_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        sizes = {}

        for entity in POINT_ENTITY_LABELS:

            feature = QgsFeature(layer.fields())
            feature.setAttribute("affiliation", "friend")
            feature.setAttribute("entity", entity)
            feature.setAttribute("status", "present")

            context = layer.createExpressionContext()
            context.setFeature(feature)

            value, ok = svg_layer.dataDefinedProperties().valueAsDouble(
                QgsSymbolLayer.Property.Size,
                context,
                0.0
            )

            self.assertTrue(ok)

            sizes[entity] = value

        self.assertEqual(sizes.pop("pop_up_point"), 16.0)

        self.assertEqual(set(sizes.values()), {8.0})


    def test_only_pop_up_point_is_offset_onto_its_own_circle(self):

        # Same root cause as the size multiplier above: the "PUP" text
        # hangs off to the RIGHT, so milsymbol draws the circle at
        # x=100 inside a 46..244 viewBox whose own midpoint is x=145 -
        # and QGIS centres a marker on its VIEWBOX, which put the click
        # in the white space between circle and text. The standard
        # anchors the circle ("The center point defines the center of
        # the symbol"), so the symbol shifts right by those 45 units.
        #
        # Verified by probe render, not arithmetic alone: before the
        # offset the circle measured 43.5 px left of the anchor at 300
        # DPI, after it 0.5 px - i.e. sub-pixel, that half being the
        # pixel-centre convention.
        layer = create_airspace_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        offsets = {}

        for entity in POINT_ENTITY_LABELS:

            feature = QgsFeature(layer.fields())
            feature.setAttribute("affiliation", "friend")
            feature.setAttribute("entity", entity)
            feature.setAttribute("status", "present")

            context = layer.createExpressionContext()
            context.setFeature(feature)

            value, ok = svg_layer.dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.Offset,
                context,
                ""
            )

            self.assertTrue(ok)

            offsets[entity] = value

        pop_up_x, pop_up_y = offsets.pop("pop_up_point").split(",")

        # 16 mm wide (8 mm doubled) x (145-100)/198 of that width.
        self.assertAlmostEqual(float(pop_up_x), 3.6364, places=3)
        self.assertEqual(float(pop_up_y), 0.0)

        self.assertEqual(set(offsets.values()), {"0,0"})


    def test_every_entity_resolves_to_a_real_rendered_symbol(self):

        layer = create_airspace_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        for entity in POINT_ENTITY_LABELS:

            with self.subTest(entity=entity):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("affiliation", "friend")
                feature.setAttribute("entity", entity)
                feature.setAttribute("status", "present")

                context = layer.createExpressionContext()
                context.setFeature(feature)

                path, ok = svg_layer.dataDefinedProperties().valueAsString(
                    QgsSymbolLayer.Property.Name,
                    context,
                    ""
                )

                self.assertTrue(ok)
                self.assertTrue(path.startswith("base64:"))


    def test_a_blank_designation_still_renders_the_icon(self):

        # QGIS short-circuits an entire function call to NULL the
        # moment any argument is NULL, which would blank the whole
        # icon rather than just its text - hence coalesce(...,'') in
        # _POINTS_SIDC_EXPRESSION. Regression-pins that.
        layer = create_airspace_control_measures_points_layer()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", "tacan")
        feature.setAttribute("status", "present")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name,
            context,
            ""
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_designations_reach_the_three_icons_that_define_a_text_slot(self):

        # A probe render of all 26 codes showed only these three accept
        # a designation at all, all via milsymbol's plain
        # `uniqueDesignation` - matching the standard's own templates,
        # which show a Field T box on exactly these three and no other.
        # Checked by rendering with and without the designation and
        # requiring the output to actually differ, rather than trusting
        # that passing the option did anything.
        import base64

        layer = create_airspace_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        def rendered(entity, designation):

            feature = QgsFeature(layer.fields())
            feature.setAttribute("affiliation", "friend")
            feature.setAttribute("entity", entity)
            feature.setAttribute("status", "present")
            feature.setAttribute("unique_designation", designation)

            context = layer.createExpressionContext()
            context.setFeature(feature)

            path, ok = svg_layer.dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.Name,
                context,
                ""
            )

            self.assertTrue(ok)

            return base64.b64decode(
                path[len("base64:"):]
            ).decode("utf-8")

        for entity in ("air_control_point", "communications_checkpoint", "tacan"):

            with self.subTest(entity=entity):

                svg = rendered(entity, "a7")

                # upper() per H.5.4's "all text labeling in upper case".
                self.assertIn(">A7<", svg)
                self.assertNotIn(">a7<", svg)

                self.assertNotEqual(svg, rendered(entity, ""))
