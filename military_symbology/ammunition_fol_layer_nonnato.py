# -*- coding: utf-8 -*-

"""
Builds the "Ammunition and FOL (Non-NATO)" point layer.

New 2026-09-18: "New Layer called Ammunition and FOL". It uses Land
Unit's dialog and renderer over its own entity list, the way Aviation
does - build_unit_style_layer() is shared, not copied - so status and
the left/right designations behave exactly as they do on Land Unit.
**Echelon, Headquarters and Combined Arms do not**: "Ammunition and FOL
do not need echelons", then "in ammunition - headquarters and combined
arms also not required" (both 2026-09-18). The fields are there, as part
of the shared dialog, and have no effect - the same way Aviation's
mast-carrying entities ignore theirs. The FOL entities follow the same
rule, as the rest of the layer.

Ten entities, all Administration or Logistics' circle with something
inside (see nonnato_symbol_engine.py's Ammunition and FOL section):

- Ammunition (All Types) - milsymbol's own Ammunition glyph, 40% larger.
- Ammunition (Air Force / Armour) - the same, with Army Aviation's
  propeller or Armour's oval centred on it.
- Ammunition (Artillery / Rocket or Missile / Small Arms) - the same,
  with Artillery's solid dot, a short vertical line or an X inside it.
- Aviation FOL - an inverted triangle on a stem, with the propeller.
- Non-Aviation FOL - the inverted triangle over a smaller solid one,
  tip to tip.
- Water, Chemicals - "W" and "C".

Reachable via the "Ammunition and FOL" entry in the toolbar's "Non-NATO
Symbols" group (see plugin.py), or directly via
add_ammunition_fol_layer_nonnato(iface).

Military Cartography Tools
"""

from qgis.core import QgsProject

from ._point_symbol_layer import default_insert_position
from ..core._layer_utils import add_layer_at_default_position
from .land_unit_layer_nonnato import build_unit_style_layer
from .nonnato_symbol_engine import (
    AMMUNITION_AIR_FORCE_ENTITY,
    AMMUNITION_ALL_TYPES_ENTITY,
    AMMUNITION_ARMOUR_ENTITY,
    AMMUNITION_ARTILLERY_ENTITY,
    AMMUNITION_ROCKET_MISSILE_ENTITY,
    AMMUNITION_SMALL_ARMS_ENTITY,
    CHEMICALS_ENTITY,
    FOL_AVIATION_ENTITY,
    FOL_NON_AVIATION_ENTITY,
    WATER_ENTITY,
)


LAYER_NAME = "Ammunition and FOL (Non-NATO)"

DEFAULT_ENTITY = AMMUNITION_ALL_TYPES_ENTITY

# "add Ammunition to the title otherwise user may get confused with FOL"
# (2026-09-18) - the first three were plain "All Types"/"Air Force"/
# "Armour" until then.
ENTITY_LABELS = {
    AMMUNITION_ALL_TYPES_ENTITY: "Ammunition (All Types)",
    AMMUNITION_AIR_FORCE_ENTITY: "Ammunition (Air Force)",
    AMMUNITION_ARMOUR_ENTITY: "Ammunition (Armour)",
    AMMUNITION_ARTILLERY_ENTITY: "Ammunition (Artillery)",
    AMMUNITION_ROCKET_MISSILE_ENTITY: "Ammunition (Rocket or Missile)",
    AMMUNITION_SMALL_ARMS_ENTITY: "Ammunition (Small Arms)",
    FOL_AVIATION_ENTITY: "Aviation FOL",
    FOL_NON_AVIATION_ENTITY: "Non-Aviation FOL",
    WATER_ENTITY: "Water",
    CHEMICALS_ENTITY: "Chemicals",
}


def build_ammunition_fol_layer_nonnato():

    """A fresh, empty "Ammunition and FOL (Non-NATO)" layer - never added to the project itself, see add_ammunition_fol_layer_nonnato()."""

    return build_unit_style_layer(LAYER_NAME, ENTITY_LABELS, DEFAULT_ENTITY)


def add_ammunition_fol_layer_nonnato(iface):

    """
    Guard-and-insert, exactly as add_aviation_layer_nonnato() does: if
    the layer already exists, warn and do nothing, since this is
    hand-placed operational data rather than something safe to replace
    silently. Returns the new layer, or None if one already existed.
    """

    project = QgsProject.instance()

    if project.mapLayersByName(LAYER_NAME):

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            f'An "{LAYER_NAME}" layer already exists - use the Layers '
            "panel to work with it, or rename it first if you want a "
            "second one."
        )

        return None

    layer = build_ammunition_fol_layer_nonnato()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )
