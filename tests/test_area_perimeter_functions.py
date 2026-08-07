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
