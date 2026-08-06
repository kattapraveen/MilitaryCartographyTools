# -*- coding: utf-8 -*-

"""
Tests for expressions/military_symbology_functions.py's
mct_area_km2()/mct_perimeter_km() - geodesic AO/NAI area and perimeter
reporting in the standard military units (km²/km), via QgsDistanceArea
rather than QGIS's own $area/$perimeter (which need the project's own
Ellipsoidal measurement setting configured correctly to avoid returning
square degrees on a geographic-CRS layer).

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
)

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestAreaAndPerimeterFunctions(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "test", "memory")

        self.feature = QgsFeature(self.layer.fields())

        # A 0.01deg x 0.01deg box at the equator - independently
        # verified via a direct QgsDistanceArea calculation before
        # writing this test, not guessed: ~1.2309 km^2 area,
        # ~4.4379 km perimeter.
        self.feature.setGeometry(
            QgsGeometry.fromWkt(
                "POLYGON((0 0, 0 0.01, 0.01 0.01, 0.01 0, 0 0))"
            )
        )

        self.context = QgsExpressionContext()

        self.context.appendScope(
            QgsExpressionContextUtils.layerScope(self.layer)
        )

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
            "mct_area_km2($geometry, @layer)"
        )

        self.assertAlmostEqual(
            result,
            1.2309072049932537,
            places=6
        )


    def test_perimeter_km_matches_geodesic_calculation(self):

        result = self._evaluate(
            "mct_perimeter_km($geometry, @layer)"
        )

        self.assertAlmostEqual(
            result,
            4.43787531568142,
            places=6
        )
