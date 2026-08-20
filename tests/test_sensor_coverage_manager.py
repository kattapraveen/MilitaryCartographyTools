# -*- coding: utf-8 -*-

"""
Tests for terrain/sensor_coverage_manager.py and
terrain/sensor_coverage_dialog.py - the setup dialog that creates the
sensor points layers, and the manager that keeps each level's coverage
in step with them.

Military Cartography Tools
"""

import os

from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
)

from .qgis_test_case import build_synthetic_ridge_dem, QgisTestCase

from MilitaryCartographyTools.terrain.sensor_coverage import (
    build_sensor_points_layer,
    coverage_layer_name,
    DEFAULT_MAX_DISTANCE_M,
    dem_layer_for,
    level_by_key,
    points_layer_name,
    set_dem_layer,
)

from MilitaryCartographyTools.terrain.sensor_coverage_dialog import (
    apply_dialog_values,
)

from MilitaryCartographyTools.terrain.sensor_coverage_manager import (
    SensorCoverageManager,
)


LOW = level_by_key("low")
MEDIUM = level_by_key("medium")


class FakeMessageBar:

    def __init__(self):

        self.warnings = []


    def pushWarning(self, title, message):

        self.warnings.append((title, message))


class FakeIface:

    def __init__(self):

        self._message_bar = FakeMessageBar()


    def messageBar(self):

        return self._message_bar


class SensorCoverageTestCase(QgisTestCase):

    def setUp(self):

        super().setUp()

        self.iface = FakeIface()
        self.manager = SensorCoverageManager(self.iface)

        self._dem_path = build_synthetic_ridge_dem(
            width=60,
            height=60,
            ridge_height=0.0
        )

        self.dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        QgsProject.instance().addMapLayer(self.dem_layer)


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


    def _add_sensor(self, points_layer, lonlat, max_distance=200.0):

        """
        Adds one sensor and returns the id the PROVIDER assigned it -
        not the id of the QgsFeature built here, which is still unset
        and would silently address nothing when passed back to
        changeGeometryValues()/deleteFeatures().
        """

        feature = QgsFeature(points_layer.fields())

        feature.setGeometry(
            QgsGeometry.fromPointXY(lonlat)
        )

        feature["sensor_height"] = 5.0
        feature["detection_height"] = 1000.0
        feature["max_distance"] = max_distance

        before = {f.id() for f in points_layer.getFeatures()}

        points_layer.dataProvider().addFeatures([feature])
        points_layer.updateExtents()

        after = {f.id() for f in points_layer.getFeatures()}

        return (after - before).pop()


    def _points_layer_in_project(self, level):

        return QgsProject.instance().mapLayersByName(
            points_layer_name(level)
        )[0]


    def _coverage_layers(self, level):

        return QgsProject.instance().mapLayersByName(
            coverage_layer_name(level)
        )


