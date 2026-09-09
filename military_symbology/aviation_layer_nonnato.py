# -*- coding: utf-8 -*-

"""
Builds the "Aviation (Non-NATO)" point layer.

New 2026-09-06, at the maintainer's own request: "Insert in land
equipment - or better make a separate layer called aviation / move army
aviation and airforce into that, same rules as land unit i.e. same
dialog box replicated". So this layer is Land Unit's own dialog and
renderer over a different entity list - it shares
build_unit_style_layer(), configure_unit_attribute_form() and
build_unit_renderer() with land_unit_layer_nonnato.py rather than
copying them, and every field, widget, default and expression is
therefore identical by construction.

Eight entities. Army Aviation and Air Force MOVED here from Land Unit;
the other six were designed for this layer:

- Army Aviation (`aviation_fixed_wing`) - milsymbol's own figure-of-8,
  hollowed. "let's start with the army aviation glyph - use only the
  figure of 8 inside the rectangle", which is what it already drew.
- Air Force - the same figure-of-8 with its right arc opened.
- Rotary Wing, Attack / Utility / Light Helicopter, Fixed Wing and
  UAV/RPV/Drone - all the figure-of-8 with a mast, differing in what
  hangs off it. See nonnato_symbol_engine.py's own Aviation family
  comment for each one's geometry.

The six mast-carrying entities draw NO frame, echelon amplifier or
Headquarters mast - "this glyph - other than the unique identifiers,
nothing else is needed". Those fields still exist on the layer, since
the dialog is replicated wholesale; they simply have no effect on those
six. Army Aviation and Air Force keep their frames and so honour all of
them.

Reachable via the "Aviation" entry in the toolbar's "Non-NATO Symbols"
group (see plugin.py), or directly via
add_aviation_layer_nonnato(iface).

Military Cartography Tools
"""

from qgis.core import QgsProject

from ._point_symbol_layer import default_insert_position
from ..core._layer_utils import add_layer_at_default_position
from .land_unit_layer_nonnato import build_unit_style_layer
from .nonnato_symbol_engine import (
    AIR_FORCE_ENTITY,
    ATTACK_HELICOPTER_ENTITY,
    FIXED_WING_ENTITY,
    LIGHT_HELICOPTER_ENTITY,
    ROTARY_WING_ENTITY,
    UAV_ENTITY,
    UTILITY_HELICOPTER_ENTITY,
)


LAYER_NAME = "Aviation (Non-NATO)"

DEFAULT_ENTITY = "aviation_fixed_wing"

# The two moved from Land Unit keep their own existing keys, so a
# project that already carries them renders unchanged - only which
# layer offers them has moved.
ENTITY_LABELS = {
    "aviation_fixed_wing": "Army Aviation",
    AIR_FORCE_ENTITY: "Air Force",
    ROTARY_WING_ENTITY: "Rotary Wing",
    ATTACK_HELICOPTER_ENTITY: "Attack Helicopter",
    UTILITY_HELICOPTER_ENTITY: "Utility Helicopter",
    LIGHT_HELICOPTER_ENTITY: "Light Helicopter",
    FIXED_WING_ENTITY: "Fixed Wing",
    UAV_ENTITY: "UAV/RPV/Drone",
}


def build_aviation_layer_nonnato():

    """A fresh, empty "Aviation (Non-NATO)" layer - never added to the project itself, see add_aviation_layer_nonnato()."""

    return build_unit_style_layer(LAYER_NAME, ENTITY_LABELS, DEFAULT_ENTITY)


def add_aviation_layer_nonnato(iface):

    """
    Guard-and-insert, exactly as add_land_unit_layer_nonnato() does: if
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

    layer = build_aviation_layer_nonnato()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )
