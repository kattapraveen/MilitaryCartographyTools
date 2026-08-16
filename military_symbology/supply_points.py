# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.25 (Table H-XXIII, "Supply point control
measure symbols") - Mini-Phase H20. Printed pages 623-635, 37 code
rows.

**This module builds 33 of the table's 37 rows**, across three layers:
its 18 POINTS, and (from 2026-08-14) the 8 SUPPLY ROUTES on a Lines
layer and the 7 SUSTAINMENT AREAS on an Areas layer. The remaining 4
are the two convoy lines and two parent rows that draw nothing; they
are audited in TABLE_H_XXIII_REMAINING below rather than dropped.

**The point/line split is the standard's own, not a convenience.**
Every one of the 18 point codes (321700-321800) is backed by a real
milsymbol icon,
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
Multiple Supply Class Point (321706) draws the SAME empty box as
General Supply Point (321700). That is the standard's own doing, not a
milsymbol gap: 321706's box carries no drawn icon at all, only a
user-typed A field ("Use supply class numbers (I, II, III, IV and V)
for A field or ALL for all classes of supply"), and the table's own
example fills it with "I/III/V". A test pins this as the ONLY glyph
collision among the 18, so the known case reads as a fact and an
accidental one still fails loudly.

**That A field is now offered**, as a "Supply class" dropdown - added
2026-08-14 at the maintainer's own request. Its options are exactly
what the template permits and no more: the template's own box reads
A/A1/A2, three sub-fields, so a combination is at most THREE of the
five classes - every such combination in ascending order, plus "ALL".
25 combinations and ALL; four classes is not offerable because the
symbol has nowhere to put the fourth.

**Both of 321706's amplifiers are drawn by this plugin, not by
milsymbol**, which defines no text option for that icon at all -
neither the A field nor T1, so its designation drew nothing until now
either. See symbol_engine.py's own _INJECTED_TEXT: the text is placed
at coordinates lifted from the sibling icons milsymbol does define
(321701-321705 for the class numeral's position, 321700 for T1), and
shrunk to fit the box when a long combination would overrun it.

**Colour: affiliation, not green** - the green is H.5.21.1's own
explicit obstacles exception and H.5.25 claims nothing like it.

Military Cartography Tools
"""

import itertools

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsSimpleLineSymbolLayer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    STATUS_LABELS,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_status_field,
    _status_driven_area_outline_symbol,
    _value_map,
    add_layer_if_absent,
)

from ._point_symbol_layer import build_single_domain_point_layer


POINTS_LAYER_NAME = "Supply Points"
LINES_LAYER_NAME = "Supply Routes (Lines)"

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

# **Field T1, not Field T** - where each icon's own unique designation
# actually sits.
#
# Every template in this table draws the designation INSIDE the lower
# part of the supply box, in the box marked "T1", and the standard's
# own examples fill it: "1AD" on General Supply Point, "3SUST" on NATO
# Class I. Field T on these templates is a separate box outside the
# symbol, to its upper right. Until 2026-08-14 every one of these
# points put the designation in T - raised by the maintainer after
# live testing: "i want the unique designation to fill field T1 as per
# manual and not field T".
#
# milsymbol exposes that position as `uniqueDesignation1`, confirmed by
# probing all 18 icons for which text options they actually define and
# where each one lands: `uniqueDesignation` draws at (150, -30), which
# is outside and above-right (Field T), and `uniqueDesignation1` at
# (100, 20), inside the box's lower part (Field T1).
#
# **The US classes are deliberately NOT in this map**, and that is the
# probe's finding, not an oversight: not one of 321707-321716 defines
# `uniqueDesignation1` at all. Field T is the only text position those
# ten icons have, so they keep it - passing them a slot they don't
# define would silently draw nothing at all.
#
# **321706 is not here either, for the opposite reason**: it defines NO
# text option whatsoever, so neither slot reaches it. See
# SHARED_GLYPH_CODES above.
# 321706's own two positions, both injected rather than milsymbol's -
# see the module docstring. Named here so the entity reads as handled
# rather than missing.
_MULTIPLE_CLASS_ENTITY = "supply_point_nato_multiple_class"

POINT_DESIGNATION_SLOTS = {
    _MULTIPLE_CLASS_ENTITY: "mctFieldT1",
}

POINT_DESIGNATION_SLOTS.update({
    entity: "uniqueDesignation1"
    for entity in (
        "general_supply_point",
        "supply_point_nato_class_i",
        "supply_point_nato_class_ii",
        "supply_point_nato_class_iii",
        "supply_point_nato_class_iv",
        "supply_point_nato_class_v",
        "medical_supply_point",
    )
})


def _supply_class_combinations():

    """
    "ALL", then every combination of at most THREE supply classes in
    ascending order - which is exactly what the template's own A/A1/A2
    box has room for, and the reason a fourth class is not offered.
    """

    combinations = {"ALL": "ALL classes of supply"}

    classes = ("I", "II", "III", "IV", "V")

    for size in (1, 2, 3):

        for combination in itertools.combinations(classes, size):

            joined = "/".join(combination)

            combinations[joined] = (
                "Class {}".format(joined)
                if size == 1
                else "Classes {}".format(joined)
            )

    return combinations


SUPPLY_CLASS_LABELS = _supply_class_combinations()

# The A field, offered on the whole layer but drawn only on 321706 -
# see _EXTRA_TEXT_FIELD_KEYS in _point_symbol_layer.py.
SUPPLY_CLASS_FIELD = {
    "name": "supply_class",
    "labels": SUPPLY_CLASS_LABELS,
    "default": "ALL",
    "slot": "mctFieldA",
    "entities": (_MULTIPLE_CLASS_ENTITY,),
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
#
# **Fifteen of the original nineteen were built on 2026-08-14** - the
# eight supply routes (330300-330403) and the seven sustainment areas
# (310100-310700) - and are gone from this list. What is left is the
# two convoys and the two parent rows that draw nothing.
# The table's own two parent rows - "Sustainment Areas" (310000) and
# "Sustainment Lines" (330000) - which name a group and draw nothing:
# TEMPLATE and EXAMPLE both read "N/A". Listed so the row arithmetic
# still adds to the printed table's own 37.
_TABLE_H_XXIII_PARENT_ROWS = ("310000", "330000")

# Nothing is left unbuilt in Table H-XXIII. The dict stays, empty,
# because a test asserts built + unbuilt equals the printed table's own
# row count - the check that kept the gap honest while there was one.
TABLE_H_XXIII_REMAINING = {}


# ---------------------------------------------------------------
# Sustainment areas - Table H-XXIII's own 310100-310700
# ---------------------------------------------------------------

AREAS_LAYER_NAME = "Sustainment Areas"

AREA_MEASURE_TYPE_LABELS = {
    "detainee_holding_area": "Detainee Holding Area",
    "epw_holding_area": "Enemy Prisoner of War Holding Area",
    "farp": "Forward Arming and Refueling Point (FARP)",
    "refugee_holding_area": "Refugee Holding Area",
    "regimental_support_area": "Regimental Support Area (RSA)",
    "brigade_support_area": "Brigade Support Area (BSA)",
    "division_support_area": "Division Support Area (DSA)",
}

AREA_MEASURE_TYPE_CODES = {
    "detainee_holding_area": "310100",
    "epw_holding_area": "310200",
    "farp": "310300",
    "refugee_holding_area": "310400",
    "regimental_support_area": "310500",
    "brigade_support_area": "310600",
    "division_support_area": "310700",
}

# **What each area is lettered with, read off the templates rather than
# derived from its name** - which matters, because the obvious guess is
# wrong twice over:
#
# - The three SUPPORT areas use a three-letter abbreviation (RSA, BSA,
#   DSA), and the four others spell their name out in full, on two
#   lines, exactly as drawn ("DETAINEE" / "HOLDING AREA"). Abbreviating
#   those to "DHA"/"EPWHA"/"RHA" would have been an invention - the
#   standard never uses those forms.
# - FARP is a single line, because its name IS the abbreviation.
_AREA_CAPTIONS = {
    "detainee_holding_area": "DETAINEE\nHOLDING AREA",
    "epw_holding_area": "EPW\nHOLDING AREA",
    "farp": "FARP",
    "refugee_holding_area": "REFUGEE\nHOLDING AREA",
    "regimental_support_area": "RSA",
    "brigade_support_area": "BSA",
    "division_support_area": "DSA",
}

# **Only four of the seven carry Field T**, and again this is the
# templates' own doing rather than a simplification: the four holding/
# FARP templates draw a "T" box beneath the caption and fill it in
# their examples ("GB", "15MP", "2AVN", "8MEB"), while the three
# support areas have no such box at all - RSA, BSA and DSA are drawn
# bare in both the TEMPLATE and the EXAMPLE column.
_AREA_DESIGNATED = (
    "detainee_holding_area",
    "epw_holding_area",
    "farp",
    "refugee_holding_area",
)


def _area_label_expression(measure_type):

    caption = "'{}'".format(_AREA_CAPTIONS[measure_type])

    if measure_type not in _AREA_DESIGNATED:
        return caption

    # The designation on its own line beneath, and only when there is
    # one - otherwise the label ends in a blank line and centres wrong.
    return (
        "{caption} || CASE WHEN coalesce(\"unique_designation\",'') <> '' "
        "THEN '\n' || upper(\"unique_designation\") ELSE '' END"
    ).format(caption=caption)


_AREA_LABEL_EXPRESSION = "CASE " + " ".join(
    "WHEN \"measure_type\" = '{}' THEN {}".format(
        measure_type, _area_label_expression(measure_type)
    )
    for measure_type in AREA_MEASURE_TYPE_LABELS
) + " ELSE '' END"

_AREA_SYMBOL_BUILDERS = {
    measure_type: _status_driven_area_outline_symbol
    for measure_type in AREA_MEASURE_TYPE_LABELS
}


def create_sustainment_areas_layer(name=AREAS_LAYER_NAME):

    """
    Table H-XXIII's own seven sustainment areas, 310100-310700.

    All seven are the same construction - "at least three anchor points
    to define the boundary of the area", a plain outline with its
    caption centred inside - which is the same freeform-area build
    Table H-V's own areas already use here. What differs between them
    is only what the caption says and whether it carries Field T.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Polygon?crs={crs.authid()}",
        name,
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
            QgsField("area_km2", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    measure_type_idx = layer.fields().indexOf("measure_type")

    layer.setEditorWidgetSetup(
        measure_type_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(AREA_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        measure_type_idx,
        QgsDefaultValue("'brigade_support_area'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("area_km2"),
        QgsDefaultValue("mct_area_km2($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _AREA_SYMBOL_BUILDERS)
    )

    layer.setLabeling(
        QgsVectorLayerSimpleLabeling(
            _build_pal_layer_settings(
                layer,
                Qgis.LabelPlacement.Horizontal,
                _AREA_LABEL_EXPRESSION,
            )
        )
    )

    layer.setLabelsEnabled(True)

    return layer


def add_sustainment_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_sustainment_areas_layer,
    )


# ---------------------------------------------------------------
# Supply routes - Table H-XXIII's own 330300-330403 (Mini-Phase H23)
# ---------------------------------------------------------------

LINE_MEASURE_TYPE_LABELS = {
    "msr": "Main Supply Route (MSR)",
    "msr_one_way": "MSR - One Way Traffic",
    "msr_two_way": "MSR - Two Way Traffic",
    "msr_alternating": "MSR - Alternating Traffic",
    "asr": "Alternate Supply Route (ASR)",
    "asr_one_way": "ASR - One Way Traffic",
    "asr_two_way": "ASR - Two Way Traffic",
    "asr_alternating": "ASR - Alternating Traffic",
}

LINE_MEASURE_TYPE_CODES = {
    "msr": "330300",
    "msr_one_way": "330301",
    "msr_two_way": "330302",
    "msr_alternating": "330303",
    "asr": "330400",
    "asr_one_way": "330401",
    "asr_two_way": "330402",
    "asr_alternating": "330403",
}

# **Eight codes, ONE construction.** The MSR and ASR halves differ only
# in the abbreviation they label with, and within each half the three
# traffic variants differ only in which arrows ride above the line. The
# standard draws all eight the same way otherwise, which is why they are
# built from one symbol function and one label expression rather than
# eight of each.
_LINE_ABBREVIATIONS = {
    measure_type: ("ASR" if measure_type.startswith("asr") else "MSR")
    for measure_type in LINE_MEASURE_TYPE_LABELS
}

_TRAFFIC_ARROWS = {
    "msr": (),
    "asr": (),
    "msr_one_way": ("forward",),
    "asr_one_way": ("forward",),
    # Inner arrow FIRST - the tuple is ordered outward from the line,
    # so Two Way's "backward" sits nearest the road and "forward" above
    # it. That is the order the standard's own example draws
    # ("MSR SUMMER": top arrow with the direction of travel, bottom
    # against it), and it was the other way round in the first build.
    "msr_two_way": ("backward", "forward"),
    "asr_two_way": ("backward", "forward"),
    "msr_alternating": ("alternating",),
    "asr_alternating": ("alternating",),
}

# --- The four numbers the standard never gives. ---
#
# It draws the arrows and labels them and dimensions none of it, so
# these were put to the project maintainer before building rather than
# guessed - the lesson from Table H-XIX, where every unnumbered guess
# needed correcting and every question asked first did not. Settled
# 2026-08-14.
_ARROW_LENGTH_MM = 12.0

# Alternating Traffic gets a LONGER glyph than the other two, because
# its own arrow is not one arrow but two heads with the word "ALT"
# between them - at 12 mm the text eats the whole shaft and leaves two
# heads floating either side of it, which the first render showed
# plainly. This is the length of the whole "<- ALT ->" assembly.
_ALTERNATING_LENGTH_MM = 20.0

# The "ALT" itself, sized to sit alongside the route's own label rather
# than scale with the glyph around it.
_ALTERNATING_TEXT_MM = 3.4
_ARROW_OFFSET_MM = 3.0
_ARROW_SPACING_MM = 3.0
_LABEL_CLEARANCE_MM = 2.0

_LINE_WIDTH_MM = 0.4

# A colour STRING for the SVG glyphs. The shared affiliation expression
# is built from color_rgb(), which evaluates to a bare "0,0,255" -
# right for a colour property, silently invalid inside an SVG, where it
# draws the glyph as nothing at all.
_ROUTE_GLYPH_COLOR_EXPRESSION = (
    "CASE "
    "WHEN \"affiliation\" = 'friend' THEN 'rgb(0,0,255)' "
    "WHEN \"affiliation\" = 'hostile' THEN 'rgb(255,0,0)' "
    "WHEN \"affiliation\" = 'neutral' THEN 'rgb(0,255,0)' "
    "WHEN \"affiliation\" = 'unknown' THEN 'rgb(255,255,0)' "
    "ELSE 'rgb(0,0,0)' "
    "END"
)

# "MSR CAMEL", "ASR 3" - the abbreviation plus Field T, which is what
# every one of the standard's own examples shows. trim() so a blank
# designation leaves "MSR" rather than a trailing space.
_LINE_LABEL_EXPRESSION = "CASE " + " ".join(
    "WHEN \"measure_type\" = '{measure_type}' THEN "
    "trim('{abbreviation} ' || upper(coalesce(\"unique_designation\",'')))"
    .format(measure_type=measure_type, abbreviation=abbreviation)
    for measure_type, abbreviation in _LINE_ABBREVIATIONS.items()
) + " ELSE '' END"


def _arrow_length_mm(mode):

    return (
        _ALTERNATING_LENGTH_MM if mode == "alternating"
        else _ARROW_LENGTH_MM
    )


def _traffic_arrow_layer(mode, offset_mm):

    """
    One traffic arrow, riding above the route on a marker line.

    Fixed at the line's CENTRAL POINT and drawn once per feature. The
    draw rules say "the line segment between each pair of anchor points
    will repeat all information associated with the line segment" - but
    a route digitized along a real road has many short segments, and
    repeating an arrow and a label on each is unreadable. Once, centred,
    at the maintainer's own call, and the same simplification this
    project already made for Boundary and the FSCL family.

    The offset is PERPENDICULAR and negative, which is QGIS's own "to
    the left of the direction of travel" - above the line as the
    template draws it, for a route running left to right.
    """

    glyph = QgsSvgMarkerSymbolLayer("")

    glyph.setSize(_arrow_length_mm(mode))

    glyph.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            "mct_supply_route_arrow_svg({colour}, {length}, {stroke}, "
            "'{mode}', 'ALT', {text})".format(
                colour=_ROUTE_GLYPH_COLOR_EXPRESSION,
                length=_arrow_length_mm(mode),
                stroke=_LINE_WIDTH_MM,
                mode=mode,
                text=_ALTERNATING_TEXT_MM,
            )
        )
    )

    marker = QgsMarkerSymbol()

    marker.changeSymbolLayer(0, glyph)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(Qgis.MarkerLinePlacement.CentralPoint)

    marker_line.setRotateSymbols(True)

    marker_line.setOffset(-offset_mm)

    marker_line.setOffsetUnit(Qgis.RenderUnit.Millimeters)

    return marker_line


def _supply_route_symbol(measure_type):

    """
    One of Table H-XXIII's eight supply routes - the road itself, plus
    whichever traffic arrows this variant carries.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(QColor(0, 0, 0))

    line_layer.setWidth(_LINE_WIDTH_MM)

    _apply_affiliation_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, line_layer)

    for index, mode in enumerate(_TRAFFIC_ARROWS[measure_type]):

        symbol.appendSymbolLayer(
            _traffic_arrow_layer(
                mode,
                _ARROW_OFFSET_MM + index * _ARROW_SPACING_MM,
            )
        )

    return symbol


def _label_offset_mm(measure_type):

    """
    How far above the line the "MSR CAMEL" label sits - clear of
    whatever arrows this variant stacked there, so the reading order is
    always line, then arrows, then label.
    """

    arrows = len(_TRAFFIC_ARROWS[measure_type])

    if not arrows:
        return _LABEL_CLEARANCE_MM

    topmost = _ARROW_OFFSET_MM + (arrows - 1) * _ARROW_SPACING_MM

    # Half the glyph's own drawn height, which is its arrowhead - see
    # mct_supply_route_arrow_svg(), where the head's half-width is a
    # thirteenth of the length.
    half_height = max(
        _arrow_length_mm(mode) / 13.0
        for mode in _TRAFFIC_ARROWS[measure_type]
    )

    return topmost + half_height + _LABEL_CLEARANCE_MM


# ---------------------------------------------------------------
# The two convoys - Table H-XXIII's own 330100/330200
# ---------------------------------------------------------------
#
# Both are a BAR of fixed page height running between the anchor
# points, with an end piece at PT1: a forward-pointing open arrowhead
# for Moving, and the same triangle REVERSED - apex back into the bar -
# for Halted. That reversal is the only difference between the two
# symbols. "Varies only in length" in Moving Convoy's own draw rules is
# what makes the height a page unit rather than a ground one.
#
# **Field A is deliberately absent.** Both of the standard's examples
# draw a vehicle ICON in the middle box - an M1A2, an M915 - between
# Field V and Field H. Left out at the maintainer's own instruction,
# 2026-08-15: "drop the Field A, if required, user will insert
# additionally; lot of symbols where we have not included multiple
# fields". Field V, Field H and the W/W1 pair are all here.
CONVOY_MEASURE_TYPE_LABELS = {
    "moving_convoy": "Moving Convoy",
    "halted_convoy": "Halted Convoy",
}

CONVOY_MEASURE_TYPE_CODES = {
    "moving_convoy": "330100",
    "halted_convoy": "330200",
}

_CONVOY_END_MODES = {
    "moving_convoy": "moving",
    "halted_convoy": "halted",
}

# **Public, because Table H-XXIV's own Counterattack borrows them.**
# The maintainer's instruction there was "draw an arrow of same
# dimensions as moving convoy", and a shared name is what makes that
# true rather than a coincidence that drifts.
#
# **Both numbers are mine, not the standard's**, which gives neither -
# it draws the bar and the head to no stated proportion. Sized so one
# line of the shared 9 pt label sits inside the bar with room to spare,
# and so the head reads as a head rather than a spike. Single constants
# precisely because they are the kind of thing a smoke test moves.
CONVOY_BODY_HEIGHT_MM = 6.0
CONVOY_HEAD_LENGTH_MM = 6.0

# Where the W - W1 pair sits, below the bar.
_CONVOY_DTG_OFFSET_MM = CONVOY_BODY_HEIGHT_MM / 2.0 + 2.6

# **QGIS sizes an SVG marker by its WIDTH**, and the rear bar's own SVG
# is a thin, tall stroke - 10 units wide against 110 tall, its stroke
# width against the body plus one stroke. So the marker size that makes
# the bar exactly the BODY's height is that ratio of it, not the height
# itself. Sized as the height directly, it drew at a ninth of the bar it
# was meant to close.
CONVOY_REAR_BAR_WIDTH_MM = CONVOY_BODY_HEIGHT_MM * 10.0 / 110.0


def _convoy_body_layer(measure_type, side):

    """
    One long side of the bar, offset half its height off the centreline
    and stopped short of the end piece.

    setTrimDistanceEnd() rather than a shortened geometry: the trim is a
    PAGE distance, matching the head it has to clear, and QGIS applies
    it after projecting - so the bar meets the head at every zoom
    without the geometry itself having to know the scale.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(QColor(0, 0, 0))

    line_layer.setWidth(_LINE_WIDTH_MM)

    _apply_affiliation_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    line_layer.setOffset(side * CONVOY_BODY_HEIGHT_MM / 2.0)

    line_layer.setOffsetUnit(Qgis.RenderUnit.Millimeters)

    line_layer.setTrimDistanceEnd(CONVOY_HEAD_LENGTH_MM)

    line_layer.setTrimDistanceEndUnit(Qgis.RenderUnit.Millimeters)

    return line_layer


def _convoy_end_layer(mode, placement, length_mm):

    """
    An end piece, rotated with the line and pinned to its own vertex.

    A marker is CENTRED on the vertex it is placed at, so the head would
    otherwise hang half its length past PT1 - the same correction the
    range fans' north axis needed. setOffsetAlongLine() backs it off by
    half.
    """

    glyph = QgsSvgMarkerSymbolLayer("")

    glyph.setSize(length_mm)

    glyph.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            "mct_convoy_end_svg('{mode}', {length}, {colour})".format(
                mode=mode,
                length=(
                    1.0 if mode == "rear"
                    else length_mm / CONVOY_BODY_HEIGHT_MM
                ),
                colour=_ROUTE_GLYPH_COLOR_EXPRESSION,
            )
        )
    )

    marker = QgsMarkerSymbol()

    marker.changeSymbolLayer(0, glyph)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(placement)

    marker_line.setRotateSymbols(True)

    # POSITIVE at the last vertex: QGIS measures the offset backwards
    # along the line from the end, so a negative one pushes the glyph
    # PAST PT1 and leaves a gap the length of the head between it and
    # the bar - which is exactly what the first render showed.
    marker_line.setOffsetAlongLine(length_mm / 2.0)

    marker_line.setOffsetAlongLineUnit(Qgis.RenderUnit.Millimeters)

    return marker_line


def _convoy_symbol(measure_type):

    """One of the two convoys: the bar, its rear bar and its end piece."""

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, _convoy_body_layer(measure_type, 1))

    symbol.appendSymbolLayer(_convoy_body_layer(measure_type, -1))

    symbol.appendSymbolLayer(
        _convoy_end_layer(
            "rear",
            Qgis.MarkerLinePlacement.FirstVertex,
            CONVOY_REAR_BAR_WIDTH_MM,
        )
    )

    symbol.appendSymbolLayer(
        _convoy_end_layer(
            _CONVOY_END_MODES[measure_type],
            Qgis.MarkerLinePlacement.LastVertex,
            CONVOY_HEAD_LENGTH_MM,
        )
    )

    return symbol


