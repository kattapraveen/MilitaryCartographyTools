# -*- coding: utf-8 -*-

"""
Qt UI for creating and editing a "New Military Layout" - the
creation dialog (NewLayoutDialog) and its in-designer counterpart
(LayoutOptionsPanel) share the same page size/orientation/scale/
heading/classification fields (LayoutFieldsWidget), and both hand
off to new_layout.py's create_layout()/update_layout() to actually
build or change a print layout. Split out from new_layout.py, which
holds the layout-building/geometry logic these widgets call into.

Military Cartography Tools
"""

from qgis.PyQt.QtWidgets import (
    QDialog,
    QWidget,
    QDockWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QDialogButtonBox,
    QPushButton
)

from .classification import LEVELS as CLASSIFICATION_LEVELS
from .new_layout import (
    PAGE_SIZES,
    COMMON_SCALES,
    _format_scale,
    _parse_scale,
    _detect_preset,
    create_layout,
    update_layout,
    get_layout_values,
)


class LayoutFieldsWidget(QWidget):

    """
    Page size / orientation / scale / heading / classification
    fields - shared by NewLayoutDialog (creating a layout from
    scratch) and LayoutOptionsPanel (editing one that's already
    open), so both use the exact same preset/orientation swap
    logic and the exact same values() shape.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.size_combo = QComboBox()

        self.size_combo.addItems(
            ["Custom"] + list(PAGE_SIZES.keys())
        )

        self.size_combo.setCurrentText(
            "A4"
        )

        self.orientation_combo = QComboBox()

        self.orientation_combo.addItems(
            ["Landscape", "Portrait"]
        )

        self.width_spin = QDoubleSpinBox()

        self.width_spin.setRange(
            10.0,
            5000.0
        )

        self.width_spin.setSuffix(
            " mm"
        )

        self.height_spin = QDoubleSpinBox()

        self.height_spin.setRange(
            10.0,
            5000.0
        )

        self.height_spin.setSuffix(
            " mm"
        )

        self.scale_combo = QComboBox()

        self.scale_combo.setEditable(
            True
        )

        self.scale_combo.addItems(
            [_format_scale(scale) for scale in COMMON_SCALES]
        )

        self.scale_combo.setCurrentText(
            _format_scale(50000)
        )

        self.heading_line1_edit = QLineEdit()

        self.heading_line1_edit.setPlaceholderText(
            "Optional - leave blank for no heading"
        )

        self.heading_line2_edit = QLineEdit()

        self.heading_line2_edit.setPlaceholderText(
            "Optional - leave blank for a one-line heading"
        )

        self.classification_combo = QComboBox()

        self.classification_combo.addItems(
            CLASSIFICATION_LEVELS
        )

        form = QFormLayout()

        form.addRow("Page size", self.size_combo)
        form.addRow("Orientation", self.orientation_combo)
        form.addRow("Width", self.width_spin)
        form.addRow("Height", self.height_spin)
        form.addRow("Scale", self.scale_combo)
        form.addRow("Heading line 1", self.heading_line1_edit)
        form.addRow("Heading line 2", self.heading_line2_edit)
        form.addRow("Classification", self.classification_combo)

        self.setLayout(
            form
        )

        self.size_combo.currentTextChanged.connect(
            self._on_size_changed
        )

        self.orientation_combo.currentTextChanged.connect(
            self._on_orientation_changed
        )

        # Apply the default preset (A4) now that every widget it
        # touches has been created.
        self._on_size_changed(
            self.size_combo.currentText()
        )


    def _on_size_changed(self, size_name):

        is_custom = size_name == "Custom"

        self.width_spin.setEnabled(is_custom)
        self.height_spin.setEnabled(is_custom)

        if not is_custom:

            larger, smaller = PAGE_SIZES[size_name]

            self._apply_dimensions(
                larger,
                smaller
            )


    def _on_orientation_changed(self, _orientation):

        # Swap whatever the current width/height values are -
        # works the same whether they came from a preset or were
        # typed in directly for Custom.
        self._set_dimensions(
            self.height_spin.value(),
            self.width_spin.value()
        )


    def _apply_dimensions(self, larger, smaller):

        if self.orientation_combo.currentText() == "Landscape":

            self._set_dimensions(larger, smaller)

        else:

            self._set_dimensions(smaller, larger)


    def _set_dimensions(self, width, height):

        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)

        self.width_spin.setValue(width)
        self.height_spin.setValue(height)

        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)


    def values(self):

        heading_lines = [
            line.text().strip()
            for line in (self.heading_line1_edit, self.heading_line2_edit)
            if line.text().strip()
        ]

        return {
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "scale": _parse_scale(self.scale_combo.currentText()),
            "heading_lines": heading_lines,
            "classification": self.classification_combo.currentText(),
        }


    def set_values(self, width_mm, height_mm, scale, heading_lines, classification):

        """
        Pre-fill every field from an existing layout's current
        state - used by LayoutOptionsPanel when a Layout Designer
        window opens on a layout this plugin already built.
        """

        size_name, orientation = _detect_preset(
            width_mm,
            height_mm
        )

        self.orientation_combo.blockSignals(True)
        self.orientation_combo.setCurrentText(orientation)
        self.orientation_combo.blockSignals(False)

        self.size_combo.blockSignals(True)
        self.size_combo.setCurrentText(size_name)
        self.size_combo.blockSignals(False)

        # Both combos' own change signals are blocked above, since
        # they'd otherwise re-apply the matched preset's nominal
        # dimensions - set the layout's actual current dimensions
        # explicitly instead.
        self.width_spin.setEnabled(size_name == "Custom")
        self.height_spin.setEnabled(size_name == "Custom")

        self._set_dimensions(
            width_mm,
            height_mm
        )

        self.scale_combo.setCurrentText(
            _format_scale(round(scale))
        )

        self.heading_line1_edit.setText(
            heading_lines[0] if len(heading_lines) > 0 else ""
        )

        self.heading_line2_edit.setText(
            heading_lines[1] if len(heading_lines) > 1 else ""
        )

        self.classification_combo.setCurrentText(
            classification
        )


class NewLayoutDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle(
            "New Military Layout"
        )

        self.name_edit = QLineEdit(
            "New Layout"
        )

        self.fields = LayoutFieldsWidget()

        name_form = QFormLayout()

        name_form.addRow("Name", self.name_edit)

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

        outer.addLayout(name_form)
        outer.addWidget(self.fields)
        outer.addWidget(buttons)

        self.setLayout(
            outer
        )


    def values(self):

        values = self.fields.values()

        values["name"] = self.name_edit.text().strip() or "New Layout"

        return values


class LayoutOptionsPanel(QDockWidget):

    """
    In-designer counterpart to NewLayoutDialog - lets page size/
    orientation/scale/heading/classification be changed on a
    layout that's already open, instead of only at creation time.
    Added to every Layout Designer window (see plugin.py's
    on_layout_designer_opened).
    """

    def __init__(self, iface, layout, parent=None):

        super().__init__("Military Layout Settings", parent)

        self.iface = iface
        self.layout = layout

        self.fields = LayoutFieldsWidget()

        apply_button = QPushButton(
            "Apply"
        )

        apply_button.clicked.connect(
            self._apply
        )

        container = QWidget()

        outer = QVBoxLayout()

        outer.addWidget(self.fields)
        outer.addWidget(apply_button)

        container.setLayout(
            outer
        )

        self.setWidget(
            container
        )

        self._load_current_values()


    def _load_current_values(self):

        values = get_layout_values(
            self.layout
        )

        self.fields.set_values(
            values["width"],
            values["height"],
            values["scale"],
            values["heading_lines"],
            values["classification"]
        )


    def _apply(self):

        values = self.fields.values()

        update_layout(
            self.layout,
            values["width"],
            values["height"],
            values["scale"],
            values["heading_lines"],
            values["classification"]
        )


def show_new_layout_dialog(iface):

    """
    Prompt for page size/orientation/scale and create the layout
    if accepted. Returns the new QgsPrintLayout, or None if the
    dialog was cancelled.
    """

    dialog = NewLayoutDialog(
        iface.mainWindow()
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    values = dialog.values()

    return create_layout(
        iface,
        values["name"],
        values["width"],
        values["height"],
        values["scale"],
        values["heading_lines"],
        values["classification"]
    )
