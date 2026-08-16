# -*- coding: utf-8 -*-

"""
Tests for military_symbology/mission_task_control_measures.py -
Table H-XXIV, Mini-Phase H21 (points only).

Military Cartography Tools
"""

import base64

import math

import re

from qgis.PyQt.QtCore import Qt

from qgis.core import (Qgis, QgsCoordinateReferenceSystem, QgsExpression,
                       QgsGeometry, QgsPalLayerSettings,
                       QgsExpressionContext, QgsFeature, QgsProject,
                       QgsSymbolLayer)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology.mission_task_control_measures import (
    POINTS_LAYER_NAME,
    POINT_ENTITY_CODES,
    POINT_ENTITY_LABELS,
    POINT_MARKER_SIZE_SCALES,
    BYPASS_CONSTRUCTION_MEASURE_TYPES,
    DELAY_CONSTRUCTION_MEASURE_TYPES,
    LABELLED_MEASURE_TYPES,
    COUNTERATTACK_MEASURE_TYPES,
    FOLLOW_CONSTRUCTION_MEASURE_TYPES,
    SECURITY_CONSTRUCTION_MEASURE_TYPES,
    LINE_LETTERS,
    LINE_MEASURE_TYPE_CODES,
    LINE_MEASURE_TYPE_LABELS,
    create_mission_task_lines_layer,
    TABLE_H_XXIV_REMAINING,
    add_mission_task_points_layer,
    create_mission_task_points_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES
from MilitaryCartographyTools.military_symbology.supply_points import (
    CONVOY_BODY_HEIGHT_MM,
    CONVOY_HEAD_LENGTH_MM,
)

WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

# milsymbol's unknown-icon fallback - a stable fragment of the path it
# draws when handed a SIDC it cannot resolve. Present iff the symbol
# did NOT render.
_MILSYMBOL_UNKNOWN_ICON_MARK = "94.8206,78.1372"


class TestMissionTaskVocabulary(QgisTestCase):

    def test_only_the_three_point_tasks_are_built(self):

        # Destroy, Interdict and Neutralize are the only rows of Table
        # H-XXIV whose DRAW RULES ask for ONE anchor point and a
        # centred glyph. Every other row is a multi-anchor arrow or
        # bracket, and milsymbol has an icon for none of them.
        self.assertEqual(
            POINT_ENTITY_CODES,
            {
                "destroy_point": "340900",
                "interdict_point": "341400",
                "neutralize_point": "341600",
            }
        )


    def test_the_unbuilt_rows_are_recorded_not_forgotten(self):

        # 3 points + 24 line tasks + 2 still unbuilt = the table's own
        # 29 rows, and **Appendix H is complete**: the two rows left
        # are the table's own section parent and the Security group
        # parent, both "N/A" for TEMPLATE and EXAMPLE, and neither will
        # ever be built. They stay on the record so this arithmetic
        # still runs.
        self.assertEqual(len(TABLE_H_XXIV_REMAINING), 2)

        for code in TABLE_H_XXIV_REMAINING:

            self.assertIn("N/A", TABLE_H_XXIV_REMAINING[code])

        self.assertEqual(
            len(POINT_ENTITY_CODES)
            + len(LINE_MEASURE_TYPE_CODES)
            + len(TABLE_H_XXIV_REMAINING),
            29
        )

        # Nothing is claimed as both built and unbuilt.
        self.assertEqual(
            set(LINE_MEASURE_TYPE_CODES.values())
            & set(TABLE_H_XXIV_REMAINING),
            set()
        )

        self.assertEqual(
            set(POINT_ENTITY_CODES.values()) & set(TABLE_H_XXIV_REMAINING),
            set()
        )


    def test_the_task_names_that_clash_are_keyed_by_code_everywhere(self):

        # Several mission tasks share a NAME with an obstacle effect or
        # maneuver control measure that has its own different code and
        # drawn form - conflating the two is a defect this project has
        # been reported for once already. Both the built record and the
        # unbuilt one are keyed by CODE, so the two can never be
        # matched up by name alone.
        #
        # Block, Disrupt and Fix have SHIPPED as mission tasks now, so
        # they belong to the built record; the rest are still unbuilt.
        # Every one has to appear in exactly one of the two.
        for name in ("Block", "Breach", "Bypass", "Canalize", "Disrupt",
                     "Fix", "Penetrate", "Seize", "Withdraw"):

            built = name in LINE_MEASURE_TYPE_LABELS.values()

            unbuilt = name in TABLE_H_XXIV_REMAINING.values()

            self.assertTrue(
                built or unbuilt,
                f"{name} is recorded neither as built nor as unbuilt"
            )

            self.assertFalse(
                built and unbuilt,
                f"{name} is recorded as both built and unbuilt"
            )



    def test_every_entity_is_registered_in_sidc(self):

        for entity, code in POINT_ENTITY_CODES.items():

            self.assertEqual(
                ENTITIES["control_measure"].get(entity), code, entity
            )


class TestMissionTaskPointsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_the_layer_builds_without_echelon_or_headquarters(self):

        layer = create_mission_task_points_layer()

        self.assertTrue(layer.isValid())

        fields = {field.name() for field in layer.fields()}

        self.assertNotIn("echelon", fields)
        self.assertNotIn("headquarters", fields)

        # Field T, which every row of the table carries.
        self.assertIn("unique_designation", fields)


    def test_every_entity_renders_a_real_glyph(self):

        # The defect class this project has hit repeatedly: an entity
        # whose SIDC does not resolve still returns a perfectly
        # well-formed base64 path, drawing milsymbol's unknown icon.
        for entity in POINT_ENTITY_LABELS:

            expression = QgsExpression(
                "mct_sidc_svg(mct_build_sidc('friend', '{}', "
                "'control_measure', 'unspecified', 'present', false))".format(
                    entity
                )
            )

            path = expression.evaluate()

            self.assertFalse(
                expression.hasEvalError(), expression.evalErrorString()
            )

            svg = base64.b64decode(
                path[len("base64:"):]
            ).decode("utf-8")

            self.assertNotIn(_MILSYMBOL_UNKNOWN_ICON_MARK, svg, entity)


    def test_no_two_entities_draw_the_same_glyph(self):

        drawn = {}

        for entity in POINT_ENTITY_LABELS:

            svg = base64.b64decode(
                QgsExpression(
                    "mct_sidc_svg(mct_build_sidc('friend', '{}', "
                    "'control_measure', 'unspecified', 'present', "
                    "false))".format(entity)
                ).evaluate()[len("base64:"):]
            ).decode("utf-8")

            self.assertNotIn(
                svg, drawn,
                f"{entity} draws the same glyph as {drawn.get(svg)}"
            )

            drawn[svg] = entity


    def test_adding_the_layer_inserts_exactly_one(self):

        layer = add_mission_task_points_layer(self.iface)

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)), 1
        )


    def test_a_second_add_warns_instead_of_replacing(self):

        first = add_mission_task_points_layer(self.iface)

        self.assertIsNone(add_mission_task_points_layer(self.iface))

        matching = QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
        self.assertEqual(len(self.iface.messageBar().calls), 1)


