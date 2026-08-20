# -*- coding: utf-8 -*-

"""
Tests for terrain/sensor_coverage.py - the three per-level sensor point
layers and the merged multi-sensor coverage polygon built from them.

Military Cartography Tools

"""

import os

from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsDistanceArea,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

from MilitaryCartographyTools.core.coordinate_utils import WGS84

from .qgis_test_case import build_synthetic_ridge_dem, QgisTestCase

from MilitaryCartographyTools.terrain.sensor_coverage import (
    build_sensor_points_layer,
    coverage_layer_name,
    default_insert_position,
    DEFAULT_MAX_DISTANCE_M,
    DEFAULT_SENSOR_HEIGHT_M,
    dem_layer_for,
    generate_sensor_coverage,
    level_by_key,
    points_layer_name,
    SENSOR_LEVELS,
    set_dem_layer,
)


LOW = level_by_key("low")
MEDIUM = level_by_key("medium")
HIGH = level_by_key("high")


class TestSensorLevels(QgisTestCase):

    def test_the_three_bands_are_contiguous_and_ascending(self):

        # The bands are a partition of height-above-the-sensor, not
        # three independent ranges - a gap or an overlap between them
        # would leave a detection height belonging to no layer, or two.
        for lower, upper in zip(SENSOR_LEVELS, SENSOR_LEVELS[1:]):

            self.assertEqual(
                lower.ceiling_m,
                upper.floor_m
            )

        self.assertEqual(
            LOW.floor_m,
            0.0
        )


    def test_each_level_has_its_own_colour(self):

        # Three coverage layers are read together over the same ground,
        # so they must be distinguishable.
        colors = [level.color for level in SENSOR_LEVELS]

        self.assertEqual(
            len(set(colors)),
            len(colors)
        )


    def test_level_by_key_returns_none_for_an_unknown_key(self):

        self.assertIsNone(
            level_by_key("stratospheric")
        )


    def test_layer_names_are_distinct_per_level(self):

        point_names = {points_layer_name(level) for level in SENSOR_LEVELS}
        coverage_names = {coverage_layer_name(level) for level in SENSOR_LEVELS}

        self.assertEqual(len(point_names), len(SENSOR_LEVELS))
        self.assertEqual(len(coverage_names), len(SENSOR_LEVELS))

        # A points layer and a coverage layer must never collide either,
        # since both live in the same project and are looked up by name.
        self.assertFalse(
            point_names & coverage_names
        )