class TestApplyDialogValues(SensorCoverageTestCase):

    def test_selected_levels_get_a_points_layer_in_the_project(self):

        apply_dialog_values(
            self.iface,
            self.manager,
            self.dem_layer,
            ["low", "high"]
        )

        project = QgsProject.instance()

        self.assertTrue(
            project.mapLayersByName(points_layer_name(LOW))
        )

        self.assertTrue(
            project.mapLayersByName(points_layer_name(level_by_key("high")))
        )

        # An unselected level gets nothing.
        self.assertFalse(
            project.mapLayersByName(points_layer_name(MEDIUM))
        )


    def test_the_chosen_dem_is_remembered_on_each_layer(self):

        apply_dialog_values(
            self.iface, self.manager, self.dem_layer, ["low"]
        )

        self.assertIs(
            dem_layer_for(self._points_layer_in_project(LOW)),
            self.dem_layer
        )


    def test_running_it_twice_does_not_create_a_second_layer(self):

        apply_dialog_values(
            self.iface, self.manager, self.dem_layer, ["low"]
        )

        apply_dialog_values(
            self.iface, self.manager, self.dem_layer, ["low"]
        )

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(points_layer_name(LOW))),
            1
        )


    def test_reapplying_repoints_an_existing_layer_at_a_new_dem(self):

        # The DEM is global to a laydown, so reopening the dialog and
        # picking a different one is how a user changes it.
        apply_dialog_values(
            self.iface, self.manager, self.dem_layer, ["low"]
        )

        other_dem = QgsRasterLayer(self._dem_path, "other_dem")

        QgsProject.instance().addMapLayer(other_dem)

        apply_dialog_values(
            self.iface, self.manager, other_dem, ["low"]
        )

        self.assertIs(
            dem_layer_for(self._points_layer_in_project(LOW)),
            other_dem
        )


    def test_no_dem_warns_and_creates_nothing(self):

        layers = apply_dialog_values(
            self.iface, self.manager, None, ["low"]
        )

        self.assertEqual(layers, [])

        self.assertFalse(
            QgsProject.instance().mapLayersByName(points_layer_name(LOW))
        )

        self.assertEqual(
            len(self.iface.messageBar().warnings),
            1
        )


class TestRegenerate(SensorCoverageTestCase):

    def _set_up_level(self, level=LOW):

        apply_dialog_values(
            self.iface, self.manager, self.dem_layer, [level.key]
        )

        return self._points_layer_in_project(level)


    def test_a_sensor_produces_a_coverage_layer_in_the_project(self):

        points = self._set_up_level()

        self._add_sensor(points, self._lonlat_at(0.5))

        coverage = self.manager.regenerate(LOW)

        self.assertIsNotNone(coverage)

        self.assertEqual(
            len(self._coverage_layers(LOW)),
            1
        )


    def test_regenerating_replaces_rather_than_stacking_up_layers(self):

        points = self._set_up_level()

        self._add_sensor(points, self._lonlat_at(0.5))

        for _ in range(3):
            self.manager.regenerate(LOW)

        self.assertEqual(
            len(self._coverage_layers(LOW)),
            1
        )


    def test_only_the_regenerated_level_is_touched(self):

        # The maintainer's own requirement: editing one level's points
        # must not recompute the other two bands.
        apply_dialog_values(
            self.iface, self.manager, self.dem_layer, ["low", "medium"]
        )

        low_points = self._points_layer_in_project(LOW)
        medium_points = self._points_layer_in_project(MEDIUM)

        self._add_sensor(low_points, self._lonlat_at(0.5))
        self._add_sensor(medium_points, self._lonlat_at(0.5))

        self.manager.regenerate(LOW)

        self.assertEqual(len(self._coverage_layers(LOW)), 1)
        self.assertEqual(len(self._coverage_layers(MEDIUM)), 0)


    def test_deleting_every_sensor_removes_the_stale_coverage(self):

        # Leaving the old shape drawn would claim coverage over ground
        # nothing can see any more.
        points = self._set_up_level()

        sensor_id = self._add_sensor(points, self._lonlat_at(0.5))

        self.manager.regenerate(LOW)

        self.assertEqual(len(self._coverage_layers(LOW)), 1)

        points.dataProvider().deleteFeatures([sensor_id])
        points.updateExtents()

        self.assertIsNone(
            self.manager.regenerate(LOW)
        )

        self.assertEqual(
            len(self._coverage_layers(LOW)),
            0
        )


    def test_a_missing_dem_warns_and_leaves_existing_coverage_alone(self):

        # A recoverable setup problem, not a reason to throw away a
        # picture that was computed against a real DEM.
        points = self._set_up_level()

        self._add_sensor(points, self._lonlat_at(0.5))

        self.manager.regenerate(LOW)

        QgsProject.instance().removeMapLayer(self.dem_layer.id())

        self.assertIsNone(
            self.manager.regenerate(LOW)
        )

        self.assertEqual(
            len(self._coverage_layers(LOW)),
            1
        )

        self.assertEqual(
            len(self.iface.messageBar().warnings),
            1
        )


    def test_no_points_layer_at_all_is_a_quiet_no_op(self):

        self.assertIsNone(
            self.manager.regenerate(LOW)
        )

        self.assertEqual(
            self.iface.messageBar().warnings,
            []
        )


    def test_moving_a_sensor_moves_its_coverage(self):

        points = self._set_up_level()

        sensor_id = self._add_sensor(points, self._lonlat_at(0.2))

        before = self.manager.regenerate(LOW).extent().center()

        points.dataProvider().changeGeometryValues(
            {
                sensor_id: QgsGeometry.fromPointXY(self._lonlat_at(0.8))
            }
        )

        points.updateExtents()

        after = self.manager.regenerate(LOW).extent().center()

        self.assertGreater(
            after.x(),
            before.x()
        )


    def test_editing_a_sensors_range_changes_its_coverage(self):

        points = self._set_up_level()

        sensor_id = self._add_sensor(points, self._lonlat_at(0.5), max_distance=100.0)

        small = self.manager.regenerate(LOW).getFeature(1).geometry().area()

        points.dataProvider().changeAttributeValues(
            {
                sensor_id: {
                    points.fields().indexOf("max_distance"): 300.0
                }
            }
        )

        large = self.manager.regenerate(LOW).getFeature(1).geometry().area()

        self.assertGreater(large, small)