# Field V and Field H, side by side inside the bar, exactly as the
# template stacks them - and nothing when both are empty, rather than a
# stray separator.
_CONVOY_LABEL_EXPRESSION = (
    "trim(upper(coalesce(\"equipment_type\",'')) || ' ' ||"
    " upper(coalesce(\"additional_information\",'')))"
)

# The W - W1 pair below it. The dash only appears when both ends are
# filled, so a start-only DTG does not read as an open-ended range.
_CONVOY_DTG_LABEL_EXPRESSION = (
    "CASE"
    " WHEN coalesce(\"dtg_start\",'') = '' AND coalesce(\"dtg_end\",'') = ''"
    " THEN ''"
    " WHEN coalesce(\"dtg_start\",'') = '' THEN upper(\"dtg_end\")"
    " WHEN coalesce(\"dtg_end\",'') = '' THEN upper(\"dtg_start\")"
    " ELSE upper(\"dtg_start\") || ' - ' || upper(\"dtg_end\")"
    " END"
)


_LINE_SYMBOL_BUILDERS = {
    measure_type: (lambda measure_type=measure_type:
                   _supply_route_symbol(measure_type))
    for measure_type in LINE_MEASURE_TYPE_LABELS
}

_LINE_SYMBOL_BUILDERS.update({
    measure_type: (lambda measure_type=measure_type:
                   _convoy_symbol(measure_type))
    for measure_type in CONVOY_MEASURE_TYPE_LABELS
})

