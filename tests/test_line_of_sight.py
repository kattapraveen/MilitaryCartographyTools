# -*- coding: utf-8 -*-

"""
Tests for terrain/line_of_sight.py - the point-to-point visibility
pipeline (DEM terrain sampling plus earth curvature/refraction
correction).

Military Cartography Tools
"""

import os

from qgis.core import QgsPointXY, QgsRasterLayer

from .qgis_test_case import build_synthetic_ridge_dem, QgisTestCase

from MilitaryCartographyTools.terrain._dem_utils import clip_and_reproject_dem
from MilitaryCartographyTools.terrain.line_of_sight import (
    compute_profile,
    curvature_refraction_drop,
    generate_line_of_sight,
    OUTPUT_LAYER_NAME,
)


class TestCurvatureRefractionDrop(QgisTestCase):

    def test_zero_distance_has_no_drop(self):

        self.assertEqual(
            curvature_refraction_drop(0.0),
            0.0
        )


    def test_drop_increases_with_distance(self):

        self.assertLess(
            curvature_refraction_drop(1000.0),
            curvature_refraction_drop(10000.0)
        )


    def test_matches_standard_formula_at_a_round_distance(self):

        # 10km, worked by hand: 10000^2 * 0.87 / (2 * 6371000) =~
        # 6.83m - an independent check that the constants
        # (EARTH_RADIUS_M/REFRACTION_COEFFICIENT) feed into the
        # formula as expected, not just a restatement of the
        # implementation.
        self.assertAlmostEqual(
            curvature_refraction_drop(10000.0),
            6.83,
            delta=0.05
        )


def _clipped_ridge_dem(**kwargs):

    path = build_synthetic_ridge_dem(**kwargs)

    dem_layer = QgsRasterLayer(
        path,
        "test_dem"
    )

    clipped = clip_and_reproject_dem(
        dem_layer,
        dem_layer.extent(),
        dem_layer.crs()
    )

    return clipped, path


def _observer_and_target(clipped_dem, row_fraction=0.5, margin_fraction=0.1):

    extent = clipped_dem.extent()

    y = extent.yMinimum() + extent.height() * row_fraction

    observer = QgsPointXY(
        extent.xMinimum() + extent.width() * margin_fraction,
        y
    )

    target = QgsPointXY(
        extent.xMaximum() - extent.width() * margin_fraction,
        y
    )

    return observer, target


class TestComputeProfile(QgisTestCase):

    def test_tall_ridge_between_low_points_blocks_visibility(self):

        clipped, path = _clipped_ridge_dem(
            width=30,
            height=10,
            ridge_height=200.0
        )

        try:
            observer, target = _observer_and_target(clipped)

            visible, blocked_at_distance, samples = compute_profile(
                clipped,
                observer,
                2.0,
                target,
                2.0
            )

            self.assertFalse(visible)
            self.assertIsNotNone(blocked_at_distance)
            self.assertGreater(len(samples), 0)

        finally:
            os.remove(path)


    def test_short_ridge_between_low_points_does_not_block(self):

        clipped, path = _clipped_ridge_dem(
            width=30,
            height=10,
            ridge_height=1.0
        )

        try:
            observer, target = _observer_and_target(clipped)

            visible, blocked_at_distance, samples = compute_profile(
                clipped,
                observer,
                2.0,
                target,
                2.0
            )

            self.assertTrue(visible)
            self.assertIsNone(blocked_at_distance)

        finally:
            os.remove(path)


    def test_curvature_alone_blocks_low_observers_over_a_long_flat_path(self):

        clipped, path = _clipped_ridge_dem(
            width=300,
            height=5,
            pixel_size=0.01,
            ridge_height=0.0
        )

        try:
            observer, target = _observer_and_target(clipped)

            visible, blocked_at_distance, _samples = compute_profile(
                clipped,
                observer,
                1.7,
                target,
                1.7
            )

            self.assertFalse(visible)
            self.assertIsNotNone(blocked_at_distance)

        finally:
            os.remove(path)


    def test_curvature_does_not_block_the_same_heights_over_a_short_flat_path(self):

        clipped, path = _clipped_ridge_dem(
            width=30,
            height=10,
            ridge_height=0.0
        )

        try:
            observer, target = _observer_and_target(clipped)

            visible, blocked_at_distance, _samples = compute_profile(
                clipped,
                observer,
                1.7,
                target,
                1.7
            )

            self.assertTrue(visible)
            self.assertIsNone(blocked_at_distance)

        finally:
            os.remove(path)


    def test_returns_none_when_a_point_falls_outside_the_dem(self):

        clipped, path = _clipped_ridge_dem(
            width=30,
            height=10
        )

        try:
            observer, target = _observer_and_target(clipped)

            far_outside = QgsPointXY(
                clipped.extent().xMaximum() + clipped.extent().width() * 10,
                observer.y()
            )

            result = compute_profile(
                clipped,
                observer,
                2.0,
                far_outside,
                2.0
            )

            self.assertIsNone(result)

        finally:
            os.remove(path)


class TestGenerateLineOfSight(QgisTestCase):

    def setUp(self):

        super().setUp()

        self._dem_path = build_synthetic_ridge_dem(
            width=30,
            height=10,
            ridge_height=1.0
        )

        self.dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def test_generates_a_styled_layer_with_expected_fields(self):

        extent = self.dem_layer.extent()

        margin = extent.width() * 0.1
        y = extent.center().y()

        observer_lonlat = QgsPointXY(extent.xMinimum() + margin, y)
        target_lonlat = QgsPointXY(extent.xMaximum() - margin, y)

        layer = generate_line_of_sight(
            self.dem_layer,
            observer_lonlat,
            2.0,
            target_lonlat,
            2.0
        )

        self.assertIsNotNone(layer)
        self.assertEqual(layer.name(), OUTPUT_LAYER_NAME)

        field_names = [field.name() for field in layer.fields()]

        self.assertIn("DIST", field_names)
        self.assertIn("TERRAIN_ELEV", field_names)
        self.assertIn("VISIBLE", field_names)

        self.assertGreater(layer.featureCount(), 0)

        self.assertTrue(
            all(
                feature["VISIBLE"]
                for feature in layer.getFeatures()
            )
        )


    def test_returns_none_when_a_point_falls_outside_the_source_dem(self):

        # The clip extent is now built purely from the two points'
        # own coordinates (see _bounding_extent()), so it always
        # "covers" both of them by construction - this has to be
        # caught as a plain containment check against the SOURCE
        # DEM's own (untouched) extent before any clipping happens,
        # not discovered after the fact from the clipped raster.
        extent = self.dem_layer.extent()

        far_outside = QgsPointXY(
            extent.xMaximum() + extent.width() * 10,
            extent.center().y()
        )

        layer = generate_line_of_sight(
            self.dem_layer,
            QgsPointXY(extent.center().x(), extent.center().y()),
            2.0,
            far_outside,
            2.0
        )

        self.assertIsNone(layer)
