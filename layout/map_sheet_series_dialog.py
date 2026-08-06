# -*- coding: utf-8 -*-

"""
Qt UI for Map Sheet Series - a small dialog reusing LayoutFieldsWidget
(the same page size/orientation/scale/heading/classification fields
New Military Layout uses) with no separate name field, since every
sheet is auto-named from its own GZD-anchored designator. Hands off
to map_sheet_series.py's generate_sheet_series() for the current map
canvas extent.

Military Cartography Tools
"""

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from .layout_dialogs import LayoutFieldsWidget
from .map_sheet_series import generate_sheet_series


class MapSheetSeriesDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle(
            "Map Sheet Series"
        )

        self.fields = LayoutFieldsWidget()

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

        outer.addWidget(
            self.fields
        )

        outer.addWidget(
            buttons
        )

        self.setLayout(
            outer
        )


    def values(self):

        return self.fields.values()


def generate_from_dialog_values(iface, values):

    """
    The generate-flow logic driven by MapSheetSeriesDialog's OK
    button - split out so it's testable without driving an actual
    QDialog, matching the rest of this plugin's dialog modules.
    Tiles the current map canvas extent - the same "generate for
    the current extent" convention every other batch-generation
    feature in this plugin already uses. Returns the list of
    created layouts, or None if the requested page size/scale
    combination would produce more than map_sheet_series.MAX_SHEETS
    sheets (reported via the message bar instead of silently
    generating an impractically large series).
    """

    # A dialog session commonly involves more than one Generate
    # attempt - e.g. trying a scale that's over MAX_SHEETS, then
    # narrowing it down - and QGIS's message bar queues pushed
    # messages rather than replacing them: an earlier attempt's
    # warning can sit hidden behind this attempt's own message and
    # resurface later (once the top message is dismissed or times
    # out), looking like a stray, contradictory result long after
    # generation actually succeeded. Clearing first guarantees only
    # this attempt's own outcome is ever shown.
    iface.messageBar().clearWidgets()

    canvas = iface.mapCanvas()

    try:

        layouts = generate_sheet_series(
            iface,
            canvas.extent(),
            canvas.mapSettings().destinationCrs(),
            values["width"],
            values["height"],
            values["scale"],
            values["heading_lines"],
            values["classification"]
        )

    except ValueError as error:

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            str(error)
        )

        return None

    iface.messageBar().pushInfo(
        "Military Cartography Tools",
        f"Created {len(layouts)} sheet"
        + ("s" if len(layouts) != 1 else "")
        + " covering the current map extent - see Project → Layouts Manager."
    )

    return layouts


def show_map_sheet_series_dialog(iface):

    dialog = MapSheetSeriesDialog(
        iface.mainWindow()
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    return generate_from_dialog_values(
        iface,
        dialog.values()
    )