# What the Lines layer's own dropdown offers: the eight routes and the
# two convoys, which are the whole of Table H-XXIII's "Sustainment
# Lines" section. Kept as a separate name from LINE_MEASURE_TYPE_LABELS
# because the route-only helpers above - abbreviations, traffic arrows,
# label offsets - are keyed by that one and a convoy has no entry in
# any of them.
ALL_LINE_MEASURE_TYPE_LABELS = dict(LINE_MEASURE_TYPE_LABELS)
ALL_LINE_MEASURE_TYPE_LABELS.update(CONVOY_MEASURE_TYPE_LABELS)


def _configure_lines_labeling(layer):

    """
    One label per feature, centred, upright and clear of the arrows.

    Upright rather than following the line, the same call already made
    for Table H-XIV's own bearing lines: a route drawn right-to-left or
    steeply downhill would otherwise read upside-down. That means an
    OverPoint label on the line's own centre rather than Line placement,
    and a per-variant vertical offset so it clears however many arrows
    are stacked underneath it.
    """

    from qgis.core import QgsRuleBasedLabeling

    root_rule = QgsRuleBasedLabeling.Rule(None)

    for measure_type in LINE_MEASURE_TYPE_LABELS:

        settings = _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            _LINE_LABEL_EXPRESSION,
            label_geometry_expression=(
                "line_interpolate_point($geometry, length($geometry) / 2)"
            ),
            quadrant=Qgis.LabelQuadrantPosition.Above,
        )

        settings.yOffset = -_label_offset_mm(measure_type)

        settings.offsetUnits = Qgis.RenderUnit.Millimeters

        rule = QgsRuleBasedLabeling.Rule(settings)

        rule.setFilterExpression(
            "\"measure_type\" = '{}'".format(measure_type)
        )

        rule.setDescription(measure_type)

        root_rule.appendChild(rule)

    # The convoys take two rules apiece: Field V and Field H inside the
    # bar, and the W - W1 pair below it. Centred and upright rather than
    # following the line, for the same reason the routes' own label is:
    # a convoy drawn right-to-left would otherwise read upside-down.
    for measure_type in CONVOY_MEASURE_TYPE_LABELS:

        for expression, offset_mm, suffix in (
            (_CONVOY_LABEL_EXPRESSION, 0.0, "fields"),
            (_CONVOY_DTG_LABEL_EXPRESSION, _CONVOY_DTG_OFFSET_MM, "dtg"),
        ):

            settings = _build_pal_layer_settings(
                layer,
                Qgis.LabelPlacement.OverPoint,
                expression,
                label_geometry_expression=(
                    "line_interpolate_point($geometry,"
                    " length($geometry) / 2)"
                ),
                quadrant=Qgis.LabelQuadrantPosition.Over,
            )

            if offset_mm:

                settings.yOffset = offset_mm

                settings.offsetUnits = Qgis.RenderUnit.Millimeters

            rule = QgsRuleBasedLabeling.Rule(settings)

            rule.setFilterExpression(
                "\"measure_type\" = '{}'".format(measure_type)
            )

            rule.setDescription(f"{measure_type}_{suffix}")

            root_rule.appendChild(rule)

    layer.setLabeling(QgsRuleBasedLabeling(root_rule))

    layer.setLabelsEnabled(True)


