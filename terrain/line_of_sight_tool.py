# -*- coding: utf-8 -*-

"""
Interactive map tool: click twice to check line of sight between two
points. The first click sets the observer and opens a small dialog
showing its coordinates and a height field; the second sets the
target and immediately runs the check. A third click starts a fresh
pair rather than continuing to accumulate points.

Military Cartography Tools
"""

from qgis.gui import QgsMapTool, QgsVertexMarker
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor

from ..core.coordinate_utils import project_to_wgs84
from .line_of_sight_dialog import LineOfSightDialog


# Matches the icon set's own #1f3a5f; the target marker uses the same
# red as a blocked Line of Sight segment (see line_of_sight.py's
# BLOCKED_COLOR) so the two markers read as "observer"/"target"
# consistently with the line itself.
OBSERVER_MARKER_COLOR = QColor(31, 58, 95)
TARGET_MARKER_COLOR = QColor(178, 34, 34)

MARKER_ICON_SIZE = 14
MARKER_PEN_WIDTH = 3


class LineOfSightTool(QgsMapTool):

    """
    Left-click twice on the canvas to run a line-of-sight check
    between an observer and target point, showing/updating a
    non-modal LineOfSightDialog as each point is set - stays active
    across repeated pairs, like the Coordinate Probe tool, until
    another tool is selected.

    Each click also drops a marker on the canvas at that point
    (observer = a blue cross, target = a red X) - clicking, especially
    the first point, previously gave no feedback on the map itself
    (only the dialog updated), which made it easy to click again
    without realising the first click had already registered.
    """

    def __init__(self, canvas, iface):

        super().__init__(canvas)

        self.iface = iface

        # Created lazily on the first click, then reused for the life
        # of the tool - same ownership model as
        # CoordinateProbeTool/CoordinateProbeDialog.
        self.dialog = None

        self.observer_marker = None
        self.target_marker = None


    def _place_observer_marker(self, map_point):

        if self.observer_marker is None:

            self.observer_marker = QgsVertexMarker(
                self.canvas()
            )

            self.observer_marker.setIconType(
                QgsVertexMarker.ICON_CROSS
            )

            self.observer_marker.setColor(
                OBSERVER_MARKER_COLOR
            )

            self.observer_marker.setPenWidth(
                MARKER_PEN_WIDTH
            )

            self.observer_marker.setIconSize(
                MARKER_ICON_SIZE
            )

        self.observer_marker.setCenter(
            map_point
        )


    def _place_target_marker(self, map_point):

        if self.target_marker is None:

            self.target_marker = QgsVertexMarker(
                self.canvas()
            )

            self.target_marker.setIconType(
                QgsVertexMarker.ICON_X
            )

            self.target_marker.setColor(
                TARGET_MARKER_COLOR
            )

            self.target_marker.setPenWidth(
                MARKER_PEN_WIDTH
            )

            self.target_marker.setIconSize(
                MARKER_ICON_SIZE
            )

        self.target_marker.setCenter(
            map_point
        )


    def _clear_target_marker(self):

        if self.target_marker is not None:

            self.canvas().scene().removeItem(
                self.target_marker
            )

            self.target_marker = None


    def _clear_observer_marker(self):

        if self.observer_marker is not None:

            self.canvas().scene().removeItem(
                self.observer_marker
            )

            self.observer_marker = None


    def _handle_point(self, map_point):

        """
        The observer/target state machine, kept separate from
        canvasReleaseEvent's event-handling glue so it's directly
        testable with a plain QgsPointXY - no real mouse event needed.
        map_point is in the canvas's own CRS (used directly for the
        on-canvas marker); converted to WGS84 for the dialog/
        visibility calculation.
        """

        if self.dialog is None:

            self.dialog = LineOfSightDialog(
                self.iface,
                self.iface.mainWindow()
            )

        starting_new_pair = (
            self.dialog.observer_lonlat is None
            or self.dialog.target_lonlat is not None
        )

        if starting_new_pair:

            self._place_observer_marker(
                map_point
            )

            self._clear_target_marker()

            self.dialog.set_observer(
                project_to_wgs84(map_point)
            )

        else:

            self._place_target_marker(
                map_point
            )

            self.dialog.set_target(
                project_to_wgs84(map_point)
            )

        self.dialog.show()
        self.dialog.raise_()


    def canvasReleaseEvent(self, event):

        if event.button() != Qt.MouseButton.LeftButton:
            return

        self._handle_point(
            event.mapPoint()
        )


    def deactivate(self):

        """
        Clear both markers when another tool is selected, rather than
        leaving them stuck on the canvas indefinitely.
        """

        self._clear_observer_marker()
        self._clear_target_marker()

        super().deactivate()
