# -*- coding: utf-8 -*-

"""
Tests for expressions/military_symbology_functions.py's
mct_area_km2()/mct_perimeter_km()/mct_length_km() - geodesic AO/NAI
area/perimeter and phase-line/boundary length reporting in the standard
military units (km²/km), via QgsDistanceArea rather than QGIS's own
$area/$perimeter (which need the project's own Ellipsoidal measurement
setting configured correctly to avoid returning square degrees on a
geographic-CRS layer).

These take only $geometry, not a layer - see
military_symbology_functions._distance_area()'s own docstring for why:
confirmed live that QGIS's in-place/attribute-table field calculator
toolbar does not populate @layer, silently producing NULL (shown as
"nan") even though $geometry itself resolves fine and @layer resolves
correctly through other entry points like the classic Field Calculator
dialog. Using QgsProject.instance().crs() instead sidesteps that
inconsistency entirely.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsGeometry,
    QgsMapSettings,
    QgsProject,
    QgsRectangle,
)

from qgis.PyQt.QtCore import QSize

import math

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestAreaAndPerimeterFunctions(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.feature = QgsFeature()

        # A 0.01deg x 0.01deg box at the equator - independently
        # verified via a direct QgsDistanceArea calculation before
        # writing this test, not guessed: ~1.2309 km^2 area,
        # ~4.4379 km perimeter.
        self.feature.setGeometry(
            QgsGeometry.fromWkt(
                "POLYGON((0 0, 0 0.01, 0.01 0.01, 0.01 0, 0 0))"
            )
        )

        # Deliberately NOT a layer-scoped context (no @layer variable at
        # all) - this is the whole point: these functions must not need
        # one.
        self.context = QgsExpressionContext()

        self.context.setFeature(
            self.feature
        )


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _evaluate(self, expression_text):

        expression = QgsExpression(expression_text)

        result = expression.evaluate(self.context)

        self.assertFalse(
            expression.hasEvalError(),
            expression.evalErrorString()
        )

        return result


    def test_area_km2_matches_geodesic_calculation(self):

        result = self._evaluate(
            "mct_area_km2($geometry)"
        )

        self.assertAlmostEqual(
            result,
            1.2309072049932537,
            places=6
        )


    def test_perimeter_km_matches_geodesic_calculation(self):

        result = self._evaluate(
            "mct_perimeter_km($geometry)"
        )

        self.assertAlmostEqual(
            result,
            4.43787531568142,
            places=6
        )


class TestCrenellateOutlineFunction(QgisTestCase):

    """
    Tests for mct_crenellate_outline() - Fortified Area's own
    castellated boundary (military_symbology/maneuver_control_measures.
    py). See that function's own docstring for why a real computed
    geometry was needed here rather than a QgsMarkerLineSymbolLayer
    styling trick (two earlier attempts using the latter both broke
    down on a real curved/multi-vertex boundary).
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.feature = QgsFeature()

        self.feature.setGeometry(
            QgsGeometry.fromWkt(
                "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))"
            )
        )

        self.context = QgsExpressionContext()

        self.context.setFeature(
            self.feature
        )


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _evaluate(self, expression_text):

        expression = QgsExpression(expression_text)

        result = expression.evaluate(self.context)

        self.assertFalse(
            expression.hasEvalError(),
            expression.evalErrorString()
        )

        return result


    def test_returns_a_non_empty_line_geometry(self):

        result = self._evaluate(
            "mct_crenellate_outline($geometry, 12)"
        )

        self.assertIsInstance(result, QgsGeometry)
        self.assertFalse(result.isEmpty())


    def test_teeth_protrude_outward_beyond_the_original_boundary(self):

        # The crenellated outline's own bounding box must be strictly
        # larger than the original polygon's - if the teeth pointed the
        # wrong way (inward) or weren't offset at all, the bounding box
        # would match or shrink instead.
        result = self._evaluate(
            "mct_crenellate_outline($geometry, 12)"
        )

        original_bbox = self.feature.geometry().boundingBox()
        crenellated_bbox = result.boundingBox()

        self.assertGreater(
            crenellated_bbox.width(),
            original_bbox.width()
        )
        self.assertGreater(
            crenellated_bbox.height(),
            original_bbox.height()
        )


    def test_output_is_a_closed_ring(self):

        result = self._evaluate(
            "mct_crenellate_outline($geometry, 12)"
        )

        line = result.constGet()

        first_point = line.pointN(0)
        last_point = line.pointN(line.numPoints() - 1)

        self.assertAlmostEqual(first_point.x(), last_point.x(), places=9)
        self.assertAlmostEqual(first_point.y(), last_point.y(), places=9)


    def test_more_teeth_produces_more_vertices(self):

        few_teeth = self._evaluate(
            "mct_crenellate_outline($geometry, 8)"
        )
        many_teeth = self._evaluate(
            "mct_crenellate_outline($geometry, 20)"
        )

        self.assertGreater(
            many_teeth.constGet().numPoints(),
            few_teeth.constGet().numPoints()
        )


    def test_defaults_to_fourteen_teeth_when_omitted(self):

        default_call = self._evaluate(
            "mct_crenellate_outline($geometry)"
        )
        explicit_fourteen = self._evaluate(
            "mct_crenellate_outline($geometry, 14)"
        )

        self.assertEqual(
            default_call.constGet().numPoints(),
            explicit_fourteen.constGet().numPoints()
        )


