# -*- coding: utf-8 -*-

"""
Qt UI for generating Tanaka contours - picks a DEM plus the
illumination/styling parameters, then hands off to
tanaka_contours.generate_tanaka_contours() for the DEM's own full
extent.

Military Cartography Tools
"""

from qgis.core import QgsMapLayerProxyModel, QgsProject
from qgis.gui import QgsMapLayerComboBox

from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QDoubleSpinBox,
    QDialogButtonBox,
)

from ..core._layer_utils import add_layer_at_default_position, replace_named_layer
from .hypsometric_tint import OUTPUT_LAYER_NAME as HYPSOMETRIC_TINT_LAYER_NAME
from .tanaka_contours import (
    generate_tanaka_contours,
    default_insert_position,
    DEFAULT_INTERVAL,
    DEFAULT_SEGMENT_LENGTH,
    DEFAULT_LIGHT_AZIMUTH,
    DEFAULT_MIN_WIDTH_MM,
    DEFAULT_MAX_WIDTH_MM,
    DEFAULT_STYLE_MODE,
    OUTPUT_LAYER_NAME,
    STYLE_ELEVATION_COLOR,
    STYLE_ILLUMINATED_OVERLAY,
    STYLE_MONOCHROME,
)


class TanakaContourDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle(
            "Tanaka Contours"
        )

        self.dem_combo = QgsMapLayerComboBox()

        self.dem_combo.setFilters(
            QgsMapLayerProxyModel.Filter.RasterLayer
        )

        self.interval_spin = QDoubleSpinBox()

        self.interval_spin.setRange(
            0.1,
            10000.0
        )

        self.interval_spin.setSuffix(
            " m"
        )

        self.interval_spin.setValue(
            DEFAULT_INTERVAL
        )

        self.segment_length_spin = QDoubleSpinBox()

        self.segment_length_spin.setRange(
            1.0,
            100000.0
        )

        self.segment_length_spin.setSuffix(
            " m"
        )

        self.segment_length_spin.setValue(
            DEFAULT_SEGMENT_LENGTH
        )

        self.azimuth_spin = QDoubleSpinBox()

        self.azimuth_spin.setRange(
            0.0,
            360.0
        )

        self.azimuth_spin.setSuffix(
            "°"
        )

        self.azimuth_spin.setValue(
            DEFAULT_LIGHT_AZIMUTH
        )

        self.min_width_spin = QDoubleSpinBox()

        self.min_width_spin.setRange(
            0.01,
            10.0
        )

        self.min_width_spin.setSingleStep(
            0.05
        )

        self.min_width_spin.setSuffix(
            " mm"
        )

        self.min_width_spin.setValue(
            DEFAULT_MIN_WIDTH_MM
        )

        self.max_width_spin = QDoubleSpinBox()

        self.max_width_spin.setRange(
            0.01,
            10.0
        )

        self.max_width_spin.setSingleStep(
            0.05
        )

        self.max_width_spin.setSuffix(
            " mm"
        )

        self.max_width_spin.setValue(
            DEFAULT_MAX_WIDTH_MM
        )

        self.style_mode_combo = QComboBox()

        self.style_mode_combo.addItem(
            "Elevation colour",
            STYLE_ELEVATION_COLOR
        )

        self.style_mode_combo.addItem(
            "Monochrome (grayscale by illumination)",
            STYLE_MONOCHROME
        )

        self.style_mode_combo.addItem(
            "Illuminated overlay (use with Hypsometric Tint)",
            STYLE_ILLUMINATED_OVERLAY
        )

        self.style_mode_combo.setCurrentIndex(
            self.style_mode_combo.findData(DEFAULT_STYLE_MODE)
        )

        self.new_layer_checkbox = QCheckBox(
            "Add as new layer (keep the existing one)"
        )

        self.new_layer_checkbox.setChecked(
            False
        )

        form = QFormLayout()

        form.addRow("DEM layer", self.dem_combo)
        form.addRow("Contour interval", self.interval_spin)
        form.addRow("Segment length", self.segment_length_spin)
        form.addRow("Light azimuth", self.azimuth_spin)
        form.addRow("Min line width (perpendicular to light)", self.min_width_spin)
        form.addRow("Max line width (facing toward/away from light)", self.max_width_spin)
        form.addRow("Style", self.style_mode_combo)
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
            "interval": self.interval_spin.value(),
            "segment_length": self.segment_length_spin.value(),
            "light_azimuth_deg": self.azimuth_spin.value(),
            "min_width_mm": self.min_width_spin.value(),
            "max_width_mm": self.max_width_spin.value(),
            "style_mode": self.style_mode_combo.currentData(),
            "add_as_new_layer": self.new_layer_checkbox.isChecked(),
        }


def generate_from_dialog_values(iface, values):

    """
    The accept-flow logic that runs once a TanakaContourDialog has
    been filled in and accepted - split out from
    show_tanaka_contour_dialog() so it's testable without driving an
    actual modal QDialog. Returns the new layer, or None if no DEM
    layer was picked.
    """

    if values["dem_layer"] is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "No raster (DEM) layer available to generate contours from."
        )

        return None

    if (
        values["style_mode"] == STYLE_ILLUMINATED_OVERLAY
        and not QgsProject.instance().mapLayersByName(HYPSOMETRIC_TINT_LAYER_NAME)
    ):

        # Non-blocking - the layer is still useful (e.g. Hypsometric
        # Tint might get added afterwards), this mode just needs it
        # to actually look like anything other than near-invisible
        # white/near-black lines against a blank canvas.
        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "Illuminated overlay mode is meant to be used together with "
            "a Hypsometric Tint layer - without one, lit segments will "
            "look nearly invisible."
        )

    dem_layer = values["dem_layer"]

    def generate():

        return generate_tanaka_contours(
            dem_layer,
            dem_layer.extent(),
            dem_layer.crs(),
            interval=values["interval"],
            segment_length=values["segment_length"],
            light_azimuth_deg=values["light_azimuth_deg"],
            min_width_mm=values["min_width_mm"],
            max_width_mm=values["max_width_mm"],
            style_mode=values["style_mode"]
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


def show_tanaka_contour_dialog(iface):

    """
    Prompt for a DEM and illumination/styling parameters, then
    generate the Tanaka contour layer for the DEM's own full extent
    if accepted. Returns the new layer, or None if the dialog was
    cancelled or no DEM layer was available to pick.
    """

    dialog = TanakaContourDialog(
        iface.mainWindow()
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    return generate_from_dialog_values(
        iface,
        dialog.values()
    )
