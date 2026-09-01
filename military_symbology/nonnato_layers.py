# -*- coding: utf-8 -*-

"""
Bundles Land Unit (Non-NATO) and Land Equipment (Non-NATO) into one
toolbar action - the non-NATO counterpart to land_layer.py's own
add_land_layers(), which bundles NATO's four Land sub-layers the same
way. Control Measure Points (Non-NATO) stays its own single toolbar
action instead, mirroring NATO's own single-action SIGINT/Sea
Surface/etc. Land Equipment's own entity list also covers Jammer/Radar
(Land-scoped SIGINT) since 2026-09-02 - merged in once a two-entity
layer stopped justifying its own module/action, so there is no
separate SIGINT bundling to speak of any more.

Military Cartography Tools
"""

from .land_equipment_layer_nonnato import (
    LAYER_NAME as EQUIPMENT_LAYER_NAME,
    add_land_equipment_layer_nonnato,
)
from .land_unit_layer_nonnato import (
    LAYER_NAME as UNIT_LAYER_NAME,
    add_land_unit_layer_nonnato,
)


def add_nonnato_land_layers(iface):

    """
    Add both "Land Unit (Non-NATO)" and "Land Equipment (Non-NATO)" in
    one call - the toolbar action's own callback. Each has its own
    already-exists guard, so calling this again only adds whichever of
    the two are still missing. Returns a dict of {layer_name:
    layer_or_None}, mirroring add_land_layers()'s own return shape.
    """

    return {
        UNIT_LAYER_NAME: add_land_unit_layer_nonnato(iface),
        EQUIPMENT_LAYER_NAME: add_land_equipment_layer_nonnato(iface),
    }
