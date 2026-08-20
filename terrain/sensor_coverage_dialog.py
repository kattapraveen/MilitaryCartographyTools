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
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..core._layer_utils import add_layer_at_default_position
from .sensor_coverage import (
    affiliation_for,
    AFFILIATION_LABELS,
    apply_points_style,
    build_sensor_points_layer,
    coverage_color_for,
    DEFAULT_AFFILIATION,
    points_layer_name,
    SENSOR_LEVELS,
    set_affiliation,
    set_dem_layer,
)


def _existing_points_layer(level):

    existing = QgsProject.instance().mapLayersByName(
        points_layer_name(level)
    )

    return existing[0] if existing else None


EXPLANATION = (
    "Each level gets its own sensor points layer. Digitize a sensor on "
    "it, set that sensor's own height, detection height and maximum "
    "range in the form, and save your edits - the coverage for that "
    "level is drawn from every sensor on it, with overlapping coverage "
    "merged into one perimeter. Give a sensor a unique designation and "
    "it is labelled just outside its own stretch of that perimeter.\n\n"
    "Detection height is measured from the antenna, so siting a sensor "
    "higher raises the whole band it covers. Colour follows the "
    "MIL-STD-2525 affiliation below, with each band a lighter tint of "
    "it."
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

        # One affiliation dropdown per level, alongside its checkbox.
        # Seeded from whatever that level's points layer already
        # remembers, so reopening the dialog shows the side in use
        # rather than resetting to Friend.
        self.level_affiliations = {}

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

            combo = QComboBox()

            for key, label in AFFILIATION_LABELS.items():

                combo.addItem(label, key)

            current = (
                affiliation_for(existing)
                if existing is not None
                else DEFAULT_AFFILIATION
            )

            combo.setCurrentIndex(
                combo.findData(current)
            )

            combo.setToolTip(
                "Colour follows MIL-STD-2525 affiliation: friend blue, "
                "hostile red, neutral green, unknown yellow. Each band "
                "is drawn as a lighter tint of the same colour."
            )

            self.level_affiliations[level.key] = combo

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(checkbox, 1)
            row.addWidget(combo)

            container = QWidget()
            container.setLayout(row)

            form.addRow(container)

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


    def selected_affiliations(self):

        return {
            key: combo.currentData()
            for key, combo in self.level_affiliations.items()
        }


    def accept(self):

        apply_dialog_values(
            self.iface,
            self.manager,
            self.dem_combo.currentLayer(),
            self.selected_level_keys(),
            self.selected_affiliations()
        )

        super().accept()


def apply_dialog_values(
    iface,
    manager,
    dem_layer,
    selected_level_keys,
    affiliations=None
):

    """
    Create whichever selected level layers this project doesn't have
    yet, point every sensor points layer at `dem_layer`, and wire them
    all for live regeneration. Split out of SensorCoverageDialog so
    it's testable without driving an actual QDialog, matching the other
    terrain/ dialogs' own generate_from_dialog_values() convention.

    `affiliations` is an optional {level key: affiliation key} mapping;
    a level not named in it keeps whatever it already had. Changing one
    restyles the points layer immediately and regenerates that level's
    coverage, so the new colour is visible without waiting for the next
    edit.

    Returns the sensor points layers now set up, newest first - or an
    empty list if there was no DEM to work against.
    """

    affiliations = affiliations or {}

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

        chosen = affiliations.get(level.key)

        changed = (
            chosen is not None
            and chosen != affiliation_for(points_layer)
        )

        if chosen is not None:

            set_affiliation(points_layer, chosen)

        # Restyle unconditionally: a layer just built took the default
        # affiliation's colour, and an existing one may have just been
        # switched to another side.
        apply_points_style(
            points_layer,
            coverage_color_for(points_layer, level)
        )

        manager.wire(points_layer, level)

        if changed:

            # The coverage carries the colour too, and it is only ever
            # rebuilt on an edit - so without this a side change would
            # not show on the footprint until the user happened to move
            # a sensor.
            manager.regenerate(level)

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
