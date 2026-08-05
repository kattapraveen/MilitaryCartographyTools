# -*- coding: utf-8 -*-

"""
Tests for terrain/hillshade_combination.py - the multi-directional
hillshade blend pipeline.

Military Cartography Tools
"""

import os

from qgis.core import (
    QgsContrastEnhancement,
    QgsProject,
    QgsPointXY,
    QgsRasterLayer,
    QgsSingleBandGrayRenderer,
    QgsVectorLayer,
)

from qgis.PyQt.QtGui import QPainter

from .qgis_test_case import build_synthetic_ridge_dem, QgisTestCase

from MilitaryCartographyTools.core.coordinate_utils import WGS84
from MilitaryCartographyTools.terrain.hypsometric_tint import (
    generate_hypsometric_tint,
    OUTPUT_LAYER_NAME as HYPSOMETRIC_TINT_LAYER_NAME,
)
from MilitaryCartographyTools.terrain.hillshade_combination import (
    _combine_hillshades,
    _run_hillshade,
    default_insert_position,
    generate_hillshade_combination,
    OUTPUT_LAYER_NAME,
    THREE_DIRECTION_AZIMUTHS,
    TWO_DIRECTION_AZIMUTHS,
)


class _RidgeDemTestCase(QgisTestCase):

    """
    Shared setUp/tearDown for tests needing the ridge DEM - a raised
    block across columns [13, 17) gives a clear, ambiguous-free
    lit/shadow contrast between opposite light azimuths, unlike the
    sloped DEM's single uniform gradient.
    """

    def setUp(self):

        super().setUp()

        self._dem_path = build_synthetic_ridge_dem()

        self.dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def _ridge_edge_point(self):

        # A point right at the ridge's rising edge (column 13 of 30) -
        # where a light direction actually matters, unlike the flat
        # interior on either side.
        extent = self.dem_layer.extent()

        edge_x = extent.xMinimum() + extent.width() * (13.0 / 30.0)
        y = extent.center().y()

        return QgsPointXY(edge_x, y)


class TestRunHillshade(_RidgeDemTestCase):

    def test_output_is_a_valid_single_band_raster(self):

        output = _run_hillshade(self.dem_layer, 315.0, 45.0, 1.0)

        self.assertTrue(
            output.isValid()
        )

        self.assertEqual(
            output.bandCount(),
            1
        )


    def test_different_azimuths_produce_different_pixel_values(self):

        north_west = _run_hillshade(self.dem_layer, 315.0, 45.0, 1.0)
        south_east = _run_hillshade(self.dem_layer, 135.0, 45.0, 1.0)

        point = self._ridge_edge_point()

        value_nw, ok_nw = north_west.dataProvider().sample(point, 1)
        value_se, ok_se = south_east.dataProvider().sample(point, 1)

        self.assertTrue(ok_nw)
        self.assertTrue(ok_se)

        self.assertNotEqual(
            value_nw,
            value_se
        )


class TestCombineHillshades(_RidgeDemTestCase):

    def test_two_layer_average_matches_the_mean_of_the_two_inputs(self):

        first = _run_hillshade(self.dem_layer, 315.0, 45.0, 1.0)
        second = _run_hillshade(self.dem_layer, 45.0, 45.0, 1.0)

        combined = _combine_hillshades([first, second])

        point = self._ridge_edge_point()

        first_value, first_ok = first.dataProvider().sample(point, 1)
        second_value, second_ok = second.dataProvider().sample(point, 1)
        combined_value, combined_ok = combined.dataProvider().sample(point, 1)

        self.assertTrue(first_ok and second_ok and combined_ok)

        self.assertAlmostEqual(
            combined_value,
            (first_value + second_value) / 2.0,
            delta=1.0
        )


    def test_three_layer_average_matches_the_mean_of_the_three_inputs(self):

        first = _run_hillshade(self.dem_layer, 315.0, 45.0, 1.0)
        second = _run_hillshade(self.dem_layer, 45.0, 45.0, 1.0)
        third = _run_hillshade(self.dem_layer, 180.0, 45.0, 1.0)

        combined = _combine_hillshades([first, second, third])

        point = self._ridge_edge_point()

        values = []

        for layer in (first, second, third):

            value, ok = layer.dataProvider().sample(point, 1)

            self.assertTrue(ok)

            values.append(value)

        combined_value, combined_ok = combined.dataProvider().sample(point, 1)

        self.assertTrue(combined_ok)

        self.assertAlmostEqual(
            combined_value,
            sum(values) / 3.0,
            delta=1.0
        )


    def test_rejects_a_single_layer(self):

        only_one = _run_hillshade(self.dem_layer, 315.0, 45.0, 1.0)

        with self.assertRaises(ValueError):
            _combine_hillshades([only_one])


