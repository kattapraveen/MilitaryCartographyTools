# -*- coding: utf-8 -*-

"""
Tests for the plugin's own wiring: the initGui()/unload() cycle,
toolbar action set/order, the User Guide menu entry, the
coordinate probe tool + its log dialog, and the per-Layout-Designer
toolbar/dock panel.

Military Cartography Tools
"""

import json
import re
import tempfile
from pathlib import Path
from unittest import mock

from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsPrintLayout, QgsLayoutItemMap
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMainWindow, QApplication, QDialog

from .qgis_test_case import QgisTestCase, FakeIface, make_canvas

from MilitaryCartographyTools import plugin as plugin_module
from MilitaryCartographyTools.plugin import MilitaryCartographyTools


def make_plugin():

    window = QMainWindow()
    canvas = make_canvas()
    iface = FakeIface(window=window, canvas=canvas)

    plugin = MilitaryCartographyTools(iface)

    return plugin, iface, window, canvas


class TestPluginLifecycle(QgisTestCase):

    def test_init_gui_grouped_tools_are_not_standalone_on_the_toolbar(self):

        # Housekeeping (2026-08-08): every tool now lives inside one of
        # six grouped toolbar buttons instead of the toolbar directly -
        # see test_init_gui_builds_expected_groups for the group
        # contents themselves. Only About, User Guide and the Symbology
        # Edition switch stand alone.
        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            texts = [action.text() for action in plugin.toolbar.actions()]

            self.assertIn("Military Cartography Tools", texts)

            for grouped_text in (
                "UTM Grid",
                "Coordinate Probe",
                "New Military Layout",
                "Tanaka Contours",
                "Import Waypoints",
                "Space",
            ):

                self.assertNotIn(grouped_text, texts)

        finally:

            plugin.unload()


    def test_init_gui_builds_expected_groups(self):

        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            self.assertEqual(
                set(plugin.group_menus),
                {
                    "grid",
                    "navigation",
                    "terrain_analysis",
                    "waypoints",
                    "print_production",
                    "nato_symbols",
                }
            )

            expected_group_items = {
                "grid": [
                    "UTM Grid",
                    "MGRS 100km Grid",
                    "Sub Grid",
                    "Clear Grid",
                ],
                "navigation": [
                    "Coordinate Probe",
                    "Bearing / Range",
                ],
                "terrain_analysis": [
                    "Tanaka Contours",
                    "Hypsometric Tint",
                    "Hillshade Combinations",
                    "Line of Sight",
                    "Viewshed",
                    "Sensor Coverage",
                    "Regenerate Sensor Coverage",
                ],
                "waypoints": [
                    "Import Waypoints",
                    "Export Waypoints",
                ],
                "print_production": [
                    "New Military Layout",
                    "Map Sheet Series",
                ],
                # Alphabetical (2026-08-18, UI request) - see
                # plugin.py's _setup_toolbar_groups() comment.
                "nato_symbols": [
                    "Activities",
                    "Air",
                    "Control Measures",
                    "Cyberspace",
                    "Land",
                    "Sea Surface",
                    "SIGINT",
                    "Space",
                    "Subsurface",
                ],
            }

            for key, expected_texts in expected_group_items.items():

                with self.subTest(group=key):

                    actual_texts = [
                        action.text()
                        for action in plugin.group_menus[key].actions()
                    ]

                    self.assertEqual(actual_texts, expected_texts)

            # "Sub Grid" nests as its own flyout inside Grid, not a
            # flat entry - its own 4 options are unaffected by grouping.
            sub_grid_option_texts = [
                action.text() for action in plugin.sub_grid_menu.actions()
            ]

            self.assertEqual(
                sub_grid_option_texts,
                ["Off", "10 km", "5 km", "1 km"]
            )

            # "Control Measures" likewise nests as its own flyout inside
            # NATO Symbols (2026-08-09, at the maintainer's request) -
            # one entry per Appendix H logical group, growing as each
            # H3-H22 mini-phase lands. The flat "Control Measure Points"
            # entry was retired on 2026-08-14 when H19/H20/H21 moved its
            # last 21 entities out to their own three layers.
            control_measures_option_texts = [
                action.text()
                for action in plugin.control_measures_menu.actions()
            ]

            # Alphabetical (2026-08-18, UI request) - see plugin.py's
            # _setup_control_measures_menu() comment.
            self.assertEqual(
                control_measures_option_texts,
                [
                    "Airspace Control Measures",
                    "C2 Measures",
                    "CBRN Defense Control Measures",
                    "Deception Control Measures",
                    "Defensive Control Measures",
                    "Field Fortification Control Measures",
                    "Fire Support Coordination Measures",
                    "Intelligence Control Measures",
                    "Maneuver Control Measures",
                    "Maneuver Control Measures II",
                    "Maritime Control Measures",
                    "Mission Tasks",
                    "Obstacle Control Measures",
                    "Offensive Control Measures",
                    "Supply Control Measures",
                    "Sustainment Points",
                    "Target Acquisition Control Measures",
                    "Target Control Measures",
                ]
            )

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
        self.assertIsNone(plugin.bearing_range_action)
        self.assertIsNone(plugin.bearing_range_tool)
        self.assertIsNone(plugin.tanaka_contours_action)
        self.assertIsNone(plugin.hypsometric_tint_action)
        self.assertIsNone(plugin.line_of_sight_action)
        self.assertIsNone(plugin.line_of_sight_tool)
        self.assertIsNone(plugin.hillshade_combination_action)
        self.assertIsNone(plugin.viewshed_action)
        self.assertIsNone(plugin.viewshed_tool)
        self.assertIsNone(plugin.import_waypoints_action)
        self.assertIsNone(plugin.export_waypoints_action)
        self.assertIsNone(plugin.map_sheet_series_action)
        self.assertIsNone(plugin.tactical_graphics_space_action)
        self.assertIsNone(plugin.tactical_graphics_air_action)
        self.assertIsNone(plugin.tactical_graphics_land_action)
        self.assertIsNone(plugin.tactical_graphics_sea_surface_action)
        self.assertIsNone(plugin.tactical_graphics_subsurface_action)
        self.assertIsNone(plugin.tactical_graphics_activities_action)
        self.assertIsNone(plugin.tactical_graphics_sigint_action)
        self.assertIsNone(plugin.tactical_graphics_cyberspace_action)
        self.assertIsNone(plugin.c2_measures_action)
        self.assertIsNone(plugin.maneuver_control_measures_action)
        self.assertIsNone(plugin.defensive_control_measures_action)
        self.assertIsNone(plugin.offensive_control_measures_action)
        self.assertIsNone(plugin.maneuver_control_measures_2_action)
        self.assertIsNone(plugin.airspace_control_measures_action)
        self.assertIsNone(plugin.maritime_control_measures_action)
        self.assertIsNone(plugin.deception_control_measures_action)
        self.assertIsNone(plugin.fire_support_coordination_measures_action)
        self.assertIsNone(plugin.target_control_measures_action)
        self.assertIsNone(plugin.target_acquisition_control_measures_action)
        self.assertIsNone(plugin.sustainment_points_action)
        self.assertIsNone(plugin.supply_points_action)
        self.assertIsNone(plugin.mission_task_points_action)
        self.assertIsNone(plugin.control_measures_menu)
        self.assertIsNone(plugin.sub_grid_menu)
        self.assertIsNone(plugin.sub_grid_group)
        self.assertEqual(plugin.group_menus, {})


    def test_init_gui_then_unload_then_init_gui_again_does_not_error(self):

        # Mirrors what Plugin Reloader does on every reload cycle -
        # this is exactly the scenario the layout_refresh
        # connection leak fix was for.
        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()
        plugin.unload()
        plugin.initGui()
        plugin.unload()


