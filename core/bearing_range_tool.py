# -*- coding: utf-8 -*-

"""
Interactive map tool: click two points to read off the true, grid,
and magnetic azimuth plus geodesic distance between them - the
inverse of the Coordinate Probe tool's single-point lookup. The
first click sets the "from" point; the second sets the "to" point
and logs a reading. A third click starts a fresh pair rather than
continuing to accumulate points, the same interaction Line of Sight
and Viewshed already use.

Military Cartography Tools
"""

import math

from qgis.core import Qgis, QgsGeometry, QgsPointXY
from qgis.gui import QgsMapTool, QgsRubberBand, QgsVertexMarker
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from . import MGRSConverter
from .coordinate_utils import (
    grid_convergence,
    magnetic_declination,
    project_to_wgs84,
    true_bearing_and_distance,
)


# Matches line_of_sight_tool.py's own marker colours/sizing, so every
# two-click tool in the plugin reads consistently on the canvas.
FROM_MARKER_COLOR = QColor(31, 58, 95)
TO_MARKER_COLOR = QColor(178, 34, 34)

MARKER_ICON_SIZE = 14
MARKER_PEN_WIDTH = 3

# The line/arrowhead connecting from-point to to-point, in the same
# blue as the from-marker. Sized in screen pixels (converted to map
# units via the canvas's own mapUnitsPerPixel()) rather than a
# fraction of the line's length, so the arrowhead stays a consistent,
# legible size regardless of zoom level or how far apart the two
# points are - the same fixed-pixel-size convention the vertex
# markers themselves already use.
LINE_COLOR = FROM_MARKER_COLOR
LINE_WIDTH_PX = 2
ARROWHEAD_LENGTH_PX = 14
ARROWHEAD_WIDTH_PX = 10

NO_POINT_TEXT = "-"

# Matches CoordinateProbeDialog's own lat/lon display precision and
# full 1m MGRS precision.
LAT_LON_DECIMALS = 6
MGRS_PRECISION = 5

COLUMN_LABELS = ["From", "To", "True Az", "Grid Az", "Mag Az", "Distance"]


def _format_lonlat(lonlat, converter):

    mgrs = converter.format(
        converter.convert(lonlat.y(), lonlat.x())
    )

    return (
        f"{lonlat.y():.{LAT_LON_DECIMALS}f}, {lonlat.x():.{LAT_LON_DECIMALS}f}\n"
        f"{mgrs}"
    )


def _format_azimuth(degrees):

    return f"{degrees:.1f}°"


