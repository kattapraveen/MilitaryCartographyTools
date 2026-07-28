# -*- coding: utf-8 -*-

"""
Interactive map tool: click anywhere on the canvas to read off
that point's coordinates in both latitude/longitude and MGRS -
a quick "what's this grid reference" lookup, the inverse of typing
a known reference into an expression. Every click adds a row to a
persistent, non-modal log window (CoordinateProbeDialog); the
clipboard always holds the most recent click's MGRS string.

Military Cartography Tools
"""

from qgis.gui import QgsMapTool
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QAbstractItemView,
    QHeaderView
)

from . import MGRSConverter
from .coordinate_utils import project_to_wgs84


# Full 1-metre MGRS precision - matches the plugin's other
# full-precision MGRS output (mct_mgrs's own default).
MGRS_PRECISION = 5

LAT_LON_DECIMALS = 6

COLUMN_LABELS = ["Latitude", "Longitude", "MGRS"]
MGRS_COLUMN = 2


class CoordinateProbeDialog(QDialog):

    """
    Non-modal log of every point clicked with the coordinate probe
    tool active, newest first - stays open and keeps accumulating
    rows across clicks (and across the tool being switched away
    from and back to), rather than reopening fresh each time.
    Double-clicking a row re-copies that row's MGRS to the
    clipboard, so an earlier reading isn't lost once a later click
    overwrites the clipboard's usual "most recent" contents.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle(
            "Coordinate Probe"
        )

        self.resize(
            420,
            300
        )

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
            MGRS_COLUMN,
            QHeaderView.ResizeMode.Stretch
        )

        self.table.cellDoubleClicked.connect(
            self._copy_row_mgrs
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

        outer.addWidget(self.table)
        outer.addLayout(button_row)

        self.setLayout(
            outer
        )


    def add_entry(self, lat, lon, mgrs):

        """
        Add a new row for a click, newest at the top.
        """

        self.table.insertRow(
            0
        )

        for column, value in enumerate(
            (
                f"{lat:.{LAT_LON_DECIMALS}f}",
                f"{lon:.{LAT_LON_DECIMALS}f}",
                mgrs
            )
        ):

            self.table.setItem(
                0,
                column,
                QTableWidgetItem(value)
            )


    def _copy_row_mgrs(self, row, _column):

        item = self.table.item(
            row,
            MGRS_COLUMN
        )

        if item is not None:

            QApplication.clipboard().setText(
                item.text()
            )


class CoordinateProbeTool(QgsMapTool):

    """
    Left-click anywhere on the canvas to log that point's lat/lon
    and MGRS coordinates in a persistent CoordinateProbeDialog, and
    copy the MGRS string to the clipboard. Stays active across
    multiple clicks, like QGIS's own Identify/Measure tools, until
    another tool is selected.
    """

    def __init__(self, canvas, iface):

        super().__init__(canvas)

        self.iface = iface

        self.converter = MGRSConverter(
            precision=MGRS_PRECISION
        )

        # Created lazily on the first click, then reused for the
        # life of the tool - closing the window only hides it
        # (QDialog's default close behaviour), so its accumulated
        # rows survive being closed and reopened.
        self.dialog = None


    def canvasReleaseEvent(self, event):

        if event.button() != Qt.MouseButton.LeftButton:
            return

        point = project_to_wgs84(
            event.mapPoint()
        )

        lat = point.y()
        lon = point.x()

        mgrs = self.converter.format(
            self.converter.convert(lat, lon)
        )

        QApplication.clipboard().setText(
            mgrs
        )

        if self.dialog is None:

            self.dialog = CoordinateProbeDialog(
                self.iface.mainWindow()
            )

        self.dialog.add_entry(
            lat,
            lon,
            mgrs
        )

        self.dialog.show()

        self.dialog.raise_()