class TestMissionTaskMarkerSize(QgisTestCase):

    """
    "mission task points - increase size by 30% like cbrn events."

    All three icons are a wide, low 208x128 - the widest box in the
    whole control-measure set - and QGIS sizes an SVG marker by its
    WIDTH, so they drew at about 42% of a supply point's scale.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _drawn_icon_scale(self, layer, entity, designation=""):

        """
        Millimetres of page per milsymbol icon unit - size / width,
        both taken from the renderer's own evaluated properties rather
        than restated.
        """

        feature = QgsFeature(layer.fields())
        feature.setAttribute("entity", entity)
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("status", "present")
        feature.setAttribute("unique_designation", designation)

        context = layer.createExpressionContext()
        context.setFeature(feature)

        properties = layer.renderer().symbol().symbolLayer(
            0
        ).dataDefinedProperties()

        size, ok = properties.valueAsDouble(
            QgsSymbolLayer.Property.Size, context, 0.0
        )

        self.assertTrue(ok)

        path, ok = properties.valueAsString(
            QgsSymbolLayer.Property.Name, context, ""
        )

        self.assertTrue(ok)

        markup = base64.b64decode(
            path[len("base64:"):]
        ).decode("utf-8")

        width = float(
            re.search(r'viewBox="\S+ \S+ (\S+) \S+"', markup).group(1)
        )

        return size / width


    def test_all_three_are_scaled_and_nothing_else_is(self):

        self.assertEqual(set(POINT_MARKER_SIZE_SCALES), set(POINT_ENTITY_CODES))

        self.assertEqual(set(POINT_MARKER_SIZE_SCALES.values()), {1.30})


    def test_each_icon_is_drawn_thirty_percent_larger(self):

        layer = create_mission_task_points_layer()

        for entity in POINT_ENTITY_LABELS:

            plain_width = QgsExpression(
                "mct_sidc_svg_width('{}')".format(
                    QgsExpression(
                        "mct_build_sidc('friend', '{}', 'control_measure', "
                        "'unspecified', 'present', false)".format(entity)
                    ).evaluate()
                )
            ).evaluate(QgsExpressionContext())

            self.assertAlmostEqual(
                self._drawn_icon_scale(layer, entity),
                1.30 * 8.0 / plain_width,
                places=6,
                msg=entity,
            )


    def test_the_bump_survives_a_designation(self):

        # It has to compose with the amplifier compensation, which
        # scales the marker the other way to hold the icon still.
        layer = create_mission_task_points_layer()

        for entity in POINT_ENTITY_LABELS:

            scales = [
                self._drawn_icon_scale(layer, entity, designation)
                for designation in ("", "A", "LONGER")
            ]

            for scale in scales[1:]:

                self.assertAlmostEqual(scale, scales[0], places=6, msg=entity)


class TestIsolateTriangles(QgisTestCase):

    """
    Isolate (341500) - Secure's own arc, with inward triangles standing
    on it.

    "triangles start 30 deg from pt2, and end 30 deg before the arrow
    head, size of triangles (base to tip) 1/3 of radius" - the
    maintainer's own instruction. The spacing and the base width are
    the standard's template's, measured off the rendered page; see
    _ISOLATE_TOOTH_STEP_DEG.
    """

    # PT1 the centre, PT2 due north at radius 10 - so the sweep starts
    # at a bearing of 90 degrees and runs CLOCKWISE, like Retain's.
    _ISOLATE = "LineString(0 0, 0 10)"

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _triangles(self, wkt=None):

        return QgsExpression(
            "mct_isolate_teeth(geom_from_wkt('{}'))".format(wkt or self._ISOLATE)
        ).evaluate().asMultiPolyline()


    @staticmethod
    def _bearing(point):

        return math.degrees(math.atan2(point.y(), point.x()))


    @staticmethod
    def _clockwise_from(bearing, reference):

        """How far clockwise `bearing` sits from `reference`, 0 to 360."""

        return (reference - bearing) % 360.0


    def test_seven_triangles_run_from_thirty_degrees_to_three_hundred(self):

        triangles = self._triangles()

        self.assertEqual(len(triangles), 7)

        for index, triangle in enumerate(triangles):

            apex = triangle[1]

            # Clockwise from PT2's own 90 degrees.
            self.assertAlmostEqual(
                self._clockwise_from(self._bearing(apex), 90.0),
                30.0 + index * 45.0,
                places=4,
                msg="triangle {}".format(index)
            )

        # The last one stands 30 degrees short of the arrowhead, which
        # sits 330 degrees round.
        self.assertAlmostEqual(
            self._clockwise_from(self._bearing(triangles[-1][1]), 90.0),
            300.0,
            places=4
        )


    def test_each_apex_reaches_a_third_of_the_radius_inward(self):

        for triangle in self._triangles():

            apex = triangle[1]

            self.assertAlmostEqual(
                math.hypot(apex.x(), apex.y()), 10.0 * 2.0 / 3.0, places=6
            )


    def test_the_base_is_not_drawn_and_its_corners_sit_on_the_perimeter(self):

        for triangle in self._triangles():

            # Corner, apex, corner - an OPEN run. The arc it stands on
            # is the base, so a fourth point closing the ring would
            # draw the one line the instruction says not to.
            self.assertEqual(len(triangle), 3)

            self.assertNotEqual(
                (triangle[0].x(), triangle[0].y()),
                (triangle[-1].x(), triangle[-1].y())
            )

            for corner in (triangle[0], triangle[-1]):

                self.assertAlmostEqual(
                    math.hypot(corner.x(), corner.y()), 10.0, places=6
                )


    def test_the_triangles_hold_their_shape_at_any_radius(self):

        # Base and height both scale with the radius, so the arc each
        # base subtends is a constant - which is what keeps a large
        # Isolate from looking like a different symbol to a small one.
        subtended = []

        for wkt in ("LineString(0 0, 0 10)", "LineString(0 0, 0 1000)"):

            triangle = self._triangles(wkt)[0]

            subtended.append(
                self._clockwise_from(
                    self._bearing(triangle[0]), self._bearing(triangle[-1])
                )
            )

        self.assertAlmostEqual(subtended[0], subtended[1], places=6)

        self.assertAlmostEqual(
            subtended[0], 2.0 * math.degrees(math.asin(1.0 / 6.0)), places=6
        )


    def test_a_degenerate_geometry_is_handed_back_untouched(self):

        # PT1 == PT2 leaves no radius. It has to fall through rather
        # than raise mid-render, the same way Retain's own arc does.
        self.assertIsNotNone(
            QgsExpression(
                "mct_isolate_teeth(geom_from_wkt('LineString(0 0, 0 0)'))"
            ).evaluate()
        )


class TestIsolateSymbol(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_isolate_draws_the_arc_the_triangles_and_the_arrowhead(self):

        layer = create_mission_task_lines_layer()

        symbol = None

        for child in layer.renderer().rootRule().children():

            if child.filterExpression() == "\"measure_type\" = 'isolate'":
                symbol = child.symbol()

        self.assertIsNotNone(symbol)

        expressions = [
            symbol.symbolLayer(index).geometryExpression()
            for index in range(symbol.symbolLayerCount())
        ]

        # Secure's own arc, Secure's own arrowhead tail, and the
        # triangles standing on that arc.
        self.assertIn("mct_retain_arc($geometry)", expressions)
        self.assertIn("mct_retain_arc_end($geometry)", expressions)
        self.assertIn("mct_isolate_teeth($geometry)", expressions)


    def test_isolate_carries_the_letter_i_on_the_perimeter(self):

        layer = create_mission_task_lines_layer()

        for rule in layer.labeling().rootRule().children():

            if rule.description() != "isolate":
                continue

            settings = rule.settings()

            self.assertEqual(settings.fieldName, "'I'")

            self.assertEqual(
                settings.geometryGenerator,
                "mct_secure_letter_point($geometry)"
            )

            return

        self.fail("no labelling rule for isolate")


class TestDelay(QgisTestCase):

    """
    Delay (340800) - the first line task on this layer that borrows no
    other symbol's construction.

    "user clicks pt1, pt2 and pt3. arrowhead at pt1, shaft from pt1 to
    pt2, then join pt2 and pt3 with a semicircle, pt2 to pt3 being the
    diameter; letter D masked, on the shaft between pt1 and pt2" - the
    maintainer's own instruction.
    """

    # Shaft running due east from PT1 to PT2, PT3 due north of PT2 -
    # the template's own layout, mirrored so the arithmetic is easy.
    _DELAY = "LineString(0 0, 10 0, 10 6)"

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    @staticmethod
    def _evaluate(expression, wkt):

        return QgsExpression(
            "{}(geom_from_wkt('{}'))".format(expression, wkt)
        ).evaluate()


    def test_the_run_starts_at_pt1_and_ends_square_to_the_shaft(self):

        run = self._evaluate("mct_delay_geometry", self._DELAY).asPolyline()

        self.assertAlmostEqual(run[0].x(), 0.0, places=6)
        self.assertAlmostEqual(run[0].y(), 0.0, places=6)

        self.assertAlmostEqual(run[-1].x(), 10.0, places=6)
        self.assertAlmostEqual(run[-1].y(), 6.0, places=6)


    def test_the_arc_takes_pt2_to_pt3_as_its_diameter(self):

        run = self._evaluate("mct_delay_geometry", self._DELAY).asPolyline()

        # Everything past PT2 is the arc, and every point of it sits
        # half a diameter from the diameter's own midpoint.
        centre = (10.0, 3.0)

        arc = [point for point in run if point.x() != 0.0 or point.y() != 0.0]

        for point in arc[1:]:

            self.assertAlmostEqual(
                math.hypot(point.x() - centre[0], point.y() - centre[1]),
                3.0,
                places=6
            )


    def test_a_skewed_pt3_is_straightened_onto_the_perpendicular(self):

        # "The 180 degree circular arc is always perpendicular to the
        # line" - the standard's own draw rule, and the maintainer's
        # decision 2026-08-16. PT3 sets the diameter's LENGTH and its
        # SIDE; the shaft sets its direction.
        run = self._evaluate(
            "mct_delay_geometry", "LineString(0 0, 10 0, 14 6)"
        ).asPolyline()

        # PT3 was clicked 4 units PAST PT2 and 6 above it. Only the 6
        # counts, so the arc still ends straight above PT2.
        self.assertAlmostEqual(run[-1].x(), 10.0, places=6)
        self.assertAlmostEqual(run[-1].y(), 6.0, places=6)

        # A square click is unchanged by the straightening - which is
        # what makes this compatible with the first build.
        square = self._evaluate("mct_delay_geometry", self._DELAY).asPolyline()

        self.assertEqual(len(run), len(square))

        for straightened, unchanged in zip(run, square):

            self.assertAlmostEqual(straightened.x(), unchanged.x(), places=6)
            self.assertAlmostEqual(straightened.y(), unchanged.y(), places=6)


    def test_pt3_on_the_shafts_own_line_leaves_no_arc(self):

        # No side to be on, so there is nothing to draw rather than a
        # guess. The shaft still appears.
        run = self._evaluate(
            "mct_delay_geometry", "LineString(0 0, 10 0, 25 0)"
        ).asPolyline()

        self.assertEqual(len(run), 2)


    def test_the_semicircle_bulges_away_from_pt1(self):

        # A diameter admits two semicircles and PT3 alone cannot choose
        # between them. The one that bulges back over the shaft would
        # cross it, so it has to be the other.
        run = self._evaluate("mct_delay_geometry", self._DELAY).asPolyline()

        self.assertGreater(max(point.x() for point in run), 10.0)

        # Mirroring PT3 to the other side mirrors the bulge with it,
        # rather than pinning it to one side of the world.
        mirrored = self._evaluate(
            "mct_delay_geometry", "LineString(0 0, 10 0, 10 -6)"
        ).asPolyline()

        self.assertGreater(max(point.x() for point in mirrored), 10.0)

        self.assertLess(min(point.y() for point in mirrored), 0.0)


    def test_the_letter_sits_at_the_middle_of_the_shaft(self):

        letter = self._evaluate(
            "mct_delay_letter_point", self._DELAY
        ).asPoint()

        self.assertAlmostEqual(letter.x(), 5.0, places=6)
        self.assertAlmostEqual(letter.y(), 0.0, places=6)


    def test_the_gap_breaks_the_shaft_around_that_point(self):

        # The gap is a PAGE width, converted through the scale into the
        # map units the shaft is measured in - so this pins that it is
        # real, positive and centred on the letter, not a figure in
        # whatever units the geometry happens to be in.
        parts = QgsExpression(
            "mct_delay_geometry(geom_from_wkt('{}'), 2, 1000)".format(
                self._DELAY
            )
        ).evaluate().asMultiPolyline()

        self.assertEqual(len(parts), 2)

        before = 5.0 - parts[0][-1].x()
        after = parts[1][0].x() - 5.0

        self.assertGreater(before, 0.0)

        self.assertAlmostEqual(before, after, places=9)

        # The arc still hangs off the second part - the break is in the
        # shaft only, and the run past PT2 is continuous.
        self.assertAlmostEqual(parts[1][-1].x(), 10.0, places=6)
        self.assertAlmostEqual(parts[1][-1].y(), 6.0, places=6)


    def test_the_arrowhead_rides_the_shaft_reversed_and_alone(self):

        # One part, so one arrowhead - and it ends at PT1, so a marker
        # on its last vertex points out of the symbol.
        shaft = self._evaluate("mct_delay_shaft", self._DELAY).asPolyline()

        self.assertEqual(len(shaft), 2)

        self.assertAlmostEqual(shaft[0].x(), 10.0, places=6)
        self.assertAlmostEqual(shaft[-1].x(), 0.0, places=6)


    def test_degenerate_inputs_fall_through(self):

        for wkt in (
            "LineString(0 0, 10 0)",      # no PT3 at all
            "LineString(0 0, 0 0, 5 5)",  # no shaft
        ):
            for function in ("mct_delay_geometry", "mct_delay_shaft",
                             "mct_delay_letter_point"):

                self.assertIsNotNone(self._evaluate(function, wkt))

        # PT2 == PT3 leaves no diameter, so there is no arc to draw -
        # but the shaft still has to appear rather than the whole
        # symbol vanishing.
        run = self._evaluate(
            "mct_delay_geometry", "LineString(0 0, 10 0, 10 0)"
        ).asPolyline()

        self.assertEqual(len(run), 2)


    def test_delay_draws_its_shaft_arc_and_head_and_carries_a_d(self):

        layer = create_mission_task_lines_layer()

        for child in layer.renderer().rootRule().children():

            if child.filterExpression() != "\"measure_type\" = 'delay'":
                continue

            symbol = child.symbol()

            expressions = [
                symbol.symbolLayer(index).geometryExpression()
                for index in range(symbol.symbolLayerCount())
            ]

            self.assertIn("mct_delay_shaft($geometry)", expressions)

            self.assertTrue(
                any(each.startswith("mct_delay_geometry($geometry")
                    for each in expressions)
            )

            break

        else:
            self.fail("no renderer rule for delay")

        for rule in layer.labeling().rootRule().children():

            if rule.description() != "delay":
                continue

            self.assertEqual(rule.settings().fieldName, "'D'")

            self.assertEqual(
                rule.settings().geometryGenerator,
                "mct_delay_letter_point($geometry)"
            )

            return

        self.fail("no labelling rule for delay")


class TestDelayConstructionIsSharedByFour(QgisTestCase):

    """
    "Retire, Withdraw, withdraw under pressure - all same as delay;
    only change being use letter R for retire, W for withdraw and WP
    for withdraw under pressure" - the maintainer's own instruction,
    and the standard's own draw rules for the four are word for word
    each other's.

    So this pins that they really are ONE construction: a change to the
    shape cannot reach one of them and miss the others.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_all_four_are_recorded_as_one_construction(self):

        self.assertEqual(
            DELAY_CONSTRUCTION_MEASURE_TYPES,
            ("delay", "retire", "withdraw", "withdraw_under_pressure")
        )

        self.assertEqual(
            {LINE_MEASURE_TYPE_CODES[measure_type]
             for measure_type in DELAY_CONSTRUCTION_MEASURE_TYPES},
            {"340800", "342000", "342400", "342500"}
        )


    def test_only_the_letter_differs_between_them(self):

        self.assertEqual(
            {measure_type: LINE_LETTERS[measure_type]
             for measure_type in DELAY_CONSTRUCTION_MEASURE_TYPES},
            {
                "delay": "D",
                "retire": "R",
                "withdraw": "W",
                "withdraw_under_pressure": "WP",
            }
        )

        layer = create_mission_task_lines_layer()

        shapes = {}

        for rule in layer.renderer().rootRule().children():

            for measure_type in DELAY_CONSTRUCTION_MEASURE_TYPES:

                if rule.filterExpression() != (
                    "\"measure_type\" = '{}'".format(measure_type)
                ):
                    continue

                symbol = rule.symbol()

                shapes[measure_type] = [
                    symbol.symbolLayer(index).geometryExpression()
                    for index in range(symbol.symbolLayerCount())
                ]

        self.assertEqual(len(shapes), 4)

        # Same layers, same geometry - the only thing that varies is
        # the width of the gap each letter needs, which is the letter.
        for measure_type in DELAY_CONSTRUCTION_MEASURE_TYPES[1:]:

            self.assertEqual(
                len(shapes[measure_type]), len(shapes["delay"]),
                msg=measure_type
            )

            self.assertIn(
                "mct_delay_shaft($geometry)", shapes[measure_type],
                msg=measure_type
            )

            self.assertTrue(
                any(each.startswith("mct_delay_geometry($geometry")
                    for each in shapes[measure_type]),
                msg=measure_type
            )


    def test_the_two_letter_wp_cuts_a_wider_gap_than_the_one_letter_w(self):

        # WP is two glyphs, so its gap has to be measured rather than
        # assumed - the shared width is Qt's own font metrics, not a
        # per-letter constant.
        widths = {}

        for letter in ("W", "WP"):

            widths[letter] = QgsExpression(
                "mct_text_width_mm('{}', 4)".format(letter)
            ).evaluate()

        self.assertGreater(widths["WP"], widths["W"])


    def test_each_of_the_four_labels_with_its_own_letter(self):

        layer = create_mission_task_lines_layer()

        lettered = {}

        for rule in layer.labeling().rootRule().children():

            if rule.description() in DELAY_CONSTRUCTION_MEASURE_TYPES:

                settings = rule.settings()

                lettered[rule.description()] = settings.fieldName

                self.assertEqual(
                    settings.geometryGenerator,
                    "mct_delay_letter_point($geometry)"
                )

        self.assertEqual(
            lettered,
            {
                "delay": "'D'",
                "retire": "'R'",
                "withdraw": "'W'",
                "withdraw_under_pressure": "'WP'",
            }
        )