class TestSensorPointsLayer(QgisTestCase):

    def _widget_config(self, layer, field_name):

        idx = layer.fields().indexOf(field_name)

        return layer.editorWidgetSetup(idx).config()


    def test_the_layer_carries_the_three_per_sensor_fields(self):

        layer = build_sensor_points_layer(LOW)

        self.assertTrue(
            layer.isValid()
        )

        self.assertEqual(
            layer.geometryType(),
            Qgis.GeometryType.Point
        )

        self.assertEqual(
            [field.name() for field in layer.fields()],
            ["sensor_height", "detection_height", "max_distance"]
        )


    def test_all_three_fields_use_a_range_spin_box(self):

        layer = build_sensor_points_layer(LOW)

        for field_name in ("sensor_height", "detection_height", "max_distance"):

            with self.subTest(field=field_name):

                idx = layer.fields().indexOf(field_name)

                self.assertEqual(
                    layer.editorWidgetSetup(idx).type(),
                    "Range"
                )


    def test_detection_height_is_clamped_to_its_own_levels_band(self):

        # This is what makes a point on the Low Level layer a low-level
        # sensor: the form itself will not accept an out-of-band target
        # height, rather than relying on the user to remember the band.
        for level in SENSOR_LEVELS:

            with self.subTest(level=level.key):

                layer = build_sensor_points_layer(level)

                config = self._widget_config(layer, "detection_height")

                self.assertEqual(config["Min"], level.floor_m)
                self.assertEqual(config["Max"], level.ceiling_m)


    def test_the_bands_do_not_all_share_one_detection_height_range(self):

        # Guards against a refactor that accidentally passes the same
        # level (or a module-level constant) to every layer - which
        # test_detection_height_is_clamped... alone would still pass if
        # every level happened to be built from the same one.
        ranges = {
            (
                self._widget_config(build_sensor_points_layer(level), "detection_height")["Min"],
                self._widget_config(build_sensor_points_layer(level), "detection_height")["Max"],
            )
            for level in SENSOR_LEVELS
        }

        self.assertEqual(
            len(ranges),
            len(SENSOR_LEVELS)
        )


    def test_sensor_height_and_range_are_not_band_limited(self):

        # The maintainer's own worked case: three radars on the SAME
        # level differing by an order of magnitude in range (30 km to
        # 180 km) and several times over in mast height. Neither field
        # may be constrained by the level.
        low_config = self._widget_config(
            build_sensor_points_layer(LOW), "max_distance"
        )

        high_config = self._widget_config(
            build_sensor_points_layer(HIGH), "max_distance"
        )

        self.assertEqual(low_config["Min"], high_config["Min"])
        self.assertEqual(low_config["Max"], high_config["Max"])

        self.assertGreaterEqual(
            low_config["Max"],
            180000.0
        )


    def test_defaults_are_in_band_and_usable(self):

        for level in SENSOR_LEVELS:

            with self.subTest(level=level.key):

                layer = build_sensor_points_layer(level)

                fields = layer.fields()

                # Each band is drawn at its own TOP (maintainer's
                # choice 2026-08-20), so the default is the ceiling -
                # not merely somewhere inside the band.
                detection_default = float(
                    layer.defaultValueDefinition(
                        fields.indexOf("detection_height")
                    ).expression()
                )

                self.assertAlmostEqual(detection_default, level.ceiling_m)

                observer_default = float(
                    layer.defaultValueDefinition(
                        fields.indexOf("sensor_height")
                    ).expression()
                )

                self.assertAlmostEqual(
                    observer_default,
                    DEFAULT_SENSOR_HEIGHT_M
                )

                distance_default = float(
                    layer.defaultValueDefinition(
                        fields.indexOf("max_distance")
                    ).expression()
                )

                self.assertAlmostEqual(
                    distance_default,
                    DEFAULT_MAX_DISTANCE_M
                )


    def test_every_field_is_aliased_with_its_unit(self):

        layer = build_sensor_points_layer(LOW)

        for field_name in ("sensor_height", "detection_height", "max_distance"):

            with self.subTest(field=field_name):

                alias = layer.fields().at(
                    layer.fields().indexOf(field_name)
                ).alias()

                self.assertIn("m", alias)
                self.assertNotEqual(alias, "")


    def test_the_layer_is_not_added_to_the_project(self):

        layer = build_sensor_points_layer(LOW)

        self.assertIsNone(
            QgsProject.instance().mapLayer(layer.id())
        )


class TestDemLayerMemory(QgisTestCase):

    """
    The DEM is global to a laydown (one terrain source, many sensors),
    remembered on the points layer rather than re-asked per run.
    """

    def test_the_dem_round_trips_through_the_points_layer(self):

        dem = QgsVectorLayer("Point?crs=EPSG:4326", "stand_in_dem", "memory")

        QgsProject.instance().addMapLayer(dem)

        points = build_sensor_points_layer(LOW)

        set_dem_layer(points, dem)

        self.assertIs(
            dem_layer_for(points),
            dem
        )


    def test_no_dem_set_yet_reads_as_none(self):

        self.assertIsNone(
            dem_layer_for(build_sensor_points_layer(LOW))
        )


    def test_a_dem_since_removed_from_the_project_reads_as_none(self):

        # A real case: the user deletes the DEM and leaves the sensor
        # points behind. The stale id must not resolve to something
        # else, or raise.
        dem = QgsVectorLayer("Point?crs=EPSG:4326", "stand_in_dem", "memory")

        QgsProject.instance().addMapLayer(dem)

        points = build_sensor_points_layer(LOW)

        set_dem_layer(points, dem)

        QgsProject.instance().removeMapLayer(dem.id())

        self.assertIsNone(
            dem_layer_for(points)
        )


