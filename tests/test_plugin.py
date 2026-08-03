# -*- coding: utf-8 -*-

"""
Tests for the plugin's own wiring: the initGui()/unload() cycle,
toolbar action set/order, the coordinate probe tool + its log
dialog, and the per-Layout-Designer toolbar/dock panel.

Military Cartography Tools
"""

from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsPrintLayout, QgsLayoutItemMap
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMainWindow, QApplication

from .qgis_test_case import QgisTestCase, FakeIface, make_canvas

from MilitaryCartographyTools.plugin import MilitaryCartographyTools


def make_plugin():

    window = QMainWindow()
    canvas = make_canvas()
    iface = FakeIface(window=window, canvas=canvas)

    plugin = MilitaryCartographyTools(iface)

    return plugin, iface, window, canvas


class TestPluginLifecycle(QgisTestCase):

    def test_init_gui_builds_expected_toolbar_actions(self):

        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            texts = [action.text() for action in plugin.toolbar.actions()]

            for expected in (
                "Military Cartography Tools",
                "UTM Grid",
                "MGRS 100km Grid",
                "Clear Grid",
                "Coordinate Probe",
                "New Military Layout",
                "Tanaka Contours",
                "Hypsometric Tint",
            ):

                self.assertIn(expected, texts)

            # Coordinate Probe sits immediately to the left of
            # (i.e. right before) New Military Layout, per request.
            probe_index = texts.index("Coordinate Probe")
            layout_index = texts.index("New Military Layout")

            self.assertEqual(layout_index - probe_index, 1)

        finally:

            plugin.unload()


    def test_main_action_and_new_layout_action_have_different_icons(self):

        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            self.assertNotEqual(
                plugin.action.icon().cacheKey(),
                plugin.new_layout_action.icon().cacheKey()
            )

        finally:

            plugin.unload()


    def test_unload_clears_toolbar_and_action_references(self):

        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()
        plugin.unload()

        self.assertIsNone(plugin.toolbar)
        self.assertIsNone(plugin.utm_action)
        self.assertIsNone(plugin.new_layout_action)
        self.assertIsNone(plugin.coordinate_probe_action)
        self.assertIsNone(plugin.coordinate_probe_tool)
        self.assertIsNone(plugin.tanaka_contours_action)
        self.assertIsNone(plugin.hypsometric_tint_action)


    def test_init_gui_then_unload_then_init_gui_again_does_not_error(self):

        # Mirrors what Plugin Reloader does on every reload cycle -
        # this is exactly the scenario the layout_refresh
        # connection leak fix was for.
        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()
        plugin.unload()
        plugin.initGui()
        plugin.unload()


class TestCoordinateProbeWiring(QgisTestCase):

    def test_toggling_action_activates_and_the_tool_syncs_back_off(self):

        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            plugin.coordinate_probe_action.setChecked(True)

            self.assertIs(canvas.mapTool(), plugin.coordinate_probe_tool)

            from qgis.gui import QgsMapToolPan

            other_tool = QgsMapToolPan(canvas)
            canvas.setMapTool(other_tool)

            self.assertFalse(plugin.coordinate_probe_action.isChecked())

        finally:

            plugin.unload()


class FakeClickEvent:

    def __init__(self, point, button=Qt.MouseButton.LeftButton):

        self._point = point
        self._button = button


    def button(self):

        return self._button


    def mapPoint(self):

        return self._point


