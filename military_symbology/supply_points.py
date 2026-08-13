# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.25 (Table H-XXIII, "Supply point control
measure symbols") - Mini-Phase H20. Printed pages 623-635, 37 code
rows.

**This module builds the table's POINTS only - 18 of the 37.** The
other 19 are areas and lines; they are audited and listed in
TABLE_H_XXIII_REMAINING below rather than dropped.

**The split is the standard's own, not a convenience.** Every one of
the 18 point codes (321700-321800) is backed by a real milsymbol icon,
checked directly against milsymbol's own
src/numbersidc/sidc/control-measure.js entry by entry. None of the 19
area/line codes (310000-310700, 330000-330403) is, which is expected:
milsymbol has no line or polygon support at all, so every line and
area in this appendix has always been hand-built here. The project
maintainer scoped this pass to "all the point symbols derived from
milsymbol.js", and that boundary falls exactly here.

**Two of the 18 are RELOCATED, not new**: General Supply Point
(321700) and Medical Supply Point (321800) already existed in sidc.py
and were offered on the shared control_measure_points.py layer. The
other 16 are new vocabulary.

**Those 16 are two vocabularies, not one.** The table splits its
supply classes by standard: 321701-321706 are the NATO classes, each
row quoting its own STANAG 2961 definition, and 321707-321716 are the
US classes I through X. They share roman numerals and mean different
things, so both the entity keys and the labels say which is which
rather than leaving "Class I" to be guessed at.

**One quirk worth knowing before anyone reports it as a bug**: NATO
Multiple Supply Class Point (321706) draws the SAME glyph as General
Supply Point (321700) - the plain supply-point box. That is the
standard's own doing, not a milsymbol gap: 321706's box carries no
drawn icon at all, only a user-typed A field ("Use supply class
numbers (I, II, III, IV and V) for A field or ALL for all classes of
supply"), and the table's own example fills it with "I/III/V". A test
pins this as the ONLY glyph collision among the 18, so the known case
reads as a fact and an accidental one still fails loudly.

**That A field is not offered yet.** These layers carry Field T
(unique designation) and nothing else, which is what the shared
point-layer builder provides; 321706 is the one row here that is less
useful without its own amplifier. Recorded rather than quietly
skipped.

**Colour: affiliation, not green** - the green is H.5.21.1's own
explicit obstacles exception and H.5.25 claims nothing like it.

Military Cartography Tools
"""

from ._control_measure_shared import add_layer_if_absent

from ._point_symbol_layer import build_single_domain_point_layer


POINTS_LAYER_NAME = "Supply Points"

POINT_ENTITY_LABELS = {
    "general_supply_point": "General Supply Point",
    "supply_point_nato_class_i": "NATO Class I Supply Point",
    "supply_point_nato_class_ii": "NATO Class II Supply Point",
    "supply_point_nato_class_iii": "NATO Class III Supply Point",
    "supply_point_nato_class_iv": "NATO Class IV Supply Point",
    "supply_point_nato_class_v": "NATO Class V Supply Point",
    "supply_point_nato_multiple_class": "NATO Multiple Supply Class Point",
    "supply_point_us_class_i": "US Class I Supply Point",
    "supply_point_us_class_ii": "US Class II Supply Point",
    "supply_point_us_class_iii": "US Class III Supply Point",
    "supply_point_us_class_iv": "US Class IV Supply Point",
    "supply_point_us_class_v": "US Class V Supply Point",
    "supply_point_us_class_vi": "US Class VI Supply Point",
    "supply_point_us_class_vii": "US Class VII Supply Point",
    "supply_point_us_class_viii": "US Class VIII Supply Point",
    "supply_point_us_class_ix": "US Class IX Supply Point",
    "supply_point_us_class_x": "US Class X Supply Point",
    "medical_supply_point": "Medical Supply Point",
}

# The two codes the standard distinguishes but does not draw
# differently - see the module docstring.
SHARED_GLYPH_CODES = ("321700", "321706")

POINT_ENTITY_CODES = {
    "general_supply_point": "321700",
    "supply_point_nato_class_i": "321701",
    "supply_point_nato_class_ii": "321702",
    "supply_point_nato_class_iii": "321703",
    "supply_point_nato_class_iv": "321704",
    "supply_point_nato_class_v": "321705",
    "supply_point_nato_multiple_class": "321706",
    "supply_point_us_class_i": "321707",
    "supply_point_us_class_ii": "321708",
    "supply_point_us_class_iii": "321709",
    "supply_point_us_class_iv": "321710",
    "supply_point_us_class_v": "321711",
    "supply_point_us_class_vi": "321712",
    "supply_point_us_class_vii": "321713",
    "supply_point_us_class_viii": "321714",
    "supply_point_us_class_ix": "321715",
    "supply_point_us_class_x": "321716",
    "medical_supply_point": "321800",
}

# --- Audited, NOT built. ---
#
# The 19 remaining rows of Table H-XXIII, all areas or lines, none
# backed by a milsymbol icon. Recorded here so the gap is explicit
# rather than looking like an oversight, and so whoever builds them
# starts from the audit rather than re-reading the table.
#
# Two of the 19 are not symbols at all: 310000 ("Sustainment Areas")
# and 330000 ("Sustainment Lines") are the sub-sections' own parent
# rows, with TEMPLATE and EXAMPLE both reading "N/A". So the real
# drawing work is 17.
#
# The 310xxx block is holding and support AREAS - freeform outlines
# whose own draw rules ask for at least three anchor points and size
# the area from them, the same construction Table H-V's areas already
# use here, each carrying its own abbreviation plus Field T.
#
# The 330xxx block is convoy and route LINES. Moving Convoy (330100)
# is a single arrow sized by two anchor points. The eight supply-route
# rows are one construction with two labels and three traffic
# variants: MSR or ASR, then one-way (a single arrow above the line),
# two-way (two opposed arrows) or alternating (a two-headed "ALT"
# arrow), repeated per line segment - the same per-segment repeat
# Table H-III's own Boundary already does here.
TABLE_H_XXIII_REMAINING = {
    "310000": "Sustainment Areas (section parent; TEMPLATE and EXAMPLE "
              "both N/A)",
    "310100": "Detainee Holding Area",
    "310200": "Enemy Prisoner of War Holding Area",
    "310300": "Forward Arming and Refueling Point (FARP)",
    "310400": "Refugee Holding Area",
    "310500": "Regimental Support Area",
    "310600": "Brigade Support Area (BSA)",
    "310700": "Division Support Area",
    "330000": "Sustainment Lines (section parent; TEMPLATE and EXAMPLE "
              "both N/A)",
    "330100": "Moving Convoy",
    "330200": "Halted Convoy",
    "330300": "Main Supply Route (MSR)",
    "330301": "Main Supply Route - One Way Traffic",
    "330302": "Main Supply Route - Two Way Traffic",
    "330303": "Main Supply Route - Alternating Traffic",
    "330400": "Alternate Supply Route (ASR)",
    "330401": "Alternate Supply Route - One Way Traffic",
    "330402": "Alternate Supply Route - Two Way Traffic",
    "330403": "Alternate Supply Route - Alternating Traffic",
}


def create_supply_points_layer(name=POINTS_LAYER_NAME):

    """Table H-XXIII's own eighteen point symbols, milsymbol-rendered."""

    return build_single_domain_point_layer(
        name,
        "control_measure",
        POINT_ENTITY_LABELS,
        "general_supply_point",
        include_echelon=False,
        include_headquarters=False,
    )


def add_supply_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_supply_points_layer,
    )