class BearingRangeDialog(QDialog):

    """
    Non-modal log of every from/to pair measured with the bearing/
    range tool active - stays open and keeps accumulating rows across
    pairs (and across the tool being switched away from and back to),
    the same persistent-log pattern CoordinateProbeDialog already
    uses.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.converter = MGRSConverter(
            precision=MGRS_PRECISION
        )

        self.from_lonlat = None
        self.to_lonlat = None

        self.setWindowTitle(
            "Bearing / Range"
        )

        self.resize(
            520,
            320
        )

        self.from_label = QLabel(
            NO_POINT_TEXT
        )

        self.to_label = QLabel(
            NO_POINT_TEXT
        )

        form = QFormLayout()

        form.addRow("From", self.from_label)
        form.addRow("To", self.to_label)

        self.table = QTableWidget(
            0,
            len(COLUMN_LABELS)
        )

        self.table.setHorizontalHeaderLabels(
            COLUMN_LABELS
        )

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        clear_button = QPushButton(
            "Clear"
        )

        clear_button.clicked.connect(
            lambda: self.table.setRowCount(0)
        )

        button_row = QHBoxLayout()

        button_row.addStretch()
        button_row.addWidget(clear_button)

        outer = QVBoxLayout()

        outer.addLayout(form)
        outer.addWidget(self.table)
        outer.addLayout(button_row)

        self.setLayout(
            outer
        )


    def set_from(self, lonlat):

        """
        Called by BearingRangeTool on the first click of a new pair -
        also clears any previous "to" point, since a new "from" point
        starts a fresh reading.
        """

        self.from_lonlat = lonlat
        self.from_label.setText(
            _format_lonlat(lonlat, self.converter)
        )

        self.to_lonlat = None
        self.to_label.setText(
            NO_POINT_TEXT
        )


    def set_to(self, lonlat):

        """
        Called by BearingRangeTool on the second click of a pair -
        computes and logs a new row immediately, unlike Line of
        Sight's Generate button, since there's no DEM/settings that
        would ever need re-running with different values afterwards.
        """

        self.to_lonlat = lonlat
        self.to_label.setText(
            _format_lonlat(lonlat, self.converter)
        )

        self._log_reading()


    def _log_reading(self):

        from_lat, from_lon = self.from_lonlat.y(), self.from_lonlat.x()
        to_lat, to_lon = self.to_lonlat.y(), self.to_lonlat.x()

        true_azimuth, distance_m = true_bearing_and_distance(
            from_lat,
            from_lon,
            to_lat,
            to_lon
        )

        # Both grid_convergence() and magnetic_declination() are
        # defined the same way (positive means that north reference
        # is east of true north), computed at the "from" point - the
        # standard convention for a grid-magnetic angle diagram - so
        # both azimuths subtract from the true azimuth the same way.
        grid_azimuth = (
            true_azimuth - grid_convergence(from_lat, from_lon)
        ) % 360.0

        magnetic_azimuth = (
            true_azimuth - magnetic_declination(from_lat, from_lon)
        ) % 360.0

        self.table.insertRow(
            0
        )

        for column, value in enumerate(
            (
                _format_lonlat(self.from_lonlat, self.converter),
                _format_lonlat(self.to_lonlat, self.converter),
                _format_azimuth(true_azimuth),
                _format_azimuth(grid_azimuth),
                _format_azimuth(magnetic_azimuth),
                f"{distance_m:.0f} m",
            )
        ):

            self.table.setItem(
                0,
                column,
                QTableWidgetItem(value)
            )

        # From/To cells are two lines (lat/lon, then MGRS) - grow
        # this row's height to fit both instead of clipping the
        # second line, which the table's default row height doesn't
        # otherwise accommodate.
        self.table.resizeRowToContents(
            0
        )


class BearingRangeTool(QgsMapTool):

    """
    Left-click twice on the canvas to log the true/grid/magnetic
    azimuth and distance between a "from" and "to" point, showing/
    updating a non-modal BearingRangeDialog as each point is set -
    stays active across repeated pairs, like Line of Sight and the
    Coordinate Probe tool, until another tool is selected.

    Each click also drops a marker on the canvas at that point (from
    = a blue cross, to = a red X), matching Line of Sight's own
    observer/target marker convention. Once both points are set, a
    line with an arrowhead pointing from "from" to "to" is drawn
    between them, so the direction of travel is visible on the map
    itself, not just as a number in the dialog.
    """

    def __init__(self, canvas, iface):

        super().__init__(canvas)

        self.iface = iface

        # Created lazily on the first click, then reused for the life
        # of the tool - same ownership model as
        # CoordinateProbeTool/LineOfSightTool.
        self.dialog = None

        self.from_marker = None
        self.to_marker = None

        # The from-point's own map-CRS click point, kept separately
        # from the dialog's WGS84 from_lonlat - the line/arrowhead
        # are drawn directly in the canvas's own CRS, same as the
        # markers, to avoid a redundant reprojection back out of
        # WGS84 just to draw them.
        self._from_map_point = None

        self.line_rubber_band = None
        self.arrow_rubber_band = None


    def _place_from_marker(self, map_point):

        if self.from_marker is None:

            self.from_marker = QgsVertexMarker(
                self.canvas()
            )

            self.from_marker.setIconType(
                QgsVertexMarker.IconType.ICON_CROSS
            )

            self.from_marker.setColor(
                FROM_MARKER_COLOR
            )

            self.from_marker.setPenWidth(
                MARKER_PEN_WIDTH
            )

            self.from_marker.setIconSize(
                MARKER_ICON_SIZE
            )

        self.from_marker.setCenter(
            map_point
        )


    def _place_to_marker(self, map_point):

        if self.to_marker is None:

            self.to_marker = QgsVertexMarker(
                self.canvas()
            )

            self.to_marker.setIconType(
                QgsVertexMarker.IconType.ICON_X
            )

            self.to_marker.setColor(
                TO_MARKER_COLOR
            )

            self.to_marker.setPenWidth(
                MARKER_PEN_WIDTH
            )

            self.to_marker.setIconSize(
                MARKER_ICON_SIZE
            )

        self.to_marker.setCenter(
            map_point
        )


    def _clear_to_marker(self):

        if self.to_marker is not None:

            self.canvas().scene().removeItem(
                self.to_marker
            )

            self.to_marker = None


    def _clear_from_marker(self):

        if self.from_marker is not None:

            self.canvas().scene().removeItem(
                self.from_marker
            )

            self.from_marker = None


    def _arrowhead_geometry(self, from_point, to_point):

        """
        A small filled triangle at to_point, pointing away from
        from_point - drawn as its own rubber band rather than a
        QgsRubberBand line-end icon, since QgsRubberBand's own
        ICON_* set (cross/X/box/circle/diamond) has no arrowhead
        shape, and doesn't rotate to match a line's direction anyway.
        Returns None if the two points coincide (zero-length line -
        no direction to point in).
        """

        dx = to_point.x() - from_point.x()
        dy = to_point.y() - from_point.y()

        line_length = math.hypot(dx, dy)

        if line_length == 0:
            return None

        units_per_pixel = self.canvas().mapUnitsPerPixel()

        arrow_length = ARROWHEAD_LENGTH_PX * units_per_pixel
        half_width = (ARROWHEAD_WIDTH_PX / 2.0) * units_per_pixel

        # Unit vector along the line, and its perpendicular - the
        # triangle's base sits arrow_length back from the tip, along
        # the line, spanning half_width to either side.
        along_x, along_y = dx / line_length, dy / line_length
        perp_x, perp_y = -along_y, along_x

        base_x = to_point.x() - along_x * arrow_length
        base_y = to_point.y() - along_y * arrow_length

        return QgsGeometry.fromPolygonXY(
            [
                [
                    to_point,
                    QgsPointXY(
                        base_x + perp_x * half_width,
                        base_y + perp_y * half_width
                    ),
                    QgsPointXY(
                        base_x - perp_x * half_width,
                        base_y - perp_y * half_width
                    ),
                    to_point,
                ]
            ]
        )


    def _draw_line(self, from_point, to_point):

        if self.line_rubber_band is None:

            self.line_rubber_band = QgsRubberBand(
                self.canvas(),
                Qgis.GeometryType.Line
            )

            self.line_rubber_band.setColor(
                LINE_COLOR
            )

            self.line_rubber_band.setWidth(
                LINE_WIDTH_PX
            )

        self.line_rubber_band.setToGeometry(
            QgsGeometry.fromPolylineXY(
                [from_point, to_point]
            )
        )

        if self.arrow_rubber_band is None:

            self.arrow_rubber_band = QgsRubberBand(
                self.canvas(),
                Qgis.GeometryType.Polygon
            )

            self.arrow_rubber_band.setColor(
                LINE_COLOR
            )

        arrowhead = self._arrowhead_geometry(
            from_point,
            to_point
        )

        if arrowhead is not None:

            self.arrow_rubber_band.setToGeometry(
                arrowhead
            )


    def _clear_line(self):

        if self.line_rubber_band is not None:

            self.canvas().scene().removeItem(
                self.line_rubber_band
            )

            self.line_rubber_band = None

        if self.arrow_rubber_band is not None:

            self.canvas().scene().removeItem(
                self.arrow_rubber_band
            )

            self.arrow_rubber_band = None


    def _handle_point(self, map_point):

        """
        The from/to state machine, kept separate from
        canvasReleaseEvent's event-handling glue so it's directly
        testable with a plain QgsPointXY - no real mouse event
        needed. map_point is in the canvas's own CRS (used directly
        for the on-canvas marker); converted to WGS84 for the
        dialog/calculation.
        """

        if self.dialog is None:

            self.dialog = BearingRangeDialog(
                self.iface.mainWindow()
            )

        starting_new_pair = (
            self.dialog.from_lonlat is None
            or self.dialog.to_lonlat is not None
        )

        if starting_new_pair:

            self._place_from_marker(
                map_point
            )

            self._clear_to_marker()
            self._clear_line()

            self._from_map_point = map_point

            self.dialog.set_from(
                project_to_wgs84(map_point)
            )

        else:

            self._place_to_marker(
                map_point
            )

            self._draw_line(
                self._from_map_point,
                map_point
            )

            self.dialog.set_to(
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
        Clear both markers and the connecting line when another
        tool is selected, rather than leaving them stuck on the
        canvas indefinitely.
        """

        self._clear_from_marker()
        self._clear_to_marker()
        self._clear_line()

        super().deactivate()