def create_supply_routes_lines_layer(name=LINES_LAYER_NAME):

    """Table H-XXIII's own eight supply routes, 330300-330403."""

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"LineString?crs={crs.authid()}",
        name,
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
            # Fields V, H and the W/W1 pair - the convoys' own
            # amplifiers. Blank on a supply route, which carries none
            # of them.
            QgsField("equipment_type", QMetaType.Type.QString),
            QgsField("additional_information", QMetaType.Type.QString),
            QgsField("dtg_start", QMetaType.Type.QString),
            QgsField("dtg_end", QMetaType.Type.QString),
            QgsField("length_km", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    measure_type_idx = layer.fields().indexOf("measure_type")

    layer.setEditorWidgetSetup(
        measure_type_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(ALL_LINE_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        measure_type_idx,
        QgsDefaultValue("'msr'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("length_km"),
        QgsDefaultValue("mct_length_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _LINE_SYMBOL_BUILDERS)
    )

    _configure_lines_labeling(layer)

    return layer


def add_supply_routes_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_supply_routes_lines_layer,
    )


def create_supply_points_layer(name=POINTS_LAYER_NAME):

    """Table H-XXIII's own eighteen point symbols, milsymbol-rendered."""

    return build_single_domain_point_layer(
        name,
        "control_measure",
        POINT_ENTITY_LABELS,
        "general_supply_point",
        include_echelon=False,
        include_headquarters=False,
        entity_designation_slots=POINT_DESIGNATION_SLOTS,
        extra_text_field=SUPPLY_CLASS_FIELD,
    )


def add_supply_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_supply_points_layer,
    )