class TestBypass(QgisTestCase):

    """
    Bypass (340300) - Table H-XIX's own Obstacle Bypass Easy (270601)
    with a "B" set into the line joining the two arrows.

    "same as obstacle bypass easy 270601, except add B (masked) on line
    segment joining the two arrows, in the middle of the line" - the
    maintainer's own instruction.
    """

    # PT1 and PT2 are the two arrow TIPS; PT3's perpendicular distance
    # from the PT1-PT2 line sets both the rear line's offset and the
    # arrows' length. Here that distance is 4.
    _BYPASS = "LineString(0 0, 0 10, 4 5)"

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_the_letter_sits_at_the_middle_of_the_joining_line(self):

        rear = QgsExpression(
            "mct_obstacle_bypass_rear_easy(geom_from_wkt('{}'))".format(
                self._BYPASS
            )
        ).evaluate().asPolyline()

        letter = QgsExpression(
            "mct_obstacle_bypass_rear_midpoint(geom_from_wkt('{}'))".format(
                self._BYPASS
            )
        ).evaluate().asPoint()

        self.assertAlmostEqual(
            letter.x(), (rear[0].x() + rear[-1].x()) / 2.0, places=6
        )

        self.assertAlmostEqual(
            letter.y(), (rear[0].y() + rear[-1].y()) / 2.0, places=6
        )


    def test_the_gap_breaks_that_line_around_the_letter(self):

        parts = QgsExpression(
            "mct_obstacle_bypass_rear_easy(geom_from_wkt('{}'), 2, 1000)".format(
                self._BYPASS
            )
        ).evaluate().asMultiPolyline()

        self.assertEqual(len(parts), 2)

        letter = QgsExpression(
            "mct_obstacle_bypass_rear_midpoint(geom_from_wkt('{}'))".format(
                self._BYPASS
            )
        ).evaluate().asPoint()

        before = math.hypot(
            letter.x() - parts[0][-1].x(), letter.y() - parts[0][-1].y()
        )

        after = math.hypot(
            parts[1][0].x() - letter.x(), parts[1][0].y() - letter.y()
        )

        self.assertGreater(before, 0.0)

        self.assertAlmostEqual(before, after, places=9)

        # The line still runs end to end - only the middle is missing.
        whole = QgsExpression(
            "mct_obstacle_bypass_rear_easy(geom_from_wkt('{}'))".format(
                self._BYPASS
            )
        ).evaluate().asPolyline()

        self.assertAlmostEqual(parts[0][0].x(), whole[0].x(), places=6)
        self.assertAlmostEqual(parts[-1][-1].x(), whole[-1].x(), places=6)


    def test_the_obstacle_version_is_untouched_without_a_gap(self):

        # Table H-XIX's own 270601 passes neither argument, so it has
        # to keep drawing one unbroken part. Every reuse on this layer
        # reaches the original the same way.
        self.assertFalse(
            QgsExpression(
                "mct_obstacle_bypass_rear_easy(geom_from_wkt('{}'))".format(
                    self._BYPASS
                )
            ).evaluate().isMultipart()
        )


    def test_bypass_draws_the_arrows_the_joining_line_and_two_heads(self):

        layer = create_mission_task_lines_layer()

        for rule in layer.renderer().rootRule().children():

            if rule.filterExpression() != "\"measure_type\" = 'bypass'":
                continue

            symbol = rule.symbol()

            expressions = [
                symbol.symbolLayer(index).geometryExpression()
                for index in range(symbol.symbolLayerCount())
            ]

            # The arrows twice - once drawn, once carrying the heads.
            self.assertEqual(
                expressions.count("mct_obstacle_bypass_arrows($geometry)"), 2
            )

            self.assertTrue(
                any(each.startswith("mct_obstacle_bypass_rear_easy($geometry,")
                    for each in expressions)
            )

            break

        else:
            self.fail("no renderer rule for bypass")

        for rule in layer.labeling().rootRule().children():

            if rule.description() != "bypass":
                continue

            self.assertEqual(rule.settings().fieldName, "'B'")

            self.assertEqual(
                rule.settings().geometryGenerator,
                "mct_obstacle_bypass_rear_midpoint($geometry)"
            )

            return

        self.fail("no labelling rule for bypass")


