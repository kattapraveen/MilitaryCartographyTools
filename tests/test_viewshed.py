# -*- coding: utf-8 -*-

"""
Tests for terrain/viewshed.py - the coverage-sweep pipeline wrapping
GDAL's own gdal_viewshed (via QGIS Processing's gdal:viewshed), then
polygonized down to just the visible area.

Military Cartography Tools
"""

import os

from qgis.PyQt.QtCore import Qt

from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsFillSymbol,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

from .qgis_test_case import build_synthetic_ridge_dem, QgisTestCase

from MilitaryCartographyTools.core.coordinate_utils import WGS84
from MilitaryCartographyTools.terrain.line_of_sight import VISIBLE_COLOR
from MilitaryCartographyTools.terrain.viewshed import (
    _apply_polygon_style,
    _observer_extent,
    default_insert_position,
    DEFAULT_COLOR,
    generate_viewshed,
    OUTLINE_WIDTH_MM,
    OUTPUT_LAYER_NAME,
    VISIBLE_VALUE,
)


class TestObserverExtent(QgisTestCase):

    def test_extent_is_centred_on_the_observer(self):

        observer = QgsPointXY(37.34, -3.09)

        extent = _observer_extent(observer, 1000.0)

        self.assertAlmostEqual(extent.center().x(), observer.x(), places=6)
        self.assertAlmostEqual(extent.center().y(), observer.y(), places=6)


    def test_larger_max_distance_produces_a_larger_extent(self):

        observer = QgsPointXY(37.34, -3.09)

        small = _observer_extent(observer, 1000.0)
        large = _observer_extent(observer, 5000.0)

        self.assertGreater(large.width(), small.width())
        self.assertGreater(large.height(), small.height())


    def test_longitude_padding_widens_away_from_the_equator(self):

        # A degree of longitude covers less ground the further from
        # the equator you are, so the same metric radius needs MORE
        # longitude degrees of padding at high latitude than near it.
        near_equator = _observer_extent(QgsPointXY(37.34, 1.0), 1000.0)
        near_pole = _observer_extent(QgsPointXY(37.34, 70.0), 1000.0)

        self.assertGreater(near_pole.width(), near_equator.width())

        # Latitude padding (height) only depends on max_distance_m,
        # not latitude, so it should be identical either way.
        self.assertAlmostEqual(
            near_pole.height(),
            near_equator.height()
        )


def _lonlat_at_fraction(dem_layer, fraction):

    """
    A WGS84 point at the given fraction of dem_layer's own extent
    width, on its centre row - dem_layer here is always the raw,
    unclipped fixture (already WGS84), so this maps directly onto a
    predictable column of build_synthetic_ridge_dem()'s own ridge
    layout without needing to reason about generate_viewshed()'s own
    (observer-centred, not whole-DEM) clip extent.
    """

    extent = dem_layer.extent()

    return QgsPointXY(
        extent.xMinimum() + extent.width() * fraction,
        extent.center().y()
    )


