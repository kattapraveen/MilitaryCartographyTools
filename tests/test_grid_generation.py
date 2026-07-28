# -*- coding: utf-8 -*-

"""
Tests for the grid generator classes (grid/utm_grid.py,
grid/mgrs_100k.py, grid/mgrs_sub_grid.py) and the shared helpers
they lean on (core/coordinate_utils.py, core/text_format.py,
grid/_style_utils.py).

Military Cartography Tools
"""

from qgis.core import QgsProject, QgsRectangle, QgsCoordinateReferenceSystem

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.core.coordinate_utils import (
    WGS84,
    get_utm_crs,
    get_utm_crs_from_zone_band,
)
from MilitaryCartographyTools.core.text_format import build_font, build_text_format
from MilitaryCartographyTools.grid.utm_grid import UTMGridGenerator
from MilitaryCartographyTools.grid.mgrs_100k import MGRS100KGenerator
from MilitaryCartographyTools.grid.mgrs_sub_grid import MGRSSubGridGenerator


# A small extent around Dar es Salaam, small enough to stay inside
# a single UTM zone/band.
EXTENT = QgsRectangle(39.0, -7.0, 39.5, -6.5)


class TestCoordinateHelpers(QgisTestCase):

    def test_wgs84_is_epsg_4326(self):

        self.assertEqual(WGS84.authid(), "EPSG:4326")


    def test_get_utm_crs_southern_hemisphere(self):

        crs = get_utm_crs(-6.79, 39.2)

        self.assertEqual(crs.authid(), "EPSG:32737")


    def test_get_utm_crs_northern_hemisphere(self):

        crs = get_utm_crs(51.5, -0.1)

        # London - UTM zone 30N.
        self.assertEqual(crs.authid(), "EPSG:32630")


    def test_get_utm_crs_from_zone_band_matches_get_utm_crs(self):

        by_latlon = get_utm_crs(-6.79, 39.2)
        by_zone_band = get_utm_crs_from_zone_band(37, "M")

        self.assertEqual(by_latlon.authid(), by_zone_band.authid())


class TestTextFormatHelpers(QgisTestCase):

    def test_build_font_defaults(self):

        font = build_font(10)

        self.assertEqual(font.pointSize(), 10)
        self.assertFalse(font.bold())
        self.assertFalse(font.italic())
        self.assertFalse(font.underline())


    def test_build_font_flags(self):

        font = build_font(9, bold=True, italic=True, underline=True)

        self.assertTrue(font.bold())
        self.assertTrue(font.italic())
        self.assertTrue(font.underline())


    def test_build_text_format_opacity_and_color(self):

        from qgis.PyQt.QtGui import QColor

        color = QColor(181, 136, 66)

        text_format = build_text_format(
            8,
            italic=True,
            color=color,
            opacity=0.4
        )

        self.assertAlmostEqual(text_format.opacity(), 0.4)
        self.assertEqual(text_format.color().name(), color.name())
        self.assertTrue(text_format.font().italic())


class TestGridGenerators(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )


    def test_utm_grid_generates_features(self):

        generator = UTMGridGenerator()

        layer = generator.generate(EXTENT)

        self.assertGreater(layer.featureCount(), 0)

        for feature in layer.getFeatures():

            self.assertTrue(feature["GZD"])
            self.assertIsInstance(feature["ZONE"], int)

            break


    def test_mgrs_100k_generates_features_from_utm_layer(self):

        utm_layer = UTMGridGenerator().generate(EXTENT)

        mgrs100k_layer = MGRS100KGenerator().generate(utm_layer)

        self.assertGreater(mgrs100k_layer.featureCount(), 0)


    def test_mgrs_100k_handles_no_utm_layer(self):

        mgrs100k_layer = MGRS100KGenerator().generate(None)

        self.assertEqual(mgrs100k_layer.featureCount(), 0)


    def test_sub_grid_generates_features_for_each_tier(self):

        utm_layer = UTMGridGenerator().generate(EXTENT)

        for spacing in (
            MGRSSubGridGenerator.ORDER_MAJOR,
            MGRSSubGridGenerator.ORDER_MEDIUM,
            MGRSSubGridGenerator.ORDER_MINOR,
        ):

            with self.subTest(spacing=spacing):

                layer = MGRSSubGridGenerator().generate(
                    EXTENT,
                    utm_layer,
                    spacing=spacing,
                    buffer_factor=0
                )

                self.assertGreater(layer.featureCount(), 0)

                axes = {
                    feature["AXIS"]
                    for feature in layer.getFeatures()
                }

                self.assertEqual(axes, {"E", "N"})


    def test_sub_grid_handles_no_utm_layer(self):

        layer = MGRSSubGridGenerator().generate(
            EXTENT,
            None,
            spacing=MGRSSubGridGenerator.ORDER_MINOR
        )

        self.assertEqual(layer.featureCount(), 0)
