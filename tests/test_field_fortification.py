# -*- coding: utf-8 -*-

"""
Tests for military_symbology/field_fortification.py - Table H-XX,
Mini-Phase H17.

Military Cartography Tools
"""

import base64
import re

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import field_fortification
from MilitaryCartographyTools.military_symbology.field_fortification import (
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_CODES,
    LINE_MEASURE_TYPE_LABELS,
    POINTS_LAYER_NAME,
    POINT_ENTITY_CODES,
    POINT_ENTITY_LABELS,
    add_field_fortification_lines_layer,
    add_field_fortification_points_layer,
    create_field_fortification_lines_layer,
    create_field_fortification_points_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES

from qgis.core import (QgsCoordinateReferenceSystem, QgsExpression,
                       QgsProject, QgsSimpleLineSymbolLayer,
                       QgsSymbolLayer)

WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestFieldFortificationVocabulary(QgisTestCase):

    def test_the_four_point_codes_match_the_table(self):

        # Read straight off Table H-XX's own CONTROL MEASURE column.
        self.assertEqual(
            POINT_ENTITY_CODES,
            {
                "shelter": "280900",
                "shelter_above_ground": "281000",
                "shelter_below_ground": "281100",
                "fort": "281200",
            }
        )

        self.assertEqual(
            set(POINT_ENTITY_LABELS), set(POINT_ENTITY_CODES)
        )


    def test_every_point_entity_is_real_sidc_vocabulary(self):

        # These are RELOCATED from control_measure_points.py, not new -
        # so they must already exist, with these exact codes.
        for entity, code in POINT_ENTITY_CODES.items():

            with self.subTest(entity=entity):

                self.assertEqual(
                    ENTITIES["control_measure"][entity], code
                )


    def test_the_two_line_codes_match_the_table(self):

        self.assertEqual(
            LINE_MEASURE_TYPE_CODES,
            {"fortified_line": "290900", "fortified_position": "291000"}
        )

        self.assertEqual(
            set(LINE_MEASURE_TYPE_LABELS), set(LINE_MEASURE_TYPE_CODES)
        )


class TestFieldFortificationPoints(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_the_layer_offers_exactly_the_four_entries(self):

        layer = create_field_fortification_points_layer()

        self.assertTrue(layer.isValid())

        fields = {field.name() for field in layer.fields()}

        # Control-measure points get neither echelon nor a headquarters
        # flag - Appendix H's own amplifier table gives them neither.
        self.assertNotIn("echelon", fields)
        self.assertNotIn("headquarters", fields)

        self.assertIn("affiliation", fields)
        self.assertIn("entity", fields)
        self.assertIn("status", fields)


    def test_every_entity_renders_a_real_glyph_not_the_unknown_icon(self):

        # The defect class this project has hit three times: an entity
        # present in sidc.py that still renders as the unknown icon.
        for entity in POINT_ENTITY_LABELS:

            with self.subTest(entity=entity):

                sidc = QgsExpression(
                    "mct_build_sidc('friend', '{}', 'control_measure',"
                    " 'unspecified', 'present', false)".format(entity)
                ).evaluate()

                self.assertEqual(len(sidc), 20)
                self.assertTrue(sidc.isdigit())

                self.assertEqual(
                    sidc[10:16], POINT_ENTITY_CODES[entity]
                )

                svg = QgsExpression(
                    "mct_sidc_svg('{}', '', '', 'rgb(0,0,0)', 1.0)"
                    .format(sidc)
                ).evaluate()

                self.assertTrue(svg.startswith("base64:"))


    def test_the_four_entries_left_the_shared_points_layer(self):

        from MilitaryCartographyTools.military_symbology.control_measure_points import (
            _ENTITY_LABELS as _SHARED,
        )

        self.assertEqual(
            set(POINT_ENTITY_LABELS) & set(_SHARED), set()
        )


class TestFieldFortificationLines(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_both_line_types_are_offered(self):

        layer = create_field_fortification_lines_layer()

        self.assertTrue(layer.isValid())

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertEqual(labels, set(LINE_MEASURE_TYPE_LABELS))


    def test_the_svg_colour_expression_matches_the_shared_one(self):

        # _RAMPART_GLYPH_COLOR_EXPRESSION exists only because the
        # shared affiliation expression is built from color_rgb(),
        # which evaluates to a bare "0,0,255" - valid for a QGIS colour
        # property and silently invalid inside SVG markup, where it
        # renders nothing at all. The two must agree on every hue, or
        # the glyphs drift away from the lines beside them.
        from MilitaryCartographyTools.military_symbology._control_measure_shared import (
            _AFFILIATION_COLOR_EXPRESSION,
        )

        shared = dict(
            re.findall(
                r"'(\w+)' THEN color_rgb\((\d+), (\d+), (\d+)\)".replace(
                    "(\\d+), (\\d+), (\\d+)", "([\\d, ]+)"
                ),
                _AFFILIATION_COLOR_EXPRESSION
            )
        )

        css = dict(
            re.findall(
                r"'(\w+)' THEN 'rgb\(([\d,]+)\)'",
                field_fortification._RAMPART_GLYPH_COLOR_EXPRESSION
            )
        )

        self.assertEqual(set(shared), set(css))

        for affiliation, triple in shared.items():

            with self.subTest(affiliation=affiliation):

                self.assertEqual(
                    triple.replace(" ", ""), css[affiliation]
                )


    def test_the_rampart_tile_repeats_seamlessly(self):

        # Consecutive tiles have to butt into one continuous profile,
        # so the tile must start and end at the SAME height - otherwise
        # every join shows a step.
        svg = QgsExpression("mct_rampart_svg('rgb(0,0,0)')").evaluate()

        self.assertTrue(svg.startswith("base64:"))

        markup = base64.b64decode(svg[len("base64:"):]).decode("utf-8")

        path = re.search(r'd="([^"]+)"', markup).group(1)

        points = re.findall(r"(-?[\d.]+),(-?[\d.]+)", path)

        first_y = float(points[0][1])
        last_y = float(points[-1][1])

        self.assertAlmostEqual(first_y, last_y)

        # The merlon rises toward NEGATIVE y, which a rotated marker
        # puts on the LEFT of travel - the side the template draws.
        self.assertLess(min(float(y) for _x, y in points), first_y)


    def test_the_rampart_tiles_overlap_to_avoid_hairline_joins(self):

        from qgis.core import Qgis

        from MilitaryCartographyTools.military_symbology.field_fortification import (
            _RAMPART_TILE_MM,
            _RAMPART_TILE_OVERLAP_MM,
            _fortified_line_symbol,
        )

        self.assertGreater(_RAMPART_TILE_OVERLAP_MM, 0)
        self.assertLess(_RAMPART_TILE_OVERLAP_MM, _RAMPART_TILE_MM * 0.25)

        symbol = _fortified_line_symbol()

        # Four marker lines, and NONE of them a plain line under the
        # whole profile - the profile IS the line, and a continuous
        # underlay would close every merlon into a box. The other three
        # are the corner bridge and the two end runs, each placed only
        # where tiling cannot reach; see _RAMPART_CORNER_CONNECTOR_MM.
        self.assertEqual(symbol.symbolLayerCount(), 4)

        self.assertEqual(
            [
                symbol.symbolLayer(index).placements()
                for index in range(symbol.symbolLayerCount())
            ],
            [
                Qgis.MarkerLinePlacement.InnerVertices,
                Qgis.MarkerLinePlacement.Interval,
                Qgis.MarkerLinePlacement.FirstVertex,
                Qgis.MarkerLinePlacement.LastVertex,
            ]
        )

        marker_line = symbol.symbolLayer(1)
        self.assertAlmostEqual(
            marker_line.interval(),
            _RAMPART_TILE_MM - _RAMPART_TILE_OVERLAP_MM
        )
        self.assertEqual(
            marker_line.intervalUnit(), Qgis.RenderUnit.Millimeters
        )
        self.assertTrue(marker_line.rotateSymbols())


    def test_both_lines_follow_present_planned_status(self):

        from MilitaryCartographyTools.military_symbology.field_fortification import (
            _fortified_position_symbol,
        )

        symbol = _fortified_position_symbol()

        front = symbol.symbolLayer(0).subSymbol().symbolLayer(0)

        self.assertTrue(
            front.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.StrokeStyle
            )
        )


class TestFieldFortificationLayerInsertion(QgisTestCase):

    """
    Actually CALL both add_*_layer(iface) entry points.

    Every test above this class builds its layer through create_*(),
    which is why this module shipped with add_field_fortification_
    points_layer() calling the wrong helper with the wrong arity - the
    suite never once ran the function the menu item is wired to, so a
    plain TypeError only surfaced on the maintainer's own restart of
    QGIS. Both new H17/H18 modules had it; both are covered now.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_adding_the_points_layer_inserts_exactly_one(self):

        layer = add_field_fortification_points_layer(self.iface)

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)),
            1
        )


    def test_adding_the_lines_layer_inserts_exactly_one(self):

        layer = add_field_fortification_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)),
            1
        )


    def test_a_second_add_warns_instead_of_replacing(self):

        for add, name in (
            (add_field_fortification_points_layer, POINTS_LAYER_NAME),
            (add_field_fortification_lines_layer, LINES_LAYER_NAME),
        ):

            first = add(self.iface)

            self.assertIsNone(add(self.iface))

            matching = QgsProject.instance().mapLayersByName(name)

            self.assertEqual(len(matching), 1)

            self.assertEqual(matching[0].id(), first.id())

        self.assertEqual(len(self.iface.messageBar().calls), 2)


class TestFieldFortificationSmokeTestFixes(QgisTestCase):

    """
    The three Table H-XX defects the maintainer's own 2026-08-13 smoke
    test turned up.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_measure_type_has_a_default_so_no_null_option_appears(self):

        # "in the lines menu, there is an additional null option unlike
        # any other menu - in measure_type - why?" Because this layer
        # was the one that never set a default, so a new feature's
        # measure_type started NULL and QGIS put its own null entry at
        # the top of the ValueMap.
        layer = create_field_fortification_lines_layer()

        default = layer.defaultValueDefinition(
            layer.fields().indexOf("measure_type")
        ).expression()

        self.assertEqual(default, "'fortified_line'")

        self.assertIn(
            QgsExpression(default).evaluate(),
            LINE_MEASURE_TYPE_LABELS
        )


    def test_the_rampart_tile_starts_and_ends_level(self):

        # "at pt1 it is directly starting with the open square, it
        # should start with a small line segment like it ends at pt2."
        # The tile used to open with the merlon's own rise at x=0.
        svg = self._rampart_svg()

        path = re.search(r'\bd="([^"]*)"', svg).group(1)

        commands = path.replace(",", " ").split()

        # "M 0,50 L 25,50 ..." - a level run out of the origin.
        self.assertEqual(commands[:6], ["M", "0", "50", "L", "25", "50"])

        # ...and the same level run into the tile's own right edge, so
        # the LAST tile leaves one at PT2 too.
        self.assertEqual(commands[-6:], ["L", "75", "50", "L", "100", "50"])


    def test_the_ramparts_rhythm_is_unchanged_by_that_shift(self):

        # Only the phase moved. A merlon 50 wide with 50 of gap either
        # side of it is the same square wave the maintainer already
        # signed off as "quite ok"; splitting the gap across the tile's
        # two ends is what buys the lead-in.
        path = re.search(r'\bd="([^"]*)"', self._rampart_svg()).group(1)

        xs = [
            float(pair.split(",")[0])
            for pair in re.findall(r"[-\d.]+,[-\d.]+", path)
        ]

        self.assertEqual(xs, [0.0, 25.0, 25.0, 75.0, 75.0, 100.0])


    def _rampart_svg(self):

        path = QgsExpression(
            "mct_rampart_svg('rgb(0,0,0)')"
        ).evaluate()

        return base64.b64decode(
            path[len("base64:"):]
        ).decode("utf-8")


    def test_fortified_position_is_built_on_the_bypass_frame(self):

        # "make the construction same as obstacle bypass easy, except
        # the lines dont start/end with arrowhead but are plain."
        symbol = field_fortification._fortified_position_symbol()

        expressions = [
            symbol.symbolLayer(index).geometryExpression()
            for index in range(symbol.symbolLayerCount())
        ]

        self.assertEqual(
            expressions,
            [
                "mct_obstacle_bypass_rear_easy($geometry)",
                "mct_obstacle_bypass_arrows($geometry)",
            ]
        )


    def test_fortified_position_draws_no_arrowheads(self):

        # The one part of Obstacle Bypass deliberately NOT reused. Any
        # marker layer at all would be an arrowhead sneaking back in.
        symbol = field_fortification._fortified_position_symbol()

        for index in range(symbol.symbolLayerCount()):

            inner = symbol.symbolLayer(index).subSymbol()

            for sub in range(inner.symbolLayerCount()):

                self.assertIsInstance(
                    inner.symbolLayer(sub),
                    QgsSimpleLineSymbolLayer
                )


    def test_fortified_position_actually_draws_both_legs(self):

        # The defect itself: "the legs are not forming". Evaluate the
        # real geometry rather than trusting the expression string -
        # the previous construction's own expression looked right and
        # drew nothing.
        wkt = "LineString(0 0, 10 0, 5 -4)"

        arms = QgsExpression(
            "mct_obstacle_bypass_arrows(geom_from_wkt('{}'))".format(wkt)
        ).evaluate()

        self.assertEqual(len(arms.asMultiPolyline()), 2)

        for arm in arms.asMultiPolyline():

            self.assertEqual(len(arm), 2)

            self.assertNotEqual(arm[0], arm[1])

        bar = QgsExpression(
            "mct_obstacle_bypass_rear_easy(geom_from_wkt('{}'))".format(wkt)
        ).evaluate()

        self.assertEqual(len(bar.asPolyline()), 2)