class TestGenerateSensorCoverage(QgisTestCase):

    def setUp(self):

        super().setUp()

        # Flat ground: every sensor sees a clean circle out to its own
        # range, which is what makes the merge behaviour below
        # predictable rather than terrain-dependent.
        self._dem_path = build_synthetic_ridge_dem(
            width=60,
            height=60,
            ridge_height=0.0
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


    def _lonlat_at(self, x_fraction, y_fraction=0.5):

        extent = self.dem_layer.extent()

        return QgsPointXY(
            extent.xMinimum() + extent.width() * x_fraction,
            extent.yMinimum() + extent.height() * y_fraction
        )


    def _points_layer(self, sensors, level=LOW):

        """
        A sensor points layer holding one feature per
        (lonlat, sensor_height, detection_height, max_distance) tuple.
        Built in WGS84 directly so the fixture's own coordinates need no
        conversion - the production layer takes the project CRS, and
        _sensor_observations() transforms whatever it finds.
        """

        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            points_layer_name(level),
            "memory"
        )

        layer.dataProvider().addAttributes(
            build_sensor_points_layer(level).fields().toList()
        )

        layer.updateFields()

        features = []

        for lonlat, sensor_height, detection_height, max_distance in sensors:

            feature = QgsFeature(layer.fields())

            feature.setGeometry(
                QgsGeometry.fromPointXY(lonlat)
            )

            feature["sensor_height"] = sensor_height
            feature["detection_height"] = detection_height
            feature["max_distance"] = max_distance

            features.append(feature)

        layer.dataProvider().addFeatures(features)

        layer.updateExtents()

        return layer


    def _coverage(self, sensors, level=LOW):

        return generate_sensor_coverage(
            self.dem_layer,
            self._points_layer(sensors, level),
            level
        )


    def test_no_sensors_at_all_produces_nothing(self):

        # Rather than an empty layer that would replace whatever is
        # already drawn.
        self.assertIsNone(
            self._coverage([])
        )


    def test_a_single_sensor_produces_a_single_coverage_polygon(self):

        layer = self._coverage(
            [(self._lonlat_at(0.5), 5.0, 1000.0, 200.0)]
        )

        self.assertTrue(layer.isValid())

        self.assertEqual(
            layer.geometryType(),
            Qgis.GeometryType.Polygon
        )

        self.assertEqual(
            layer.featureCount(),
            1
        )


    def test_the_output_layer_is_named_for_its_level(self):

        for level in SENSOR_LEVELS:

            with self.subTest(level=level.key):

                layer = generate_sensor_coverage(
                    self.dem_layer,
                    self._points_layer(
                        [(self._lonlat_at(0.5), 5.0, level.ceiling_m, 200.0)],
                        level
                    ),
                    level
                )

                self.assertEqual(
                    layer.name(),
                    coverage_layer_name(level)
                )


    def test_overlapping_sensors_merge_into_one_connected_shape(self):

        # The whole point of the feature: two sensors close enough that
        # their footprints overlap must read as ONE perimeter, not two
        # circles drawn on top of each other.
        close_together = [
            (self._lonlat_at(0.45), 5.0, 1000.0, 300.0),
            (self._lonlat_at(0.55), 5.0, 1000.0, 300.0),
        ]

        geometry = self._coverage(close_together).getFeature(1).geometry()

        self.assertEqual(
            len(geometry.asGeometryCollection()),
            1
        )


    def test_sensors_too_far_apart_stay_separate_shapes(self):

        # The other half of the same requirement: no overlap means no
        # merge, and each sensor keeps its own outline.
        far_apart = [
            (self._lonlat_at(0.08), 5.0, 1000.0, 120.0),
            (self._lonlat_at(0.92), 5.0, 1000.0, 120.0),
        ]

        geometry = self._coverage(far_apart).getFeature(1).geometry()

        self.assertEqual(
            len(geometry.asGeometryCollection()),
            2
        )


    def test_merged_coverage_is_not_double_counted(self):

        # A union, not a sum: two overlapping footprints must cover less
        # than their two areas added together, or the "merge" is really
        # just stacking.
        one = self._coverage(
            [(self._lonlat_at(0.45), 5.0, 1000.0, 300.0)]
        )

        two = self._coverage(
            [
                (self._lonlat_at(0.45), 5.0, 1000.0, 300.0),
                (self._lonlat_at(0.55), 5.0, 1000.0, 300.0),
            ]
        )

        def area(layer):
            return layer.getFeature(1).geometry().area()

        self.assertGreater(area(two), area(one))
        self.assertLess(area(two), area(one) * 2)


    def test_each_sensors_own_range_is_used_not_a_shared_one(self):

        # The maintainer's own worked case in miniature: two sensors on
        # the same level with very different ranges. The long-ranged one
        # must contribute more ground than the short-ranged one.
        short = self._coverage(
            [(self._lonlat_at(0.5), 5.0, 1000.0, 100.0)]
        )

        mixed = self._coverage(
            [
                (self._lonlat_at(0.5), 5.0, 1000.0, 100.0),
                (self._lonlat_at(0.5), 5.0, 1000.0, 400.0),
            ]
        )

        self.assertGreater(
            mixed.getFeature(1).geometry().area(),
            short.getFeature(1).geometry().area() * 2
        )


    def test_a_sensor_outside_the_dem_is_skipped_not_fatal(self):

        extent = self.dem_layer.extent()

        far_outside = QgsPointXY(
            extent.xMaximum() + extent.width() * 10,
            extent.center().y()
        )

        layer = self._coverage(
            [
                (self._lonlat_at(0.5), 5.0, 1000.0, 200.0),
                (far_outside, 5.0, 1000.0, 200.0),
            ]
        )

        # The valid sensor still draws.
        self.assertIsNotNone(layer)

        self.assertEqual(
            layer.featureCount(),
            1
        )


    def test_every_sensor_outside_the_dem_produces_nothing(self):

        extent = self.dem_layer.extent()

        far_outside = QgsPointXY(
            extent.xMaximum() + extent.width() * 10,
            extent.center().y()
        )

        self.assertIsNone(
            self._coverage([(far_outside, 5.0, 1000.0, 200.0)])
        )


    def test_coverage_is_drawn_in_its_own_levels_colour(self):

        layer = generate_sensor_coverage(
            self.dem_layer,
            self._points_layer(
                [(self._lonlat_at(0.5), 5.0, MEDIUM.ceiling_m, 200.0)],
                MEDIUM
            ),
            MEDIUM
        )

        fill = layer.renderer().symbol().symbolLayer(0).color()

        self.assertEqual(
            (fill.red(), fill.green(), fill.blue()),
            MEDIUM.color
        )


    def test_the_output_layer_is_not_added_to_the_project(self):

        layer = self._coverage(
            [(self._lonlat_at(0.5), 5.0, 1000.0, 200.0)]
        )

        self.assertIsNone(
            QgsProject.instance().mapLayer(layer.id())
        )


    def test_max_range_is_actually_enforced(self):

        # gdal:viewshed's own -md is IGNORED in the DEM output mode this
        # now uses (confirmed by probe 2026-08-20: byte-identical output
        # with -md set and unset), so the range limit is imposed by
        # _clip_to_range() instead. Without it the coverage would run
        # out to the corners of the DEM clip box - about 1.4x the
        # intended range on the diagonal.
        max_distance = 200.0

        centre = self._lonlat_at(0.5)

        layer = self._coverage(
            [(centre, 5.0, 1000.0, max_distance)]
        )

        transform = QgsCoordinateTransform(
            WGS84,
            layer.crs(),
            QgsProject.instance()
        )

        centre_geometry = QgsGeometry.fromPointXY(
            transform.transform(centre)
        )

        # Measured on the ellipsoid, in metres, rather than in the
        # layer's own degrees.
        measure = QgsDistanceArea()
        measure.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
        measure.setEllipsoid("WGS84")

        furthest = measure.measureLength(
            QgsGeometry.fromPolylineXY(
                [
                    centre_geometry.asPoint(),
                    layer.getFeature(1).geometry().boundingBox().center()
                ]
            )
        )

        # A cheap sanity bound first, then the real one: no vertex of
        # the coverage may sit beyond the stated range (plus one DEM
        # pixel of polygonization slack).
        self.assertLess(furthest, max_distance)

        for vertex in layer.getFeature(1).geometry().vertices():

            distance = measure.measureLength(
                QgsGeometry.fromPolylineXY(
                    [centre_geometry.asPoint(), QgsPointXY(vertex)]
                )
            )

            self.assertLessEqual(
                distance,
                max_distance * 1.05
            )


    def test_siting_a_sensor_higher_enlarges_its_coverage(self):

        # The maintainer's own boat-versus-plateau case, in miniature:
        # the band is measured above the ANTENNA, so lifting the sensor
        # lifts the whole slice of airspace it covers, and it sees
        # further. Same sensor, same capability, different ground.
        ridge_path = build_synthetic_ridge_dem(
            width=60,
            height=60,
            base_elevation=0.0,
            ridge_height=300.0,
            ridge_start_column=28,
            ridge_end_column=32
        )

        try:

            dem = QgsRasterLayer(ridge_path, "stepped_dem")

            extent = dem.extent()

            def at(fraction):
                return QgsPointXY(
                    extent.xMinimum() + extent.width() * fraction,
                    extent.center().y()
                )

            def area(observer):
                layer = generate_sensor_coverage(
                    dem,
                    self._points_layer([(observer, 5.0, 500.0, 400.0)]),
                    LOW
                )
                return layer.getFeature(1).geometry().area()

            # On the raised block versus on the flat ground beside it.
            on_high_ground = area(at(0.5))
            on_low_ground = area(at(0.1))

            self.assertGreater(on_high_ground, on_low_ground)

        finally:

            try:
                os.remove(ridge_path)
            except OSError:
                pass


    def test_a_higher_band_covers_at_least_as_much_as_a_lower_one(self):

        # Each band is drawn at its own top, so for identically sited
        # sensors the three nest: High contains Medium contains Low.
        # This is what makes the three layers readable stacked.
        centre = self._lonlat_at(0.5)

        areas = []

        for level in SENSOR_LEVELS:

            layer = generate_sensor_coverage(
                self.dem_layer,
                self._points_layer(
                    [(centre, 5.0, level.ceiling_m, 400.0)],
                    level
                ),
                level
            )

            areas.append(layer.getFeature(1).geometry().area())

        for lower, higher in zip(areas, areas[1:]):

            self.assertGreaterEqual(
                round(higher, 12),
                round(lower, 12)
            )


    def test_terrain_taller_than_the_target_still_blocks_it(self):

        # The consequence of computing at an ABSOLUTE altitude: a target
        # cannot be seen "over" ground that stands higher than the
        # target itself is flying. A detection height of 100 m from a
        # 5 m mast puts the target at ~105 m; a 300 m ridge must still
        # hide what is behind it.
        ridge_path = build_synthetic_ridge_dem(
            width=60,
            height=20,
            base_elevation=0.0,
            ridge_height=300.0,
            ridge_start_column=20,
            ridge_end_column=24
        )

        try:

            dem = QgsRasterLayer(ridge_path, "ridge_dem")

            extent = dem.extent()

            def at(fraction):
                return QgsPointXY(
                    extent.xMinimum() + extent.width() * fraction,
                    extent.center().y()
                )

            def covers(fraction, detection_height):

                layer = generate_sensor_coverage(
                    dem,
                    self._points_layer([(at(0.05), 5.0, detection_height, 600.0)]),
                    LOW
                )

                if layer is None:
                    return False

                transform = QgsCoordinateTransform(
                    WGS84, layer.crs(), QgsProject.instance()
                )

                probe = QgsGeometry.fromPointXY(
                    transform.transform(at(fraction))
                )

                return layer.getFeature(1).geometry().contains(probe)

            self.assertFalse(
                covers(0.75, 100.0)
            )

            # Lift the target well above the ridge and it reappears.
            self.assertTrue(
                covers(0.75, 3000.0)
            )

            # The sharpest statement of the whole rework, and the one
            # assertion that genuinely separates it from the old
            # above-ground model: the RIDGE TOP ITSELF is not covered
            # at a low detection height. A target 105 m above sea level
            # cannot be over a 300 m hill.
            #
            # Confirmed 2026-08-20 that the two models really do differ
            # here rather than this passing for free - the old
            # visible_area_for_observer() path reports this same point
            # as covered, because a fixed -tz makes the target ride up
            # to 400 m along with the terrain instead of flying level.
            self.assertFalse(
                covers(0.36, 100.0)
            )

        finally:

            try:
                os.remove(ridge_path)
            except OSError:
                pass


    def test_default_insert_position_places_it_at_the_top_of_the_tree(self):

        project = QgsProject.instance()

        existing = QgsVectorLayer("Point?crs=EPSG:4326", "Existing", "memory")
        project.addMapLayer(existing, False)
        project.layerTreeRoot().insertLayer(0, existing)

        layer = self._coverage(
            [(self._lonlat_at(0.5), 5.0, 1000.0, 200.0)]
        )

        project.addMapLayer(layer, False)

        default_insert_position(project, layer)

        self.assertEqual(
            [c.name() for c in project.layerTreeRoot().children()],
            [layer.name(), "Existing"]
        )
