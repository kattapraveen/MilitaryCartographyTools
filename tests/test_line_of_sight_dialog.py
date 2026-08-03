# -*- coding: utf-8 -*-

"""
Tests for terrain/line_of_sight_dialog.py's generate_from_dialog_values()
- the generate-flow logic driven by LineOfSightDialog's Generate
button, split out so it's testable without driving an actual QDialog.
Mirrors tests/test_tanaka_dialog.py's and
tests/test_hypsometric_tint_dialog.py's shape, covering the same
"Add as new layer" default-replace-in-place behaviour.

Military Cartography Tools
"""

import os

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

from .qgis_test_case import (
    build_synthetic_ridge_dem,
    FakeIface,
    QgisTestCase,
    make_canvas,
)

from MilitaryCartographyTools.terrain.line_of_sight import OUTPUT_LAYER_NAME
from MilitaryCartographyTools.terrain.line_of_sight_dialog import (
    generate_from_dialog_values,
    LineOfSightDialog,
    _describe_result,
)


class TestGenerateFromDialogValues(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

        # A short ridge that doesn't block the default eye-height
        # points used below - these tests are about layer management
        # (replace-in-place, add-as-new, position preservation), not
        # the visibility calculation itself (see test_line_of_sight.py
        # for that).
        self._dem_path = build_synthetic_ridge_dem(
            width=30,
            height=10,
            ridge_height=1.0
        )

        self.dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        extent = self.dem_layer.extent()

        margin = extent.width() * 0.1
        y = extent.center().y()

        self.observer_lonlat = QgsPointXY(extent.xMinimum() + margin, y)
        self.target_lonlat = QgsPointXY(extent.xMaximum() - margin, y)

        canvas = make_canvas()

        canvas.setExtent(extent)

        self.iface = FakeIface(canvas=canvas)


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def _values(self, add_as_new_layer=False, observer=True, target=True):

        return {
            "dem_layer": self.dem_layer,
            "observer_lonlat": self.observer_lonlat if observer else None,
            "observer_height": 2.0,
            "target_lonlat": self.target_lonlat if target else None,
            "target_height": 2.0,
            "add_as_new_layer": add_as_new_layer,
        }


    def test_no_dem_layer_warns_and_returns_none(self):

        result = generate_from_dialog_values(
            self.iface,
            self._values() | {"dem_layer": None}
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_missing_points_warns_and_returns_none(self):

        result = generate_from_dialog_values(
            self.iface,
            self._values(target=False)
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_point_outside_dem_warns_and_returns_none(self):

        extent = self.dem_layer.extent()

        far_outside = QgsPointXY(
            extent.xMaximum() + extent.width() * 10,
            extent.center().y()
        )

        result = generate_from_dialog_values(
            self.iface,
            self._values() | {"target_lonlat": far_outside}
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_failed_regenerate_after_a_successful_one_does_not_crash(self):

        # Real reported bug: once a "Line of Sight" layer already
        # exists (so replace_named_layer() has a remembered position
        # to restore), a subsequent regenerate attempt that fails
        # (point outside the DEM) crashed with AttributeError on
        # None.id() instead of warning cleanly - the first attempt in
        # test_point_outside_dem_warns_and_returns_none never hit
        # this, since with no prior layer there's no remembered
        # position and that code path was skipped entirely.
        first = generate_from_dialog_values(self.iface, self._values())

        self.assertIsNotNone(first)

        extent = self.dem_layer.extent()

        far_outside = QgsPointXY(
            extent.xMaximum() + extent.width() * 10,
            extent.center().y()
        )

        result = generate_from_dialog_values(
            self.iface,
            self._values() | {"target_lonlat": far_outside}
        )

        self.assertIsNone(result)

        # The failed attempt shouldn't have destroyed the previous
        # successful result.
        self.assertIsNotNone(
            QgsProject.instance().mapLayer(first.id())
        )


    def test_default_replaces_existing_layer_rather_than_adding_another(self):

        first = generate_from_dialog_values(self.iface, self._values())

        self.assertIsNotNone(first)

        first_id = first.id()

        second = generate_from_dialog_values(self.iface, self._values())

        self.assertIsNotNone(second)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)

        self.assertIsNone(
            QgsProject.instance().mapLayer(first_id)
        )


    def test_checkbox_keeps_previous_layer_alongside_the_new_one(self):

        first = generate_from_dialog_values(self.iface, self._values())

        second = generate_from_dialog_values(
            self.iface,
            self._values(add_as_new_layer=True)
        )

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 2)

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(first.id())
        )


    def test_regenerate_preserves_manually_moved_layer_position(self):

        first = generate_from_dialog_values(self.iface, self._values())

        root = QgsProject.instance().layerTreeRoot()

        other = QgsVectorLayer("Point?crs=EPSG:4326", "Other", "memory")
        QgsProject.instance().addMapLayer(other, False)
        root.insertLayer(0, other)

        node = root.findLayer(first.id())
        node.parent().removeChildNode(node)
        root.insertLayer(1, first)

        self.assertEqual(
            [c.name() for c in root.children()],
            ["Other", OUTPUT_LAYER_NAME]
        )

        generate_from_dialog_values(self.iface, self._values())

        self.assertEqual(
            [c.name() for c in root.children()],
            ["Other", OUTPUT_LAYER_NAME]
        )


    def test_describe_result_reports_total_distance_when_visible(self):

        layer = generate_from_dialog_values(self.iface, self._values())

        total_distance, blocked_at_distance = _describe_result(layer)

        self.assertGreater(total_distance, 0)
        self.assertIsNone(blocked_at_distance)


    def test_describe_result_reports_blocked_distance(self):

        blocking_dem_path = build_synthetic_ridge_dem(
            width=30,
            height=10,
            ridge_height=200.0
        )

        try:

            blocking_dem = QgsRasterLayer(
                blocking_dem_path,
                "blocking_dem"
            )

            layer = generate_from_dialog_values(
                self.iface,
                self._values() | {"dem_layer": blocking_dem}
            )

            total_distance, blocked_at_distance = _describe_result(layer)

            self.assertGreater(total_distance, 0)
            self.assertIsNotNone(blocked_at_distance)
            self.assertLess(blocked_at_distance, total_distance)

        finally:
            os.remove(blocking_dem_path)


class TestDialogResultLabel(QgisTestCase):

    """
    LineOfSightDialog itself (not just generate_from_dialog_values())
    - confirms the persistent "Result" label actually gets updated as
    a real user interaction would drive it, and resets when a new
    observer/target pair starts.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

        # Flat (no ridge) - these tests are about the dialog's own
        # Result label behaviour, not the visibility calculation
        # itself, so this uses the dialog's own default heights
        # (1.7m observer / 0.0m target) with nothing in the way,
        # rather than tuning a ridge height around them.
        self._dem_path = build_synthetic_ridge_dem(
            width=30,
            height=10,
            ridge_height=0.0
        )

        self.dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        QgsProject.instance().addMapLayer(
            self.dem_layer
        )

        extent = self.dem_layer.extent()

        margin = extent.width() * 0.1
        y = extent.center().y()

        self.observer_lonlat = QgsPointXY(extent.xMinimum() + margin, y)
        self.target_lonlat = QgsPointXY(extent.xMaximum() - margin, y)

        canvas = make_canvas()

        canvas.setExtent(extent)

        self.iface = FakeIface(canvas=canvas)


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def test_result_label_shows_distance_after_completing_a_pair(self):

        dialog = LineOfSightDialog(self.iface)

        dialog.dem_combo.setLayer(
            self.dem_layer
        )

        dialog.set_observer(self.observer_lonlat)
        dialog.set_target(self.target_lonlat)

        self.assertIn("visible", dialog.result_label.text())
        self.assertNotEqual(dialog.result_label.text(), "-")


    def test_result_label_resets_when_a_new_pair_starts(self):

        dialog = LineOfSightDialog(self.iface)

        dialog.dem_combo.setLayer(
            self.dem_layer
        )

        dialog.set_observer(self.observer_lonlat)
        dialog.set_target(self.target_lonlat)

        dialog.set_observer(self.target_lonlat)

        self.assertEqual(dialog.result_label.text(), "-")