class TestBreachAndCanalize(QgisTestCase):

    """
    Breach (340200) and Canalize (340400) - Bypass with the arrowheads
    replaced by a slanting line across each arm's tip.

    "same as bypass, replace the arrowheads with slanting lines at the
    edges, converging out" (Breach), then "same as breach, replace B
    with C, and reverse the orientation slanting lines, converging in"
    (Canalize) - the maintainer's own instructions.
    """

    # PT1 and PT2 are the opening's two ends, PT3 sets how far the arms
    # run. The rear line sits on PT3's side and the arms run back OUT
    # from it to the tips - so with PT3 to the east, the arms run due
    # WEST and "toward the rear" is a LARGER x.
    _BYPASS = "LineString(0 10, 0 0, 8 5)"

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _ticks(self, converging_out, wkt=None):

        return QgsExpression(
            "mct_bypass_ticks(geom_from_wkt('{}'), {})".format(
                wkt or self._BYPASS, str(converging_out).lower()
            )
        ).evaluate().asMultiPolyline()


    @staticmethod
    def _outer_and_inner(tick, tip_y, centre_y):

        """The tick's two ends, sorted by distance from the centreline."""

        return sorted(
            tick,
            key=lambda point: abs(point.y() - centre_y),
            reverse=True
        )


    def test_one_tick_per_arm_centred_on_its_own_tip(self):

        ticks = self._ticks(True)

        self.assertEqual(len(ticks), 2)

        for tick, tip in zip(ticks, ((0.0, 10.0), (0.0, 0.0))):

            self.assertEqual(len(tick), 2)

            self.assertAlmostEqual(
                (tick[0].x() + tick[1].x()) / 2.0, tip[0], places=6
            )

            self.assertAlmostEqual(
                (tick[0].y() + tick[1].y()) / 2.0, tip[1], places=6
            )


    def test_breachs_ticks_lean_their_outer_ends_back(self):

        # Converging out: the pair closes as it runs away from the
        # symbol, which is what makes the outer end the rearward one.
        for tick, tip_y in zip(self._ticks(True), (10.0, 0.0)):

            outer, inner = self._outer_and_inner(tick, tip_y, 5.0)

            self.assertGreater(outer.x(), inner.x())


    def test_canalize_mirrors_them(self):

        for tick, tip_y in zip(self._ticks(False), (10.0, 0.0)):

            outer, inner = self._outer_and_inner(tick, tip_y, 5.0)

            self.assertLess(outer.x(), inner.x())


    def test_the_ticks_do_not_flip_when_pt1_and_pt2_are_swapped(self):

        # The whole point of building these as geometry rather than as
        # a rotated marker per arm: each tick's outward direction comes
        # from its own tip's side of the opening, so clicking the two
        # ends the other way round draws the SAME symbol rather than
        # turning Breach into Canalize.
        swapped = self._ticks(True, "LineString(0 0, 0 10, 8 5)")

        for tick in swapped:

            outer, inner = self._outer_and_inner(tick, 0.0, 5.0)

            self.assertGreater(outer.x(), inner.x())


    def test_the_tick_is_sixty_degrees_to_its_arm(self):

        for tick in self._ticks(True):

            # Arms run due east, so the angle to the arm is the tick's
            # own angle off horizontal.
            angle = math.degrees(
                math.atan2(
                    abs(tick[1].y() - tick[0].y()),
                    abs(tick[1].x() - tick[0].x()),
                )
            )

            self.assertAlmostEqual(angle, 60.0, places=6)


    def test_the_length_is_a_quarter_of_the_arm_until_the_cap_bites(self):

        # PT3 is 8 out, so each arm is 8 and each tick a quarter of it.
        for tick in self._ticks(True):

            self.assertAlmostEqual(
                math.hypot(
                    tick[1].x() - tick[0].x(), tick[1].y() - tick[0].y()
                ),
                2.0,
                places=6
            )

        # With a cap given, the tick can only get shorter.
        capped = QgsExpression(
            "mct_bypass_ticks(geom_from_wkt('{}'), true, 6, 1000)".format(
                self._BYPASS
            )
        ).evaluate().asMultiPolyline()

        self.assertLess(
            math.hypot(
                capped[0][1].x() - capped[0][0].x(),
                capped[0][1].y() - capped[0][0].y(),
            ),
            2.0
        )


    def test_degenerate_input_draws_no_ticks(self):

        # PT3 on the PT1-PT2 line leaves no arms to put them on.
        self.assertTrue(
            QgsExpression(
                "mct_bypass_ticks(geom_from_wkt("
                "'LineString(0 10, 0 0, 0 5)'), true)"
            ).evaluate().isEmpty()
        )


    def test_all_three_share_the_arrows_and_the_joining_line(self):

        self.assertEqual(
            BYPASS_CONSTRUCTION_MEASURE_TYPES,
            ("bypass", "breach", "canalize")
        )

        layer = create_mission_task_lines_layer()

        drawn = {}

        for rule in layer.renderer().rootRule().children():

            for measure_type in BYPASS_CONSTRUCTION_MEASURE_TYPES:

                if rule.filterExpression() != (
                    "\"measure_type\" = '{}'".format(measure_type)
                ):
                    continue

                symbol = rule.symbol()

                drawn[measure_type] = [
                    symbol.symbolLayer(index).geometryExpression()
                    for index in range(symbol.symbolLayerCount())
                ]

        self.assertEqual(len(drawn), 3)

        for measure_type, expressions in drawn.items():

            self.assertIn(
                "mct_obstacle_bypass_arrows($geometry)", expressions,
                msg=measure_type
            )

            self.assertTrue(
                any(each.startswith("mct_obstacle_bypass_rear_easy($geometry,")
                    for each in expressions),
                msg=measure_type
            )

        # Only Bypass carries arrowheads; only the other two carry ticks.
        self.assertEqual(
            drawn["bypass"].count("mct_obstacle_bypass_arrows($geometry)"), 2
        )

        for measure_type, outward in (("breach", "true"), ("canalize", "false")):

            self.assertIn(
                "mct_bypass_ticks($geometry, {}, 6, @map_scale)".format(
                    outward
                ),
                drawn[measure_type],
                msg=measure_type
            )

            self.assertEqual(
                drawn[measure_type].count(
                    "mct_obstacle_bypass_arrows($geometry)"
                ),
                1,
                msg=measure_type
            )


    def test_breach_letters_b_and_canalize_letters_c(self):

        layer = create_mission_task_lines_layer()

        lettered = {}

        for rule in layer.labeling().rootRule().children():

            if rule.description() in ("breach", "canalize"):

                lettered[rule.description()] = rule.settings().fieldName

                self.assertEqual(
                    rule.settings().geometryGenerator,
                    "mct_obstacle_bypass_rear_midpoint($geometry)"
                )

        self.assertEqual(lettered, {"breach": "'B'", "canalize": "'C'"})


class TestClear(QgisTestCase):

    """
    Clear (340500) - Penetrate with two more arrows on it.

    "start with penetrate of mission task, same construction, just add
    another two arrows of same lengths, distance from the middle arrow
    - 3/4 of the length between the midpoint of base shaft to the end;
    on both sides" - the maintainer's own instruction, and the same
    proportion the standard's own template draws.
    """

    # Base line PT1-PT2 running north, 20 long, with PT3 due east of
    # its midpoint at a perpendicular distance of 8.
    _CLEAR = "LineString(0 0, 0 20, 8 10)"

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _stems(self, wkt=None):

        return QgsExpression(
            "mct_clear_side_stems(geom_from_wkt('{}'))".format(
                wkt or self._CLEAR
            )
        ).evaluate().asMultiPolyline()


    def test_two_arrows_one_either_side_of_the_middle_one(self):

        stems = self._stems()

        self.assertEqual(len(stems), 2)

        # Three quarters of the HALF base - 20/2 * 0.75 - either side
        # of the midpoint, which sits at y = 10.
        self.assertEqual(
            sorted(round(stem[-1].y(), 6) for stem in stems),
            [2.5, 17.5]
        )

        for stem in stems:

            self.assertAlmostEqual(stem[-1].x(), 0.0, places=6)


    def test_they_are_the_same_length_as_the_middle_arrow(self):

        for stem in self._stems():

            self.assertAlmostEqual(
                math.hypot(
                    stem[0].x() - stem[-1].x(), stem[0].y() - stem[-1].y()
                ),
                8.0,
                places=6
            )


    def test_they_run_tip_to_foot_so_the_heads_land_on_the_base(self):

        # A last-vertex marker fires on the last vertex of every part,
        # so the foot has to BE that vertex - the same arrangement
        # Penetrate's own head uses.
        for stem in self._stems():

            self.assertAlmostEqual(stem[0].x(), 8.0, places=6)

            self.assertAlmostEqual(stem[-1].x(), 0.0, places=6)


    def test_they_stay_perpendicular_to_the_base_line(self):

        # The standard's own rule - "the arrows will stay perpendicular
        # to the vertical line, regardless of the rotational
        # orientation of the symbol as a whole" - and it comes free
        # from the projection Block already does.
        stems = self._stems("LineString(0 0, 20 20, 0 20)")

        for stem in stems:

            along = (stem[0].x() - stem[-1].x()) * 20 + \
                    (stem[0].y() - stem[-1].y()) * 20

            self.assertAlmostEqual(along, 0.0, places=6)


    def test_degenerate_input_draws_no_side_arrows(self):

        for wkt in (
            "LineString(0 0, 0 20, 0 10)",  # PT3 on the base line
            "LineString(0 0, 0 0, 8 0)",    # no base line
            "LineString(0 0, 0 20)",        # no PT3
        ):
            self.assertTrue(
                QgsExpression(
                    "mct_clear_side_stems(geom_from_wkt('{}'))".format(wkt)
                ).evaluate().isEmpty()
            )


    def test_clear_draws_penetrates_layers_plus_the_outer_pair(self):

        layer = create_mission_task_lines_layer()

        drawn = {}

        for rule in layer.renderer().rootRule().children():

            for measure_type in ("penetrate", "clear"):

                if rule.filterExpression() == (
                    "\"measure_type\" = '{}'".format(measure_type)
                ):
                    symbol = rule.symbol()

                    drawn[measure_type] = [
                        symbol.symbolLayer(index).geometryExpression()
                        for index in range(symbol.symbolLayerCount())
                    ]

        self.assertEqual(len(drawn), 2)

        # Everything Penetrate draws, Clear draws too - bar the letter
        # itself, which is the one thing inside the gap expression that
        # differs between the two.
        for expression in drawn["penetrate"]:

            self.assertIn(
                expression.replace("'P'", "'C'"), drawn["clear"]
            )

        # Plus the outer pair, twice - drawn once, headed once.
        self.assertEqual(
            drawn["clear"].count("mct_clear_side_stems($geometry)"), 2
        )

        self.assertEqual(len(drawn["clear"]), len(drawn["penetrate"]) + 2)


    def test_clear_carries_c_on_the_middle_arrow(self):

        layer = create_mission_task_lines_layer()

        for rule in layer.labeling().rootRule().children():

            if rule.description() != "clear":
                continue

            self.assertEqual(rule.settings().fieldName, "'C'")

            self.assertEqual(
                rule.settings().geometryGenerator,
                "mct_block_letter_point($geometry)"
            )

            return

        self.fail("no labelling rule for clear")


