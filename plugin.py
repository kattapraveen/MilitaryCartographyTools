# -*- coding: utf-8 -*-
"""
Military Cartography Tools

Main plugin class.

Copyright (C) 2026 Praveen Kumar

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License v2 or later.
"""

import configparser
from pathlib import Path

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QAction, QIcon, QActionGroup
from qgis.PyQt.QtWidgets import QMessageBox, QToolButton, QMenu, QToolBar
from qgis.PyQt import sip
from qgis.core import Qgis, QgsMessageLog, QgsLayoutItemMap

from .expressions import mgrs_functions
from .expressions import military_symbology_functions
from .core.layout_refresh import connect_layout_refresh, disconnect_layout_refresh
from .core.coordinate_probe_tool import CoordinateProbeTool
from .core.bearing_range_tool import BearingRangeTool
from .grid import GridManager, add_grid_frame, remove_grid_frame
from .grid.grid_settings import GridSettings
from .layout import show_new_layout_dialog, LayoutOptionsPanel, show_map_sheet_series_dialog
from .military_symbology.space_layer import add_space_layer
from .military_symbology.air_layer import add_air_layer
from .military_symbology.land_layer import add_land_layers
from .military_symbology.sea_surface_layer import add_sea_surface_layer
from .military_symbology.subsurface_layer import add_subsurface_layers
from .military_symbology.activities_layer import add_activities_layer
from .military_symbology.control_measure_points import (
    add_control_measure_points_layer,
)
from .military_symbology.control_measures import (
    add_control_measures_lines_layer,
    add_control_measures_areas_layer,
)
from .terrain import (
    show_tanaka_contour_dialog,
    show_hypsometric_tint_dialog,
    show_hillshade_combination_dialog,
)
from .terrain.line_of_sight_tool import LineOfSightTool
from .terrain.viewshed_tool import ViewshedTool
from .waypoints import show_export_waypoints_dialog, show_import_waypoints_dialog


SUB_GRID_OPTIONS = [
    ("Off", None),
    ("10 km", 10000),
    ("5 km", 5000),
    ("1 km", 1000),
]


_plugin_dir = Path(__file__).parent

_cfg = configparser.ConfigParser()
_cfg.read(_plugin_dir / "metadata.txt")

PLUGIN_NAME = _cfg.get("general", "name")
PLUGIN_VERSION = _cfg.get("general", "version")
PLUGIN_ID = _plugin_dir.name