class TestUserGuide(QgisTestCase):

    def test_user_guide_is_in_both_menus_and_next_to_about_on_the_toolbar(self):

        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            self.assertIn(plugin.user_guide_action, iface.menu_actions)
            self.assertIn(
                plugin.user_guide_action,
                iface.pluginHelpMenu().actions()
            )
            self.assertEqual(
                [action.text() for action in plugin.toolbar.actions()[:3]],
                [
                    "Military Cartography Tools",
                    "User Guide",
                    "Symbology Edition",
                ]
            )

        finally:

            plugin.unload()


    def test_reload_cycles_leave_no_stale_help_menu_entries(self):

        # Help -> Plugins is QGIS's menu, so it outlives unload() -
        # an entry not removed there would pile up on every reload.
        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()
        plugin.unload()

        self.assertIsNone(plugin.user_guide_action)
        self.assertEqual(iface.pluginHelpMenu().actions(), [])
        self.assertEqual(iface.menu_actions, [])

        plugin.initGui()

        try:

            self.assertEqual(len(iface.pluginHelpMenu().actions()), 1)

        finally:

            plugin.unload()


    def test_opens_the_shipped_guide_as_a_local_file(self):

        plugin, iface, window, canvas = make_plugin()

        with mock.patch.object(
            plugin_module.QDesktopServices, "openUrl", return_value=True
        ) as open_url, mock.patch.object(
            plugin_module.QMessageBox, "warning"
        ) as warning:

            plugin.show_user_guide()

        url = open_url.call_args.args[0]

        self.assertTrue(url.isLocalFile())
        self.assertEqual(
            Path(url.toLocalFile()),
            plugin.plugin_dir / "docs" / "user-guide-offline.html"
        )
        self.assertTrue(Path(url.toLocalFile()).is_file())
        warning.assert_not_called()


    def test_missing_guide_warns_instead_of_failing_silently(self):

        plugin, iface, window, canvas = make_plugin()

        with tempfile.TemporaryDirectory() as empty_dir:

            plugin.plugin_dir = Path(empty_dir)

            with mock.patch.object(
                plugin_module.QDesktopServices, "openUrl"
            ) as open_url, mock.patch.object(
                plugin_module.QMessageBox, "warning"
            ) as warning:

                plugin.show_user_guide()

        open_url.assert_not_called()
        warning.assert_called_once()


    def test_browser_refusing_to_open_it_also_warns(self):

        plugin, iface, window, canvas = make_plugin()

        with mock.patch.object(
            plugin_module.QDesktopServices, "openUrl", return_value=False
        ), mock.patch.object(
            plugin_module.QMessageBox, "warning"
        ) as warning:

            plugin.show_user_guide()

        warning.assert_called_once()


    def test_shipped_guide_loads_nothing_from_the_network(self):

        # The guide tells the reader the plugin runs fully offline, and
        # is read on air-gapped machines - a remote script, stylesheet
        # or image would contradict it and silently fail there. The
        # bundle stores its page JSON-escaped, hence the optional
        # backslash before the quote.
        guide = (
            Path(plugin_module.__file__).parent
            / "docs" / "user-guide-offline.html"
        )
        html = guide.read_text(encoding="utf-8")

        self.assertEqual(
            re.findall(r"""(?:src|href)=\\?["']https?://[^"'\\]*""", html),
            []
        )

        # Libraries the bundler lifted from a CDN (React) are listed by
        # their original URL; each must also be carried inline, or the
        # page falls back to fetching it.
        ext = re.search(
            r'<script type="__bundler/ext_resources">(.*?)</script>',
            html,
            re.S
        )

        if ext is not None:

            manifest = json.loads(re.search(
                r'<script type="__bundler/manifest">(.*?)</script>',
                html,
                re.S
            ).group(1))

            for resource in json.loads(ext.group(1)):

                with self.subTest(resource=resource["id"]):

                    self.assertIn(resource["uuid"], manifest)


    def test_shipped_guide_is_marked_for_detect_secrets(self):

        # The Plugin Repository runs detect-secrets on every upload, and
        # the bundle's inlined libraries are long base64 strings that it
        # reports as "Base64 High Entropy String" - a finding costs a
        # version number. The marker must end the manifest's own line.
        # Claude Design's bundler does not add it: after rebuilding
        # there, run tools/rebuild_user_guide.py.
        html = (
            Path(plugin_module.__file__).parent
            / "docs" / "user-guide-offline.html"
        ).read_text(encoding="utf-8")

        manifest_line = re.search(
            r'<script type="__bundler/manifest">\n([^\n]*)',
            html
        )

        if manifest_line is None:

            self.skipTest("the guide is no longer a manifest bundle")

        self.assertTrue(
            manifest_line.group(1).endswith(
                "</script><!-- pragma: allowlist secret -->"
            )
        )


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


