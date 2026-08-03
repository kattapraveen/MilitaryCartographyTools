# -*- coding: utf-8 -*-

"""
Qt UI for generating Tanaka contours - picks a DEM plus the
illumination/styling parameters, then hands off to
tanaka_contours.generate_tanaka_contours() for the current map
canvas extent.

Military Cartography Tools
"""

from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox, QgsColorButton

from qgis.PyQt.QtWidgets import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QDoubleSpinBox,
    QDialogButtonBox,
)

from .tanaka_contours import (
    generate_tanaka_contours,
    DEFAULT_INTERVAL,
    DEFAULT_SEGMENT_LENGTH,
    DEFAULT_LIGHT_AZIMUTH,
    DEFAULT_MIN_WIDTH_MM,
    DEFAULT_MAX_WIDTH_MM,
    DEFAULT_LIT_COLOR,
    DEFAULT_SHADOW_COLOR,
)

from qgis.PyQt.QtGui import QColor


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

        self.lit_color_button = QgsColorButton()

        self.lit_color_button.setColor(
            QColor(DEFAULT_LIT_COLOR)
        )

        self.shadow_color_button = QgsColorButton()

        self.shadow_color_button.setColor(
            QColor(DEFAULT_SHADOW_COLOR)
        )

        form = QFormLayout()

        form.addRow("DEM layer", self.dem_combo)
        form.addRow("Contour interval", self.interval_spin)
        form.addRow("Segment length", self.segment_length_spin)
        form.addRow("Light azimuth", self.azimuth_spin)
        form.addRow("Min line width (lit)", self.min_width_spin)
        form.addRow("Max line width (shadow)", self.max_width_spin)
        form.addRow("Lit color", self.lit_color_button)
        form.addRow("Shadow color", self.shadow_color_button)

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
            "lit_color": self.lit_color_button.color(),
            "shadow_color": self.shadow_color_button.color(),
        }


def show_tanaka_contour_dialog(iface):

    """
    Prompt for a DEM and illumination/styling parameters, then
    generate the Tanaka contour layer for the current map canvas
    extent if accepted. Returns the new layer, or None if the
    dialog was cancelled or no DEM layer was available to pick.
    """

    dialog = TanakaContourDialog(
        iface.mainWindow()
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    values = dialog.values()

    if values["dem_layer"] is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "No raster (DEM) layer available to generate contours from."
        )

        return None

    canvas = iface.mapCanvas()

    return generate_tanaka_contours(
        values["dem_layer"],
        canvas.extent(),
        canvas.mapSettings().destinationCrs(),
        interval=values["interval"],
        segment_length=values["segment_length"],
        light_azimuth_deg=values["light_azimuth_deg"],
        min_width_mm=values["min_width_mm"],
        max_width_mm=values["max_width_mm"],
        lit_color=values["lit_color"],
        shadow_color=values["shadow_color"]
    )
