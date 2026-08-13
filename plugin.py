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
from .military_symbology.sigint_layer import add_sigint_layer
from .military_symbology.cyberspace_layer import add_cyberspace_layer
from .military_symbology.sustainment_control_measures import (
    add_sustainment_points_layer,
)
from .military_symbology.supply_points import (
    add_supply_points_layer,
)
from .military_symbology.mission_task_control_measures import (
    add_mission_task_points_layer,
)
from .military_symbology.c2_measures import (
    add_c2_measures_lines_layer,
    add_c2_measures_areas_layer,
    add_c2_measures_points_layer,
)
from .military_symbology.maneuver_control_measures import (
    add_maneuver_control_measures_lines_layer,
    add_maneuver_control_measures_areas_layer,
)
from .military_symbology.defensive_control_measures import (
    add_defensive_control_measures_areas_layer,
    add_defensive_control_measures_points_layer,
)
from .military_symbology.offensive_control_measures import (
    add_offensive_control_measures_lines_layer,
    add_offensive_control_measures_areas_layer,
    add_offensive_control_measures_points_layer,
)
from .military_symbology.maneuver_control_measures_2 import (
    add_maneuver_control_measures_2_lines_layer,
    add_maneuver_control_measures_2_areas_layer,
)
from .military_symbology.airspace_control_measures import (
    add_airspace_control_measures_lines_layer,
    add_airspace_control_measures_areas_layer,
    add_airspace_control_measures_points_layer,
)
from .military_symbology.maritime_control_measures import (
    add_maritime_control_measures_lines_layer,
    add_maritime_control_measures_points_layer,
)
from .military_symbology.deception_control_measures import (
    add_deception_control_measures_lines_layer,
)
from .military_symbology.fire_support_coordination_measures import (
    add_fire_support_coordination_measures_lines_layer,
    add_fire_support_coordination_measures_areas_layer,
)
from .military_symbology.cbrn_defense import (
    add_cbrn_defense_points_layer,
)
from .military_symbology.field_fortification import (
    add_field_fortification_lines_layer,
    add_field_fortification_points_layer,
)
from .military_symbology.obstacle_control_measures import (
    add_obstacle_control_measures_areas_layer,
    add_obstacle_control_measures_lines_layer,
    add_obstacle_control_measures_minefields_layer,
    add_obstacle_control_measures_points_layer,
)
from .military_symbology.target_control_measures import (
    add_target_control_measures_lines_layer,
    add_target_control_measures_points_layer,
    add_target_control_measures_areas_layer,
)
from .military_symbology.target_acquisition_control_measures import (
    add_target_acquisition_control_measures_areas_layer,
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
        self.tactical_graphics_sigint_action = None
        self.tactical_graphics_cyberspace_action = None

        # "Control Measures" nests as its own flyout submenu (like Sub
        # Grid below) rather than a single QAction, since Appendix H's
        # ~17 H.5.x logical groups (C2 Measures, Maneuver, Defensive,
        # ...) each get their own entry as their own mini-phase lands -
        # see _setup_control_measures_menu(). Every entry is one H.5.x
        # group's own layer; the flat "Control Measure Points" layer
        # that used to sit alongside them - a holding pen for entities
        # whose own table had not been built yet - was emptied and
        # retired by H19/H20/H21 (2026-08-14).
        self.control_measures_menu = None
        self.c2_measures_action = None
        self.maneuver_control_measures_action = None
        self.defensive_control_measures_action = None
        self.offensive_control_measures_action = None
        self.maneuver_control_measures_2_action = None
        self.airspace_control_measures_action = None
        self.obstacle_control_measures_action = None
        self.field_fortification_action = None
        self.cbrn_defense_action = None
        self.maritime_control_measures_action = None
        self.deception_control_measures_action = None
        self.fire_support_coordination_measures_action = None
        self.target_control_measures_action = None
        self.target_acquisition_control_measures_action = None
        self.sustainment_points_action = None
        self.supply_points_action = None
        self.mission_task_points_action = None

        self.sub_grid_menu = None
        self.sub_grid_group = None

        # Toolbar-button/Plugins-submenu grouping (housekeeping
        # 2026-08-08, see _setup_toolbar_groups()) - keyed by group
        # key ("grid", "navigation", etc.), each value the QMenu shared
        # by that group's toolbar dropdown and Plugins submenu.
        self.group_menus = {}

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
        self._setup_tactical_graphics_sigint_action()
        self._setup_tactical_graphics_cyberspace_action()
        self._setup_control_measures_menu()

        # Assembles every action built above (all built with
        # standalone=False, plus the sub-grid menu) into the grouped
        # toolbar buttons/Plugins submenus below - must run last, once
        # every individual action/menu already exists.
        self._setup_toolbar_groups()

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
        callback=None,
        standalone=True
    ):

        """
        A QAction with an icon from icons/icon_name - shared by every
        top-level action initGui() builds below, since they all follow
        the same icon+tooltip+callback shape (only the main "about"
        action and the sub-grid dropdown, which isn't a QAction at all,
        are built separately). `standalone` (default True) controls
        whether this action is placed directly on the main toolbar and
        in the flat Plugins menu, the same as before every action got
        grouped - pass False for an action that instead belongs inside
        one of _setup_toolbar_groups()'s own group menus, which places
        it there itself once every individual action has been built.
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

        if standalone:

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
            callback=self.toggle_utm_grid,
            standalone=False
        )

        self.mgrs100k_action = self._build_action(
            "mgrs100k_grid.svg",
            "MGRS 100km Grid",
            tooltip="Show/hide the MGRS 100km square grid",
            checkable=True,
            callback=self.toggle_mgrs100k_grid,
            standalone=False
        )


    def _setup_sub_grid_menu(self):

        # A plain QMenu (not a standalone toolbar button, unlike
        # before the toolbar/menu grouping housekeeping) - nested
        # into the Grid group's own menu by _setup_toolbar_groups(),
        # both on the toolbar and in the Plugins menu, as a "Sub
        # Grid" flyout alongside UTM/MGRS 100km/Clear Grid. Parented
        # to the toolbar (not the main window) so sip.delete(self.
        # toolbar) in unload() cascades and cleans this up too, same
        # reasoning as every other toolbar-owned widget here.
        self.sub_grid_menu = QMenu(
            "Sub Grid",
            self.toolbar
        )

        self.sub_grid_menu.setIcon(
            QIcon(
                str(
                    self.plugin_dir / "icons" / "sub_grid.svg"
                )
            )
        )

        self.sub_grid_menu.setToolTipsVisible(True)

        self.sub_grid_menu.menuAction().setToolTip(
            "Sub Grid (10km / 5km / 1km) spacing"
        )

        self.sub_grid_group = QActionGroup(
            self.sub_grid_menu
        )

        # Nothing is generated until the user picks an option -
        # "Off" starts checked, matching every other grid toggle.
        for label, value in SUB_GRID_OPTIONS:

            option_action = QAction(
                label,
                self.sub_grid_menu
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
            callback=self.clear_grids,
            standalone=False
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
            callback=self.create_new_layout,
            standalone=False
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
            callback=self.create_tanaka_contours,
            standalone=False
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
            callback=self.create_hypsometric_tint,
            standalone=False
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
            callback=self.create_hillshade_combination,
            standalone=False
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
            callback=self.toggle_coordinate_probe,
            standalone=False
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
            callback=self.toggle_bearing_range,
            standalone=False
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
            callback=self.toggle_line_of_sight,
            standalone=False
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
            callback=self.toggle_viewshed,
            standalone=False
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
            callback=self.create_import_waypoints,
            standalone=False
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
            callback=self.create_export_waypoints,
            standalone=False
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
            callback=self.create_map_sheet_series,
            standalone=False
        )


    def _setup_tactical_graphics_space_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/space_layer.py. Covers both of Appendix B's
        # sections (Space Equipment/Platform and the single Space
        # Missile entity) in one layer.
        self.tactical_graphics_space_action = self._build_action(
            "tactical_graphics_space.svg",
            "Space",
            tooltip=(
                "Add a Space layer (MIL-STD-2525D Appendix B) that "
                "renders each point's own symbol automatically from its "
                "attributes"
            ),
            callback=self.create_tactical_graphics_space,
            standalone=False
        )


    def _setup_tactical_graphics_air_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/air_layer.py. Covers both of Appendix C's
        # sections (Air Equipment/Platform and the single Air Missile
        # entity) in one layer.
        self.tactical_graphics_air_action = self._build_action(
            "tactical_graphics_air.svg",
            "Air",
            tooltip=(
                "Add an Air layer (MIL-STD-2525D Appendix C) that "
                "renders each point's own symbol automatically from its "
                "attributes"
            ),
            callback=self.create_tactical_graphics_air,
            standalone=False
        )


    def _setup_tactical_graphics_land_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/land_layer.py. Adds all four of Appendix
        # D's layers (Land Unit/Civilian/Equipment/Installation) in one
        # click - each is a genuinely distinct, substantial vocabulary
        # (unlike Space/Air Missile, not folded into a shared layer).
        self.tactical_graphics_land_action = self._build_action(
            "tactical_graphics_land.svg",
            "Land",
            tooltip=(
                "Add Land Unit/Civilian/Equipment/Installation layers "
                "(MIL-STD-2525D Appendix D) that render each point's "
                "own symbol automatically from its attributes"
            ),
            callback=self.create_tactical_graphics_land,
            standalone=False
        )


    def _setup_tactical_graphics_sea_surface_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/sea_surface_layer.py.
        self.tactical_graphics_sea_surface_action = self._build_action(
            "tactical_graphics_sea_surface.svg",
            "Sea Surface",
            tooltip=(
                "Add a Sea Surface layer (MIL-STD-2525D Appendix E) "
                "that renders each point's own symbol automatically "
                "from its attributes"
            ),
            callback=self.create_tactical_graphics_sea_surface,
            standalone=False
        )


    def _setup_tactical_graphics_subsurface_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/subsurface_layer.py. Adds both of Appendix
        # F's layers (Subsurface, Mine Warfare) in one click.
        self.tactical_graphics_subsurface_action = self._build_action(
            "tactical_graphics_subsurface.svg",
            "Subsurface",
            tooltip=(
                "Add Subsurface and Mine Warfare layers (MIL-STD-2525D "
                "Appendix F) that render each point's own symbol "
                "automatically from its attributes"
            ),
            callback=self.create_tactical_graphics_subsurface,
            standalone=False
        )


    def _setup_tactical_graphics_activities_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/activities_layer.py.
        self.tactical_graphics_activities_action = self._build_action(
            "tactical_graphics_activities.svg",
            "Activities",
            tooltip=(
                "Add an Activities layer (MIL-STD-2525D Appendix G) "
                "that renders each point's own symbol automatically "
                "from its attributes"
            ),
            callback=self.create_tactical_graphics_activities,
            standalone=False
        )


    def _setup_tactical_graphics_sigint_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/sigint_layer.py.
        self.tactical_graphics_sigint_action = self._build_action(
            "tactical_graphics_sigint.svg",
            "SIGINT",
            tooltip=(
                "Add a SIGINT layer (MIL-STD-2525D Appendix J) "
                "that renders each point's own symbol automatically "
                "from its attributes"
            ),
            callback=self.create_tactical_graphics_sigint,
            standalone=False
        )


    def _setup_tactical_graphics_cyberspace_action(self):

        # One-shot action, not a map tool - see
        # military_symbology/cyberspace_layer.py.
        self.tactical_graphics_cyberspace_action = self._build_action(
            "tactical_graphics_cyberspace.svg",
            "Cyberspace",
            tooltip=(
                "Add a Cyberspace layer (MIL-STD-2525D Appendix L) "
                "that renders each point's own symbol automatically "
                "from its attributes"
            ),
            callback=self.create_tactical_graphics_cyberspace,
            standalone=False
        )


    def _setup_control_measures_menu(self):

        # "Control Measures" nests as its own flyout submenu (same
        # QMenu-inside-a-group mechanism as Sub Grid inside Grid - see
        # _setup_sub_grid_menu()) rather than a single QAction, at the
        # project maintainer's own request (2026-08-09): Appendix H
        # covers ~17 logical sections (C2 Measures, Maneuver, Defensive,
        # Offensive, Airspace, Maritime, Deception, Fire Support,
        # Targets, Target Acquisition, Obstacles, Field Fortification,
        # CBRN, Sustainment, Supply, Mission Tasks, Intelligence - see
        # docs/roadmap.md's own H3-H22 mini-phase table), and one click
        # adding every one of them at once (the old single "Control
        # Measures" action) would only get more unwieldy as each
        # mini-phase lands - see military_symbology/c2_measures.py's own
        # docstring for the full rationale. Each entry here is its own
        # H.5.x group, added only once that group's own mini-phase is
        # actually built. The flat "Control Measure Points" layer that
        # used to sit alongside them held whichever point entities had
        # no table module yet; H19/H20/H21 moved its last 21 entries
        # out to Sustainment/Supply/Mission Task Points and it was
        # retired (2026-08-14).
        self.control_measures_menu = QMenu(
            "Control Measures",
            self.toolbar
        )

        self.control_measures_menu.setIcon(
            QIcon(
                str(
                    self.plugin_dir / "icons" / "control_measures.svg"
                )
            )
        )

        self.control_measures_menu.setToolTipsVisible(True)

        self.control_measures_menu.menuAction().setToolTip(
            "Appendix H control measures, grouped by logical section"
        )

        self.c2_measures_action = QAction(
            "C2 Measures",
            self.control_measures_menu
        )

        self.c2_measures_action.setToolTip(
            "Add C2 Measures layers (MIL-STD-2525D Appendix H.5.5/"
            "H.5.9/H.5.10: Boundary, Light Line, Area of Operations, "
            "Named/Target Area of Interest, Airfield Zone, Command and "
            "Control Points)"
        )

        self.c2_measures_action.triggered.connect(
            self.create_c2_measures
        )

        self.control_measures_menu.addAction(
            self.c2_measures_action
        )

        self.maneuver_control_measures_action = QAction(
            "Maneuver Control Measures",
            self.control_measures_menu
        )

        self.maneuver_control_measures_action.setToolTip(
            "Add Maneuver Control Measures layers (MIL-STD-2525D "
            "Appendix H.5.11, Table H-VII: Forward Line of Troops, "
            "Phase Line, FEBA, Principal Direction of Fire, Assembly "
            "Area, Action Areas, Drop/Extraction/Landing/Pickup Zones, "
            "Fortified Area, and similar)"
        )

        self.maneuver_control_measures_action.triggered.connect(
            self.create_maneuver_control_measures
        )

        self.control_measures_menu.addAction(
            self.maneuver_control_measures_action
        )

        self.defensive_control_measures_action = QAction(
            "Defensive Control Measures",
            self.control_measures_menu
        )

        self.defensive_control_measures_action.setToolTip(
            "Add Defensive Control Measures layers (MIL-STD-2525D "
            "Appendix H.5.12: Table H-VIII areas - Battle Position, "
            "Strong Point, Engagement Area; Table H-IX points - "
            "Observation Post and variants, Target Reference Point)"
        )

        self.defensive_control_measures_action.triggered.connect(
            self.create_defensive_control_measures
        )

        self.control_measures_menu.addAction(
            self.defensive_control_measures_action
        )

        self.offensive_control_measures_action = QAction(
            "Offensive Control Measures",
            self.control_measures_menu
        )

        self.offensive_control_measures_action.setToolTip(
            "Add Offensive Control Measures layers (MIL-STD-2525D "
            "Appendix H.5.13, Tables H-X/H-XI: Axis of Advance, "
            "Direction of Attack, Final Coordination Line, Limit of "
            "Advance, Line of Departure, Assault/Attack Position, "
            "Objective Area, and similar)"
        )

        self.offensive_control_measures_action.triggered.connect(
            self.create_offensive_control_measures
        )

        self.control_measures_menu.addAction(
            self.offensive_control_measures_action
        )

        self.maneuver_control_measures_2_action = QAction(
            "Maneuver Control Measures II",
            self.control_measures_menu
        )

        self.maneuver_control_measures_2_action.setToolTip(
            "Add a second set of Maneuver Control Measures layers "
            "(MIL-STD-2525D Appendix H.5.14, Table H-XII: Encirclement, "
            "Penetration Box, Support by Fire Position, Search Area/"
            "Reconnaissance Area, Airhead/Bridgehead/Holding/Release "
            "Line)"
        )

        self.maneuver_control_measures_2_action.triggered.connect(
            self.create_maneuver_control_measures_2
        )

        self.control_measures_menu.addAction(
            self.maneuver_control_measures_2_action
        )

        self.airspace_control_measures_action = QAction(
            "Airspace Control Measures",
            self.control_measures_menu
        )

        self.airspace_control_measures_action.setToolTip(
            "Add Airspace Control Measures layers (MIL-STD-2525D "
            "Appendix H.5.15, Table H-XIII: Air Corridor, Low-Level "
            "Transit Route, Minimum-Risk Route, Safe Lane, SAAFR, "
            "Transit Corridor, UA Route, IFF Off/On Line, Base Defense "
            "Zone, High-Density Airspace Control Zone, Restricted/Weapon "
            "Engagement Zones, Weapons Free Zone, plus the airspace "
            "control points - ACP, CCP, TACAN, Orbit and the rest)"
        )

        self.airspace_control_measures_action.triggered.connect(
            self.create_airspace_control_measures
        )

        self.control_measures_menu.addAction(
            self.airspace_control_measures_action
        )

        self.maritime_control_measures_action = QAction(
            "Maritime Control Measures",
            self.control_measures_menu
        )

        self.maritime_control_measures_action.setToolTip(
            "Add Maritime Control Measures layers (MIL-STD-2525D "
            "Appendix H.5.16, Table H-XIV - lines: the Bearing Line "
            "family, Bearing/Electronic/Electronic Warfare/Acoustic/"
            "Torpedo/Electro-Optical Intercept/Jammer/RDF; points: the "
            "full vocabulary grouped by the table's own headings - "
            "Surface and Subsurface Stations, Routes, Reference Points, "
            "Sonobuoys, Search, Emergency, Hazard and the rest)"
        )

        self.maritime_control_measures_action.triggered.connect(
            self.create_maritime_control_measures
        )

        self.control_measures_menu.addAction(
            self.maritime_control_measures_action
        )

        self.deception_control_measures_action = QAction(
            "Deception Control Measures",
            self.control_measures_menu
        )

        self.deception_control_measures_action.setToolTip(
            "Add a Deception Control Measures (Lines) layer "
            "(MIL-STD-2525D Appendix H.5.17, Table H-XV: Decoy/Dummy)"
        )

        self.deception_control_measures_action.triggered.connect(
            self.create_deception_control_measures
        )

        self.control_measures_menu.addAction(
            self.deception_control_measures_action
        )

        self.fire_support_coordination_measures_action = QAction(
            "Fire Support Coordination Measures",
            self.control_measures_menu
        )

        self.fire_support_coordination_measures_action.setToolTip(
            "Add Fire Support Coordination Measures layers "
            "(MIL-STD-2525D Appendix H.5.18, Table H-XVI: ACA, Free/No/"
            "Restricted Fire Area, Position Area For Artillery, FSCL, "
            "CFL, NFL, BCL, RFL, Munition Flight Path)"
        )

        self.fire_support_coordination_measures_action.triggered.connect(
            self.create_fire_support_coordination_measures
        )

        self.control_measures_menu.addAction(
            self.fire_support_coordination_measures_action
        )

        self.target_control_measures_action = QAction(
            "Target Control Measures",
            self.control_measures_menu
        )

        self.target_control_measures_action.setToolTip(
            "Add Target Control Measures layers (MIL-STD-2525D Appendix "
            "H.5.19, Table H-XVII: Linear/Linear Smoke Target, Final "
            "Protective Fire, Area Target, Series or Group of Targets, "
            "Smoke, Bomb Area, Fire Support Area)"
        )

        self.target_control_measures_action.triggered.connect(
            self.create_target_control_measures
        )

        self.control_measures_menu.addAction(
            self.target_control_measures_action
        )

        self.obstacle_control_measures_action = QAction(
            "Obstacle Control Measures",
            self.control_measures_menu
        )

        self.obstacle_control_measures_action.setToolTip(
            "Add Obstacle Control Measures (Points) and (Areas) layers "
            "(MIL-STD-2525D Appendix H.5.21, Table H-XIX). Points: "
            "mines, booby trap, engineer regulating point, "
            "tetrahedrons/dragons teeth, towers. Areas: the four "
            "obstacle zones, the mined-area family and UXO Area. "
            "Minefields: the table's own five minefield codes, each a "
            "fixed-size box of mine glyphs, with an Anti-personnel / "
            "Anti-tank / Unknown / combined mine-type choice. Lines: "
            "the wire-obstacle family. "
            "Obstacles draw green by default, with a per-feature "
            "switch to black. The table's lines are being built in "
            "later batches."
        )

        self.obstacle_control_measures_action.triggered.connect(
            self.create_obstacle_control_measures
        )

        self.control_measures_menu.addAction(
            self.obstacle_control_measures_action
        )

        self.field_fortification_action = QAction(
            "Field Fortification Control Measures",
            self.control_measures_menu
        )

        self.field_fortification_action.setToolTip(
            "Add Field Fortification (Points) and (Lines) layers "
            "(MIL-STD-2525D Appendix H.5.22, Table H-XX). Points: "
            "Shelter, Above Ground Shelter, Below Ground Shelter and "
            "Fort, each a static icon centred on one clicked point. "
            "Lines: Fortified Line, a crenellated rampart profile that "
            "accepts as many points as you want, and Fortified "
            "Position, whose two points are its front corners. Both "
            "lines put their front on the LEFT of the direction you "
            "digitize."
        )

        self.field_fortification_action.triggered.connect(
            self.create_field_fortification
        )

        self.control_measures_menu.addAction(
            self.field_fortification_action
        )

        self.cbrn_defense_action = QAction(
            "CBRN Defense Control Measures",
            self.control_measures_menu
        )

        self.cbrn_defense_action.setToolTip(
            "Add the CBRN Defense (Points) layer (MIL-STD-2525D "
            "Appendix H.5.23, Table H-XXI): the chemical, biological, "
            "nuclear and radiological event points, their Toxic "
            "Industrial Material variants, and the eleven "
            "decontamination point/site types. The table's own "
            "contaminated AREAS and its dose-rate contour line are not "
            "built yet."
        )

        self.cbrn_defense_action.triggered.connect(
            self.create_cbrn_defense
        )

        self.control_measures_menu.addAction(
            self.cbrn_defense_action
        )

        self.target_acquisition_control_measures_action = QAction(
            "Target Acquisition Control Measures",
            self.control_measures_menu
        )

        self.target_acquisition_control_measures_action.setToolTip(
            "Add a Target Acquisition Control Measures (Areas) layer "
            "(MIL-STD-2525D Appendix H.5.20, Table H-XVIII: Artillery "
            "Target Intelligence Zone, Call For Fire Zone, Censor Zone, "
            "Critical Friendly Zone, Dead Space Area, Sensor Zone, "
            "Target Build-up/Value Area, Zone of Responsibility, Blue/"
            "Purple Kill Box)"
        )

        self.target_acquisition_control_measures_action.triggered.connect(
            self.create_target_acquisition_control_measures
        )

        self.control_measures_menu.addAction(
            self.target_acquisition_control_measures_action
        )

        self.sustainment_points_action = QAction(
            "Sustainment Points",
            self.control_measures_menu
        )

        self.sustainment_points_action.setToolTip(
            "Add a Sustainment Points layer (ambulance exchange, "
            "ammunition supply, casualty and detainee collection, "
            "traffic control post, and similar - Table H-XXII)"
        )

        self.sustainment_points_action.triggered.connect(
            self.create_sustainment_points
        )

        self.control_measures_menu.addAction(
            self.sustainment_points_action
        )

        self.supply_points_action = QAction(
            "Supply Points",
            self.control_measures_menu
        )

        self.supply_points_action.setToolTip(
            "Add a Supply Points layer (general and medical supply "
            "points plus the NATO and US supply classes - Table "
            "H-XXIII)"
        )

        self.supply_points_action.triggered.connect(
            self.create_supply_points
        )

        self.control_measures_menu.addAction(
            self.supply_points_action
        )

        self.mission_task_points_action = QAction(
            "Mission Task Points",
            self.control_measures_menu
        )

        self.mission_task_points_action.setToolTip(
            "Add a Mission Task Points layer (Destroy, Interdict and "
            "Neutralize - the three point-type mission tasks of Table "
            "H-XXIV)"
        )

        self.mission_task_points_action.triggered.connect(
            self.create_mission_task_points
        )

        self.control_measures_menu.addAction(
            self.mission_task_points_action
        )


    def _setup_toolbar_groups(self):

        # Housekeeping (2026-08-08): every action above is now built
        # with standalone=False, so none of them land on the main
        # toolbar or the flat Plugins menu by themselves - this groups
        # them into six logical toolbar buttons (each a QToolButton
        # with an InstantPopup dropdown, the same mechanism the
        # existing Sub Grid control already used) mirrored as six
        # nested submenus in the Plugins menu (the group's own QMenu,
        # added once via its own menuAction() - see
        # _build_toolbar_group()). Only the main "about" action stays
        # a standalone top-level item. Must run after every individual
        # action/menu above has been built.
        groups = [
            (
                "grid",
                "group_grid.svg",
                "Grid",
                "UTM/MGRS grid toggles, sub-grid spacing, and Clear Grid",
                [
                    self.utm_action,
                    self.mgrs100k_action,
                    self.sub_grid_menu,
                    self.clear_action,
                ],
            ),
            (
                "navigation",
                "group_navigation.svg",
                "Navigation",
                "Coordinate Probe and Bearing/Range measurement tools",
                [
                    self.coordinate_probe_action,
                    self.bearing_range_action,
                ],
            ),
            (
                "terrain_analysis",
                "group_terrain_analysis.svg",
                "Terrain Analysis",
                (
                    "DEM-derived terrain analysis: Tanaka Contours, "
                    "Hypsometric Tint, Hillshade Combinations, Line of "
                    "Sight, Viewshed"
                ),
                [
                    self.tanaka_contours_action,
                    self.hypsometric_tint_action,
                    self.hillshade_combination_action,
                    self.line_of_sight_action,
                    self.viewshed_action,
                ],
            ),
            (
                "waypoints",
                "group_waypoints.svg",
                "Waypoints",
                "Import/export waypoints (GPX/KML)",
                [
                    self.import_waypoints_action,
                    self.export_waypoints_action,
                ],
            ),
            (
                "nato_symbols",
                "group_nato_symbols.svg",
                "NATO Symbols",
                (
                    "MIL-STD-2525D/APP-6 tactical graphics: point symbol "
                    "layers (Space/Air/Land/Sea Surface/Subsurface/"
                    "Activities/SIGINT/Cyberspace) and Control Measures"
                ),
                [
                    self.tactical_graphics_space_action,
                    self.tactical_graphics_air_action,
                    self.tactical_graphics_land_action,
                    self.tactical_graphics_sea_surface_action,
                    self.tactical_graphics_subsurface_action,
                    self.tactical_graphics_activities_action,
                    self.tactical_graphics_sigint_action,
                    self.tactical_graphics_cyberspace_action,
                    self.control_measures_menu,
                ],
            ),
            # Print Production stays last, always (2026-08-09, at the
            # maintainer's request) - "creating print layouts" is the
            # natural final step of a mapping workflow, so its own group
            # button anchors the end of the toolbar regardless of what
            # else is added before it.
            (
                "print_production",
                "group_print_production.svg",
                "Print Production",
                "New Military Layout and Map Sheet Series",
                [
                    self.new_layout_action,
                    self.map_sheet_series_action,
                ],
            ),
        ]

        for key, icon_name, title, tooltip, items in groups:

            self.group_menus[key] = self._build_toolbar_group(
                key,
                icon_name,
                title,
                tooltip,
                items
            )


    def _build_toolbar_group(self, key, icon_name, title, tooltip, items):

        """
        One QToolButton (added to the main toolbar, InstantPopup
        dropdown) and one nested Plugins-menu submenu, both backed by
        the SAME QMenu instance - clicking either shows identical
        items in identical (checked/unchecked, etc.) state, since
        they're literally the same QAction objects underneath. `items`
        is a list of QAction and/or QMenu instances (a QMenu - e.g.
        Sub Grid - nests as its own flyout via QMenu.addMenu()). Returns
        the QMenu, which the caller keeps in self.group_menus for
        unload() to detach cleanly from the Plugins menu before the
        toolbar (and this menu, one of its children) gets destroyed.
        """

        icon = QIcon(
            str(
                self.plugin_dir / "icons" / icon_name
            )
        )

        # Parented to the toolbar (not the main window) so
        # sip.delete(self.toolbar) in unload() cascades and cleans
        # this up too, same reasoning as the Sub Grid menu above.
        menu = QMenu(
            title,
            self.toolbar
        )

        menu.setIcon(
            icon
        )

        for item in items:

            if isinstance(item, QMenu):

                menu.addMenu(
                    item
                )

            else:

                menu.addAction(
                    item
                )

        button = QToolButton()

        button.setIcon(
            icon
        )

        button.setText(
            title
        )

        button.setToolTip(
            tooltip
        )

        # Icon-only (2026-08-09, at the maintainer's request): the
        # group's own tooltip (below) already communicates the function
        # on hover, and dropping the text keeps the toolbar's six group
        # buttons compact - .setText() above is kept regardless, for
        # accessibility (screen readers) and the Plugins-menu submenu's
        # own title, neither of which this style affects.
        button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )

        button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )

        button.setMenu(
            menu
        )

        button.setObjectName(
            f"{PLUGIN_ID}_group_{key}"
        )

        self.toolbar.addWidget(
            button
        )

        self.iface.addPluginToMenu(
            PLUGIN_NAME,
            menu.menuAction()
        )

        return menu


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

        # Detach every top-level Plugins-menu entry - the main
        # "about" action plus each group's own menuAction() (see
        # _build_toolbar_group()) - before the toolbar teardown below
        # destroys the QMenu objects backing the latter (all parented
        # to the toolbar). Removing a QAction from a QMenu after its
        # underlying object is already gone would leave a dangling
        # reference in that menu; individual grouped actions (UTM
        # Grid, Tanaka Contours, and so on) were never registered with
        # the Plugins menu directly, only ever added into their own
        # group's QMenu, so detaching each group's single menuAction()
        # here is sufficient - nothing further to do per child action.
        for action in [self.action] + [
            menu.menuAction() for menu in self.group_menus.values()
        ]:

            if action is not None:

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
        self.tactical_graphics_sigint_action = None
        self.tactical_graphics_cyberspace_action = None
        self.c2_measures_action = None
        self.maneuver_control_measures_action = None
        self.defensive_control_measures_action = None
        self.offensive_control_measures_action = None
        self.maneuver_control_measures_2_action = None
        self.airspace_control_measures_action = None
        self.obstacle_control_measures_action = None
        self.maritime_control_measures_action = None
        self.deception_control_measures_action = None
        self.fire_support_coordination_measures_action = None
        self.target_control_measures_action = None
        self.target_acquisition_control_measures_action = None
        self.sustainment_points_action = None
        self.supply_points_action = None
        self.mission_task_points_action = None

        # sub_grid_menu/group, control_measures_menu, and every
        # group_menus entry ARE parented to the toolbar (see
        # _setup_sub_grid_menu()/_setup_control_measures_menu()/
        # _build_toolbar_group()), so sip.delete(self.toolbar) above
        # already destroyed them.
        self.sub_grid_menu = None
        self.sub_grid_group = None
        self.control_measures_menu = None
        self.group_menus = {}

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
        Add a "Space" layer (MIL-STD-2525D Appendix B), ready for
        placing symbols with QGIS's own native point editing tools.
        """

        add_space_layer(
            self.iface
        )


    def create_tactical_graphics_air(self):
        """
        Add an "Air" layer (MIL-STD-2525D Appendix C), ready for
        placing symbols with QGIS's own native point editing tools.
        """

        add_air_layer(
            self.iface
        )


    def create_tactical_graphics_land(self):
        """
        Add "Land Unit"/"Land Civilian"/"Land Equipment"/"Land
        Installation" layers (MIL-STD-2525D Appendix D), ready for
        placing symbols with QGIS's own native point editing tools.
        """

        add_land_layers(
            self.iface
        )


    def create_tactical_graphics_sea_surface(self):
        """
        Add a "Sea Surface" layer (MIL-STD-2525D Appendix E), ready for
        placing symbols with QGIS's own native point editing tools.
        """

        add_sea_surface_layer(
            self.iface
        )


    def create_tactical_graphics_subsurface(self):
        """
        Add "Subsurface" and "Mine Warfare" layers (MIL-STD-2525D
        Appendix F), ready for placing symbols with QGIS's own native
        point editing tools.
        """

        add_subsurface_layers(
            self.iface
        )


    def create_tactical_graphics_activities(self):
        """
        Add an "Activities" layer (MIL-STD-2525D Appendix G), ready for
        placing symbols with QGIS's own native point editing tools.
        """

        add_activities_layer(
            self.iface
        )


    def create_tactical_graphics_sigint(self):
        """
        Add a "SIGINT" layer (MIL-STD-2525D Appendix J), ready for
        placing symbols with QGIS's own native point editing tools.
        """

        add_sigint_layer(
            self.iface
        )


    def create_tactical_graphics_cyberspace(self):
        """
        Add a "Cyberspace" layer (MIL-STD-2525D Appendix L), ready for
        placing symbols with QGIS's own native point editing tools.
        """

        add_cyberspace_layer(
            self.iface
        )


    def create_c2_measures(self):
        """
        Add the C2 Measures layers (lines: Boundary, Light Line; areas:
        Area of Operations, Named/Target Area of Interest, Airfield
        Zone; points: Checkpoint, Contact/Coordination/Decision Point,
        and similar, Table H-VI - MIL-STD-2525D Appendix H.5.5/H.5.9/
        H.5.10), ready for digitizing with QGIS's own native editing
        tools.
        """

        add_c2_measures_lines_layer(
            self.iface
        )

        add_c2_measures_areas_layer(
            self.iface
        )

        add_c2_measures_points_layer(
            self.iface
        )


    def create_maneuver_control_measures(self):
        """
        Add the Maneuver Control Measures layers (lines: Forward Line
        of Troops, Phase Line, FEBA, Principal Direction of Fire;
        areas: Area, Assembly Area, Action Areas, Drop/Extraction/
        Landing/Pickup Zones, Fortified Area - MIL-STD-2525D Appendix
        H.5.11, Table H-VII), ready for digitizing with QGIS's own
        native editing tools.
        """

        add_maneuver_control_measures_lines_layer(
            self.iface
        )

        add_maneuver_control_measures_areas_layer(
            self.iface
        )


    def create_defensive_control_measures(self):
        """
        Add the Defensive Control Measures layers (areas: Battle
        Position, Strong Point, Engagement Area, Table H-VIII; points:
        Observation Post and its variants, Target Reference Point,
        Table H-IX - MIL-STD-2525D Appendix H.5.12), ready for
        digitizing with QGIS's own native editing tools.
        """

        add_defensive_control_measures_areas_layer(
            self.iface
        )

        add_defensive_control_measures_points_layer(
            self.iface
        )


    def create_offensive_control_measures(self):
        """
        Add the Offensive Control Measures layers (lines: Axis of
        Advance, Direction of Attack, Infiltration Lane, Final
        Coordination Line, Limit of Advance, Line of Departure(/Line of
        Contact), Probable Line of Deployment; areas: Assault Position,
        Attack Position, Objective Area; points: Point of Departure -
        MIL-STD-2525D Appendix H.5.13, Tables H-X/H-XI), ready for
        digitizing with QGIS's own native editing tools.
        """

        add_offensive_control_measures_lines_layer(
            self.iface
        )

        add_offensive_control_measures_areas_layer(
            self.iface
        )

        add_offensive_control_measures_points_layer(
            self.iface
        )


    def create_maneuver_control_measures_2(self):
        """
        Add a second set of Maneuver Control Measures layers
        (Encirclement, Penetration Box, Support by Fire Position,
        Search Area/Reconnaissance Area, Airhead/Bridgehead/Holding/
        Release Line - MIL-STD-2525D Appendix H.5.14, Table H-XII),
        ready for digitizing with QGIS's own native editing tools.
        """

        add_maneuver_control_measures_2_lines_layer(
            self.iface
        )

        add_maneuver_control_measures_2_areas_layer(
            self.iface
        )


    def create_airspace_control_measures(self):
        """
        Add Airspace Control Measures layers (lines: Air Corridor,
        Low-Level Transit Route, Minimum-Risk Route, Safe Lane, SAAFR,
        Transit Corridor, UA Route, IFF Off/On Line; areas: High-Density
        Airspace Control Zone, Restricted Operations Zone family,
        Weapon Engagement Zone family, Weapons Free Zone -
        MIL-STD-2525D Appendix H.5.15, Table H-XIII), ready for
        digitizing with QGIS's own native editing tools. The airspace
        control point vocabulary (ACP, CCP, TACAN, Orbit, and similar)
        now comes with them, on its own third Points layer - see
        airspace_control_measures.py's own docstring.
        """

        add_airspace_control_measures_lines_layer(
            self.iface
        )

        add_airspace_control_measures_areas_layer(
            self.iface
        )

        add_airspace_control_measures_points_layer(
            self.iface
        )


    def create_maritime_control_measures(self):
        """
        Add a Maritime Control Measures (Lines) layer (the Bearing Line
        family - Bearing, Electronic, Electronic Warfare, Acoustic (and
        its Ambiguous variant), Torpedo, Electro-Optical Intercept,
        Jammer, Radio Detention Finder - MIL-STD-2525D Appendix H.5.16,
        Table H-XIV), plus a Points layer carrying the table's own
        full 105-entry point vocabulary (printed pages 474-501,
        grouped by the table's own sub-headings - Surface/Subsurface
        Stations, Routes, Sonobuoys, Hazard, and the rest), ready for
        digitizing with QGIS's own native editing tools. Table H-XIV
        has no Areas section. See maritime_control_measures.py's own
        docstring for the five codes deliberately left out and for the
        AEGIS-combat-system-specific family that stays out of scope
        entirely.
        """

        add_maritime_control_measures_lines_layer(
            self.iface
        )

        add_maritime_control_measures_points_layer(
            self.iface
        )


    def create_deception_control_measures(self):
        """
        Add a Deception Control Measures (Lines) layer (Decoy/Dummy -
        MIL-STD-2525D Appendix H.5.17, Table H-XV), ready for digitizing
        with QGIS's own native editing tools. Every other entry in this
        table is either a cross-reference to a symbol already built in
        Maneuver/Offensive Control Measures, or deferred to the future
        Obstacles table - see deception_control_measures.py's own
        docstring.
        """

        add_deception_control_measures_lines_layer(
            self.iface
        )


    def create_fire_support_coordination_measures(self):
        """
        Add Fire Support Coordination Measures layers (areas: Airspace
        Coordination Area, Free/No/Restricted Fire Area, Position Area
        For Artillery; lines: Fire Support Coordination Line,
        Coordinated Fire Line, No Fire Line, Battlefield Coordination
        Line, Restrictive Fire Line, Munition Flight Path -
        MIL-STD-2525D Appendix H.5.18, Table H-XVI), ready for
        digitizing with QGIS's own native editing tools.
        """

        add_fire_support_coordination_measures_lines_layer(
            self.iface
        )

        add_fire_support_coordination_measures_areas_layer(
            self.iface
        )


    def create_target_control_measures(self):
        """
        Add Target Control Measures layers (lines: Linear Target,
        Linear Smoke Target, Final Protective Fire; areas: Area Target,
        Series or Group of Targets, Smoke, Bomb Area, Fire Support Area
        - MIL-STD-2525D Appendix H.5.19, Table H-XVII), ready for
        digitizing with QGIS's own native editing tools, plus a Points
        layer carrying this table's own nine point entries
        (Point/Single/Nuclear/Recorded Target, Fire Support Station,
        Firing/Hide/Launch/Reload/Survey Control Point).
        """

        add_target_control_measures_lines_layer(
            self.iface
        )

        add_target_control_measures_areas_layer(
            self.iface
        )

        add_target_control_measures_points_layer(
            self.iface
        )


    def create_cbrn_defense(self):
        """
        Add the CBRN Defense (Points) layer - Table H-XXI
        (MIL-STD-2525D Appendix H.5.23).

        Points only so far: the table's seven contaminated areas, its
        Minimum Safe Distance Zone and its dose-rate contour line are
        audited but not built - see cbrn_defense.py's own
        TABLE_H_XXI_REMAINING for what each needs.
        """

        add_cbrn_defense_points_layer(
            self.iface
        )

    def create_field_fortification(self):
        """
        Add the Field Fortification (Points) and (Lines) layers - Table
        H-XX (MIL-STD-2525D Appendix H.5.22), ready for digitizing with
        QGIS's own native tools.

        Affiliation-coloured, not green: the green rule is H.5.21.1's
        own exception for obstacles, and H.5.22 claims nothing like it.
        See field_fortification.py's own docstring for the three
        proportions the standard leaves unnumbered here.
        """

        add_field_fortification_points_layer(
            self.iface
        )

        add_field_fortification_lines_layer(
            self.iface
        )

    def create_obstacle_control_measures(self):
        """
        Add the Obstacle Control Measures (Points) and (Areas) layers -
        Table H-XIX (MIL-STD-2525D Appendix H.5.21), ready for
        digitizing with QGIS's own native tools.

        Obstacles draw GREEN rather than in the affiliation hue every
        other control measure uses, with a per-feature Colour field to
        switch any one to black. Points (batch B1) and areas (batch B2)
        exist so far; the table's large line family arrives in later
        batches - see obstacle_control_measures.py's own docstring for
        the full inventory and batch plan.
        """

        add_obstacle_control_measures_points_layer(
            self.iface
        )

        add_obstacle_control_measures_areas_layer(
            self.iface
        )

        add_obstacle_control_measures_minefields_layer(
            self.iface
        )

        add_obstacle_control_measures_lines_layer(
            self.iface
        )


    def create_target_acquisition_control_measures(self):
        """
        Add a Target Acquisition Control Measures (Areas) layer
        (Artillery Target Intelligence Zone, Call For Fire Zone,
        Censor Zone, Critical Friendly Zone, Dead Space Area, Sensor
        Zone, Target Build-up Area, Target Value Area, Zone of
        Responsibility, Blue Kill Box, Purple Kill Box - MIL-STD-2525D
        Appendix H.5.20, Table H-XVIII), ready for digitizing with
        QGIS's own native editing tools. Both Weapon/Sensor Range Fan
        variants are not built - see that module's own docstring.
        """

        add_target_acquisition_control_measures_areas_layer(
            self.iface
        )


    def create_sustainment_points(self):
        """
        Add a "Sustainment Points" layer - Table H-XXII's own sixteen
        drawable point symbols (MIL-STD-2525D Appendix H.5.24), ready
        for placing with QGIS's own native point editing tools.
        """

        add_sustainment_points_layer(
            self.iface
        )


    def create_supply_points(self):
        """
        Add a "Supply Points" layer - Table H-XXIII's own eighteen
        point symbols, general and medical supply points plus the NATO
        and US supply classes (MIL-STD-2525D Appendix H.5.25). That
        table's own areas and lines are not built; see
        supply_points.py's own docstring.
        """

        add_supply_points_layer(
            self.iface
        )


    def create_mission_task_points(self):
        """
        Add a "Mission Task Points" layer - Destroy, Interdict and
        Neutralize, the three of Table H-XXIV's 29 rows that are point
        symbols (MIL-STD-2525D Appendix H.5.26). The other 26 are
        multi-anchor constructions; see
        mission_task_control_measures.py's own docstring.
        """

        add_mission_task_points_layer(
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