class TestReliefInPlace(QgisTestCase):

    """
    Relief in Place (341900) - Retire's shape with no letter and a
    second arrow running back the other way.

    "same construction as retire, remove the letter R and let the line
    be continuous, just add another arrow parallel to pt1-pt2 line
    segment with the arrowhead touching pt3" - the maintainer's own
    instruction.
    """

    # Shaft due east from PT1 to PT2, PT3 square to it and 6 north.
    _RIP = "LineString(0 0, 10 0, 10 6)"

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _return_arrow(self, wkt=None):

        return QgsExpression(
            "mct_relief_in_place_return_arrow(geom_from_wkt('{}'))".format(
                wkt or self._RIP
            )
        ).evaluate().asPolyline()


    def test_its_head_lands_where_the_arc_finishes(self):

        arrow = self._return_arrow()

        arc = QgsExpression(
            "mct_delay_geometry(geom_from_wkt('{}'))".format(self._RIP)
        ).evaluate().asPolyline()

        self.assertAlmostEqual(arrow[-1].x(), arc[-1].x(), places=6)
        self.assertAlmostEqual(arrow[-1].y(), arc[-1].y(), places=6)


    def test_it_is_parallel_to_the_shaft_and_the_same_length(self):

        arrow = self._return_arrow()

        self.assertAlmostEqual(arrow[-1].y(), arrow[0].y(), places=6)

        self.assertAlmostEqual(
            math.hypot(
                arrow[-1].x() - arrow[0].x(), arrow[-1].y() - arrow[0].y()
            ),
            10.0,
            places=6
        )


    def test_it_points_the_opposite_way_to_the_first_arrow(self):

        # Two units passing each other - the first arrow's head is at
        # PT1 and this one's is at the far end of the curve.
        arrow = self._return_arrow()

        self.assertGreater(arrow[-1].x(), arrow[0].x())

        shaft = QgsExpression(
            "mct_delay_shaft(geom_from_wkt('{}'))".format(self._RIP)
        ).evaluate().asPolyline()

        self.assertLess(shaft[-1].x(), shaft[0].x())


    def test_a_skewed_pt3_keeps_the_head_on_the_curve(self):

        # The arc is forced perpendicular, so its end is not PT3 unless
        # PT3 was clicked square. The arrow follows the ARC, not the
        # raw click, or it would float off the end of it.
        skewed = "LineString(0 0, 10 0, 15 6)"

        arrow = self._return_arrow(skewed)

        arc = QgsExpression(
            "mct_delay_geometry(geom_from_wkt('{}'))".format(skewed)
        ).evaluate().asPolyline()

        self.assertAlmostEqual(arrow[-1].x(), arc[-1].x(), places=6)
        self.assertAlmostEqual(arrow[-1].y(), arc[-1].y(), places=6)


    def test_degenerate_input_draws_no_second_arrow(self):

        for wkt in (
            "LineString(0 0, 10 0, 25 0)",  # PT3 on the shaft's line
            "LineString(0 0, 0 0, 5 5)",    # no shaft
            "LineString(0 0, 10 0)",        # no PT3
        ):
            self.assertTrue(
                QgsExpression(
                    "mct_relief_in_place_return_arrow(geom_from_wkt('{}'))"
                    .format(wkt)
                ).evaluate().isEmpty()
            )


    def test_the_shaft_runs_unbroken_because_there_is_no_letter(self):

        self.assertNotIn("relief_in_place", LINE_LETTERS)

        layer = create_mission_task_lines_layer()

        for rule in layer.renderer().rootRule().children():

            if rule.filterExpression() != (
                "\"measure_type\" = 'relief_in_place'"
            ):
                continue

            symbol = rule.symbol()

            expressions = [
                symbol.symbolLayer(index).geometryExpression()
                for index in range(symbol.symbolLayerCount())
            ]

            # A zero gap, so mct_delay_geometry takes its own no-gap
            # path and returns one continuous part.
            self.assertIn(
                "mct_delay_geometry($geometry, 0, @map_scale)", expressions
            )

            self.assertEqual(
                expressions.count(
                    "mct_relief_in_place_return_arrow($geometry)"
                ),
                2
            )

            break

        else:
            self.fail("no renderer rule for relief_in_place")

        # It writes the standard's own "RIP" rather than a letter, and
        # that is why it stays out of LINE_LETTERS: the text sits in
        # open paper, so nothing cuts a gap for it.
        written = [
            rule.settings().fieldName
            for rule in layer.labeling().rootRule().children()
            if rule.description() == "relief_in_place"
        ]

        self.assertEqual(written, ["'RIP'"])


    def test_the_rip_text_sits_between_the_two_arrows(self):

        point = QgsExpression(
            "mct_relief_in_place_text_point(geom_from_wkt('{}'))".format(
                self._RIP
            )
        ).evaluate().asPoint()

        # Half way along the shaft and half way out to the return
        # arrow - the middle of the enclosed shape.
        self.assertAlmostEqual(point.x(), 5.0, places=6)
        self.assertAlmostEqual(point.y(), 3.0, places=6)


    def test_the_rip_text_grows_with_the_shape_and_stops_at_24pt(self):

        def size(wkt, scale):

            return QgsExpression(
                "mct_relief_in_place_text_size(geom_from_wkt('{}'),"
                " make_rectangle_3points(make_point(0, 0), make_point(1, 0),"
                " make_point(1, 1)), {}, 24)".format(wkt, scale)
            ).evaluate()

        # Zoomed out far enough, the shape is small on the page and so
        # is the text.
        small = size(self._RIP, 100000000)

        self.assertGreater(small, 0.0)

        self.assertLess(small, 24.0)

        # Zoomed in, it stops at the cap rather than filling the screen.
        self.assertAlmostEqual(size(self._RIP, 1000), 24.0, places=6)


    def test_a_narrow_shape_sizes_the_rip_text_by_its_width(self):

        # The shaft and the gap are set by different clicks, so the
        # text has to fit BOTH or it runs out through the arrows.
        def size(wkt):

            return QgsExpression(
                "mct_relief_in_place_text_size(geom_from_wkt('{}'),"
                " make_rectangle_3points(make_point(0, 0), make_point(1, 0),"
                " make_point(1, 1)), 100000000, 24)".format(wkt)
            ).evaluate()

        # Same gap between the arrows, a quarter of the shaft.
        self.assertLess(
            size("LineString(0 0, 2.5 0, 2.5 6)"),
            size("LineString(0 0, 10 0, 10 6)")
        )


    def test_the_rip_text_needs_no_gap_cut_for_it(self):

        # Unlike every letter on this layer it does not sit on a line,
        # which is what let the shaft stay continuous.
        self.assertNotIn("relief_in_place", LINE_LETTERS)

        self.assertIn("relief_in_place", LABELLED_MEASURE_TYPES)


    def test_degenerate_input_writes_nothing(self):

        for wkt in ("LineString(0 0, 10 0, 25 0)", "LineString(0 0, 10 0)"):

            self.assertTrue(
                QgsExpression(
                    "mct_relief_in_place_text_point(geom_from_wkt('{}'))"
                    .format(wkt)
                ).evaluate().isEmpty()
            )


    def test_the_four_lettered_delay_tasks_still_exclude_it(self):

        # DELAY_CONSTRUCTION_MEASURE_TYPES promises that only the
        # letter differs between its members. Relief in Place draws the
        # same shape but breaks that promise, so it stays out.
        self.assertNotIn(
            "relief_in_place", DELAY_CONSTRUCTION_MEASURE_TYPES
        )


