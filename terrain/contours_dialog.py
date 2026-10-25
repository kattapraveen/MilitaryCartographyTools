# -*- coding: utf-8 -*-

"""
Qt UI for generating plain contours - picks a DEM, an extent, the
interval and index spacing, and a colour, then hands off to
contours.generate_contours().

The interval opens at whatever suits the canvas's current scale (see
contours.suggested_interval()), with a button to re-derive it after
zooming. That default is the whole point of the dialog: asking for
20 m contours on a 1:1,000,000 sheet should be a deliberate choice,
not an accident. It is only a default - the spin box accepts
anything.

Military Cartography Tools
"""

from qgis.core import QgsMapLayerProxyModel, QgsProject
from qgis.gui import QgsColorButton, QgsExtentGroupBox, QgsMapLayerComboBox

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..core._layer_utils import add_layer_at_default_position, replace_named_layer
from .contours import (
    DEFAULT_COLOUR,
    DEFAULT_INDEX_EVERY,
    DEFAULT_INTERVAL,
    OUTPUT_LAYER_NAME,
    default_insert_position,
    generate_contours,
    suggested_interval,
)


class ContoursDialog(QDialog):

    def __init__(self, parent=None, canvas=None):

        super().__init__(parent)

        self.setWindowTitle(
            "Contours"
        )

        self._canvas = canvas

        self.dem_combo = QgsMapLayerComboBox()

        self.dem_combo.setFilters(
            QgsMapLayerProxyModel.Filter.RasterLayer
        )

        # Same extent control, defaults and reset-on-DEM-change as the
        # Tanaka dialog - see terrain/tanaka_dialog.py for the
        # reasoning, which applies unchanged here.
        self.extent_group = QgsExtentGroupBox()

        self.extent_group.setTitle(
            "Extent"
        )

        if canvas is not None:
            self.extent_group.setMapCanvas(canvas)

        self.dem_combo.layerChanged.connect(
            self._sync_extent_to_dem
        )

        self.interval_spin = QDoubleSpinBox()

        self.interval_spin.setRange(
            0.1,
            10000.0
        )

        self.interval_spin.setDecimals(1)

        self.interval_spin.setSuffix(
            " m"
        )

        self.from_scale_button = QPushButton(
            "From scale"
        )

        self.from_scale_button.setToolTip(
            "Set the interval to what a sheet at the map's current "
            "scale would normally use."
        )

        self.from_scale_button.clicked.connect(
            self.apply_suggested_interval
        )

        interval_row = QHBoxLayout()
        interval_row.addWidget(self.interval_spin)
        interval_row.addWidget(self.from_scale_button)

        self.index_every_spin = QSpinBox()

        self.index_every_spin.setRange(
            1,
            20
        )

        self.index_every_spin.setValue(
            DEFAULT_INDEX_EVERY
        )

        self.index_every_spin.setPrefix(
            "every "
        )

        self.index_every_spin.setSuffix(
            " lines"
        )

        self.colour_button = QgsColorButton()

        self.colour_button.setColor(
            QColor(DEFAULT_COLOUR)
        )

        self.colour_button.setAllowOpacity(False)

        self.new_layer_checkbox = QCheckBox(
            "Add as a new layer (keep any existing Contours layer)"
        )

        form = QFormLayout()

        form.addRow("DEM layer", self.dem_combo)
        form.addRow("Contour interval", interval_row)
        form.addRow("Index contours", self.index_every_spin)
        form.addRow("Colour", self.colour_button)
        form.addRow(self.new_layer_checkbox)

        self.scale_label = QLabel()

        self.scale_label.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        outer = QVBoxLayout()

        outer.addLayout(form)
        outer.addWidget(self.extent_group)
        outer.addWidget(self.scale_label)
        outer.addWidget(buttons)

        self.setLayout(outer)

        self._sync_extent_to_dem(
            self.dem_combo.currentLayer()
        )

        self.apply_suggested_interval()


    def _map_scale(self):

        """
        The canvas's current scale denominator, or None without a
        canvas - which is how the tests build this dialog.
        """

        if self._canvas is None:
            return None

        scale = self._canvas.scale()

        return scale if scale > 0 else None


    def apply_suggested_interval(self):

        """
        Set the interval to what a sheet at the canvas's current scale
        would normally use, and say so. Without a canvas, fall back to
        the module default and say nothing - there is no scale to
        reason from.
        """

        scale = self._map_scale()

        if scale is None:

            self.interval_spin.setValue(DEFAULT_INTERVAL)
            self.scale_label.setText("")

            return

        interval = suggested_interval(scale)

        self.interval_spin.setValue(interval)

        self.scale_label.setText(
            f"At the map's current scale of about 1:{scale:,.0f}, a "
            f"sheet would normally use a {interval:g} m interval."
        )


    def _sync_extent_to_dem(self, dem_layer):

        """
        Point the extent box at the newly-selected DEM and reset it to
        that DEM's own full extent - see tanaka_dialog's own copy of
        this for why it resets rather than carrying the old extent
        over.
        """

        if dem_layer is None:
            return

        extent = dem_layer.extent()
        crs = dem_layer.crs()

        self.extent_group.setOriginalExtent(extent, crs)
        self.extent_group.setCurrentExtent(extent, crs)
        self.extent_group.setOutputCrs(crs)
        self.extent_group.setOutputExtentFromOriginal()


    def values(self):

        return {
            "dem_layer": self.dem_combo.currentLayer(),
            "extent": self.extent_group.outputExtent(),
            "extent_crs": self.extent_group.outputCrs(),
            "interval": self.interval_spin.value(),
            "index_every": self.index_every_spin.value(),
            "colour": self.colour_button.color().name(),
            "add_as_new_layer": self.new_layer_checkbox.isChecked(),
        }


def generate_from_dialog_values(iface, values):

    """
    The accept-flow logic that runs once a ContoursDialog has been
    filled in and accepted - split out from show_contours_dialog() so
    it's testable without driving an actual modal QDialog. Returns the
    new layer, or None if no DEM layer was picked.
    """

    if values["dem_layer"] is None:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            "No raster (DEM) layer available to generate contours from."
        )

        return None

    dem_layer = values["dem_layer"]

    # .get() throughout, and an empty rectangle falls back the same
    # way, for the reasons tanaka_dialog's own copy spells out.
    extent = values.get("extent")
    extent_crs = values.get("extent_crs")

    if extent is None or extent.isEmpty():
        extent = dem_layer.extent()
        extent_crs = dem_layer.crs()

    elif extent_crs is None or not extent_crs.isValid():
        extent_crs = dem_layer.crs()

    def generate():

        return generate_contours(
            dem_layer,
            extent,
            extent_crs,
            interval=values.get("interval", DEFAULT_INTERVAL),
            index_every=values.get("index_every", DEFAULT_INDEX_EVERY),
            colour=values.get("colour", DEFAULT_COLOUR),
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


def show_contours_dialog(iface):

    """
    Prompt for a DEM, an extent, an interval and a colour, then
    generate the contour layer if accepted. Returns the new layer, or
    None if the dialog was cancelled or no DEM layer was available to
    pick.
    """

    dialog = ContoursDialog(
        iface.mainWindow(),
        canvas=iface.mapCanvas()
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    return generate_from_dialog_values(
        iface,
        dialog.values()
    )