class TestWiring(SensorCoverageTestCase):

    def test_committing_an_edit_regenerates_that_levels_coverage(self):

        # The whole "automatic, no Generate button" requirement, end to
        # end: digitize a sensor, save edits, coverage appears.
        points = self._set_up_layer()

        points.startEditing()

        feature = QgsFeature(points.fields())

        feature.setGeometry(
            QgsGeometry.fromPointXY(self._lonlat_at(0.5))
        )

        feature["sensor_height"] = 5.0
        feature["detection_height"] = 1000.0
        feature["max_distance"] = 200.0

        points.addFeature(feature)

        points.commitChanges()

        self.assertEqual(
            len(self._coverage_layers(LOW)),
            1
        )


    def _set_up_layer(self):

        apply_dialog_values(
            self.iface, self.manager, self.dem_layer, ["low"]
        )

        return self._points_layer_in_project(LOW)


    def test_wiring_the_same_layer_twice_connects_it_only_once(self):

        points = self._set_up_layer()

        # apply_dialog_values() already wired it; attach_existing()
        # runs every time the dialog is opened, and a second connection
        # would regenerate twice per commit.
        self.manager.attach_existing()
        self.manager.wire(points, LOW)

        self.assertEqual(
            len(self.manager._wired_layer_ids),
            1
        )


    def test_attach_existing_picks_up_a_layer_the_manager_never_saw(self):

        # Stands in for a project reopened from disk: the layer is
        # there, but no signal connection is.
        points = build_sensor_points_layer(LOW)

        set_dem_layer(points, self.dem_layer)

        QgsProject.instance().addMapLayer(points)

        self.manager.attach_existing()

        self.assertIn(
            points.id(),
            self.manager._wired_layer_ids
        )


    def test_defaults_let_a_sensor_be_placed_without_touching_the_form(self):

        # A user who digitizes a point and just saves should still get
        # coverage, using the field defaults.
        points = self._set_up_layer()

        points.startEditing()

        feature = QgsFeature(points.fields())

        feature.setGeometry(
            QgsGeometry.fromPointXY(self._lonlat_at(0.5))
        )

        feature["sensor_height"] = 5.0
        feature["detection_height"] = 1000.0
        feature["max_distance"] = DEFAULT_MAX_DISTANCE_M

        points.addFeature(feature)
        points.commitChanges()

        self.assertEqual(
            len(self._coverage_layers(LOW)),
            1
        )