class MilitaryCartographyTools:
    """
    Main plugin class.
    """

    def __init__(self, iface):

        self.iface = iface

        self.plugin_dir = Path(__file__).parent

        self.toolbar = None
        self.action = None

        self.utm_action = None
        self.mgrs100k_action = None
        self.clear_action = None
        self.new_layout_action = None
        self.coordinate_probe_action = None
        self.bearing_range_action = None
        self.tanaka_contours_action = None
        self.hypsometric_tint_action = None
        self.line_of_sight_action = None
        self.hillshade_combination_action = None
        self.viewshed_action = None
        self.import_waypoints_action = None
        self.export_waypoints_action = None
        self.map_sheet_series_action = None
        self.tactical_graphics_space_action = None
        self.tactical_graphics_air_action = None
        self.tactical_graphics_land_action = None
        self.tactical_graphics_sea_surface_action = None
        self.tactical_graphics_subsurface_action = None
        self.tactical_graphics_activities_action = None
        self.control_measures_action = None

        self.sub_grid_button = None
        self.sub_grid_menu = None
        self.sub_grid_group = None

        self.grid_manager = None
        self.coordinate_probe_tool = None
        self.bearing_range_tool = None
        self.line_of_sight_tool = None
        self.viewshed_tool = None

        # One small toolbar per currently-open Layout Designer
        # window, keyed by the designer interface itself - just
        # the grid frame action, not a full copy of the canvas
        # toolbar (the layout already shows whatever grid is
        # built on the canvas; this only adds the print-specific
        # border ticks/annotations).
        self.layout_toolbars = {}

        # One "Military Layout Settings" dock panel per currently-
        # open Layout Designer window, same keying as
        # layout_toolbars - lets page size/orientation/scale/
        # heading/classification be changed on that specific
        # layout in place, instead of only at creation time via
        # New Military Layout.
        self.layout_panels = {}

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    @staticmethod
    def log(message: str, level=Qgis.MessageLevel.Info):

        QgsMessageLog.logMessage(
            message,
            PLUGIN_NAME,
            level
        )


    # ------------------------------------------------------------------
    # QGIS Plugin API
    # ------------------------------------------------------------------

    def initGui(self):
        """
        Initialize plugin GUI.
        """

        mgrs_functions.register()
        military_symbology_functions.register()

        self.log(
            "MGRS expression functions registered."
        )

        self._init_layout_refresh()
        self._init_grid_manager()

        self.toolbar = self.iface.addToolBar(
            PLUGIN_NAME
        )

        self.toolbar.setObjectName(
            PLUGIN_ID
        )

        self._setup_main_action()
        self._setup_grid_toggle_actions()
        self._setup_sub_grid_menu()
        self._setup_clear_action()
        self._setup_coordinate_probe_action()
        self._setup_bearing_range_action()
        self._setup_new_layout_action()
        self._setup_tanaka_contours_action()
        self._setup_hypsometric_tint_action()
        self._setup_line_of_sight_action()
        self._setup_hillshade_combination_action()
        self._setup_viewshed_action()
        self._setup_import_waypoints_action()
        self._setup_export_waypoints_action()
        self._setup_map_sheet_series_action()
        self._setup_tactical_graphics_space_action()
        self._setup_tactical_graphics_air_action()
        self._setup_tactical_graphics_land_action()
        self._setup_tactical_graphics_sea_surface_action()
        self._setup_tactical_graphics_subsurface_action()
        self._setup_tactical_graphics_activities_action()
        self._setup_control_measures_action()

        # Add the grid-frame toolbar to every print layout window -
        # each Layout Designer gets its own small toolbar, since a
        # print layout's map item has its own extent/scale,
        # independent of the interactive canvas.
        self.iface.layoutDesignerOpened.connect(
            self.on_layout_designer_opened
        )

        self.iface.layoutDesignerWillBeClosed.connect(
            self.on_layout_designer_closed
        )

        self.log(
            f"{PLUGIN_NAME} {PLUGIN_VERSION} loaded."
        )


    def _init_layout_refresh(self):

        try:

            connect_layout_refresh()

            self.log(
                "Layout refresh connected."
            )

        except Exception as e:

            self.log(
                f"Layout refresh connection failed: {e}",
                Qgis.MessageLevel.Warning
            )


    def _init_grid_manager(self):

        try:

            self.grid_manager = GridManager(
                self.iface
            )

            self.log(
                "Grid manager initialised."
            )

        except Exception as e:

            self.log(
                f"Grid manager initialisation failed: {e}",
                Qgis.MessageLevel.Warning
            )


    def _build_action(
        self,
        icon_name,
        text,
        tooltip=None,
        checkable=False,
        callback=None
    ):

        """
        A QAction with an icon from icons/icon_name, added to the
        main toolbar and the Plugins menu - shared by every
        top-level action initGui() builds below, since they all
        follow the same icon+tooltip+toolbar+menu shape (only the
        main "about" action and the sub-grid dropdown, which isn't
        a QAction at all, are built separately).
        """

        action = QAction(
            QIcon(
                str(
                    self.plugin_dir / "icons" / icon_name
                )
            ),
            text,
            self.iface.mainWindow()
        )

        if tooltip:

            action.setToolTip(
                tooltip
            )

        if checkable:

            action.setCheckable(True)

        if callback is not None:

            (action.toggled if checkable else action.triggered).connect(
                callback
            )

        self.toolbar.addAction(
            action
        )

        self.iface.addPluginToMenu(
            PLUGIN_NAME,
            action
        )

        return action


    def _setup_main_action(self):

        self.action = QAction(
            QIcon(
                str(
                    self.plugin_dir / "icons" / "icon.svg"
                )
            ),
            PLUGIN_NAME,
            self.iface.mainWindow()
        )

        self.action.triggered.connect(
            self.show_about
        )

        self.iface.addPluginToMenu(
            PLUGIN_NAME,
            self.action
        )

        self.toolbar.addAction(
            self.action
        )


    def _setup_grid_toggle_actions(self):

        self.utm_action = self._build_action(
            "utm_grid.svg",
            "UTM Grid",
            tooltip="Show/hide the UTM Grid Zone Designator grid",
            checkable=True,
            callback=self.toggle_utm_grid
        )

        self.mgrs100k_action = self._build_action(
            "mgrs100k_grid.svg",
            "MGRS 100km Grid",
            tooltip="Show/hide the MGRS 100km square grid",
            checkable=True,
            callback=self.toggle_mgrs100k_grid
        )


    def _setup_sub_grid_menu(self):

        # QToolBar.addWidget() reparents the widget to the
        # toolbar, so parenting the menu/actions to the button
        # (rather than the main window) means sip.delete(self.
        # toolbar) in unload() cascades and cleans all of this
        # up too - same reasoning as the toolbar fix above.
        self.sub_grid_button = QToolButton()

        self.sub_grid_button.setIcon(
            QIcon(
                str(
                    self.plugin_dir / "icons" / "sub_grid.svg"
                )
            )
        )

        self.sub_grid_button.setText(
            "Sub Grid"
        )

        self.sub_grid_button.setToolTip(
            "Sub Grid (10km / 5km / 1km) spacing"
        )

        self.sub_grid_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )

        self.sub_grid_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )

        self.sub_grid_menu = QMenu(
            self.sub_grid_button
        )

        self.sub_grid_group = QActionGroup(
            self.sub_grid_button
        )

        # Nothing is generated until the user picks an option -
        # "Off" starts checked, matching every other grid toggle.
        for label, value in SUB_GRID_OPTIONS:

            option_action = QAction(
                label,
                self.sub_grid_button
            )

            option_action.setCheckable(True)

            option_action.setChecked(
                value is None
            )

            option_action.triggered.connect(
                lambda checked, v=value: self.set_sub_grid_option(v)
            )

            self.sub_grid_group.addAction(
                option_action
            )

            self.sub_grid_menu.addAction(
                option_action
            )

            self.iface.addPluginToMenu(
                PLUGIN_NAME,
                option_action
            )

        self.sub_grid_button.setMenu(
            self.sub_grid_menu
        )

        self.toolbar.addWidget(
            self.sub_grid_button
        )


    def _setup_clear_action(self):

        # Removes every grid layer and turns every toggle off.
        # Grids are only ever built once and then shown/hidden by
        # the toggles above, so this is the explicit action for
        # wiping the slate before picking grids again for a new
        # area.
        self.clear_action = self._build_action(
            "clear_grid.svg",
            "Clear Grid",
            tooltip="Remove all grid layers and turn every grid off",
            callback=self.clear_grids
        )


    def _setup_new_layout_action(self):

        # Creates a fully-configured print layout (page size,
        # orientation, initial scale) in one step, rather than
        # QGIS's own New Layout dialog which only takes a name and
        # starts blank.
        self.new_layout_action = self._build_action(
            "new_layout.svg",
            "New Military Layout",
            tooltip=(
                "Create a new print layout with a chosen page "
                "size, orientation, and starting scale"
            ),
            callback=self.create_new_layout
        )


    def _setup_tanaka_contours_action(self):

        # Illuminated contours from a DEM, clipped to the current
        # map canvas extent - see terrain/tanaka_contours.py.
        self.tanaka_contours_action = self._build_action(
            "tanaka_contours.svg",
            "Tanaka Contours",
            tooltip=(
                "Generate illuminated (Tanaka) contours from a DEM "
                "for the current map extent"
            ),
            callback=self.create_tanaka_contours
        )


    def _setup_hypsometric_tint_action(self):

        # Filled elevation-colour raster from a DEM, clipped to the
        # current map canvas extent - see terrain/hypsometric_tint.py.
        self.hypsometric_tint_action = self._build_action(
            "hypsometric_tint.svg",
            "Hypsometric Tint",
            tooltip=(
                "Generate a filled hypsometric (elevation colour) "
                "raster from a DEM for the current map extent"
            ),
            callback=self.create_hypsometric_tint
        )


    def _setup_hillshade_combination_action(self):

        # Multi-directional hillshade blend from a DEM, clipped to
        # the current map canvas extent - see
        # terrain/hillshade_combination.py.
        self.hillshade_combination_action = self._build_action(
            "hillshade_combination.svg",
            "Hillshade Combinations",
            tooltip=(
                "Generate a multi-directional hillshade blend (2-3 "
                "light azimuths averaged) from a DEM for the "
                "current map extent"
            ),
            callback=self.create_hillshade_combination
        )


    def _setup_coordinate_probe_action(self):

        # Click-to-read-coordinates tool - stays active across
        # multiple clicks like QGIS's own Identify/Measure tools,
        # so the toggle needs to track when some OTHER tool
        # replaces it too (see _on_map_tool_changed), not just
        # respond to its own button.
        self.coordinate_probe_tool = CoordinateProbeTool(
            self.iface.mapCanvas(),
            self.iface
        )

        self.coordinate_probe_action = self._build_action(
            "coordinate_probe.svg",
            "Coordinate Probe",
            tooltip=(
                "Click the map to show that point's latitude/"
                "longitude and MGRS coordinates on the message "
                "bar, and copy the MGRS coordinate to the "
                "clipboard"
            ),
            checkable=True,
            callback=self.toggle_coordinate_probe
        )

        self.iface.mapCanvas().mapToolSet.connect(
            self._on_map_tool_changed
        )


    def _setup_bearing_range_action(self):

        # Two-click true/grid/magnetic azimuth + distance tool - see
        # core/bearing_range_tool.py. Stays active across repeated
        # pairs like the coordinate probe/line of sight tools, so it
        # shares the same _on_map_tool_changed un-check handling (no
        # separate mapToolSet connection needed - one connection
        # already covers every map tool).
        self.bearing_range_tool = BearingRangeTool(
            self.iface.mapCanvas(),
            self.iface
        )

        self.bearing_range_action = self._build_action(
            "bearing_range.svg",
            "Bearing / Range",
            tooltip=(
                "Click two points on the map to read the true, grid, "
                "and magnetic azimuth and distance between them"
            ),
            checkable=True,
            callback=self.toggle_bearing_range
        )


    def _setup_line_of_sight_action(self):

        # Two-click point-to-point visibility check tool - see
        # terrain/line_of_sight_tool.py/terrain/line_of_sight.py.
        # Stays active across repeated pairs like the coordinate
        # probe tool, so it shares the same _on_map_tool_changed
        # un-check handling (no separate mapToolSet connection
        # needed - one connection already covers every map tool).
        self.line_of_sight_tool = LineOfSightTool(
            self.iface.mapCanvas(),
            self.iface
        )

        self.line_of_sight_action = self._build_action(
            "line_of_sight.svg",
            "Line of Sight",
            tooltip=(
                "Click two points on the map to check whether the "
                "second is visible from the first, accounting for "
                "terrain and earth curvature/refraction"
            ),
            checkable=True,
            callback=self.toggle_line_of_sight
        )


    def _setup_viewshed_action(self):

        # Single-click coverage-sweep tool - see
        # terrain/viewshed_tool.py/terrain/viewshed.py. Stays active
        # across repeated clicks like the coordinate probe/line of
        # sight tools, so it shares the same _on_map_tool_changed
        # un-check handling (no separate mapToolSet connection
        # needed - one connection already covers every map tool).
        self.viewshed_tool = ViewshedTool(
            self.iface.mapCanvas(),
            self.iface
        )

        self.viewshed_action = self._build_action(
            "viewshed.svg",
            "Viewshed",
            tooltip=(
                "Click a point on the map to show everywhere visible "
                "from it within a chosen range, accounting for "
                "terrain and earth curvature/refraction"
            ),
            checkable=True,
            callback=self.toggle_viewshed
        )


    def _setup_import_waypoints_action(self):

        # One-shot dialog action, not a map tool - see
        # waypoints/gpx_kml_dialog.py.
        self.import_waypoints_action = self._build_action(
            "import_waypoints.svg",
            "Import Waypoints",
            tooltip=(
                "Import waypoints from a GPX or KML file, labelled "
                "with their MGRS grid reference"
            ),
            callback=self.create_import_waypoints
        )


    def _setup_export_waypoints_action(self):

        # One-shot dialog action, not a map tool - see
        # waypoints/gpx_kml_dialog.py.
        self.export_waypoints_action = self._build_action(
            "export_waypoints.svg",
            "Export Waypoints",
            tooltip=(
                "Export a point layer to a GPX or KML file, with "
                "each waypoint's name set to its MGRS grid reference"
            ),
            callback=self.create_export_waypoints
        )


    def _setup_map_sheet_series_action(self):

        # One-shot dialog action, not a map tool - see
        # layout/map_sheet_series_dialog.py.
        self.map_sheet_series_action = self._build_action(
            "map_sheet_series.svg",
            "Map Sheet Series",
            tooltip=(
                "Batch-generate a numbered series of print sheets "
                "tiling the current map extent"
            ),
            callback=self.create_map_sheet_series
        )


    def _setup_tactical_graphics_space_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/space_layer.py. Covers both of Appendix B's
        # sections (Space Equipment/Platform and the single Space
        # Missile entity) in one layer.
        self.tactical_graphics_space_action = self._build_action(
            "tactical_graphics_space.svg",
            "Tactical Graphics - Space",
            tooltip=(
                "Add a Space layer (MIL-STD-2525D Appendix B) that "
                "renders each point's own symbol automatically from its "
                "attributes"
            ),
            callback=self.create_tactical_graphics_space
        )


    def _setup_tactical_graphics_air_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/air_layer.py. Covers both of Appendix C's
        # sections (Air Equipment/Platform and the single Air Missile
        # entity) in one layer.
        self.tactical_graphics_air_action = self._build_action(
            "tactical_graphics_air.svg",
            "Tactical Graphics - Air",
            tooltip=(
                "Add an Air layer (MIL-STD-2525D Appendix C) that "
                "renders each point's own symbol automatically from its "
                "attributes"
            ),
            callback=self.create_tactical_graphics_air
        )


    def _setup_tactical_graphics_land_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/land_layer.py. Adds all four of Appendix
        # D's layers (Land Unit/Civilian/Equipment/Installation) in one
        # click - each is a genuinely distinct, substantial vocabulary
        # (unlike Space/Air Missile, not folded into a shared layer).
        self.tactical_graphics_land_action = self._build_action(
            "tactical_graphics_land.svg",
            "Tactical Graphics - Land",
            tooltip=(
                "Add Land Unit/Civilian/Equipment/Installation layers "
                "(MIL-STD-2525D Appendix D) that render each point's "
                "own symbol automatically from its attributes"
            ),
            callback=self.create_tactical_graphics_land
        )


    def _setup_tactical_graphics_sea_surface_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/sea_surface_layer.py.
        self.tactical_graphics_sea_surface_action = self._build_action(
            "tactical_graphics_sea_surface.svg",
            "Tactical Graphics - Sea Surface",
            tooltip=(
                "Add a Sea Surface layer (MIL-STD-2525D Appendix E) "
                "that renders each point's own symbol automatically "
                "from its attributes"
            ),
            callback=self.create_tactical_graphics_sea_surface
        )


    def _setup_tactical_graphics_subsurface_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/subsurface_layer.py. Adds both of Appendix
        # F's layers (Subsurface, Mine Warfare) in one click.
        self.tactical_graphics_subsurface_action = self._build_action(
            "tactical_graphics_subsurface.svg",
            "Tactical Graphics - Subsurface",
            tooltip=(
                "Add Subsurface and Mine Warfare layers (MIL-STD-2525D "
                "Appendix F) that render each point's own symbol "
                "automatically from its attributes"
            ),
            callback=self.create_tactical_graphics_subsurface
        )


    def _setup_tactical_graphics_activities_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/activities_layer.py.
        self.tactical_graphics_activities_action = self._build_action(
            "tactical_graphics_activities.svg",
            "Tactical Graphics - Activities",
            tooltip=(
                "Add an Activities layer (MIL-STD-2525D Appendix G) "
                "that renders each point's own symbol automatically "
                "from its attributes"
            ),
            callback=self.create_tactical_graphics_activities
        )


    def _setup_control_measures_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/control_measures.py and
        # military_symbology/control_measure_points.py. Adds the lines,
        # areas, AND control-measure-points layers in one click -
        # conceptually one feature (per docs/roadmap.md's own Phase 10
        # bullet), even though QGIS needs separate layers since a vector
        # layer is always a single geometry type.
        self.control_measures_action = self._build_action(
            "control_measures.svg",
            "Tactical Graphics - Control Measures",
            tooltip=(
                "Add layers for control measures (phase lines, "
                "boundaries, axis of advance, objectives, NAIs, and "
                "point control measures like checkpoints/decision "
                "points/supply points)"
            ),
            callback=self.create_control_measures
        )


    def unload(self):
        """
        Unload plugin.
        """

        mgrs_functions.unregister()
        military_symbology_functions.unregister()

        disconnect_layout_refresh()

        if self.coordinate_probe_tool is not None:

            if self.iface.mapCanvas().mapTool() is self.coordinate_probe_tool:

                self.iface.mapCanvas().unsetMapTool(
                    self.coordinate_probe_tool
                )

            try:

                self.iface.mapCanvas().mapToolSet.disconnect(
                    self._on_map_tool_changed
                )

            except (TypeError, RuntimeError):

                pass

        if self.bearing_range_tool is not None:

            if self.iface.mapCanvas().mapTool() is self.bearing_range_tool:

                self.iface.mapCanvas().unsetMapTool(
                    self.bearing_range_tool
                )

        if self.line_of_sight_tool is not None:

            if self.iface.mapCanvas().mapTool() is self.line_of_sight_tool:

                self.iface.mapCanvas().unsetMapTool(
                    self.line_of_sight_tool
                )

        try:

            self.iface.layoutDesignerOpened.disconnect(
                self.on_layout_designer_opened
            )

            self.iface.layoutDesignerWillBeClosed.disconnect(
                self.on_layout_designer_closed
            )

        except (TypeError, RuntimeError):

            # Already disconnected (e.g. initGui() never
            # completed, or unload() is somehow running twice) -
            # PyQt raises TypeError for a signal that was never
            # connected and RuntimeError if the underlying C++
            # object is already gone; either way there's nothing
            # left to disconnect.
            pass

        for designer, toolbar in list(self.layout_toolbars.items()):

            designer.window().removeToolBar(
                toolbar
            )

            sip.delete(toolbar)

        self.layout_toolbars.clear()

        for designer, panel in list(self.layout_panels.items()):

            designer.window().removeDockWidget(
                panel
            )

            sip.delete(panel)

        self.layout_panels.clear()

        # Detach every action from the Plugins menu before the
        # toolbar teardown below destroys the ones parented to
        # it (sub-grid option actions) - removing a QAction from
        # a QMenu after its underlying object is already gone
        # would leave a dangling reference in that menu.
        for action in [
            self.action,
            self.utm_action,
            self.mgrs100k_action,
            self.clear_action,
            self.new_layout_action,
            self.coordinate_probe_action,
            self.bearing_range_action,
            self.tanaka_contours_action,
            self.hypsometric_tint_action,
            self.line_of_sight_action,
            self.hillshade_combination_action,
            self.viewshed_action,
            self.import_waypoints_action,
            self.export_waypoints_action,
            self.map_sheet_series_action,
            self.tactical_graphics_space_action,
            self.tactical_graphics_air_action,
            self.tactical_graphics_land_action,
            self.tactical_graphics_sea_surface_action,
            self.tactical_graphics_subsurface_action,
            self.tactical_graphics_activities_action,
            self.control_measures_action,
        ]:

            if action is not None:

                self.iface.removePluginMenu(
                    PLUGIN_NAME,
                    action
                )

        if self.sub_grid_menu is not None:

            for action in self.sub_grid_menu.actions():

                self.iface.removePluginMenu(
                    PLUGIN_NAME,
                    action
                )


        if self.toolbar is not None:

            self.iface.removeToolBarIcon(
                self.action
            )

            self.iface.mainWindow().removeToolBar(
                self.toolbar
            )

            # Delete the underlying C++ object immediately rather
            # than via deleteLater(): Plugin Reloader calls unload()
            # and re-runs initGui() synchronously without returning
            # to the Qt event loop, so a deferred delete leaves the
            # old toolbar (same object name) alive when the new one
            # is created, triggering QGIS's duplicate-widget cleanup.
            sip.delete(self.toolbar)

            self.toolbar = None


        # utm_action/mgrs100k_action/clear_action/new_layout_action/
        # coordinate_probe_action/bearing_range_action/
        # tanaka_contours_action/hypsometric_tint_action/
        # line_of_sight_action/hillshade_combination_action/
        # viewshed_action/import_waypoints_action/
        # export_waypoints_action/map_sheet_series_action are
        # parented to the main window (like self.action above), not
        # the toolbar, so they survive sip.delete(self.toolbar) -
        # just drop the references.
        self.utm_action = None
        self.mgrs100k_action = None
        self.clear_action = None
        self.new_layout_action = None
        self.coordinate_probe_action = None
        self.coordinate_probe_tool = None
        self.bearing_range_action = None
        self.bearing_range_tool = None
        self.tanaka_contours_action = None
        self.hypsometric_tint_action = None
        self.line_of_sight_action = None
        self.line_of_sight_tool = None
        self.hillshade_combination_action = None
        self.viewshed_action = None
        self.viewshed_tool = None
        self.import_waypoints_action = None
        self.export_waypoints_action = None
        self.map_sheet_series_action = None
        self.tactical_graphics_space_action = None
        self.tactical_graphics_air_action = None
        self.tactical_graphics_land_action = None
        self.tactical_graphics_sea_surface_action = None
        self.tactical_graphics_subsurface_action = None
        self.tactical_graphics_activities_action = None
        self.control_measures_action = None

        # sub_grid_button/menu/group ARE children of the toolbar
        # widget (added via addWidget), so sip.delete(self.
        # toolbar) above already destroyed them.
        self.sub_grid_button = None
        self.sub_grid_menu = None
        self.sub_grid_group = None

        self.log(
            f"{PLUGIN_NAME} unloaded."
        )


    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def toggle_utm_grid(self, checked):
        """
        Show/hide the UTM Grid Zone Designator grid. Only
        generates it the first time - after that this just
        toggles layer-tree visibility (see Regenerate Grids
        for rebuilding it against a new map extent).
        """

        GridSettings.set_utm_visible(
            checked
        )

        if self.grid_manager is None:
            return

        if checked:

            self.grid_manager.show_utm()

        else:

            self.grid_manager.hide_utm()


    def toggle_mgrs100k_grid(self, checked):
        """
        Show/hide the MGRS 100km square grid. Only generates
        it the first time - see toggle_utm_grid().
        """

        GridSettings.set_mgrs100_visible(
            checked
        )

        if self.grid_manager is None:
            return

        if checked:

            # The 100km grid is built from the UTM Grid Zone
            # Designator layer - bring it up first if it isn't
            # already showing (this also flips the UTM toggle
            # on, via its own toggled signal).
            if not self.utm_action.isChecked():

                self.utm_action.setChecked(True)

            self.grid_manager.show_mgrs100k()

        else:

            self.grid_manager.hide_mgrs100k()


    def set_sub_grid_option(self, spacing):
        """
        Switch the sub grid: None hides it, otherwise spacing
        (10000/5000/1000) selects 10km/5km/1km. Each spacing is
        only generated the first time it's picked - after that,
        switching just shows/hides the matching layer.
        """

        if self.grid_manager is None:
            return

        if spacing is None:

            GridSettings.set_mgrs_sub_visible(False)

            self.grid_manager.hide_sub_grid()

            return

        GridSettings.set_mgrs_sub_visible(True)

        GridSettings.set_mgrs_sub_spacing(
            spacing
        )

        # Same dependency pattern as MGRS 100km: bring UTM up
        # first if it isn't already on.
        if not self.utm_action.isChecked():

            self.utm_action.setChecked(True)

        self.grid_manager.show_sub_grid()


    def clear_grids(self):
        """
        Remove every grid layer (all sub-grid spacings
        included) and turn every toggle off - a clean slate
        before picking grids again for a new area.
        """

        if self.grid_manager is None:
            return

        self.grid_manager.clear()


        GridSettings.set_utm_visible(False)

        self.utm_action.setChecked(False)

        GridSettings.set_mgrs100_visible(False)

        self.mgrs100k_action.setChecked(False)

        GridSettings.set_mgrs_sub_visible(False)

        for action in self.sub_grid_menu.actions():

            if action.text() == "Off":

                action.setChecked(True)


    def create_new_layout(self):
        """
        Prompt for page size/orientation/scale and create a new
        print layout accordingly.
        """

        show_new_layout_dialog(
            self.iface
        )


    def create_tanaka_contours(self):
        """
        Prompt for a DEM and illumination parameters, then generate
        a Tanaka contour layer for the current map extent.
        """

        show_tanaka_contour_dialog(
            self.iface
        )


    def create_hypsometric_tint(self):
        """
        Prompt for a DEM and opacity, then generate a hypsometric
        tint layer for the current map extent.
        """

        show_hypsometric_tint_dialog(
            self.iface
        )


    def create_hillshade_combination(self):
        """
        Prompt for a DEM and an azimuth preset, then generate a
        combined hillshade layer for the current map extent.
        """

        show_hillshade_combination_dialog(
            self.iface
        )


    def toggle_coordinate_probe(self, checked):
        """
        Activate/deactivate the coordinate probe map tool.
        """

        if checked:

            self.iface.mapCanvas().setMapTool(
                self.coordinate_probe_tool
            )

        else:

            self.iface.mapCanvas().unsetMapTool(
                self.coordinate_probe_tool
            )


    def toggle_bearing_range(self, checked):
        """
        Activate/deactivate the bearing/range map tool.
        """

        if checked:

            self.iface.mapCanvas().setMapTool(
                self.bearing_range_tool
            )

        else:

            self.iface.mapCanvas().unsetMapTool(
                self.bearing_range_tool
            )


    def toggle_line_of_sight(self, checked):
        """
        Activate/deactivate the line of sight map tool.
        """

        if checked:

            self.iface.mapCanvas().setMapTool(
                self.line_of_sight_tool
            )

        else:

            self.iface.mapCanvas().unsetMapTool(
                self.line_of_sight_tool
            )


    def toggle_viewshed(self, checked):
        """
        Activate/deactivate the viewshed map tool.
        """

        if checked:

            self.iface.mapCanvas().setMapTool(
                self.viewshed_tool
            )

        else:

            self.iface.mapCanvas().unsetMapTool(
                self.viewshed_tool
            )


    def create_import_waypoints(self):
        """
        Prompt for a GPX/KML file and import its waypoints, labelled
        with their MGRS grid reference.
        """

        show_import_waypoints_dialog(
            self.iface
        )


    def create_export_waypoints(self):
        """
        Prompt for a point layer and a GPX/KML destination, then
        export it with each waypoint's name set to its MGRS grid
        reference.
        """

        show_export_waypoints_dialog(
            self.iface
        )


    def create_map_sheet_series(self):
        """
        Prompt for page size/orientation/scale, then batch-generate
        a numbered series of print sheets tiling the current map
        extent.
        """

        show_map_sheet_series_dialog(
            self.iface
        )


    def create_tactical_graphics_space(self):
        """
        Add a "Tactical Graphics - Space" layer (MIL-STD-2525D Appendix
        B), ready for placing symbols with QGIS's own native point
        editing tools.
        """

        add_space_layer(
            self.iface
        )


    def create_tactical_graphics_air(self):
        """
        Add a "Tactical Graphics - Air" layer (MIL-STD-2525D Appendix
        C), ready for placing symbols with QGIS's own native point
        editing tools.
        """

        add_air_layer(
            self.iface
        )


    def create_tactical_graphics_land(self):
        """
        Add "Tactical Graphics - Land Unit/Civilian/Equipment/
        Installation" layers (MIL-STD-2525D Appendix D), ready for
        placing symbols with QGIS's own native point editing tools.
        """

        add_land_layers(
            self.iface
        )


    def create_tactical_graphics_sea_surface(self):
        """
        Add a "Tactical Graphics - Sea Surface" layer (MIL-STD-2525D
        Appendix E), ready for placing symbols with QGIS's own native
        point editing tools.
        """

        add_sea_surface_layer(
            self.iface
        )


    def create_tactical_graphics_subsurface(self):
        """
        Add "Tactical Graphics - Subsurface" and "Tactical Graphics -
        Mine Warfare" layers (MIL-STD-2525D Appendix F), ready for
        placing symbols with QGIS's own native point editing tools.
        """

        add_subsurface_layers(
            self.iface
        )


    def create_tactical_graphics_activities(self):
        """
        Add a "Tactical Graphics - Activities" layer (MIL-STD-2525D
        Appendix G), ready for placing symbols with QGIS's own native
        point editing tools.
        """

        add_activities_layer(
            self.iface
        )


    def create_control_measures(self):
        """
        Add the control-measures layers (lines: phase lines,
        boundaries, axis of advance; areas: objectives, NAIs; points:
        checkpoints, decision points, supply points, and similar),
        ready for digitizing/placing with QGIS's own native editing
        tools.
        """

        add_control_measures_lines_layer(
            self.iface
        )

        add_control_measures_areas_layer(
            self.iface
        )

        add_control_measure_points_layer(
            self.iface
        )


    def _on_map_tool_changed(self, new_tool, old_tool):
        """
        Keep each checkable tool's toolbar button in sync when some
        OTHER tool (e.g. Pan, Identify, or one of this plugin's own
        other tools) replaces it - QGIS map tools don't un-check
        their own toolbar button automatically when deselected this
        way.
        """

        for action, tool in (
            (self.coordinate_probe_action, self.coordinate_probe_tool),
            (self.bearing_range_action, self.bearing_range_tool),
            (self.line_of_sight_action, self.line_of_sight_tool),
            (self.viewshed_action, self.viewshed_tool),
        ):

            if action is not None and new_tool is not tool:

                action.setChecked(
                    False
                )


    # ------------------------------------------------------------------
    # Print layout grid frame
    # ------------------------------------------------------------------

    def on_layout_designer_opened(self, designer):
        """
        Add a small "grid frame" toolbar, and the Military Layout
        Settings dock panel, to a newly-opened Layout Designer
        window.
        """

        layout = designer.layout()

        if layout is None:
            return

        map_item = None

        for item in layout.items():

            if isinstance(item, QgsLayoutItemMap):
                map_item = item
                break

        if map_item is None:
            return

        toolbar = self._build_grid_frame_toolbar(
            designer,
            map_item
        )

        settings_action = self._build_layout_settings_panel(
            designer,
            layout
        )

        toolbar.addAction(
            settings_action
        )

        designer.window().addToolBar(
            toolbar
        )

        self.layout_toolbars[designer] = toolbar


    def _build_grid_frame_toolbar(self, designer, map_item):

        """
        Adds/removes the native QGIS map-grid border (ticks +
        coordinate annotations) on this layout's map item, at
        whatever sub-grid spacing is currently selected on the
        canvas. Returns the toolbar without adding it to the
        window yet - on_layout_designer_opened() adds the Layout
        Settings toggle action to it first.
        """

        toolbar = QToolBar(
            "Military Grid Frame"
        )

        toolbar.setObjectName(
            f"{PLUGIN_ID}_layout"
        )

        add_action = QAction(
            QIcon(
                str(
                    self.plugin_dir / "icons" / "sub_grid.svg"
                )
            ),
            "Add Grid Frame",
            designer.window()
        )

        add_action.setToolTip(
            "Add border ticks and coordinate annotations for "
            "this layout's map, spaced automatically for its "
            "current print scale, and hide the sub-grid's own "
            "on-map tick labels for this layout"
        )

        add_action.triggered.connect(
            lambda: add_grid_frame(
                map_item
            )
        )

        toolbar.addAction(
            add_action
        )

        remove_action = QAction(
            QIcon(
                str(
                    self.plugin_dir / "icons" / "clear_grid.svg"
                )
            ),
            "Remove Grid Frame",
            designer.window()
        )

        remove_action.setToolTip(
            "Remove this layout's grid frame"
        )

        remove_action.triggered.connect(
            lambda: remove_grid_frame(
                map_item
            )
        )

        toolbar.addAction(
            remove_action
        )

        return toolbar


    def _build_layout_settings_panel(self, designer, layout):

        """
        Military Layout Settings dock panel - lets this specific
        layout's page size/orientation/scale/heading/
        classification be changed in place (calling
        layout.update_layout()) rather than only at creation time
        via New Military Layout. Returns a checkable action that
        shows/hides it, for the caller to place on a toolbar.
        """

        panel = LayoutOptionsPanel(
            self.iface,
            layout,
            designer.window()
        )

        designer.window().addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,
            panel
        )

        self.layout_panels[designer] = panel

        # The panel is shown by default when the designer opens,
        # but closing it (its dock title bar's own close button)
        # previously left no way to bring it back short of
        # reopening the whole designer window.
        # QDockWidget.toggleViewAction() is a checkable action
        # that's already wired to the dock's own visibility, so
        # this just needs an icon and a home on the toolbar.
        settings_action = panel.toggleViewAction()

        settings_action.setIcon(
            QIcon(
                str(
                    self.plugin_dir / "icons" / "layout_settings.svg"
                )
            )
        )

        settings_action.setToolTip(
            "Show/hide the Military Layout Settings panel for "
            "this layout"
        )

        return settings_action


    def on_layout_designer_closed(self, designer):
        """
        Drop our references when a Layout Designer window closes -
        the toolbar and dock panel are both Qt children of that
        window and are cleaned up by Qt when the window goes away.
        """

        self.layout_toolbars.pop(
            designer,
            None
        )

        self.layout_panels.pop(
            designer,
            None
        )


    def show_about(self):
        """
        Show plugin information.
        """

        QMessageBox.information(
            self.iface.mainWindow(),
            PLUGIN_NAME,
            f"""
{PLUGIN_NAME}
Version {PLUGIN_VERSION}

Military mapping and MGRS tools for QGIS.

Copyright © 2026 Praveen Kumar


Includes MGRS conversion engine:

Alex Bruy
Boundless / Planet Federal / Planet Inc.


Licensed under GNU GPL v2 or later.


Additional information:

README.md
THIRD_PARTY_NOTICES.md
LICENSE
            """
        )