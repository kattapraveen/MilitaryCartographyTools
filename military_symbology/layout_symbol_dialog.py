# -*- coding: utf-8 -*-

"""
"Insert Symbol" dialog for the print layout designer (U-1) - lets a
MIL-STD-2525/APP-6 symbol be placed directly onto a layout page as a
QgsLayoutItemPicture, rather than only being reachable by digitizing a
feature on one of the plugin's own map layers. A layout page is not a
map canvas - there is no attribute table, no ValueMap-backed field, no
feature to hold an entity/affiliation - so the picture is a static
image built once at insertion time, the same way any inserted photo or
logo would be. See plugin.py's on_layout_designer_opened() for where
this is wired into the designer's own toolbar, alongside the existing
Add/Remove Grid Frame actions.

Deliberately minimal: Affiliation, Symbol Set and Entity only - no
echelon/status/headquarters/sector modifiers, matching the standing
decision to leave the manual's amplifier fields partial rather than
build them out everywhere they could apply. There is nothing to edit
after insertion anyway (it is a picture, not a feature), so anyone who
needs the fuller amplifier set is better served building the symbol as
a real feature on a map layer and copying that in some other way.

Military Cartography Tools
"""

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
)

from ._control_measure_shared import (
    DEFAULT_POINT_AFFILIATION,
    POINT_AFFILIATION_LABELS,
)
from .edition import current_edition
from .sidc import SYMBOL_SETS, build_sidc, entities_for_edition

# Every SYMBOL_SETS key gets an explicit label here, checked by
# tests/test_layout_symbol_dialog.py against SYMBOL_SETS itself - so a
# future symbol set added to sidc.py cannot be silently missing from
# this dialog. Text matches each domain's own layer name where one
# maps cleanly to a single symbol_set (see e.g. land_layer.py's
# UNIT_LAYER_NAME = "Land Unit" for "ground_unit"); the five SIGINT
# entries are disambiguated with their own dimension, since they share
# one entity vocabulary across five distinct SIDC symbol_set codes
# (see sigint_layer.py) but are not one dropdown choice here.
SYMBOL_SET_LABELS = {
    "ground_unit": "Land Unit",
    "air": "Air",
    "air_missile": "Air Missile",
    "sea_surface": "Sea Surface",
    "subsurface": "Subsurface",
    "space": "Space",
    "space_missile": "Space Missile",
    "land_civilian": "Land Civilian",
    "land_equipment": "Land Equipment",
    "land_installation": "Land Installation",
    "mine_warfare": "Mine Warfare",
    "activities": "Activities",
    "cyberspace": "Cyberspace",
    "control_measure": "Control Measure Point",
    "sigint_space": "SIGINT (Space)",
    "sigint_air": "SIGINT (Air)",
    "sigint_land": "SIGINT (Land)",
    "sigint_sea_surface": "SIGINT (Sea Surface)",
    "sigint_subsurface": "SIGINT (Subsurface)",
}

DEFAULT_SYMBOL_SET = "ground_unit"


def humanize_entity_key(key):

    """
    "command_post_node" -> "Command Post Node" - a plain, uniform
    fallback rather than the hand-curated per-layer ENTITY_LABELS
    dicts (e.g. land_layer.py's _UNIT_ENTITY_LABELS), which are
    private to their own modules by this codebase's own convention and
    not meant for reuse elsewhere. Less polished than those (no
    acronym casing, no parenthetical expansions), but uniform across
    every symbol_set with zero cross-module coupling - the right
    trade for a small, standalone dialog rather than importing a
    dozen private label dicts from a dozen layer modules.
    """

    return key.replace("_", " ").title()


class InsertSymbolDialog(QDialog):

    """
    Affiliation / Symbol Set / Entity, in that order - Entity is a
    real cascading dropdown, repopulated from entities_for_edition()
    whenever Symbol Set changes, matching the cascading behaviour the
    canvas layers' own attribute forms use. sidc()/entity_label()
    below read back the current selection once the dialog is
    accepted; edition is read from the toolbar's own Symbology Edition
    setting at build time, not offered here, so a layout symbol always
    matches whatever a newly-added canvas layer would use right now.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Insert Symbol")

        self.affiliation_combo = QComboBox()

        for key, label in POINT_AFFILIATION_LABELS.items():
            self.affiliation_combo.addItem(label, key)

        self.affiliation_combo.setCurrentIndex(
            self.affiliation_combo.findData(DEFAULT_POINT_AFFILIATION)
        )

        self.symbol_set_combo = QComboBox()

        for key, label in SYMBOL_SET_LABELS.items():
            self.symbol_set_combo.addItem(label, key)

        self.symbol_set_combo.setCurrentIndex(
            self.symbol_set_combo.findData(DEFAULT_SYMBOL_SET)
        )

        self.entity_combo = QComboBox()

        self.symbol_set_combo.currentIndexChanged.connect(
            self._repopulate_entities
        )

        self._repopulate_entities()

        form = QFormLayout()

        form.addRow("Affiliation", self.affiliation_combo)
        form.addRow("Symbol Set", self.symbol_set_combo)
        form.addRow("Entity", self.entity_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Insert")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()

        layout.addLayout(form)
        layout.addWidget(buttons)

        self.setLayout(layout)


    def _repopulate_entities(self):

        symbol_set = self.symbol_set_combo.currentData()

        entities = entities_for_edition(current_edition()).get(
            symbol_set, {}
        )

        self.entity_combo.clear()

        for key in entities:
            self.entity_combo.addItem(humanize_entity_key(key), key)


    def sidc(self):

        """The SIDC for the current selection, under the current edition."""

        return build_sidc(
            affiliation=self.affiliation_combo.currentData(),
            entity=self.entity_combo.currentData(),
            symbol_set=self.symbol_set_combo.currentData(),
            edition=current_edition(),
        )


    def entity_label(self):

        """The chosen entity's display label, for the caller's own use."""

        return self.entity_combo.currentText()