class TestSecurityTasks(QgisTestCase):

    """
    Cover (342201), Guard (342202) and Screen (342203) - one
    construction with three letters.

    "user is to click 3pts, pt1, pt2, pt3; i'll describe from center
    outwards; at pt2 - make a gap for a milsymbol say infantry
    batallion, now next to the milsymbol space on both sides, add the
    letter - C for Cover, G for Guard, S for Screen, introduce a small
    gap, now from there towards pt1 and pt3 draw a lightning bolt
    ending in an arrow head, both lightning bolts are mirror images of
    each other" - the maintainer's own instruction.
    """

    # PT2 is the CENTRE - the middle click - with the two arms running
    # due west to PT1 and due east to PT3.
    _SECURITY = "LineString(-100 0, 0 0, 100 0)"

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _bolts(self, wkt=None):

        # No start offset: the reserved space and the letters are a
        # PAGE measurement, and leaving them out here keeps these
        # assertions about the bolt's own shape rather than about the
        # millimetre conversion, which _page_gap_in_map_units already
        # has its own tests for.
        return QgsExpression(
            "mct_security_arms(geom_from_wkt('{}'))".format(
                wkt or self._SECURITY
            )
        ).evaluate().asMultiPolyline()


    def test_the_middle_click_is_the_centre(self):

        # Not the standard's own order, which makes PT1 the centre.
        # The maintainer's makes the feature a plain three-vertex line
        # drawn end, centre, end.
        bolts = self._bolts()

        self.assertEqual(len(bolts), 2)

        # One bolt runs west and one east, both starting at the centre.
        self.assertLess(bolts[0][-1].x(), 0.0)
        self.assertGreater(bolts[1][-1].x(), 0.0)

        for bolt in bolts:

            self.assertAlmostEqual(bolt[0].x(), 0.0, places=6)


    def test_each_bolt_is_a_rail_a_diagonal_and_a_rail(self):

        for bolt in self._bolts():

            self.assertEqual(len(bolt), 4)

            # The first rail lies ON the clicked line, the second is
            # dropped off it - the spine is what the user drew.
            self.assertAlmostEqual(bolt[0].y(), 0.0, places=6)
            self.assertAlmostEqual(bolt[1].y(), 0.0, places=6)

            self.assertAlmostEqual(bolt[2].y(), bolt[3].y(), places=6)

            self.assertNotAlmostEqual(bolt[2].y(), 0.0, places=6)


    def test_the_diagonal_runs_back_toward_the_centre(self):

        # What makes it a lightning bolt rather than a step: the
        # diagonal loses ground as it drops.
        for bolt in self._bolts():

            outward = 1.0 if bolt[-1].x() > 0 else -1.0

            self.assertLess(
                outward * bolt[2].x(), outward * bolt[1].x()
            )


    def test_the_diagonal_is_forty_five_degrees(self):

        # The distance it travels back equals the distance it drops -
        # 0.70 to 0.60 of the bolt, against a 0.10 drop.
        for bolt in self._bolts():

            back = abs(bolt[2].x() - bolt[1].x())

            drop = abs(bolt[2].y() - bolt[1].y())

            self.assertAlmostEqual(back, drop, places=6)


    def test_the_two_bolts_are_mirror_images(self):

        west, east = self._bolts()

        # Mirroring one about the centre's own vertical gives the
        # other, point for point - which is what the instruction asked
        # for and what keeps the pair reading as one symbol.
        for left, right in zip(west, east):

            self.assertAlmostEqual(left.x(), -right.x(), places=6)
            self.assertAlmostEqual(left.y(), right.y(), places=6)


    def test_they_stay_mirrored_on_a_bent_line(self):

        # The two normals are opposite rotations of their OWN arm, so
        # the pair mirrors however the line is drawn rather than only
        # when it is straight.
        bolts = self._bolts(wkt="LineString(0 100, 0 0, 100 0)")

        self.assertEqual(len(bolts), 2)

        for bolt in bolts:

            self.assertEqual(len(bolt), 4)

        # Each drops to its own arm's own side: walking outward, PT1's
        # bolt drops to the LEFT and PT3's to the RIGHT. On a straight
        # line those are the same physical side, which is what makes
        # the pair read as a mirror; on a bent one each still follows
        # its own arm.
        north, east = bolts

        self.assertLess(north[2].x(), 0.0)

        self.assertLess(east[2].y(), 0.0)


    def test_an_arm_too_short_for_its_start_draws_nothing(self):

        # The letters and the reserved symbol space come first; an arm
        # that cannot fit them must not double back on itself.
        # A 20 mm start at 1:1000 is 20 metres of ground, which is
        # wider than this whole feature.
        bolts = QgsExpression(
            "mct_security_arms(geom_from_wkt("
            "'LineString(-0.0001 0, 0 0, 0.0001 0)'), 20, 1000)"
        ).evaluate()

        self.assertTrue(bolts.isEmpty())


    def test_degenerate_input_draws_nothing(self):

        for wkt in ("LineString(0 0, 0 0, 0 0)", "LineString(0 0, 10 0)"):

            self.assertTrue(
                QgsExpression(
                    "mct_security_arms(geom_from_wkt('{}'))".format(wkt)
                ).evaluate().isEmpty()
            )


    def test_the_letters_sit_either_side_of_the_reserved_space(self):

        points = [
            QgsExpression(
                "mct_security_letter_point(geom_from_wkt('{}'), {}, 6, 1000)"
                .format(self._SECURITY, side)
            ).evaluate().asPoint()
            for side in (1, 2)
        ]

        # Toward PT1 and toward PT3, the same distance out either way.
        self.assertLess(points[0].x(), 0.0)
        self.assertGreater(points[1].x(), 0.0)

        self.assertAlmostEqual(points[0].x(), -points[1].x(), places=9)

        # On the spine, like the first rail.
        for point in points:

            self.assertAlmostEqual(point.y(), 0.0, places=9)


    def test_all_three_share_one_construction(self):

        self.assertEqual(
            SECURITY_CONSTRUCTION_MEASURE_TYPES, ("cover", "guard", "screen")
        )

        self.assertEqual(
            {LINE_MEASURE_TYPE_CODES[measure_type]
             for measure_type in SECURITY_CONSTRUCTION_MEASURE_TYPES},
            {"342201", "342202", "342203"}
        )

        self.assertEqual(
            {measure_type: LINE_LETTERS[measure_type]
             for measure_type in SECURITY_CONSTRUCTION_MEASURE_TYPES},
            {"cover": "C", "guard": "G", "screen": "S"}
        )

        layer = create_mission_task_lines_layer()

        shapes = {}

        for rule in layer.renderer().rootRule().children():

            for measure_type in SECURITY_CONSTRUCTION_MEASURE_TYPES:

                if rule.filterExpression() == (
                    "\"measure_type\" = '{}'".format(measure_type)
                ):
                    symbol = rule.symbol()

                    shapes[measure_type] = [
                        symbol.symbolLayer(index).geometryExpression()
                        for index in range(symbol.symbolLayerCount())
                    ]

        self.assertEqual(len(shapes), 3)

        for measure_type, expressions in shapes.items():

            # The bolts twice - once drawn, once carrying the heads.
            self.assertEqual(len(expressions), 2, msg=measure_type)

            self.assertEqual(expressions[0], expressions[1], msg=measure_type)

            self.assertTrue(
                expressions[0].startswith("mct_security_arms($geometry,"),
                msg=measure_type
            )


    def test_each_writes_its_letter_twice(self):

        layer = create_mission_task_lines_layer()

        written = {}

        for rule in layer.labeling().rootRule().children():

            if rule.description() in SECURITY_CONSTRUCTION_MEASURE_TYPES:

                written.setdefault(rule.description(), []).append(
                    rule.settings().fieldName
                )

        self.assertEqual(
            written,
            {
                "cover": ["'C'", "'C'"],
                "guard": ["'G'", "'G'"],
                "screen": ["'S'", "'S'"],
            }
        )


    def test_the_security_parent_row_is_recorded_as_undrawable(self):

        # 342200's own TEMPLATE and EXAMPLE both read "N/A", so it will
        # never be built - the same standing as the table's own section
        # parent. It stays in the record so the arithmetic still runs.
        self.assertIn("342200", TABLE_H_XXIV_REMAINING)

        self.assertIn("N/A", TABLE_H_XXIV_REMAINING["342200"])


class TestFollowTasks(QgisTestCase):

    """
    Follow and Assume (341200) and Follow and Support (341300).

    Two anchor points, PT1 the tip and PT2 the rear, and the standard's
    own draw rules say the symbol "varies only in length" - so the tag
    and the head are FIXED PAGE SIZES and only the line between them
    stretches. That is what most of this pins.
    """

    # Running due east, rear at the origin. PT1 first, per the
    # standard's own order and the one Delay already uses.
    _FOLLOW = "LineString(0.01 0, 0 0, 0 0)"

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    @staticmethod
    def _evaluate(expression, scale=20000):

        return QgsExpression(
            "{}(geom_from_wkt('LineString(0.01 0, 0 0)'), {})".format(
                expression, scale
            )
        ).evaluate()


    def test_the_tag_and_the_head_do_not_change_with_the_length(self):

        # "varies only in length" - the whole point of building these
        # out of page millimetres rather than fractions of the line.
        def tag_height(wkt):

            ring = QgsExpression(
                "mct_follow_tag(geom_from_wkt('{}'), 100000)".format(wkt)
            ).evaluate().asPolyline()

            return max(p.y() for p in ring) - min(p.y() for p in ring)

        short = tag_height("LineString(0.01 0, 0 0)")
        long = tag_height("LineString(0.4 0, 0 0)")

        self.assertGreater(short, 0.0)

        self.assertAlmostEqual(short, long, places=12)


    def test_the_tag_is_a_closed_ring_pointing_forward(self):

        ring = self._evaluate("mct_follow_tag").asPolyline()

        self.assertEqual(
            (ring[0].x(), ring[0].y()), (ring[-1].x(), ring[-1].y())
        )

        # Its nose is the furthest point forward, on the axis.
        nose = max(ring, key=lambda point: point.x())

        self.assertAlmostEqual(nose.y(), 0.0, places=12)


    def test_only_supports_tag_is_notched(self):

        plain = QgsExpression(
            "mct_follow_tag(geom_from_wkt('LineString(0.01 0, 0 0)'),"
            " 100000, false)"
        ).evaluate().asPolyline()

        notched = QgsExpression(
            "mct_follow_tag(geom_from_wkt('LineString(0.01 0, 0 0)'),"
            " 100000, true)"
        ).evaluate().asPolyline()

        self.assertEqual(len(notched), len(plain) + 1)

        # The notch bites forward into the back edge, on the axis.
        bite = [
            point for point in notched
            if point.x() > 0 and abs(point.y()) < 1e-12
        ]

        self.assertEqual(len(bite), 2)


    def test_assumes_head_is_an_outlined_ring_and_supports_is_filled(self):

        assume = self._evaluate("mct_follow_assume_head")

        self.assertEqual(
            assume.wkbType(), Qgis.WkbType.LineString
        )

        ring = assume.asPolyline()

        self.assertEqual(
            (ring[0].x(), ring[0].y()), (ring[-1].x(), ring[-1].y())
        )

        support = self._evaluate("mct_follow_support_head")

        self.assertEqual(
            support.wkbType(), Qgis.WkbType.Polygon
        )


    def test_assumes_head_is_the_taller_of_the_two(self):

        def height(geometry):

            box = geometry.boundingBox()

            return box.yMaximum() - box.yMinimum()

        self.assertGreater(
            height(self._evaluate("mct_follow_assume_head")),
            height(self._evaluate("mct_follow_support_head"))
        )


    def test_both_heads_reach_pt1(self):

        for expression in (
            "mct_follow_assume_head", "mct_follow_support_head"
        ):
            box = self._evaluate(expression).boundingBox()

            self.assertAlmostEqual(box.xMaximum(), 0.01, places=9)


    def test_the_connector_is_the_only_part_that_stretches(self):

        def connector_length(wkt):

            run = QgsExpression(
                "mct_follow_connector(geom_from_wkt('{}'), 20000)".format(wkt)
            ).evaluate().asPolyline()

            return math.hypot(
                run[-1].x() - run[0].x(), run[-1].y() - run[0].y()
            )

        self.assertGreater(
            connector_length("LineString(0.4 0, 0 0)"),
            connector_length("LineString(0.01 0, 0 0)")
        )


    def test_a_symbol_too_short_for_its_own_glyphs_loses_the_line(self):

        # Rather than drawing it backwards through the tag.
        self.assertTrue(
            QgsExpression(
                "mct_follow_connector(geom_from_wkt("
                "'LineString(0.00001 0, 0 0)'), 100000)"
            ).evaluate().isEmpty()
        )


    def test_degenerate_input_draws_nothing(self):

        for expression in (
            "mct_follow_tag", "mct_follow_connector",
            "mct_follow_assume_head", "mct_follow_support_head",
        ):
            for wkt in ("LineString(0 0, 0 0)", "LineString(0 0)"):

                self.assertTrue(
                    QgsExpression(
                        "{}(geom_from_wkt('{}'), 100000)".format(
                            expression, wkt
                        )
                    ).evaluate().isEmpty(),
                    msg="{} {}".format(expression, wkt)
                )


    def test_assumes_line_is_dashed_whatever_the_status(self):

        # "The dashed lines in this graphic shall be displayed in
        # present and anticipated status" - the standard's own note, so
        # this dash is what the symbol IS, not what state it is in.
        layer = create_mission_task_lines_layer()

        for rule in layer.renderer().rootRule().children():

            if rule.filterExpression() != (
                "\"measure_type\" = 'follow_and_assume'"
            ):
                continue

            symbol = rule.symbol()

            for index in range(symbol.symbolLayerCount()):

                generator = symbol.symbolLayer(index)

                if not generator.geometryExpression().startswith(
                    "mct_follow_connector"
                ):
                    continue

                stroke = generator.subSymbol().symbolLayer(0)

                self.assertEqual(stroke.penStyle(), Qt.PenStyle.DashLine)

                self.assertFalse(
                    stroke.dataDefinedProperties().isActive(
                        QgsSymbolLayer.Property.StrokeStyle
                    )
                )

                return

        self.fail("no connector layer for follow_and_assume")


    def test_supports_line_follows_the_status_like_everything_else(self):

        layer = create_mission_task_lines_layer()

        for rule in layer.renderer().rootRule().children():

            if rule.filterExpression() != (
                "\"measure_type\" = 'follow_and_support'"
            ):
                continue

            symbol = rule.symbol()

            for index in range(symbol.symbolLayerCount()):

                generator = symbol.symbolLayer(index)

                if not generator.geometryExpression().startswith(
                    "mct_follow_connector"
                ):
                    continue

                stroke = generator.subSymbol().symbolLayer(0)

                self.assertTrue(
                    stroke.dataDefinedProperties().isActive(
                        QgsSymbolLayer.Property.StrokeStyle
                    )
                )

                return

        self.fail("no connector layer for follow_and_support")


    def test_the_pair_is_recorded_as_one_construction(self):

        self.assertEqual(
            FOLLOW_CONSTRUCTION_MEASURE_TYPES,
            ("follow_and_assume", "follow_and_support")
        )

        self.assertEqual(
            {LINE_MEASURE_TYPE_CODES[measure_type]
             for measure_type in FOLLOW_CONSTRUCTION_MEASURE_TYPES},
            {"341200", "341300"}
        )

        # Neither carries a letter, so neither cuts a gap.
        for measure_type in FOLLOW_CONSTRUCTION_MEASURE_TYPES:

            self.assertNotIn(measure_type, LINE_LETTERS)

            self.assertNotIn(measure_type, LABELLED_MEASURE_TYPES)