class TestGenerateViewshed(QgisTestCase):

    def setUp(self):

        super().setUp()

        self._ridge_dem_path = build_synthetic_ridge_dem(
            width=30,
            height=10,
            ridge_height=200.0
        )

        self.ridge_dem_layer = QgsRasterLayer(
            self._ridge_dem_path,
            "test_ridge_dem"
        )

        self._flat_dem_path = build_synthetic_ridge_dem(
            width=30,
            height=10,
            ridge_height=0.0
        )

        self.flat_dem_layer = QgsRasterLayer(
            self._flat_dem_path,
            "test_flat_dem"
        )


    def tearDown(self):

        for path in (self._ridge_dem_path, self._flat_dem_path):

            try:
                os.remove(path)
            except OSError:
                pass


    def test_a_viewshed_never_extends_beyond_the_dem(self):

        # Found via Sensor Coverage 2026-08-20, but the defect lives in
        # the shared clip helper and so applied here too:
        # gdal:warpreproject pads a TARGET_EXTENT larger than its source
        # with NoData, and gdal_viewshed reports that padding as
        # visible - so a max distance exceeding the DEM produced a
        # footprint over ground with no data behind it at all.
        observer_lonlat = _lonlat_at_fraction(
            self.flat_dem_layer,
            0.5
        )

        layer = generate_viewshed(
            self.flat_dem_layer,
            observer_lonlat,
            2.0,
            2.0,
            50000.0
        )

        self.assertIsNotNone(layer)

        # generate_viewshed() returns its polygon in whatever local UTM
        # zone the clip resolved to, NOT in the DEM's own CRS, so the
        # two extents have to be brought together before comparing.
        to_dem_crs = QgsCoordinateTransform(
            layer.crs(),
            self.flat_dem_layer.crs(),
            QgsProject.instance()
        )

        coverage_extent = to_dem_crs.transformBoundingBox(
            layer.extent()
        )

        dem_extent = self.flat_dem_layer.extent()

        # Two pixels of slack for reprojection rounding at the edges.
        slack = 2.0 * self.flat_dem_layer.rasterUnitsPerPixelX()

        self.assertTrue(
            dem_extent.buffered(slack).contains(coverage_extent)
        )


    def test_output_is_a_valid_polygon_layer_of_only_visible_area(self):

        observer_lonlat = _lonlat_at_fraction(
            self.ridge_dem_layer,
            0.1
        )

        layer = generate_viewshed(
            self.ridge_dem_layer,
            observer_lonlat,
            2.0,
            2.0,
            300.0
        )

        self.assertTrue(
            layer.isValid()
        )

        self.assertEqual(
            layer.name(),
            OUTPUT_LAYER_NAME
        )

        self.assertEqual(
            layer.geometryType(),
            Qgis.GeometryType.Polygon
        )

        self.assertGreater(
            layer.featureCount(),
            0
        )

        # Every feature is the visible class - dead ground/out of
        # range never reach the final layer at all.
        self.assertTrue(
            all(
                feature["DN"] == VISIBLE_VALUE
                for feature in layer.getFeatures()
            )
        )


    def test_a_ridge_shrinks_the_visible_area_compared_to_flat_ground(self):

        # Confirms the ridge is actually taken into account - a
        # visible polygon with something in the way should cover
        # LESS total area than the same analysis over flat ground,
        # since the ridge's own dead ground is excluded from it.
        ridge_observer = _lonlat_at_fraction(self.ridge_dem_layer, 0.1)
        flat_observer = _lonlat_at_fraction(self.flat_dem_layer, 0.1)

        ridge_layer = generate_viewshed(
            self.ridge_dem_layer, ridge_observer, 2.0, 2.0, 300.0
        )

        flat_layer = generate_viewshed(
            self.flat_dem_layer, flat_observer, 2.0, 2.0, 300.0
        )

        def total_area(layer):
            return sum(f.geometry().area() for f in layer.getFeatures())

        self.assertLess(
            total_area(ridge_layer),
            total_area(flat_layer)
        )


    def test_output_is_styled_with_a_fill_symbol(self):

        observer_lonlat = _lonlat_at_fraction(
            self.ridge_dem_layer,
            0.1
        )

        layer = generate_viewshed(
            self.ridge_dem_layer,
            observer_lonlat,
            2.0,
            2.0,
            300.0
        )

        symbol = layer.renderer().symbol()

        self.assertIsInstance(
            symbol,
            QgsFillSymbol
        )


    def test_opacity_is_applied(self):

        observer_lonlat = _lonlat_at_fraction(
            self.ridge_dem_layer,
            0.1
        )

        layer = generate_viewshed(
            self.ridge_dem_layer,
            observer_lonlat,
            2.0,
            2.0,
            300.0,
            opacity=0.4
        )

        self.assertAlmostEqual(
            layer.opacity(),
            0.4
        )


    def test_colour_and_outline_only_reach_the_output_layer(self):

        observer_lonlat = _lonlat_at_fraction(
            self.ridge_dem_layer,
            0.1
        )

        layer = generate_viewshed(
            self.ridge_dem_layer,
            observer_lonlat,
            2.0,
            2.0,
            300.0,
            color=(10, 20, 200),
            outline_only=True
        )

        symbol_layer = layer.renderer().symbol().symbolLayer(0)

        stroke = symbol_layer.strokeColor()

        self.assertEqual(
            (stroke.red(), stroke.green(), stroke.blue()),
            (10, 20, 200)
        )

        self.assertEqual(
            symbol_layer.brushStyle(),
            Qt.BrushStyle.NoBrush
        )


    def test_output_layer_is_not_added_to_the_project(self):

        # generate_viewshed() deliberately doesn't add its result to
        # the project - see core/_layer_utils.py's module
        # docstring for why. Insertion is the dialog's job - see
        # tests/test_viewshed_dialog.py.
        observer_lonlat = _lonlat_at_fraction(
            self.ridge_dem_layer,
            0.1
        )

        layer = generate_viewshed(
            self.ridge_dem_layer,
            observer_lonlat,
            2.0,
            2.0,
            300.0
        )

        self.assertIsNone(
            QgsProject.instance().mapLayer(layer.id())
        )


    def test_default_insert_position_places_it_at_the_top_of_the_tree(self):

        project = QgsProject.instance()

        existing = QgsVectorLayer("Point?crs=EPSG:4326", "Existing", "memory")
        project.addMapLayer(existing, False)
        project.layerTreeRoot().insertLayer(0, existing)

        observer_lonlat = _lonlat_at_fraction(
            self.ridge_dem_layer,
            0.1
        )

        layer = generate_viewshed(
            self.ridge_dem_layer,
            observer_lonlat,
            2.0,
            2.0,
            300.0
        )

        project.addMapLayer(layer, False)

        default_insert_position(project, layer)

        root = project.layerTreeRoot()

        self.assertEqual(
            [c.name() for c in root.children()],
            [layer.name(), "Existing"]
        )


    def test_returns_none_when_the_observer_falls_outside_the_source_dem(self):

        extent = self.ridge_dem_layer.extent()

        far_outside = QgsPointXY(
            extent.xMaximum() + extent.width() * 10,
            extent.center().y()
        )

        layer = generate_viewshed(
            self.ridge_dem_layer,
            far_outside,
            2.0,
            2.0,
            300.0
        )

        self.assertIsNone(layer)


