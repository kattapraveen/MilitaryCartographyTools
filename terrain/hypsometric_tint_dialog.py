# -*- coding: utf-8 -*-

"""
Qt UI for generating a hypsometric tint layer - picks a DEM plus
opacity, then hands off to
hypsometric_tint.generate_hypsometric_tint() for the DEM's own full
extent.

Military Cartography Tools
"""

from qgis.core import QgsMapLayerProxyModel, QgsProject
from qgis.gui import QgsMapLayerComboBox

from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QSpinBox,
    QDialogButtonBox,
)

from ..core._layer_utils import add_layer_at_default_position, replace_named_layer
from .hypsometric_tint import (
    generate_hypsometric_tint,
    default_insert_position,
    OUTPUT_LAYER_NAME,
)


class HypsometricTintDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle(
            "Hypsometric Tint"
        )

        self.dem_combo = QgsMapLayerComboBox()

        self.dem_combo.setFilters(
            QgsMapLayerProxyModel.Filter.RasterLayer
        )

        self.opacity_spin = QSpinBox()

        self.opacity_spin.setRange(
            0,
            100
        )

        self.opacity_spin.setSuffix(
            "%"
        )

        self.opacity_spin.setValue(
            100
        )

        self.new_layer_checkbox = QCheckBox(
            "Add as new layer (keep the existing one)"
        )

        self.new_layer_checkbox.setChecked(
            False
        )

        form = QFormLayout()

        form.addRow("DEM layer", self.dem_combo)
        form.addRow("Opacity", self.opacity_spin)
        form.addRow(self.new_layer_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(
            self.accept
        )

        buttons.rejected.connect(
            self.reject
        )

        outer = QVBoxLayout()

        outer.addLayout(form)
        outer.addWidget(buttons)

        self.setLayout(
            outer
        )


    def values(self):

        return {
            "dem_layer": self.dem_combo.currentLayer(),
            "opacity": self.opacity_spin.value() / 100.0,
            "add_as_new_layer": self.new_layer_checkbox.isChecked(),
        }


def generate_from_dialog_values(iface, values):

    """
    The accept-flow logic that runs once a HypsometricTintDialog has
    been filled in and accepted - split out from
    show_hypsometric_tint_dialog() so it's testable without driving
    an actual modal QDialog. Returns the new layer, or None if no DEM
    layer was picked.
    """

    if values["dem_layer"] is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "No raster (DEM) layer available to generate a hypsometric tint from."
        )

        return None

    dem_layer = values["dem_layer"]

    def generate():

        return generate_hypsometric_tint(
            dem_layer,
            dem_layer.extent(),
            dem_layer.crs(),
            opacity=values["opacity"]
        )

    if values["add_as_new_layer"]:

        new_layer = generate()

        if new_layer is None:
            return None

        return add_layer_at_default_position(
            QgsProject.instance(),
            new_layer,
            default_insert_position
        )

    # Default behaviour: correct the existing layer in place rather
    # than piling up a new one on every re-run with tweaked settings,
    # preserving wherever the user has since dragged it in the Layers
    # panel. Only replaces layers by this exact name, so a layer the
    # user has since renamed is left alone.
    return replace_named_layer(
        OUTPUT_LAYER_NAME,
        generate,
        default_insert_position
    )


def show_hypsometric_tint_dialog(iface):

    """
    Prompt for a DEM and opacity, then generate the hypsometric tint
    layer for the DEM's own full extent if accepted. Returns the new
    layer, or None if the dialog was cancelled or no DEM layer was
    available to pick.
    """

    dialog = HypsometricTintDialog(
        iface.mainWindow()
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    return generate_from_dialog_values(
        iface,
        dialog.values()
    )