class TestCounterattack(QgisTestCase):

    """
    Counterattack (340600) - the Moving Convoy's arrow, dashed, run
    backwards so its head lands on PT1.

    "let's start with moving convoy 330100 as template; user click
    three points - pt1,2,3; draw an arrow of same dimensions as moving
    convoy, but with dashed line; starting at pt3 with arrow head tip
    at pt1; put text CATK - same rules for text as RIP" - the
    maintainer's own instruction.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _inner(self):

        # Held on the instance, not a local: let the layer fall out of
        # scope here and Python frees it, taking the renderer's C++
        # objects with it - "wrapped C/C++ object has been deleted" on
        # the very next line. The same ownership trap this project has
        # hit through by-value accessors.
        self.layer = create_mission_task_lines_layer()

        layer = self.layer

        for rule in layer.renderer().rootRule().children():

            if rule.filterExpression() == "\"measure_type\" = 'counterattack'":

                generator = rule.symbol().symbolLayer(0)

                self.assertEqual(
                    generator.geometryExpression(), "reverse($geometry)"
                )

                return generator.subSymbol()

        self.fail("no renderer rule for counterattack")


    def test_it_is_drawn_on_the_reversed_line_so_the_head_lands_on_pt1(self):

        # The convoy's own head sits on its LAST vertex; this one has to
        # sit on PT1, the first click. Reversing the geometry is what
        # lets the convoy's offset and end-trim carry over untouched
        # instead of being re-derived with the signs flipped.
        inner = self._inner()

        # The two rails, and nothing else - the end pieces are their
        # own layers now, reading PT1 and the last vertex directly.
        self.assertEqual(inner.symbolLayerCount(), 2)


    def test_the_rails_are_the_convoys_own_dimensions(self):

        inner = self._inner()

        offsets = sorted(
            inner.symbolLayer(index).offset() for index in (0, 1)
        )

        self.assertEqual(
            offsets,
            [-CONVOY_BODY_HEIGHT_MM / 2.0, CONVOY_BODY_HEIGHT_MM / 2.0]
        )

        for index in (0, 1):

            self.assertAlmostEqual(
                inner.symbolLayer(index).trimDistanceEnd(),
                CONVOY_HEAD_LENGTH_MM,
                places=9
            )


    def test_the_rails_are_dashed_whatever_the_status(self):

        # Its own note: "The dashed lines in this graphic shall be
        # displayed in present and anticipated status".
        inner = self._inner()

        for index in (0, 1):

            rail = inner.symbolLayer(index)

            self.assertEqual(rail.penStyle(), Qt.PenStyle.DashLine)

            self.assertFalse(
                rail.dataDefinedProperties().isActive(
                    QgsSymbolLayer.Property.StrokeStyle
                )
            )


    def test_catk_stands_just_behind_the_arrowhead(self):

        # "put it slightly behind the arrow head as is shown in the
        # manual". Centring it also landed the word on a three-point
        # arrow's own bend, across both rails.
        point = QgsExpression(
            "mct_counterattack_text_point(geom_from_wkt("
            "'LineString(0.06 0, 0.03 0, 0 0)'),"
            " make_rectangle_3points(make_point(0, 0), make_point(1, 0),"
            " make_point(1, 1)), 200000, 6, 6, 24)"
        ).evaluate().asPoint()

        # Behind PT1 - which is at 0.06 - but well forward of the
        # midpoint at 0.03, where it used to sit.
        self.assertLess(point.x(), 0.06)

        self.assertGreater(point.x(), 0.03)

        self.assertAlmostEqual(point.y(), 0.0, places=12)


    def test_catk_follows_the_leg_the_head_is_on(self):

        # Walked from PT1 along the geometry, so on a bent arrow it
        # stays on the head's own leg instead of landing on the bend.
        point = QgsExpression(
            "mct_counterattack_text_point(geom_from_wkt("
            "'LineString(0.06 0.06, 0.06 0, 0 0)'),"
            " make_rectangle_3points(make_point(0, 0), make_point(1, 0),"
            " make_point(1, 1)), 200000, 6, 6, 24)"
        ).evaluate().asPoint()

        # PT1 is due north of the bend, so the text is too.
        self.assertAlmostEqual(point.x(), 0.06, places=12)

        self.assertLess(point.y(), 0.06)

        self.assertGreater(point.y(), 0.0)


    def test_a_short_arrow_falls_back_to_its_middle(self):

        # Better a cramped label than one hanging off the back of the
        # symbol entirely.
        point = QgsExpression(
            "mct_counterattack_text_point(geom_from_wkt("
            "'LineString(0.0002 0, 0 0)'),"
            " make_rectangle_3points(make_point(0, 0), make_point(1, 0),"
            " make_point(1, 1)), 200000, 6, 6, 24)"
        ).evaluate().asPoint()

        self.assertAlmostEqual(point.x(), 0.0001, places=12)


    def test_it_writes_catk_sized_to_its_own_arrow(self):

        layer = create_mission_task_lines_layer()

        for rule in layer.labeling().rootRule().children():

            if rule.description() != "counterattack":
                continue

            settings = rule.settings()

            self.assertEqual(settings.fieldName, "'CATK'")

            self.assertTrue(
                settings.dataDefinedProperties().isActive(
                    QgsPalLayerSettings.Property.Size
                )
            )

            return

        self.fail("no labelling rule for counterattack")


    def test_the_text_grows_with_the_arrow_and_stops_at_the_bar(self):

        def size(wkt, scale):

            return QgsExpression(
                "mct_counterattack_text_size(geom_from_wkt('{}'),"
                " make_rectangle_3points(make_point(0, 0), make_point(1, 0),"
                " make_point(1, 1)), {}, 6, 24)".format(wkt, scale)
            ).evaluate()

        short = size("LineString(0 0, 0.02 0, 0.03 0)", 500000)

        long = size("LineString(0 0, 0.2 0, 0.4 0)", 500000)

        self.assertGreater(short, 0.0)

        self.assertLess(short, long)

        # **The bar, not the 24 pt cap, is what actually stops it** -
        # the arrow's height is a fixed page size, so the cap never
        # binds in practice. Worth pinning so a later change to the bar
        # cannot silently change the text.
        self.assertLess(long, 24.0)

        self.assertAlmostEqual(long, 0.62 * 6.0 * 72.0 / 25.4, places=9)


    def test_degenerate_input_writes_nothing(self):

        self.assertEqual(
            QgsExpression(
                "mct_counterattack_text_size(geom_from_wkt("
                "'LineString(0 0, 0 0)'), make_rectangle_3points("
                "make_point(0, 0), make_point(1, 0), make_point(1, 1)),"
                " 500000, 6, 24)"
            ).evaluate(),
            0.0
        )


class TestCounterattackByFireAndTheDashedHead(QgisTestCase):

    """
    The two changes the maintainer asked for after Counterattack's own
    smoke render, plus Counterattack by Fire (340700).

    "the arrowhead being solid is not acceptable, so change it to
    dashed - figure it out; align CATK text with the arrowhead, in case
    drawn inverted as you say right to left, include a logic to keep
    the text straight".
    """

    _CATK = "LineString(0.05 0, 0.03 0, 0 0)"

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.layer = create_mission_task_lines_layer()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _expressions(self, measure_type):

        for rule in self.layer.renderer().rootRule().children():

            if rule.filterExpression() == (
                "\"measure_type\" = '{}'".format(measure_type)
            ):
                symbol = rule.symbol()

                return [
                    symbol.symbolLayer(index).geometryExpression()
                    for index in range(symbol.symbolLayerCount())
                ]

        self.fail("no renderer rule for " + measure_type)


    def test_the_head_is_geometry_now_so_that_it_can_be_dashed(self):

        # An SVG has no pen style, which is why the first build could
        # not dash it. Drawn as real geometry it takes the same stroke
        # the rails do.
        self.assertTrue(
            any(each.startswith("mct_counterattack_head($geometry,")
                for each in self._expressions("counterattack"))
        )

        symbol = None

        for rule in self.layer.renderer().rootRule().children():

            if rule.filterExpression() == "\"measure_type\" = 'counterattack'":
                symbol = rule.symbol()

        for index in range(symbol.symbolLayerCount()):

            generator = symbol.symbolLayer(index)

            if not generator.geometryExpression().startswith(
                "mct_counterattack_head"
            ):
                continue

            self.assertEqual(
                generator.subSymbol().symbolLayer(0).penStyle(),
                Qt.PenStyle.DashLine
            )

            return

        self.fail("no head layer")


    def test_the_head_keeps_the_convoy_glyphs_own_flare(self):

        # Redrawn from the convoy's SVG rather than reinvented, so this
        # asserts the ratio the SVG uses is the ratio the geometry
        # uses - the link the comment claims.
        from MilitaryCartographyTools.expressions import (
            military_symbology_functions as functions
        )

        self.assertAlmostEqual(
            functions._CATK_HEAD_FLARE_RATIO,
            functions._CONVOY_SVG_HEAD_FLARE / functions._CONVOY_SVG_BODY,
            places=12
        )


    def test_the_head_sits_at_pt1_and_flares_past_the_bar(self):

        head = QgsExpression(
            "mct_counterattack_head(geom_from_wkt('{}'), 20000, 6, 6)".format(
                self._CATK
            )
        ).evaluate().asPolyline()

        self.assertEqual(len(head), 5)

        # Its middle point is the tip, on PT1 itself.
        self.assertAlmostEqual(head[2].x(), 0.05, places=9)
        self.assertAlmostEqual(head[2].y(), 0.0, places=9)

        # And it reaches wider than the bar it grows out of.
        reach = max(abs(point.y()) for point in head)

        bar = QgsExpression(
            "mct_counterattack_rear(geom_from_wkt('{}'), 20000, 6)".format(
                self._CATK
            )
        ).evaluate().asPolyline()

        self.assertGreater(reach, max(abs(point.y()) for point in bar))


    def test_the_rear_bar_closes_the_arrow_at_the_last_click(self):

        bar = QgsExpression(
            "mct_counterattack_rear(geom_from_wkt('{}'), 20000, 6)".format(
                self._CATK
            )
        ).evaluate().asPolyline()

        self.assertEqual(len(bar), 2)

        for point in bar:

            self.assertAlmostEqual(point.x(), 0.0, places=9)


    def test_the_text_follows_the_arrow_but_never_stands_on_its_head(self):

        def angle(wkt):

            return QgsExpression(
                "mct_counterattack_text_angle(geom_from_wkt('{}'))".format(wkt)
            ).evaluate()

        # Pointing east - upright and unrotated.
        self.assertAlmostEqual(angle("LineString(1 0, 0 0)"), 0.0, places=9)

        # Pointing WEST. Read literally that is half a turn, which
        # would write CATK upside down; folded, it is the same as east.
        self.assertAlmostEqual(angle("LineString(0 0, 1 0)"), 0.0, places=9)

        # **CLOCKWISE, which is what QGIS's label rotation takes.** A
        # head climbing north-east tilts the text UP the page, and that
        # is a NEGATIVE rotation in QGIS's own sense. The first build
        # had this the other way round and drew every label mirrored
        # about the horizontal.
        self.assertAlmostEqual(angle("LineString(1 1, 0 0)"), -45.0, places=9)

        self.assertAlmostEqual(
            angle("LineString(0 0, 1 1)"), -45.0, places=9
        )

        # Every direction of the compass stays legible.
        for degrees in range(0, 360, 7):

            radians = math.radians(degrees)

            result = angle(
                "LineString({} {}, 0 0)".format(
                    math.cos(radians), math.sin(radians)
                )
            )

            self.assertGreaterEqual(result, -90.0)

            self.assertLess(result, 90.0)


    def test_which_end_of_catk_lands_at_the_arrowhead(self):

        # The maintainer's own restatement of what "upright" means:
        # "left to right K is near the arrowhead, right to left C is
        # near the arrowhead". Both follow from the text always reading
        # left to right on the page, which is what the fold guarantees.
        def reads_towards_the_head(wkt):

            geometry = QgsGeometry.fromWkt(wkt)

            tip = geometry.asPolyline()[0]

            behind = geometry.asPolyline()[1]

            rotation = QgsExpression(
                "mct_counterattack_text_angle(geom_from_wkt('{}'))".format(wkt)
            ).evaluate()

            # The direction the text runs, C towards K, on the page.
            reading = math.radians(-rotation)

            return (
                math.cos(reading) * (tip.x() - behind.x())
                + math.sin(reading) * (tip.y() - behind.y())
            ) > 0

        # Pointing east: the text runs the same way the arrow does, so
        # K - its last letter - is the one at the head.
        self.assertTrue(reads_towards_the_head("LineString(1 0, 0 0)"))

        # Pointing west: the text still runs east, which is now AWAY
        # from the head, so C is the letter that lands there.
        self.assertFalse(reads_towards_the_head("LineString(0 0, 1 0)"))


    def test_the_angle_is_wired_onto_both_counterattack_labels(self):

        rotated = {}

        for rule in self.layer.labeling().rootRule().children():

            if rule.description() not in COUNTERATTACK_MEASURE_TYPES:
                continue

            rotated[rule.description()] = rule.settings(
            ).dataDefinedProperties().isActive(
                QgsPalLayerSettings.Property.LabelRotation
            )

        self.assertEqual(
            rotated,
            {"counterattack": True, "counterattack_by_fire": True}
        )


    def test_by_fire_is_counterattack_plus_a_bracket_and_a_solid_arrow(self):

        plain = self._expressions("counterattack")

        by_fire = self._expressions("counterattack_by_fire")

        for expression in plain:

            self.assertIn(expression, by_fire)

        self.assertEqual(len(by_fire), len(plain) + 2)

        self.assertIn(
            "mct_counterattack_by_fire_arrow($geometry, @map_scale)", by_fire
        )


    def test_the_bracket_wraps_the_arrowhead_rather_than_barring_it(self):

        # It was a bar across the axis first, and a filled triangle
        # sitting on a bar reads as a flag on a pole - which is what
        # the maintainer sent back. The standard's own example draws an
        # open bracket whose arms sweep BACK past the tip.
        bracket = QgsExpression(
            "mct_counterattack_by_fire_bracket(geom_from_wkt('{}'),"
            " 20000, 6)".format(self._CATK)
        ).evaluate().asPolyline()

        self.assertEqual(len(bracket), 4)

        # Its straight run stands clear of the tip...
        for point in bracket[1:3]:

            self.assertGreater(point.x(), 0.05)

        # ...and its two arms reach back behind it, and wider.
        for point in (bracket[0], bracket[-1]):

            self.assertLess(point.x(), 0.05)

            self.assertGreater(abs(point.y()), abs(bracket[1].y()))


    def test_the_bracket_spans_the_head_it_wraps(self):

        # Same reach as the head's own flare, by construction rather
        # than by coincidence.
        bracket = QgsExpression(
            "mct_counterattack_by_fire_bracket(geom_from_wkt('{}'),"
            " 20000, 6)".format(self._CATK)
        ).evaluate().asPolyline()

        head = QgsExpression(
            "mct_counterattack_head(geom_from_wkt('{}'), 20000, 6, 6)".format(
                self._CATK
            )
        ).evaluate().asPolyline()

        self.assertAlmostEqual(
            abs(bracket[1].y()),
            max(abs(point.y()) for point in head),
            places=9
        )


    def test_the_by_fire_arrow_is_filled_and_points_on_past_the_bracket(self):

        arrow = QgsExpression(
            "mct_counterattack_by_fire_arrow(geom_from_wkt('{}'),"
            " 20000)".format(self._CATK)
        ).evaluate()

        self.assertEqual(arrow.wkbType(), Qgis.WkbType.Polygon)

        bracket = QgsExpression(
            "mct_counterattack_by_fire_bracket(geom_from_wkt('{}'),"
            " 20000, 6)".format(self._CATK)
        ).evaluate()

        # Its tip is the furthest thing forward in the whole symbol.
        self.assertGreater(
            arrow.boundingBox().xMaximum(), bracket.boundingBox().xMaximum()
        )

        # **It has a stem**, which is what stops it reading as a flag
        # on a pole: a bare triangle would be three corners, and this
        # has the four more that make the shaft.
        self.assertEqual(len(arrow.asPolygon()[0]), 8)

        # And it stands clear of the bracket rather than against it.
        self.assertGreater(
            arrow.boundingBox().xMinimum(), bracket.boundingBox().xMaximum()
        )


    def test_degenerate_input_draws_none_of_it(self):

        for expression, arguments in (
            ("mct_counterattack_head", "20000, 6, 6"),
            ("mct_counterattack_rear", "20000, 6"),
            ("mct_counterattack_by_fire_bracket", "20000, 6"),
            ("mct_counterattack_by_fire_arrow", "20000"),
        ):
            for wkt in ("LineString(0 0, 0 0)", "LineString(0 0)"):

                self.assertTrue(
                    QgsExpression(
                        "{}(geom_from_wkt('{}'), {})".format(
                            expression, wkt, arguments
                        )
                    ).evaluate().isEmpty(),
                    msg="{} {}".format(expression, wkt)
                )
