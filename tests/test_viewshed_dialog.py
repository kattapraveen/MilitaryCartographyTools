# -*- coding: utf-8 -*-

"""
Tests for terrain/viewshed_dialog.py's generate_from_dialog_values() -
the generate-flow logic driven by ViewshedDialog's Generate button,
split out so it's testable without driving an actual QDialog. Mirrors
tests/test_line_of_sight_dialog.py's shape, covering the same
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

from MilitaryCartographyTools.terrain.viewshed import OUTPUT_LAYER_NAME
from MilitaryCartographyTools.terrain.viewshed_dialog import (
    generate_from_dialog_values,
    ViewshedDialog,
)


class TestGenerateFromDialogValues(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

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

        canvas = make_canvas()

        canvas.setExtent(extent)

        self.iface = FakeIface(canvas=canvas)


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def _values(self, add_as_new_layer=False, observer=True):

        return {
            "dem_layer": self.dem_layer,
            "observer_lonlat": self.observer_lonlat if observer else None,
            "observer_height": 2.0,
            "target_height": 2.0,
            "max_distance": 300.0,
            "opacity": 0.65,
            "add_as_new_layer": add_as_new_layer,
        }


    def test_no_dem_layer_warns_and_returns_none(self):

        result = generate_from_dialog_values(
            self.iface,
            self._values() | {"dem_layer": None}
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_no_observer_yet_warns_and_returns_none(self):

        result = generate_from_dialog_values(
            self.iface,
            self._values(observer=False)
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_observer_outside_dem_warns_and_returns_none(self):

        extent = self.dem_layer.extent()

        far_outside = QgsPointXY(
            extent.xMaximum() + extent.width() * 10,
            extent.center().y()
        )

        result = generate_from_dialog_values(
            self.iface,
            self._values() | {"observer_lonlat": far_outside}
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


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


    def test_opacity_reaches_the_generated_layer(self):

        layer = generate_from_dialog_values(
            self.iface,
            self._values() | {"opacity": 0.3}
        )

        self.assertAlmostEqual(layer.opacity(), 0.3)


    def test_max_distance_reaches_generate_viewshed(self):

        # A short max_distance should produce a visible area with LESS
        # total polygon area than a longer one over the same DEM/
        # observer, confirming the dialog's value actually reaches
        # generate_viewshed() rather than being ignored.
        short_layer = generate_from_dialog_values(
            self.iface,
            self._values() | {"max_distance": 50.0}
        )

        long_layer = generate_from_dialog_values(
            self.iface,
            self._values(add_as_new_layer=True) | {"max_distance": 300.0}
        )

        def total_area(layer):
            return sum(f.geometry().area() for f in layer.getFeatures())

        self.assertLess(
            total_area(short_layer),
            total_area(long_layer)
        )


class TestViewshedDialog(QgisTestCase):

    """
    ViewshedDialog itself (not just generate_from_dialog_values()) -
    confirms set_observer() actually drives generation through as a
    real click would, via ViewshedTool.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

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

        canvas = make_canvas()

        canvas.setExtent(extent)

        self.iface = FakeIface(canvas=canvas)


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def test_set_observer_generates_a_layer(self):

        dialog = ViewshedDialog(self.iface)

        dialog.dem_combo.setLayer(
            self.dem_layer
        )

        dialog.set_observer(self.observer_lonlat)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_observer_label_updates(self):

        dialog = ViewshedDialog(self.iface)

        dialog.dem_combo.setLayer(
            self.dem_layer
        )

        self.assertEqual(dialog.observer_label.text(), "-")

        dialog.set_observer(self.observer_lonlat)

        self.assertNotEqual(dialog.observer_label.text(), "-")