class TestBearingRangeWiring(QgisTestCase):

    def test_toggling_action_activates_and_the_tool_syncs_back_off(self):

        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            plugin.bearing_range_action.setChecked(True)

            self.assertIs(canvas.mapTool(), plugin.bearing_range_tool)

            from qgis.gui import QgsMapToolPan

            other_tool = QgsMapToolPan(canvas)
            canvas.setMapTool(other_tool)

            self.assertFalse(plugin.bearing_range_action.isChecked())

        finally:

            plugin.unload()


    def test_toggling_coordinate_probe_does_not_uncheck_bearing_range(self):

        # _on_map_tool_changed() loops over every checkable tool - a
        # regression here would un-check every OTHER tool's action
        # whenever any one of them activates, not just the one that
        # actually lost the canvas.
        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            plugin.bearing_range_action.setChecked(True)
            plugin.coordinate_probe_action.setChecked(True)

            self.assertIs(canvas.mapTool(), plugin.coordinate_probe_tool)
            self.assertFalse(plugin.bearing_range_action.isChecked())

        finally:

            plugin.unload()


class TestLineOfSightWiring(QgisTestCase):

    def test_toggling_action_activates_and_the_tool_syncs_back_off(self):

        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            plugin.line_of_sight_action.setChecked(True)

            self.assertIs(canvas.mapTool(), plugin.line_of_sight_tool)

            from qgis.gui import QgsMapToolPan

            other_tool = QgsMapToolPan(canvas)
            canvas.setMapTool(other_tool)

            self.assertFalse(plugin.line_of_sight_action.isChecked())

        finally:

            plugin.unload()


    def test_toggling_coordinate_probe_does_not_uncheck_line_of_sight(self):

        # _on_map_tool_changed() now loops over both checkable tools -
        # a regression here would un-check every OTHER tool's action
        # whenever any one of them activates, not just the one that
        # actually lost the canvas.
        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            plugin.line_of_sight_action.setChecked(True)
            plugin.coordinate_probe_action.setChecked(True)

            self.assertIs(canvas.mapTool(), plugin.coordinate_probe_tool)
            self.assertFalse(plugin.line_of_sight_action.isChecked())

        finally:

            plugin.unload()


