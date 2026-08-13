# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.26 (Table H-XXIV, "Mission Task Symbols") -
Mini-Phase H21. Printed pages 636-655, 29 code rows.

**Three of the 29 are points; this module builds those three.** Destroy
(340900), Interdict (341400) and Neutralize (341600) each take ONE
anchor point and draw a centred glyph - checked on the table's own
DRAW RULES ("This symbol requires one anchor point. The center point
defines center of the symbol"), not inferred. Every other row in the
table is an arrow, a bracket or an outlined region built from two to
fifty anchor points, and milsymbol has no icon for any of them: 3 of
29 present, verified entry by entry against milsymbol's own
src/numbersidc/sidc/control-measure.js. The project maintainer scoped
this pass to "all the point symbols derived from milsymbol.js", and
the split falls exactly on that line.

**All three are RELOCATED, not new.** They already existed in sidc.py
as destroy_point/interdict_point/neutralize_point and were offered on
the shared control_measure_points.py layer. Moving them here empties
that layer's last three entries; it is retired with this mini-phase.

**Do not confuse these with the same task names elsewhere in Appendix
H.** Several mission tasks share a name with an obstacle-effect or
maneuver control measure that has its OWN, different code and its own
drawn form - Block, Breach, Bypass, Canalize, Disrupt, Fix, Penetrate,
Seize and Withdraw all appear both here and in Tables H-VII/H-XIX.
Conflating the two is a defect this project has already been reported
for once (see docs/roadmap.md's own Phase 10 entry), so the 26 unbuilt
rows are listed below by code rather than by name alone.

Military Cartography Tools
"""

from ._control_measure_shared import add_layer_if_absent

from ._point_symbol_layer import build_single_domain_point_layer


POINTS_LAYER_NAME = "Mission Task Points"

POINT_ENTITY_LABELS = {
    "destroy_point": "Destroy",
    "interdict_point": "Interdict",
    "neutralize_point": "Neutralize",
}

POINT_ENTITY_CODES = {
    "destroy_point": "340900",
    "interdict_point": "341400",
    "neutralize_point": "341600",
}

# --- Audited, NOT built. ---
#
# The 26 remaining rows of Table H-XXIV. 340000 is the section's own
# parent entry, with TEMPLATE and EXAMPLE both reading "N/A", so the
# real drawing work is 25.
#
# Every one is a multi-anchor construction rather than a centred
# glyph, and none has a milsymbol icon. Roughly three families:
#
# - Arrow tasks (Counterattack, Counterattack by Fire, Penetrate,
#   Seize, Withdraw and the rest) - N anchor points, PT1 at the
#   arrowhead's tip, working back to the rear. Counterattack's own
#   draw rules allow N between 3 and 50.
# - Bracket/effect tasks (Block, Breach, Bypass, Canalize, Clear,
#   Delay, Disrupt, Fix, Isolate) - the same shapes Table H-XIX's own
#   obstacle effects already build here, under DIFFERENT codes. See
#   the module docstring: these are not the same symbols.
# - Security tasks (342200 and its three variants) - Cover, Guard and
#   Screen are sub-codes of Security, drawn as an open bracket along
#   the screened front.
TABLE_H_XXIV_REMAINING = {
    "340000": "Mission Tasks (section parent; TEMPLATE and EXAMPLE "
              "both N/A)",
    "340100": "Block",
    "340200": "Breach",
    "340300": "Bypass",
    "340400": "Canalize",
    "340500": "Clear",
    "340600": "Counterattack",
    "340700": "Counterattack by Fire",
    "340800": "Delay",
    "341000": "Disrupt",
    "341100": "Fix",
    "341200": "Follow and Assume",
    "341300": "Follow and Support",
    "341500": "Isolate",
    "341700": "Occupy",
    "341800": "Penetrate",
    "341900": "Relief in Place (RIP)",
    "342000": "Retire/Retirement",
    "342100": "Secure",
    "342200": "Security",
    "342201": "Security - Cover",
    "342202": "Security - Guard",
    "342203": "Security - Screen",
    "342300": "Seize",
    "342400": "Withdraw",
    "342500": "Withdraw Under Pressure",
}


def create_mission_task_points_layer(name=POINTS_LAYER_NAME):

    """Table H-XXIV's own three point symbols, milsymbol-rendered."""

    return build_single_domain_point_layer(
        name,
        "control_measure",
        POINT_ENTITY_LABELS,
        "destroy_point",
        include_echelon=False,
        include_headquarters=False,
    )


def add_mission_task_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_mission_task_points_layer,
    )
