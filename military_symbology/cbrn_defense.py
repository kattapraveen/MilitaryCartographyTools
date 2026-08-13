# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.23 (Table H-XXI, "CBRN defense control
measure symbols") - Mini-Phase H18. Printed pages 606-614, 27 code
rows.

**This module currently builds the table's POINTS only - 18 of the 27.**
The remaining nine are areas and lines and are audited but deliberately
NOT built yet; see TABLE_H_XXI_REMAINING below for what they are and
what has to be settled before they can be.

**Why the split is a clean one, not an arbitrary stopping place.**
Every one of the 18 point codes (281300-281809) is backed by a real
milsymbol icon - checked directly against milsymbol's own
src/numbersidc/sidc/control-measure.js, entry by entry, not inferred
from the code prefix. None of the nine area/line codes
(271700-272200) is, which is expected: milsymbol has no line or
polygon support at all, so every line and area in this appendix has
always been hand-built. So the points are mechanical and the areas
are new drawing work, and they divide exactly there.

**Colour: affiliation, not green.** As with Table H-XX, the green is
H.5.21.1's own explicit exception for obstacles and H.5.23 claims
nothing like it. For milsymbol-rendered points the affiliation hue
comes free (see control_measure_points.py's own docstring).

**Four of the 18 are RELOCATED, not new**: Chemical/Biological/Nuclear/
Radiological Event already existed in sidc.py and were offered on the
shared control_measure_points.py layer. They move here with the rest
of their table, exactly as Tables H-VI, H-IX, H-XIII, H-XIX and H-XX's
own points did before them. The other 14 are new vocabulary.

**One quirk worth knowing before anyone reports it as a bug**: Nuclear
Event (281500) and Nuclear Fallout Producing Event (281600) are two
distinct codes that milsymbol draws with the SAME icon
(TP.NUCLEAR EVENT). That is the standard's own doing - the two rows
have different names and different codes but no drawn difference -
and it is pinned by a test so it reads as a known fact rather than a
duplication defect.
"""

from ._point_symbol_layer import (
    add_single_domain_point_layer,
    build_single_domain_point_layer,
)


POINTS_LAYER_NAME = "CBRN Defense Points"

# Table H-XXI's own 18 point entries, in the standard's own order.
# Names follow the standard's own CONTROL MEASURE column, cross-checked
# against milsymbol's own icon names.
POINT_ENTITY_LABELS = {
    "chemical_event": "Chemical Event",
    "chemical_toxic_industrial_material":
        "Chemical - Toxic Industrial Material",
    "biological_event": "Biological Event",
    "biological_toxic_industrial_material":
        "Biological - Toxic Industrial Material",
    "nuclear_event": "Nuclear Event",
    "nuclear_fallout_producing_event": "Nuclear Fallout Producing Event",
    "radiological_event": "Radiological Event",
    "radiological_toxic_industrial_material":
        "Radiological - Toxic Industrial Material",
    "decontamination_point": "Decontamination Point/Site",
    "decontamination_point_alternate":
        "Decontamination Point/Site - Alternate",
    "decontamination_point_equipment":
        "Decontamination Point/Site - Equipment",
    "decontamination_point_troops": "Decontamination Point/Site - Troops",
    "decontamination_point_equipment_troops":
        "Decontamination Point/Site - Equipment and Troops",
    "decontamination_point_operational":
        "Decontamination Point/Site - Operational",
    "decontamination_point_thorough":
        "Decontamination Point/Site - Thorough",
    "decontamination_point_main_equipment":
        "Main Equipment Decontamination Point/Site",
    "decontamination_point_forward_troop":
        "Forward Troop Decontamination Point/Site",
    "decontamination_point_wounded_personnel":
        "Wounded Personnel Decontamination Site",
}

POINT_ENTITY_CODES = {
    "chemical_event": "281300",
    "chemical_toxic_industrial_material": "281301",
    "biological_event": "281400",
    "biological_toxic_industrial_material": "281401",
    "nuclear_event": "281500",
    "nuclear_fallout_producing_event": "281600",
    "radiological_event": "281700",
    "radiological_toxic_industrial_material": "281701",
    "decontamination_point": "281800",
    "decontamination_point_alternate": "281801",
    "decontamination_point_equipment": "281802",
    "decontamination_point_troops": "281803",
    "decontamination_point_equipment_troops": "281804",
    "decontamination_point_operational": "281805",
    "decontamination_point_thorough": "281806",
    "decontamination_point_main_equipment": "281807",
    "decontamination_point_forward_troop": "281808",
    "decontamination_point_wounded_personnel": "281809",
}

# The two codes the standard distinguishes but does not draw
# differently - see the module docstring.
SHARED_GLYPH_CODES = ("281500", "281600")

# --- Audited, NOT built. ---
#
# The nine remaining rows of Table H-XXI, all areas or lines, none
# backed by a milsymbol icon. Recorded here so the gap is explicit
# rather than looking like an oversight, and so whoever builds them
# starts from the audit rather than re-reading the table.
#
# The seven contaminated areas share ONE construction: a freeform
# outline of at least three anchor points, a YELLOW HATCHED fill, and
# a single centred glyph - an inverted triangle carrying a letter
# (B/C/N/R) with an optional "T" beneath it for the Toxic Industrial
# Material variants. The outline, the fill and the anchor-point rules
# are all fully specified by the standard; **the triangle glyph's own
# proportions are not**, and that glyph does not exist in milsymbol,
# so it has to be drawn. That is the one open question, and on this
# table's own track record it is worth asking about rather than
# guessing at.
#
# Minimum Safe Distance Zone (272100) is a circle - its own draw rules
# DO number it (a centre point plus a radius point), so it is the one
# of the nine that could be built without asking anything.
#
# Radiation Dose Rate Contour Line (272200) is a plain line carrying a
# dose-rate label at each end, in the same shape as Table H-III's own
# Boundary labelling.
TABLE_H_XXI_REMAINING = {
    "271700": "Biological Contaminated Area",
    "271701": "Biological Contaminated Area - Toxic Industrial Material",
    "271800": "Chemical Contaminated Area",
    "271801": "Chemical Contaminated Area - Toxic Industrial Material",
    "271900": "Nuclear Contaminated Area",
    "272000": "Radiological Contaminated Area",
    "272001": "Radiological Contaminated Material",
    "272100": "Minimum Safe Distance Zone",
    "272200": "Radiation Dose Rate Contour Line",
}


def create_cbrn_defense_points_layer(name=POINTS_LAYER_NAME):

    """
    Table H-XXI's own 18 point symbols, milsymbol-rendered.

    No echelon and no headquarters flag, the same call every other
    control-measure point layer in this project makes - Appendix H's
    own amplifier table gives them neither.
    """

    return build_single_domain_point_layer(
        name,
        "control_measure",
        POINT_ENTITY_LABELS,
        "chemical_event",
        include_echelon=False,
        include_headquarters=False,
    )


def add_cbrn_defense_points_layer(iface):

    return add_single_domain_point_layer(
        iface,
        POINTS_LAYER_NAME,
        create_cbrn_defense_points_layer,
    )
