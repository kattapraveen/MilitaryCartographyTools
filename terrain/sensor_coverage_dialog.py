# -*- coding: utf-8 -*-

"""
Qt UI for multi-sensor coverage - picks the one global DEM and which of
the three level layers a project needs, then creates any that are
missing and wires them for live regeneration.

Unlike the other terrain/ dialogs, this one does not generate anything
by itself: it sets a laydown up, and the coverage is then produced (and
reproduced) by SensorCoverageManager whenever the user commits an edit
to a sensor points layer. So it is a one-shot setup dialog, not a
non-modal control panel like ViewshedDialog.

Military Cartography Tools
"""

from qgis.core import QgsMapLayerProxyModel, QgsProject
from qgis.gui import QgsMapLayerComboBox

from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from ..core._layer_utils import add_layer_at_default_position
from .sensor_coverage import (
    apply_points_style,
    build_sensor_points_layer,
    points_layer_name,
    SENSOR_LEVELS,
    set_dem_layer,
)


def _existing_points_layer(level):

    existing = QgsProject.instance().mapLayersByName(
        points_layer_name(level)
    )

    return existing[0] if existing else None


EXPLANATION = (
    "Each level gets its own sensor points layer. Digitize a sensor on "
    "it and set that sensor's own height, detection height and maximum "
    "range in the form.\n\n"
    "There is no Generate button: coverage is drawn when you SAVE the "
    "points layer's edits, and redrawn on every later save. Placing or "
    "moving a sensor on its own will not update it - saving is what "
    "recomputes, deliberately, since each sensor is a full viewshed "
    "run and doing that mid-drag would make dragging unusable.\n\n"
    "Overlapping coverage merges into one perimeter, but only between "
    "sensors of the same MIL-STD-2525 affiliation, which each sensor "
    "carries itself and which decides its colour. Give a sensor a "
    "unique designation and it is labelled just outside its own stretch "
    "of the perimeter. Detection height is measured from the antenna, "
    "so siting a sensor higher raises the whole band it covers."
)


def _points_layer_exists(level):

    return _existing_points_layer(level) is not None


class SensorCoverageDialog(QDialog):

    def __init__(self, iface, manager, parent=None):

        super().__init__(parent)

        self.iface = iface
        self.manager = manager

        self.setWindowTitle(
            "Sensor Coverage"
        )

        explanation = QLabel(EXPLANATION)
        explanation.setWordWrap(True)

        self.dem_combo = QgsMapLayerComboBox()

        self.dem_combo.setFilters(
            QgsMapLayerProxyModel.Filter.RasterLayer
        )

        # One checkbox per level, already ticked (and disabled) for a
        # level whose layer this project has: the box means "this
        # project has a layer for this band", so an existing one is not
        # something the dialog can offer to un-create.
        self.level_checkboxes = {}

        form = QFormLayout()

        form.addRow("DEM layer", self.dem_combo)

        for level in SENSOR_LEVELS:

            checkbox = QCheckBox(level.label)

            existing = _existing_points_layer(level)

            if existing is not None:

                checkbox.setChecked(True)
                checkbox.setEnabled(False)
                checkbox.setToolTip(
                    "This project already has a sensor points layer for "
                    "this level."
                )

            self.level_checkboxes[level.key] = checkbox

            form.addRow(checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        outer = QVBoxLayout()

        outer.addWidget(explanation)
        outer.addLayout(form)
        outer.addWidget(buttons)

        self.setLayout(outer)


    def selected_level_keys(self):

        return [
            key
            for key, checkbox in self.level_checkboxes.items()
            if checkbox.isChecked()
        ]


    def accept(self):

        apply_dialog_values(
            self.iface,
            self.manager,
            self.dem_combo.currentLayer(),
            self.selected_level_keys()
        )

        super().accept()


def apply_dialog_values(iface, manager, dem_layer, selected_level_keys):

    """
    Create whichever selected level layers this project doesn't have
    yet, point every sensor points layer at `dem_layer`, and wire them
    all for live regeneration. Split out of SensorCoverageDialog so
    it's testable without driving an actual QDialog, matching the other
    terrain/ dialogs' own generate_from_dialog_values() convention.

    Affiliation is deliberately NOT set here - it is a per-SENSOR field
    on the points layer, so it belongs in the attribute form, not in a
    dialog that can only speak for a whole level at once.

    Returns the sensor points layers now set up, newest first - or an
    empty list if there was no DEM to work against.
    """

    if dem_layer is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "No raster (DEM) layer available to compute sensor coverage "
            "against."
        )

        return []

    project = QgsProject.instance()

    layers = []

    for level in SENSOR_LEVELS:

        if level.key not in selected_level_keys:
            continue

        existing = project.mapLayersByName(
            points_layer_name(level)
        )

        if existing:

            points_layer = existing[0]

        else:

            points_layer = add_layer_at_default_position(
                project,
                build_sensor_points_layer(level),
                _default_points_insert_position
            )

        # The DEM is global to the laydown, so it is (re)applied to
        # every selected layer, not only the ones just created - this
        # is also how a user repoints an existing laydown at a
        # different DEM.
        set_dem_layer(points_layer, dem_layer)

        # Restyled even for an existing layer, so a project made before
        # the marker became affiliation-driven picks the new symbol up
        # on the next visit to this dialog.
        apply_points_style(points_layer, level)

        manager.wire(points_layer, level)

        layers.append(points_layer)

    return layers


def _default_points_insert_position(project, layer):

    """
    Top of the tree - the sensor points sit above their own coverage
    polygon (inserted at the top in its turn, but only once coverage
    exists), so the markers stay clickable rather than being buried
    under the shape they generate.
    """

    project.layerTreeRoot().insertLayer(
        0,
        layer
    )