class TestPolygonStyle(QgisTestCase):

    """
    _apply_polygon_style() on its own, against a throwaway polygon
    layer - the styling is independent of the (slow) gdal:viewshed
    pipeline that normally produces the layer, so it's tested
    directly rather than through a full generate_viewshed() run for
    every combination. One end-to-end check that the arguments
    actually reach the output layer lives in TestGenerateViewshed.
    """

    def _layer(self):

        return QgsVectorLayer(
            "Polygon?crs=EPSG:4326",
            "styling_target",
            "memory"
        )


    def _symbol_layer(self, layer):

        return layer.renderer().symbol().symbolLayer(0)


    def test_default_is_a_filled_polygon_with_no_outline(self):

        layer = self._layer()

        _apply_polygon_style(layer, 0.65)

        symbol_layer = self._symbol_layer(layer)

        self.assertEqual(
            symbol_layer.brushStyle(),
            Qt.BrushStyle.SolidPattern
        )

        self.assertEqual(
            symbol_layer.strokeStyle(),
            Qt.PenStyle.NoPen
        )


    def test_default_colour_is_line_of_sights_own_visible_green(self):

        # Not a restatement of DEFAULT_COLOR's own definition - this
        # pins the shared colour language between Viewshed and Line of
        # Sight, which is the reason that default was chosen.
        self.assertEqual(DEFAULT_COLOR, VISIBLE_COLOR)

        layer = self._layer()

        _apply_polygon_style(layer, 0.65)

        red, green, blue = VISIBLE_COLOR

        fill = self._symbol_layer(layer).color()

        self.assertEqual(
            (fill.red(), fill.green(), fill.blue()),
            (red, green, blue)
        )


    def test_a_picked_colour_reaches_the_fill(self):

        layer = self._layer()

        _apply_polygon_style(layer, 0.65, color=(200, 30, 90))

        fill = self._symbol_layer(layer).color()

        self.assertEqual(
            (fill.red(), fill.green(), fill.blue()),
            (200, 30, 90)
        )


    def test_outline_only_drops_the_fill_and_draws_the_boundary(self):

        layer = self._layer()

        _apply_polygon_style(layer, 0.65, outline_only=True)

        symbol_layer = self._symbol_layer(layer)

        self.assertEqual(
            symbol_layer.brushStyle(),
            Qt.BrushStyle.NoBrush
        )

        self.assertEqual(
            symbol_layer.strokeStyle(),
            Qt.PenStyle.SolidLine
        )

        self.assertAlmostEqual(
            symbol_layer.strokeWidth(),
            OUTLINE_WIDTH_MM
        )


    def test_outline_only_takes_the_same_picked_colour(self):

        # The colour picker drives whichever of the two the toggle
        # currently selects - it isn't a fill-only control.
        layer = self._layer()

        _apply_polygon_style(
            layer,
            0.65,
            color=(200, 30, 90),
            outline_only=True
        )

        stroke = self._symbol_layer(layer).strokeColor()

        self.assertEqual(
            (stroke.red(), stroke.green(), stroke.blue()),
            (200, 30, 90)
        )


    def test_opacity_applies_in_both_modes(self):

        for outline_only in (False, True):

            with self.subTest(outline_only=outline_only):

                layer = self._layer()

                _apply_polygon_style(
                    layer,
                    0.3,
                    outline_only=outline_only
                )

                self.assertAlmostEqual(layer.opacity(), 0.3)