class TestViewshedWiring(QgisTestCase):

    def test_toggling_action_activates_and_the_tool_syncs_back_off(self):

        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            plugin.viewshed_action.setChecked(True)

            self.assertIs(canvas.mapTool(), plugin.viewshed_tool)

            from qgis.gui import QgsMapToolPan

            other_tool = QgsMapToolPan(canvas)
            canvas.setMapTool(other_tool)

            self.assertFalse(plugin.viewshed_action.isChecked())

        finally:

            plugin.unload()


    def test_toggling_line_of_sight_does_not_uncheck_viewshed(self):

        # _on_map_tool_changed() loops over every checkable tool - a
        # regression here would un-check every OTHER tool's action
        # whenever any one of them activates, not just the one that
        # actually lost the canvas.
        plugin, iface, window, canvas = make_plugin()

        plugin.initGui()

        try:

            plugin.viewshed_action.setChecked(True)
            plugin.line_of_sight_action.setChecked(True)

            self.assertIs(canvas.mapTool(), plugin.line_of_sight_tool)
            self.assertFalse(plugin.viewshed_action.isChecked())

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
            self.assertIn("Insert Symbol", action_texts)

            plugin.on_layout_designer_closed(designer)

            self.assertNotIn(designer, plugin.layout_toolbars)
            self.assertNotIn(designer, plugin.layout_panels)

        finally:

            plugin.unload()


    def test_insert_symbol_adds_a_picture_item(self):

        # U-1: "Insert Symbol" places a static SVG picture on the
        # layout page rather than a georeferenced feature - the
        # dialog itself is covered by test_layout_symbol_dialog.py,
        # so here the dialog is accepted with its own defaults and
        # this only checks the picture actually lands on the layout.
        from unittest.mock import patch

        from qgis.core import QgsLayoutItemPicture

        from MilitaryCartographyTools.military_symbology.layout_symbol_dialog \
            import InsertSymbolDialog

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

            before = [
                item for item in layout.items()
                if isinstance(item, QgsLayoutItemPicture)
            ]

            self.assertEqual(before, [])

            with patch.object(
                InsertSymbolDialog, "exec",
                return_value=QDialog.DialogCode.Accepted
            ):
                plugin._insert_symbol(designer)

            pictures = [
                item for item in layout.items()
                if isinstance(item, QgsLayoutItemPicture)
            ]

            self.assertEqual(len(pictures), 1)

            picture = pictures[0]

            self.assertTrue(picture.picturePath().startswith("base64:"))
            self.assertTrue(picture.id())

        finally:

            plugin.unload()
