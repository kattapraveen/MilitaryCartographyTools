# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.24 (Table H-XXII, "Sustainment point
control measure symbols") - Mini-Phase H19. Printed pages 615-622,
17 code rows.

**Sixteen of the seventeen are built; the seventeenth is not a symbol.**
320000 ("Sustainment Points") is the section's own parent entry, and
its TEMPLATE and EXAMPLE columns both read "N/A" - it names the group,
it does not draw anything. Every other H table with a parent row is
handled the same way.

**All sixteen are RELOCATED, not new.** They already existed in
sidc.py and were offered on the shared control_measure_points.py
layer; they move here with the rest of their own table, exactly as
Tables H-VI, H-IX, H-XIII, H-XIV, H-XVII, H-XIX, H-XX and H-XXI's own
points did before them. Between this module, supply_points.py and
mission_task_control_measures.py, that shared layer is emptied
completely and retired - see plugin.py.

**Colour: affiliation, not green.** The green is H.5.21.1's own
explicit exception for obstacles, and H.5.24 claims nothing like it.
For milsymbol-rendered points the affiliation hue comes free.

**Field T.** Every row in the table carries a unique designation, in
the sector to the right of the icon; it reaches the symbol through the
shared point-layer builder's own text channel (see
_point_symbol_layer.py). Nothing here has to arrange that - it is
worth saying only because it was missing from that builder until
2026-08-13 and every layer built on it was silently dropping the
field.

Military Cartography Tools
"""

from ._control_measure_shared import add_layer_if_absent

from ._point_symbol_layer import build_single_domain_point_layer


POINTS_LAYER_NAME = "Sustainment Points"

# Table H-XXII's own sixteen drawable entries, in the standard's own
# order. Names follow the table's own CONTROL MEASURE column,
# cross-checked entry by entry against milsymbol's own
# src/numbersidc/sidc/control-measure.js rather than inferred from the
# code prefix.
POINT_ENTITY_LABELS = {
    "ambulance_exchange_point": "Ambulance Exchange Point",
    "ammunition_supply_point": "Ammunition Supply Point",
    "ammunition_transfer_point": "Ammunition Transfer and Holding Point",
    "cannibalization_point": "Cannibalization Point",
    "casualty_collection_point": "Casualty Collection Point",
    "civilian_collection_point": "Civilian Collection Point",
    "detainee_collection_point": "Detainee Collection Point",
    "enemy_prisoner_of_war_collection_point":
        "Enemy Prisoner of War Collection Point",
    "logistics_release_point": "Logistics Release Point",
    "maintenance_collection_point": "Maintenance Collection Point (MCP)",
    "medevac_pickup_point":
        "Medical Evacuation (MEDEVAC) Pick-Up Point",
    "rearm_refuel_resupply_point":
        "Rearm, Refuel and Resupply Point (R3P)",
    "refuel_on_the_move_point": "Refuel on the Move (ROM) Point",
    "traffic_control_post": "Traffic Control Post (TCP)",
    "trailer_transfer_point": "Trailer Transfer Point (TTP)",
    "unit_maintenance_collection_point":
        "Unit Maintenance Collection Point (UMCP)",
}

POINT_ENTITY_CODES = {
    "ambulance_exchange_point": "320100",
    "ammunition_supply_point": "320200",
    "ammunition_transfer_point": "320300",
    "cannibalization_point": "320400",
    "casualty_collection_point": "320500",
    "civilian_collection_point": "320600",
    "detainee_collection_point": "320700",
    "enemy_prisoner_of_war_collection_point": "320800",
    "logistics_release_point": "320900",
    "maintenance_collection_point": "321000",
    "medevac_pickup_point": "321100",
    "rearm_refuel_resupply_point": "321200",
    "refuel_on_the_move_point": "321300",
    "traffic_control_post": "321400",
    "trailer_transfer_point": "321500",
    "unit_maintenance_collection_point": "321600",
}

# The one row of the table that is deliberately not built, and why -
# recorded rather than dropped, so the 16 + 1 = 17 adds up against the
# printed table and a test can say so.
TABLE_H_XXII_NOT_A_SYMBOL = {
    "320000": "Sustainment Points (section parent; TEMPLATE and "
              "EXAMPLE both N/A)",
}


# **Field T1, not Field T** - where each icon's own unique designation
# actually sits.
#
# Every template in Table H-XXII draws the designation INSIDE the lower
# part of the box, in the box marked "T1", and the standard's own
# examples fill it: "4077" under Ambulance Exchange Point's own "AXP",
# "MNSE" under Ammunition Supply Point's "ASP". Field T is a separate
# box outside the symbol, to its upper right. Until 2026-08-14 every
# one of these points put the designation in T; raised by the
# maintainer after live testing, as the same fix already applied to
# Table H-XXIII's supply points.
#
# milsymbol exposes that position as `uniqueDesignation1`, confirmed by
# probing all 16 icons for which text options they actually define and
# where each one lands: `uniqueDesignation` draws at (150, -30),
# outside and above-right, and `uniqueDesignation1` at (100, 30),
# inside the box's lower part.
#
# **Ambulance Exchange Point (320100) is deliberately absent**, and not
# because its template lacks a T1 box - it has one, and the standard's
# own example fills it with "4077". milsymbol defines NO text option
# whatsoever for that icon, neither T nor T1, so no slot reaches it and
# its designation cannot be drawn at all. The same milsymbol gap Table
# H-XXIII's own NATO Multiple Supply Class Point has. Recorded rather
# than quietly skipped.
POINT_DESIGNATION_SLOTS = {
    entity: "uniqueDesignation1"
    for entity in POINT_ENTITY_CODES
    if entity != "ambulance_exchange_point"
}


def create_sustainment_points_layer(name=POINTS_LAYER_NAME):

    """
    Table H-XXII's own sixteen point symbols, milsymbol-rendered.

    No echelon and no headquarters flag, the same call every other
    control-measure point layer in this project makes - Appendix H's
    own amplifier table gives them neither.
    """

    return build_single_domain_point_layer(
        name,
        "control_measure",
        POINT_ENTITY_LABELS,
        "ambulance_exchange_point",
        include_echelon=False,
        include_headquarters=False,
        entity_designation_slots=POINT_DESIGNATION_SLOTS,
    )


def add_sustainment_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_sustainment_points_layer,
    )