class TestSeaLevelClamp(QgisTestCase):

    """
    Regression coverage for a real requirement: an observer or target
    over open water sits at the sea surface, not the seabed - a
    bathymetric DEM's negative below-mean-sea-level values must be
    clamped to 0 before height/visibility calculations, or an observer
    over water would incorrectly compute its own eye height from a
    large negative seafloor depth instead of the water surface.
    """

    def setUp(self):

        super().setUp()

        # A single-column depression exactly at the observer's own
        # point (not a wide trench, which would create unrelated
        # self-shadowing effects on the profile, confounding the
        # result) - flat sea level (0) everywhere else.
        self._dem_path = build_synthetic_ridge_dem(
            width=30,
            height=10,
            base_elevation=0.0,
            ridge_height=-50.0,
            ridge_start_column=3,
            ridge_end_column=4
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


    def test_observer_over_water_is_not_treated_as_being_at_seabed_depth(self):

        # Without the clamp, the observer's own eye height would be
        # computed from -50m (the seabed) instead of 0m (the
        # surface), making the sightline start so low that the
        # surrounding flat (0m) terrain would immediately block it -
        # a far point on that flat terrain would then be excluded
        # from the visible polygon entirely. With the clamp, the
        # observer is correctly at the water surface and that far
        # point is visible.
        observer_lonlat = _lonlat_at_fraction(self.dem_layer, 0.1)

        layer = generate_viewshed(
            self.dem_layer,
            observer_lonlat,
            2.0,
            2.0,
            300.0
        )

        far_side = _lonlat_at_fraction(self.dem_layer, 0.9)

        transform = QgsCoordinateTransform(
            WGS84,
            layer.crs(),
            QgsProject.instance()
        )

        far_point_geometry = QgsGeometry.fromPointXY(
            transform.transform(far_side)
        )

        self.assertTrue(
            any(
                feature.geometry().contains(far_point_geometry)
                for feature in layer.getFeatures()
            )
        )