class TestCombineHillshadesOverflowRegression(QgisTestCase):

    """
    Regression coverage for a real bug: gdal:rastercalculator
    evaluates FORMULA using each input's own on-disk dtype (Byte for
    a gdal:hillshade output), so a naive "(A+B+C)/3" silently
    overflowed the intermediate SUM in 8-bit arithmetic before the
    divide ever happened - confirmed live against a real DEM, where
    three individually-correct ~180 (mid-gray, flat terrain) inputs
    combined into ~9 instead of ~180. A flat DEM reproduces this
    directly: every azimuth legitimately produces a near-uniform
    mid-gray value, and three such values reliably sum past 255 -
    unlike the ridge DEM used elsewhere in this file, whose strong
    light/shadow contrast at the sampled edge could coincidentally
    keep the (buggy) sum under 255 and mask the bug.
    """

    def setUp(self):

        super().setUp()

        self._dem_path = build_synthetic_ridge_dem(ridge_height=0.0)

        self.dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def _flat_interior_point(self):

        extent = self.dem_layer.extent()

        return QgsPointXY(
            extent.center().x(),
            extent.center().y()
        )


    def test_three_layer_average_of_high_flat_values_does_not_overflow(self):

        first = _run_hillshade(self.dem_layer, 315.0, 45.0, 1.0)
        second = _run_hillshade(self.dem_layer, 45.0, 45.0, 1.0)
        third = _run_hillshade(self.dem_layer, 180.0, 45.0, 1.0)

        combined = _combine_hillshades([first, second, third])

        point = self._flat_interior_point()

        values = []

        for layer in (first, second, third):

            value, ok = layer.dataProvider().sample(point, 1)

            self.assertTrue(ok)

            values.append(value)

        # Flat terrain at every azimuth - these should all be well
        # above 85 (255 / 3), so a correct average only stays
        # plausible if the SUM was computed at full precision rather
        # than wrapping around in 8-bit arithmetic first.
        self.assertGreater(sum(values), 255)

        combined_value, combined_ok = combined.dataProvider().sample(point, 1)

        self.assertTrue(combined_ok)

        self.assertAlmostEqual(
            combined_value,
            sum(values) / 3.0,
            delta=1.0
        )


class TestGenerateHillshadeCombinationIntegration(_RidgeDemTestCase):

    def test_output_is_a_valid_grayscale_raster(self):

        output = generate_hillshade_combination(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84
        )

        self.assertTrue(
            output.isValid()
        )

        self.assertEqual(
            output.name(),
            OUTPUT_LAYER_NAME
        )

        self.assertIsInstance(
            output.renderer(),
            QgsSingleBandGrayRenderer
        )


    def test_blend_mode_is_overlay(self):

        # Regression test: Multiply can only ever darken, which
        # dragged a real combined Tint+Hillshade render's mid/high
        # elevation band toward a muddy, desaturated brown-purple that
        # no longer read as the source ramp's own colours - confirmed
        # live against a real DEM (Kilimanjaro, Tanzania SRTM).
        # Overlay preserves the underlying colour's hue far better
        # while still showing relief.
        output = generate_hillshade_combination(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84
        )

        self.assertEqual(
            output.blendMode(),
            QPainter.CompositionMode.CompositionMode_Overlay
        )


    def test_opacity_is_applied(self):

        output = generate_hillshade_combination(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84,
            opacity=0.6
        )

        self.assertAlmostEqual(
            output.opacity(),
            0.6
        )


    def test_contrast_enhancement_is_not_stretched(self):

        # Regression test: a per-generation min/max stretch crushed a
        # near-flat area (e.g. open water) toward black, since
        # hillshade's 0-255 scale is already meaningful on an
        # absolute basis and shouldn't be re-normalised per run.
        output = generate_hillshade_combination(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84
        )

        enhancement = output.renderer().contrastEnhancement()

        self.assertEqual(
            enhancement.contrastEnhancementAlgorithm(),
            QgsContrastEnhancement.ContrastEnhancementAlgorithm.NoEnhancement
        )


    def test_two_direction_preset_generates_successfully(self):

        output = generate_hillshade_combination(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84,
            azimuths=TWO_DIRECTION_AZIMUTHS
        )

        self.assertTrue(
            output.isValid()
        )


    def test_three_direction_preset_generates_successfully(self):

        output = generate_hillshade_combination(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84,
            azimuths=THREE_DIRECTION_AZIMUTHS
        )

        self.assertTrue(
            output.isValid()
        )


    def test_output_layer_is_not_added_to_the_project(self):

        # generate_hillshade_combination() deliberately doesn't add
        # its result to the project - see terrain/_layer_utils.py's
        # module docstring for why. Insertion is the dialog's job -
        # see tests/test_hillshade_combination_dialog.py.
        output = generate_hillshade_combination(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84
        )

        self.assertIsNone(
            QgsProject.instance().mapLayer(output.id())
        )


    def test_default_insert_position_lands_at_bottom_when_no_hypsometric_tint_exists(self):

        dummy = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            "dummy_on_top",
            "memory"
        )

        QgsProject.instance().addMapLayer(
            dummy
        )

        output = generate_hillshade_combination(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84
        )

        project = QgsProject.instance()

        project.addMapLayer(output, False)

        default_insert_position(project, output)

        root = project.layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(
            names[-1],
            OUTPUT_LAYER_NAME
        )


    def test_default_insert_position_lands_directly_above_an_existing_hypsometric_tint_layer(self):

        project = QgsProject.instance()

        tint = generate_hypsometric_tint(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84
        )

        project.addMapLayer(tint, False)
        project.layerTreeRoot().insertLayer(0, tint)

        output = generate_hillshade_combination(
            self.dem_layer,
            self.dem_layer.extent(),
            WGS84
        )

        project.addMapLayer(output, False)

        default_insert_position(project, output)

        root = project.layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(
            names,
            [OUTPUT_LAYER_NAME, HYPSOMETRIC_TINT_LAYER_NAME]
        )
