# -*- coding: utf-8 -*-

"""
Interactive map tool: click to generate a viewshed from that point,
showing/updating a non-modal ViewshedDialog. Unlike Line of Sight's
two-click observer/target pair, every click here is a complete,
standalone analysis on its own - the tool just needs one point, so
each click simply moves the observer and re-runs the check.

Military Cartography Tools
"""

from qgis.gui import QgsMapTool, QgsVertexMarker
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor

from ..core.coordinate_utils import project_to_wgs84
from .viewshed_dialog import ViewshedDialog


# Matches line_of_sight_tool.py's own OBSERVER_MARKER_COLOR/ICON_CROSS
# convention - both tools' markers represent the same concept (an
# observer point just clicked), and Viewshed never has a second marker
# to distinguish it from, so there's no reason for a different colour.
OBSERVER_MARKER_COLOR = QColor(31, 58, 95)

MARKER_ICON_SIZE = 14
MARKER_PEN_WIDTH = 3


class ViewshedTool(QgsMapTool):

    """
    Left-click on the canvas to generate a viewshed from that point,
    showing/updating a non-modal ViewshedDialog - stays active across
    repeated clicks, like the Coordinate Probe and Line of Sight
    tools, until another tool is selected.
    """

    def __init__(self, canvas, iface):

        super().__init__(canvas)

        self.iface = iface

        # Created lazily on the first click, then reused for the life
        # of the tool - same ownership model as
        # CoordinateProbeTool/LineOfSightTool.
        self.dialog = None

        self.observer_marker = None


    def _place_observer_marker(self, map_point):

        if self.observer_marker is None:

            self.observer_marker = QgsVertexMarker(
                self.canvas()
            )

            self.observer_marker.setIconType(
                QgsVertexMarker.IconType.ICON_CROSS
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


    def _clear_observer_marker(self):

        if self.observer_marker is not None:

            self.canvas().scene().removeItem(
                self.observer_marker
            )

            self.observer_marker = None


    def _handle_point(self, map_point):

        """
        Kept separate from canvasReleaseEvent's event-handling glue
        so it's directly testable with a plain QgsPointXY - no real
        mouse event needed. map_point is in the canvas's own CRS
        (used directly for the on-canvas marker); converted to WGS84
        for the dialog/generation call.
        """

        if self.dialog is None:

            self.dialog = ViewshedDialog(
                self.iface,
                self.iface.mainWindow()
            )

        self._place_observer_marker(
            map_point
        )

        self.dialog.set_observer(
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
        Clear the marker when another tool is selected, rather than
        leaving it stuck on the canvas indefinitely.
        """

        self._clear_observer_marker()

        super().deactivate()