class TestCoordinateProbeToolAndDialog(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:32737")
        )


    def test_click_adds_row_and_copies_mgrs_to_clipboard(self):

        from qgis.core import QgsPointXY
        from MilitaryCartographyTools.core.coordinate_probe_tool import (
            CoordinateProbeTool,
            CoordinateProbeDialog,
        )

        canvas = make_canvas("EPSG:32737")
        iface = FakeIface(canvas=canvas)

        tool = CoordinateProbeTool(canvas, iface)

        self.assertIsNone(tool.dialog)

        point = QgsPointXY(515000, 9251000)

        tool.canvasReleaseEvent(FakeClickEvent(point))

        self.assertIsInstance(tool.dialog, CoordinateProbeDialog)
        self.assertEqual(tool.dialog.table.rowCount(), 1)

        clipboard_text = QApplication.clipboard().text()
        self.assertTrue(clipboard_text)

        mgrs_cell = tool.dialog.table.item(0, 2).text()
        self.assertEqual(mgrs_cell, clipboard_text)


    def test_right_click_is_ignored(self):

        from qgis.core import QgsPointXY
        from MilitaryCartographyTools.core.coordinate_probe_tool import CoordinateProbeTool

        canvas = make_canvas("EPSG:32737")
        iface = FakeIface(canvas=canvas)

        tool = CoordinateProbeTool(canvas, iface)

        tool.canvasReleaseEvent(
            FakeClickEvent(QgsPointXY(515000, 9251000), Qt.MouseButton.RightButton)
        )

        self.assertIsNone(tool.dialog)


    def test_repeated_clicks_accumulate_newest_first(self):

        from qgis.core import QgsPointXY
        from MilitaryCartographyTools.core.coordinate_probe_tool import CoordinateProbeTool

        canvas = make_canvas("EPSG:32737")
        iface = FakeIface(canvas=canvas)

        tool = CoordinateProbeTool(canvas, iface)

        tool.canvasReleaseEvent(FakeClickEvent(QgsPointXY(515000, 9251000)))
        first_mgrs = QApplication.clipboard().text()

        tool.canvasReleaseEvent(FakeClickEvent(QgsPointXY(520000, 9255000)))
        second_mgrs = QApplication.clipboard().text()

        self.assertEqual(tool.dialog.table.rowCount(), 2)
        self.assertEqual(tool.dialog.table.item(0, 2).text(), second_mgrs)
        self.assertEqual(tool.dialog.table.item(1, 2).text(), first_mgrs)


    def test_double_click_row_recopies_that_rows_mgrs(self):

        from qgis.core import QgsPointXY
        from MilitaryCartographyTools.core.coordinate_probe_tool import CoordinateProbeTool

        canvas = make_canvas("EPSG:32737")
        iface = FakeIface(canvas=canvas)

        tool = CoordinateProbeTool(canvas, iface)

        tool.canvasReleaseEvent(FakeClickEvent(QgsPointXY(515000, 9251000)))
        first_mgrs = QApplication.clipboard().text()

        tool.canvasReleaseEvent(FakeClickEvent(QgsPointXY(520000, 9255000)))

        tool.dialog._copy_row_mgrs(1, 2)

        self.assertEqual(QApplication.clipboard().text(), first_mgrs)


    def test_dialog_survives_close_and_is_reused(self):

        from qgis.core import QgsPointXY
        from MilitaryCartographyTools.core.coordinate_probe_tool import CoordinateProbeTool

        canvas = make_canvas("EPSG:32737")
        iface = FakeIface(canvas=canvas)

        tool = CoordinateProbeTool(canvas, iface)

        tool.canvasReleaseEvent(FakeClickEvent(QgsPointXY(515000, 9251000)))

        dialog_before = tool.dialog
        dialog_before.close()

        tool.canvasReleaseEvent(FakeClickEvent(QgsPointXY(520000, 9255000)))

        self.assertIs(tool.dialog, dialog_before)
        self.assertEqual(tool.dialog.table.rowCount(), 2)


class TestLayoutDesignerWiring(QgisTestCase):

    class FakeDesigner:

        def __init__(self, layout, window):

            self._layout = layout
            self._window = window


        def layout(self):

            return self._layout


        def window(self):

            return self._window


    def test_on_layout_designer_opened_builds_toolbar_and_panel(self):

        plugin, iface, window, canvas = make_plugin()
        plugin.initGui()

        try:

            project = QgsProject.instance()
            layout = QgsPrintLayout(project)
            layout.initializeDefaults()

            map_item = QgsLayoutItemMap(layout)
            layout.addLayoutItem(map_item)

            project.layoutManager().addLayout(layout)

            designer = self.FakeDesigner(layout, window)

            plugin.on_layout_designer_opened(designer)

            self.assertIn(designer, plugin.layout_toolbars)
            self.assertIn(designer, plugin.layout_panels)

            toolbar = plugin.layout_toolbars[designer]
            action_texts = [a.text() for a in toolbar.actions()]

            self.assertIn("Add Grid Frame", action_texts)
            self.assertIn("Remove Grid Frame", action_texts)

            plugin.on_layout_designer_closed(designer)

            self.assertNotIn(designer, plugin.layout_toolbars)
            self.assertNotIn(designer, plugin.layout_panels)

        finally:

            plugin.unload()
