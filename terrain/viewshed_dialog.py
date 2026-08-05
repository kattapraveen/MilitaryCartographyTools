# -*- coding: utf-8 -*-

"""
Qt UI for the Viewshed tool - a small non-modal dialog that the map
tool (viewshed_tool.py) fills in as the observer point is clicked,
showing its coordinates plus editable height/max-distance/opacity
fields, then hands off to viewshed.generate_viewshed().

Military Cartography Tools
"""

from qgis.core import QgsMapLayerProxyModel, QgsProject
from qgis.gui import QgsMapLayerComboBox

from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..core._layer_utils import add_layer_at_default_position, replace_named_layer
from .line_of_sight import DEFAULT_OBSERVER_HEIGHT_M, DEFAULT_TARGET_HEIGHT_M
from .viewshed import (
    generate_viewshed,
    default_insert_position,
    DEFAULT_MAX_DISTANCE_M,
    OUTPUT_LAYER_NAME,
)


NO_POINT_TEXT = "-"

# Matches LineOfSightDialog's/CoordinateProbeDialog's own lat/lon
# display precision, for consistency between all three
# coordinate-showing dialogs.
LAT_LON_DECIMALS = 6

MAX_HEIGHT_M = 9999.0

MIN_DISTANCE_M = 50.0
MAX_DISTANCE_M = 50000.0


def _format_lonlat(lonlat):

    return f"{lonlat.y():.{LAT_LON_DECIMALS}f}, {lonlat.x():.{LAT_LON_DECIMALS}f}"


class ViewshedDialog(QDialog):

    def __init__(self, iface, parent=None):

        super().__init__(parent)

        self.iface = iface

        self.observer_lonlat = None

        self.setWindowTitle(
            "Viewshed"
        )

        self.dem_combo = QgsMapLayerComboBox()

        self.dem_combo.setFilters(
            QgsMapLayerProxyModel.Filter.RasterLayer
        )

        self.observer_label = QLabel(
            NO_POINT_TEXT
        )

        self.observer_height_spin = QDoubleSpinBox()

        self.observer_height_spin.setRange(
            0.0,
            MAX_HEIGHT_M
        )

        self.observer_height_spin.setSuffix(
            " m"
        )

        self.observer_height_spin.setValue(
            DEFAULT_OBSERVER_HEIGHT_M
        )

        self.target_height_spin = QDoubleSpinBox()

        self.target_height_spin.setRange(
            0.0,
            MAX_HEIGHT_M
        )

        self.target_height_spin.setSuffix(
            " m"
        )

        self.target_height_spin.setValue(
            DEFAULT_TARGET_HEIGHT_M
        )

        self.max_distance_spin = QDoubleSpinBox()

        self.max_distance_spin.setRange(
            MIN_DISTANCE_M,
            MAX_DISTANCE_M
        )

        self.max_distance_spin.setSuffix(
            " m"
        )

        self.max_distance_spin.setValue(
            DEFAULT_MAX_DISTANCE_M
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
            65
        )

        self.new_layer_checkbox = QCheckBox(
            "Add as new layer (keep the existing one)"
        )

        self.new_layer_checkbox.setChecked(
            False
        )

        self.generate_button = QPushButton(
            "Generate"
        )

        self.generate_button.setEnabled(
            False
        )

        self.generate_button.clicked.connect(
            self._on_generate_clicked
        )

        form = QFormLayout()

        form.addRow("DEM layer", self.dem_combo)
        form.addRow("Observer", self.observer_label)
        form.addRow("Observer height", self.observer_height_spin)
        form.addRow("Target height", self.target_height_spin)
        form.addRow("Max distance", self.max_distance_spin)
        form.addRow("Opacity", self.opacity_spin)
        form.addRow(self.new_layer_checkbox)

        outer = QVBoxLayout()

        outer.addLayout(form)
        outer.addWidget(self.generate_button)

        self.setLayout(
            outer
        )


    def set_observer(self, lonlat):

        """
        Called by ViewshedTool on every click - unlike Line of Sight's
        observer/target pair, every click here is a fresh, complete
        analysis on its own, so there's no pair state to track. Also
        triggers an immediate run with the current height/distance
        values (adjustable afterwards via the Generate button).
        """

        self.observer_lonlat = lonlat

        self.observer_label.setText(
            _format_lonlat(lonlat)
        )

        self.generate_button.setEnabled(
            True
        )

        self._on_generate_clicked()


    def values(self):

        return {
            "dem_layer": self.dem_combo.currentLayer(),
            "observer_lonlat": self.observer_lonlat,
            "observer_height": self.observer_height_spin.value(),
            "target_height": self.target_height_spin.value(),
            "max_distance": self.max_distance_spin.value(),
            "opacity": self.opacity_spin.value() / 100.0,
            "add_as_new_layer": self.new_layer_checkbox.isChecked(),
        }


    def _on_generate_clicked(self):

        generate_from_dialog_values(
            self.iface,
            self.values()
        )


def generate_from_dialog_values(iface, values):

    """
    The generate-flow logic driven by ViewshedDialog's Generate button
    (and its own auto-run on each click) - split out so it's testable
    without driving an actual QDialog. Returns the new layer, or None
    if no DEM/observer point was available, or if the point fell
    outside the DEM.
    """

    if values["dem_layer"] is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "No raster (DEM) layer available to generate a viewshed against."
        )

        return None

    if values["observer_lonlat"] is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "Click a point on the map to set the observer first."
        )

        return None

    def generate():

        return generate_viewshed(
            values["dem_layer"],
            values["observer_lonlat"],
            values["observer_height"],
            values["target_height"],
            values["max_distance"],
            opacity=values["opacity"]
        )

    if values["add_as_new_layer"]:

        layer = generate()

        if layer is not None:

            layer = add_layer_at_default_position(
                QgsProject.instance(),
                layer,
                default_insert_position
            )

    else:
        # Default behaviour: correct the existing layer in place
        # rather than piling up a new one on every re-run/re-click,
        # preserving wherever the user has since dragged it in the
        # Layers panel.
        layer = replace_named_layer(
            OUTPUT_LAYER_NAME,
            generate,
            default_insert_position
        )

    if layer is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "Observer point falls outside the DEM's coverage."
        )

        return None

    return layer
