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
    QgsFeature,
    QgsGeometry,
    QgsProject,
)

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
