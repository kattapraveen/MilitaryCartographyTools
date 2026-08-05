# -*- coding: utf-8 -*-

"""
Qt UI for the Line of Sight tool - a small non-modal dialog that the
map tool (line_of_sight_tool.py) fills in as the observer/target
points are clicked, showing each point's coordinates plus an editable
height field, then hands off to line_of_sight.generate_line_of_sight().

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
    QVBoxLayout,
)

from ..core._layer_utils import add_layer_at_default_position, replace_named_layer
from .line_of_sight import (
    generate_line_of_sight,
    default_insert_position,
    DEFAULT_OBSERVER_HEIGHT_M,
    DEFAULT_TARGET_HEIGHT_M,
    OUTPUT_LAYER_NAME,
)


NO_POINT_TEXT = "-"

# Matches CoordinateProbeDialog's own lat/lon display precision, for
# consistency between the two coordinate-showing dialogs.
LAT_LON_DECIMALS = 6

MAX_HEIGHT_M = 9999.0


def _format_lonlat(lonlat):

    return f"{lonlat.y():.{LAT_LON_DECIMALS}f}, {lonlat.x():.{LAT_LON_DECIMALS}f}"


class LineOfSightDialog(QDialog):

    def __init__(self, iface, parent=None):

        super().__init__(parent)

        self.iface = iface

        self.observer_lonlat = None
        self.target_lonlat = None

        self.setWindowTitle(
            "Line of Sight"
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

        self.target_label = QLabel(
            NO_POINT_TEXT
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

        self.new_layer_checkbox = QCheckBox(
            "Add as new layer (keep the existing one)"
        )

        self.new_layer_checkbox.setChecked(
            False
        )

        self.result_label = QLabel(
            NO_POINT_TEXT
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
        form.addRow("Target", self.target_label)
        form.addRow("Target height", self.target_height_spin)
        form.addRow(self.new_layer_checkbox)
        form.addRow("Result", self.result_label)

        outer = QVBoxLayout()

        outer.addLayout(form)
        outer.addWidget(self.generate_button)

        self.setLayout(
            outer
        )


    def set_observer(self, lonlat):

        """
        Called by LineOfSightTool on the first click of a new pair -
        also clears any previous target, since a new observer starts
        a fresh check.
        """

        self.observer_lonlat = lonlat
        self.observer_label.setText(
            _format_lonlat(lonlat)
        )

        self.target_lonlat = None
        self.target_label.setText(
            NO_POINT_TEXT
        )

        self.result_label.setText(
            NO_POINT_TEXT
        )

        self._update_generate_enabled()


    def set_target(self, lonlat):

        """
        Called by LineOfSightTool on the second click of a pair -
        triggers an immediate first run with the current height
        values (adjustable afterwards via the Generate button).
        """

        self.target_lonlat = lonlat
        self.target_label.setText(
            _format_lonlat(lonlat)
        )

        self._update_generate_enabled()

        self._on_generate_clicked()


    def _update_generate_enabled(self):

        self.generate_button.setEnabled(
            self.observer_lonlat is not None
            and self.target_lonlat is not None
        )


    def values(self):

        return {
            "dem_layer": self.dem_combo.currentLayer(),
            "observer_lonlat": self.observer_lonlat,
            "observer_height": self.observer_height_spin.value(),
            "target_lonlat": self.target_lonlat,
            "target_height": self.target_height_spin.value(),
            "add_as_new_layer": self.new_layer_checkbox.isChecked(),
        }


    def _on_generate_clicked(self):

        layer = generate_from_dialog_values(
            self.iface,
            self.values()
        )

        if layer is None:
            return

        total_distance, blocked_at_distance = _describe_result(
            layer
        )

        if blocked_at_distance is None:

            self.result_label.setText(
                f"{total_distance:.0f} m - visible"
            )

        else:

            self.result_label.setText(
                f"{total_distance:.0f} m - blocked ~{blocked_at_distance:.0f} m away"
            )


def _describe_result(layer):

    """
    (total_distance_m, blocked_at_distance_m_or_None) read back from a
    generated Line of Sight layer's own DIST/VISIBLE fields. Total
    distance sums every segment's own geometry length rather than
    re-deriving it from the original observer/target points - each
    segment is a straight subdivision of the same overall line, so the
    sum is exact.
    """

    total_distance = sum(
        feature.geometry().length()
        for feature in layer.getFeatures()
    )

    blocked_feature = next(
        (
            feature
            for feature in layer.getFeatures()
            if not feature["VISIBLE"]
        ),
        None
    )

    blocked_at_distance = (
        blocked_feature["DIST"] if blocked_feature is not None else None
    )

    return total_distance, blocked_at_distance


def generate_from_dialog_values(iface, values):

    """
    The generate-flow logic driven by LineOfSightDialog's Generate
    button (and its own auto-run on a second click) - split out so
    it's testable without driving an actual QDialog. Returns the new
    layer, or None if no DEM/points were available, or if a point
    fell outside the DEM.
    """

    if values["dem_layer"] is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "No raster (DEM) layer available to check line of sight against."
        )

        return None

    if values["observer_lonlat"] is None or values["target_lonlat"] is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "Click two points on the map to set the observer and target first."
        )

        return None

    def generate():

        return generate_line_of_sight(
            values["dem_layer"],
            values["observer_lonlat"],
            values["observer_height"],
            values["target_lonlat"],
            values["target_height"]
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
        # rather than piling up a new one on every re-run with
        # tweaked heights, preserving wherever the user has since
        # dragged it in the Layers panel.
        layer = replace_named_layer(
            OUTPUT_LAYER_NAME,
            generate,
            default_insert_position
        )

    if layer is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "Observer or target point falls outside the DEM's coverage."
        )

        return None

    # No message bar push for the visible/blocked result itself - the
    # dialog's own Result label (kept in sync by _on_generate_clicked,
    # via the same _describe_result() this would otherwise duplicate)
    # already shows it persistently, right where the user is already
    # looking. The message bar above is reserved for cases with no
    # other feedback path (no DEM, no points, point outside the DEM).
    return layer