class TestLengthFunction(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.feature = QgsFeature()

        # A 0.01deg line along the equator - independently verified via
        # a direct QgsDistanceArea calculation before writing this
        # test: ~1.1132 km, matching the well-known ~111.32 km/degree
        # of longitude at the equator.
        self.feature.setGeometry(
            QgsGeometry.fromWkt("LINESTRING(0 0, 0.01 0)")
        )

        self.context = QgsExpressionContext()

        self.context.setFeature(
            self.feature
        )


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_length_km_matches_geodesic_calculation(self):

        expression = QgsExpression("mct_length_km($geometry)")

        result = expression.evaluate(self.context)

        self.assertFalse(
            expression.hasEvalError(),
            expression.evalErrorString()
        )

        self.assertAlmostEqual(
            result,
            1.1131949079327358,
            places=6
        )


class TestInscribedCircleFunctions(QgisTestCase):

    """
    mct_inscribed_centre() and mct_inscribed_radius_mm() - the pair
    that lets Table H-XXI's contaminated areas size their own glyph to
    the area they sit in.

    The radius is in PAGE millimetres, and that is the whole subtlety:
    the first build measured it geodesically, which is a perfectly
    defensible measurement of the ground and the wrong answer for the
    page - a degree of longitude and a degree of latitude take the
    same width on a map drawn in a geographic CRS but are not the same
    distance on the Earth. It drew the glyph 29% oversized.
    """

    def setUp(self):

        super().setUp()

        military_symbology_functions.register()

        self.project = QgsProject.instance()
        self.project.setCrs(WGS84)

    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()

    def _context_for(self, geometry, extent, width_px, dpi):

        settings = QgsMapSettings()
        settings.setDestinationCrs(WGS84)
        settings.setOutputSize(QSize(width_px, width_px))
        settings.setOutputDpi(dpi)
        settings.setExtent(extent)

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.globalScope())
        context.appendScope(
            QgsExpressionContextUtils.projectScope(self.project)
        )
        context.appendScope(
            QgsExpressionContextUtils.mapSettingsScope(settings)
        )

        feature = QgsFeature()
        feature.setGeometry(geometry)
        context.setFeature(feature)

        return context

    def test_the_centre_is_the_pole_of_inaccessibility(self):

        # A rectangle twice as wide as it is tall: the point furthest
        # from any edge is the middle, and the largest circle that fits
        # has the half-HEIGHT as its radius.
        geometry = QgsGeometry.fromWkt(
            "POLYGON((77.0 28.0, 77.2 28.0, 77.2 28.1, 77.0 28.1, 77.0 28.0))"
        )

        context = self._context_for(
            geometry, QgsRectangle(76.9, 27.9, 77.3, 28.3), 800, 96
        )

        centre = QgsExpression(
            "mct_inscribed_centre($geometry)"
        ).evaluate(context).asPoint()

        self.assertAlmostEqual(centre.x(), 77.1, places=3)
        self.assertAlmostEqual(centre.y(), 28.05, places=3)

    def test_the_radius_is_the_distance_the_page_actually_shows(self):

        geometry = QgsGeometry.fromWkt(
            "POLYGON((77.0 28.0, 77.2 28.0, 77.2 28.1, 77.0 28.1, 77.0 28.0))"
        )

        # A square view 0.4 degrees across, 800 px wide at 96 dpi - so
        # the page is 800/96 inch = 211.667 mm wide, and one degree of
        # the view is exactly a quarter of that whatever the latitude,
        # because the map draws degrees, not metres.
        extent = QgsRectangle(76.9, 27.9, 77.3, 28.3)

        context = self._context_for(geometry, extent, 800, 96)

        millimetres_per_degree = (800 / 96.0 * 25.4) / extent.width()

        radius_mm = QgsExpression(
            "mct_inscribed_radius_mm($geometry, @map_extent, @map_scale)"
        ).evaluate(context)

        # The rectangle's own half-height, 0.05 degrees.
        self.assertAlmostEqual(
            radius_mm, 0.05 * millimetres_per_degree, places=3
        )

    def test_the_radius_is_a_page_measure_not_a_ground_one(self):

        # The bug this pair was rebuilt to fix, pinned directly: at 28
        # degrees north a geodesic measurement of the same 0.05 degrees
        # is over a quarter larger than what the page shows.
        geometry = QgsGeometry.fromWkt(
            "POLYGON((77.0 28.0, 77.2 28.0, 77.2 28.1, 77.0 28.1, 77.0 28.0))"
        )

        extent = QgsRectangle(76.9, 27.9, 77.3, 28.3)

        context = self._context_for(geometry, extent, 800, 96)

        radius_mm = QgsExpression(
            "mct_inscribed_radius_mm($geometry, @map_extent, @map_scale)"
        ).evaluate(context)

        ground_metres = military_symbology_functions._distance_area(
        ).measureLine(
            QgsGeometry.fromWkt("POINT(77.1 28.05)").asPoint(),
            QgsGeometry.fromWkt("POINT(77.1 28.0)").asPoint()
        )

        map_scale = QgsExpression("@map_scale").evaluate(context)

        geodesic_mm = ground_metres * 1000.0 / map_scale

        self.assertGreater(geodesic_mm, radius_mm * 1.2)

    def test_the_radius_does_not_depend_on_how_big_the_window_is(self):

        # @map_scale already carries the window size, so a wider window
        # at the same extent is a smaller scale and the same number of
        # millimetres. If the recovery of metres-per-unit ever stops
        # cancelling its own reference DPI and width, this catches it.
        geometry = QgsGeometry.fromWkt(
            "POLYGON((77.0 28.0, 77.2 28.0, 77.2 28.1, 77.0 28.1, 77.0 28.0))"
        )

        extent = QgsRectangle(76.9, 27.9, 77.3, 28.3)

        expression = QgsExpression(
            "mct_inscribed_radius_mm($geometry, @map_extent, @map_scale)"
        )

        small = expression.evaluate(
            self._context_for(geometry, extent, 400, 96)
        )

        large = expression.evaluate(
            self._context_for(geometry, extent, 1600, 96)
        )

        self.assertAlmostEqual(small * 4.0, large, places=3)

    def test_a_point_has_no_inscribed_circle(self):

        # A geometry generator's own sub-symbol sees the POINT being
        # drawn rather than the feature's polygon, so this path is
        # reached in real use - it must not raise.
        context = self._context_for(
            QgsGeometry.fromWkt("POINT(77.1 28.05)"),
            QgsRectangle(76.9, 27.9, 77.3, 28.3),
            800,
            96
        )

        self.assertEqual(
            QgsExpression(
                "mct_inscribed_radius_mm($geometry, @map_extent, @map_scale)"
            ).evaluate(context),
            0.0
        )

        self.assertIsNone(
            QgsExpression(
                "mct_inscribed_centre($geometry)"
            ).evaluate(context)
        )
