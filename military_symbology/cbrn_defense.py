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

**Field T (unique designation).** Every row in the table carries it -
to the right of the box on the decontamination points, at the lower
left of the triangle on the events - and it reaches the symbol through
mct_sidc_svg's own text channel, wired in the shared point-layer
builder (see _point_symbol_layer.py, where it was missing until
2026-08-13). milsymbol's `uniqueDesignation` slot is the right one
here: probed directly, it places the text to the RIGHT of the box,
where the template puts T, while `uniqueDesignation1` places it INSIDE
the box, which is the template's own T1. One icon,
Biological - Toxic Industrial Material (281401), defines no
designation slot at all in milsymbol even though the table draws a T
on it; passing one is a harmless no-op, so that row simply shows no
designation.

**One quirk worth knowing before anyone reports it as a bug**: Nuclear
Event (281500) and Nuclear Fallout Producing Event (281600) are two
distinct codes that milsymbol draws with the SAME icon
(TP.NUCLEAR EVENT). That is the standard's own doing - the two rows
have different names and different codes but no drawn difference -
and it is pinned by a test so it reads as a known fact rather than a
duplication defect.
"""

from ._control_measure_shared import add_layer_if_absent

from ._point_symbol_layer import build_single_domain_point_layer


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

# **The eight events are drawn smaller than the ten decontamination
# points, and that is milsymbol's bounding boxes, not this layer.**
#
# Every event icon (281300-281701) is a wide, low inverted triangle
# whose declared box is 158x118; every decontamination point
# (281800-281809) is a narrow, tall box-and-spike at 88x168. QGIS
# sizes an SVG marker by its WIDTH, so at one marker size the events
# render at 8/158 mm per icon unit against the decon points' 8/88 -
# barely more than half the scale, and unreadable next to them, which
# is what the maintainer's smoke test reported.
#
# Their number: 30%, asked for directly. Note that matching the decon
# points' drawn scale exactly would be 158/88, about 80% - so this is
# a legibility call rather than a normalisation, and is theirs to
# revisit.
_EVENT_MARKER_SIZE_SCALE = 1.30

_EVENT_ENTITIES = (
    "chemical_event",
    "chemical_toxic_industrial_material",
    "biological_event",
    "biological_toxic_industrial_material",
    "nuclear_event",
    "nuclear_fallout_producing_event",
    "radiological_event",
    "radiological_toxic_industrial_material",
)

POINT_MARKER_SIZE_SCALES = {
    entity: _EVENT_MARKER_SIZE_SCALE for entity in _EVENT_ENTITIES
}

# **Field T1, not Field T, on the ten decontamination points** - where
# their own templates put the designation.
#
# Every 2818xx template draws it INSIDE the lower part of the box, in
# the box marked "T1", and the standard's own examples fill it -
# "1/2COY" under Forward Troop Decontamination Point/Site's own "DCN
# (F) T", "4CBRN" under Wounded Personnel Decontamination Site's "DCN
# W". Field T is a separate box outside the symbol, to its upper right.
# Until 2026-08-14 all ten put it in T.
#
# Found while fixing the identical defect on Tables H-XXII and H-XXIII,
# whose supply/sustainment boxes are the same shape with the same T1
# box; applied here at the maintainer's own instruction after being
# raised, since this table had already been signed off. milsymbol
# exposes the position as `uniqueDesignation1` at (100, 30), against
# Field T's (150, -30) - probed per icon, not assumed.
#
# **The eight EVENTS are deliberately not here.** They are a different
# icon family - a wide inverted triangle, not the box - and milsymbol
# gives them one text position only, at (40, 90). Nothing to move.
POINT_DESIGNATION_SLOTS = {
    entity: "uniqueDesignation1"
    for entity in POINT_ENTITY_CODES
    if entity not in _EVENT_ENTITIES
}

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
        entity_marker_size_scales=POINT_MARKER_SIZE_SCALES,
        entity_designation_slots=POINT_DESIGNATION_SLOTS,
    )


def add_cbrn_defense_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_cbrn_defense_points_layer,
    )
