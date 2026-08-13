# -*- coding: utf-8 -*-

"""
Tests for military_symbology/field_fortification.py - Table H-XX,
Mini-Phase H17.

Military Cartography Tools
"""

import base64
import re

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import field_fortification
from MilitaryCartographyTools.military_symbology.field_fortification import (
    LINE_MEASURE_TYPE_CODES,
    LINE_MEASURE_TYPE_LABELS,
    POINT_ENTITY_CODES,
    POINT_ENTITY_LABELS,
    create_field_fortification_lines_layer,
    create_field_fortification_points_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES

from qgis.core import (QgsCoordinateReferenceSystem, QgsExpression,
                       QgsProject, QgsSymbolLayer)

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

        # The profile IS the line - no straight line underneath it.
        self.assertEqual(symbol.symbolLayerCount(), 1)

        marker_line = symbol.symbolLayer(0)

        self.assertEqual(
            marker_line.placements(), Qgis.MarkerLinePlacement.Interval
        )
        self.assertAlmostEqual(
            marker_line.interval(),
            _RAMPART_TILE_MM - _RAMPART_TILE_OVERLAP_MM
        )
        self.assertEqual(
            marker_line.intervalUnit(), Qgis.RenderUnit.Millimeters
        )
        self.assertTrue(marker_line.rotateSymbols())


    def test_fortified_position_front_is_just_the_two_clicked_points(self):

        from qgis.core import QgsGeometry, QgsPointXY

        wkt = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), QgsPointXY(100, 0), QgsPointXY(150, 60)]
        ).asWkt()

        result = QgsExpression(
            "mct_fortified_position_front(geom_from_wkt('{}'))".format(wkt)
        ).evaluate()

        points = result.asPolyline()

        # Trimmed, so a stray third click cannot bend the front bar.
        self.assertEqual(len(points), 2)
        self.assertAlmostEqual(points[1].x(), 100)
        self.assertAlmostEqual(points[1].y(), 0)


    def test_fortified_position_legs_are_a_fixed_millimetre_depth(self):

        # "Points 1 and 2 determine the length of the symbol, which
        # varies only in length" - so the depth is fixed, and therefore
        # cannot be generated geometry (layer units) at all.
        from qgis.core import Qgis, QgsMarkerLineSymbolLayer

        from MilitaryCartographyTools.military_symbology.field_fortification import (
            _FORTIFIED_POSITION_DEPTH_MM,
            _fortified_position_symbol,
        )

        symbol = _fortified_position_symbol()

        self.assertEqual(symbol.symbolLayerCount(), 2)

        leg_generator = symbol.symbolLayer(1)

        inner = leg_generator.subSymbol()

        marker_line = inner.symbolLayer(0)

        self.assertIsInstance(marker_line, QgsMarkerLineSymbolLayer)

        # The front is trimmed to two points, so "every vertex" is
        # exactly the two front corners.
        self.assertEqual(
            marker_line.placements(), Qgis.MarkerLinePlacement.Vertex
        )
        self.assertTrue(marker_line.rotateSymbols())

        marker = marker_line.subSymbol()

        # QGIS sizes an SVG marker by its WIDTH, and the leg glyph's
        # viewBox is 2*depth square - so the marker is 2*depth and one
        # viewBox unit is one millimetre.
        self.assertAlmostEqual(
            marker.symbolLayer(0).size(), 2.0 * _FORTIFIED_POSITION_DEPTH_MM
        )


    def test_the_leg_glyph_runs_back_from_the_corner(self):

        svg = QgsExpression(
            "mct_fortified_position_leg_svg('rgb(0,0,0)', 4.0, 0.4)"
        ).evaluate()

        markup = base64.b64decode(svg[len("base64:"):]).decode("utf-8")

        path = re.search(r'd="([^"]+)"', markup).group(1)

        # Starts AT the corner (the glyph's own origin) and runs to
        # +y, which a rotated marker puts on the RIGHT of travel -
        # leaving the closed front facing left.
        self.assertTrue(path.startswith("M 0,0"))

        end_y = float(re.search(r"L 0,([\d.]+)", path).group(1))

        self.assertAlmostEqual(end_y, 4.0)


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
