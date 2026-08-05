# -*- coding: utf-8 -*-

"""
Qt UI for GPX/KML waypoint import/export - two small, independent
dialogs (not a combined import/export tab set - each is a single,
focused one-shot action, matching the rest of this plugin's one-
button-one-dialog convention, e.g. New Military Layout).

Military Cartography Tools
"""

from pathlib import Path

from qgis.core import QgsMapLayerProxyModel, QgsProject
from qgis.gui import QgsMapLayerComboBox

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ..core._layer_utils import add_layer_at_default_position
from .gpx_kml_io import default_insert_position, export_waypoints, import_waypoints


GPX_KML_FILE_FILTER = "GPX/KML files (*.gpx *.kml);;GPX files (*.gpx);;KML files (*.kml)"


def _file_picker_row(line_edit, browse_callback):

    browse_button = QPushButton(
        "Browse..."
    )

    browse_button.clicked.connect(
        browse_callback
    )

    row = QHBoxLayout()

    row.addWidget(line_edit)
    row.addWidget(browse_button)

    return row


class ImportWaypointsDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle(
            "Import Waypoints (GPX/KML)"
        )

        self.path_edit = QLineEdit()

        self.path_edit.setReadOnly(
            True
        )

        form = QFormLayout()

        form.addRow(
            "File",
            _file_picker_row(self.path_edit, self._browse)
        )

        self.import_button = QPushButton(
            "Import"
        )

        self.import_button.setEnabled(
            False
        )

        self.import_button.clicked.connect(
            self.accept
        )

        outer = QVBoxLayout()

        outer.addLayout(form)
        outer.addWidget(self.import_button)

        self.setLayout(
            outer
        )


    def _browse(self):

        path, _filter = QFileDialog.getOpenFileName(
            self,
            "Import Waypoints",
            "",
            GPX_KML_FILE_FILTER
        )

        if path:

            self.path_edit.setText(
                path
            )

            self.import_button.setEnabled(
                True
            )


    def values(self):

        return {
            "file_path": self.path_edit.text(),
        }


class ExportWaypointsDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle(
            "Export Waypoints (GPX/KML)"
        )

        self.layer_combo = QgsMapLayerComboBox()

        self.layer_combo.setFilters(
            QgsMapLayerProxyModel.Filter.PointLayer
        )

        self.format_combo = QComboBox()

        self.format_combo.addItems(
            ["GPX", "KML"]
        )

        self.format_combo.currentTextChanged.connect(
            self._update_path_extension
        )

        self.path_edit = QLineEdit()

        self.path_edit.setReadOnly(
            True
        )

        form = QFormLayout()

        form.addRow("Layer", self.layer_combo)
        form.addRow("Format", self.format_combo)
        form.addRow(
            "File",
            _file_picker_row(self.path_edit, self._browse)
        )

        self.export_button = QPushButton(
            "Export"
        )

        self.export_button.setEnabled(
            False
        )

        self.export_button.clicked.connect(
            self.accept
        )

        outer = QVBoxLayout()

        outer.addLayout(form)
        outer.addWidget(self.export_button)

        self.setLayout(
            outer
        )


    def _update_path_extension(self, new_format):

        """
        Swap an already-chosen path's extension to match a changed
        format selection, rather than leaving e.g. "waypoints.gpx"
        on disk after switching the dropdown to KML - the file that
        actually gets written wouldn't match what's shown otherwise.
        """

        current_path = self.path_edit.text()

        if not current_path:
            return

        new_suffix = ".gpx" if new_format == "GPX" else ".kml"

        self.path_edit.setText(
            str(Path(current_path).with_suffix(new_suffix))
        )


    def _browse(self):

        suffix = ".gpx" if self.format_combo.currentText() == "GPX" else ".kml"

        path, _filter = QFileDialog.getSaveFileName(
            self,
            "Export Waypoints",
            f"waypoints{suffix}",
            GPX_KML_FILE_FILTER
        )

        if path:

            self.path_edit.setText(
                str(Path(path).with_suffix(suffix))
            )

            self.export_button.setEnabled(
                True
            )


    def values(self):

        return {
            "source_layer": self.layer_combo.currentLayer(),
            "file_format": self.format_combo.currentText(),
            "file_path": self.path_edit.text(),
        }


def import_from_dialog_values(iface, values):

    """
    The accept-flow logic driven by ImportWaypointsDialog's Import
    button - split out so it's testable without driving an actual
    modal QDialog, matching the rest of this plugin's dialog modules.
    Returns the new layer, or None if the file had no readable
    waypoints.
    """

    file_path = values["file_path"]

    layer = import_waypoints(
        file_path
    )

    if layer is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            f"No readable waypoints found in {file_path}."
        )

        return None

    layer.setName(
        Path(file_path).stem
    )

    return add_layer_at_default_position(
        QgsProject.instance(),
        layer,
        default_insert_position
    )


def export_from_dialog_values(iface, values):

    """
    The accept-flow logic driven by ExportWaypointsDialog's Export
    button - split out so it's testable without driving an actual
    modal QDialog. Returns True on success, False if there was
    nothing to export or the write failed (either way, the message
    bar already explains why).
    """

    if values["source_layer"] is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "Choose a point layer to export first."
        )

        return False

    if not values["file_path"]:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "Choose a destination file first."
        )

        return False

    success, error_message = export_waypoints(
        values["source_layer"],
        values["file_path"],
        values["file_format"]
    )

    if not success:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            f"Failed to export waypoints: {error_message}"
        )

        return False

    iface.messageBar().pushInfo(
        "Military Cartography Tools",
        f"Exported waypoints to {values['file_path']}."
    )

    return True


def show_import_waypoints_dialog(iface):

    dialog = ImportWaypointsDialog(
        iface.mainWindow()
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    return import_from_dialog_values(
        iface,
        dialog.values()
    )


def show_export_waypoints_dialog(iface):

    dialog = ExportWaypointsDialog(
        iface.mainWindow()
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False

    return export_from_dialog_values(
        iface,
        dialog.values()
    )
