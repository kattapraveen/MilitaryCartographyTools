# -*- coding: utf-8 -*-

"""
Builds ready-to-use layers for MIL-STD-2525D Appendix H.5.19 (Table
H-XVII, "Target control measure symbols") - Mini-Phase H12, the twelfth
H.5.x logical group in this appendix-by-appendix pass.

**Points: this table's own nine entries, on their own POINTS layer**
(printed pages 525-536) - Point/Single Target (240601), Nuclear Target
(240602), Fire Support Station
(240900, under the table's own "Naval Gunfire" heading), and the whole
"Fires Points" sub-section (Firing 250100, Hide 250200, Launch 250300,
Reload 250400, Survey Control Point 250500). All nine were already in
sidc.py under these exact codes from an earlier pass; they moved off the
shared control_measure_points.py layer 2026-08-12, the same per-table
convention every other H.5.x group now follows. sidc.py's own entities
are untouched by the move.

**Fire Support Station was reported "missing" and was not** - the
entity, its code and its rendering were all already correct. Two things
made it easy to overlook, both fixed here: it was one line in a flat
~44-entry shared dropdown, and its own "FSS" text sits OUTSIDE the X
glyph, widening milsymbol's viewBox to 158 against its siblings' 108 -
so at a fixed 8mm marker width the X itself drew at about two-thirds
their scale, AND the X's own centre sat 25 viewBox units left of the
point QGIS anchors on. See _POINT_SIZE_MULTIPLIERS and
_FIRE_SUPPORT_STATION_OFFSET_RATIO; the same asymmetry, measured the
same way, as airspace_control_measures.py's own Pop-Up Point.

**Target-Recorded (240603) is deliberately NOT built** - it is marked
"(AEGIS Only)" in its own CONTROL MEASURE cell, and this project does
not ship AEGIS-only symbols. It was kept on the first pass, on the
reasoning that it draws a real icon rather than an AEGIS display
construct; that reasoning was overturned 2026-08-12 when the standing
rule was applied consistently across the whole appendix. See
docs/roadmap.md for the sweep that removed it and Airfield (131900).

**Lines: 3 new measure types**, all sharing the same perpendicular
end-tick construction confirmed against each one's own EXAMPLE column
(genuine black ticks touching each end, not grey illustrative
annotation - the same per-measure-type check this appendix has used
since Phase Line's own H3 precedent): Linear Target (240701, plain,
optional name - no fixed abbreviation), Linear Smoke Target (240702,
fixed "SMOKE" second line under an optional name), Final Protective
Fire (240703, fixed centred "FPF" - its own optional weapon-type/unit
info box, Fields T1/V, dropped per this appendix's usual "extra
descriptive field box" tolerance).

**Areas: 5 new measure types**, each folding an Irregular/Rectangle/
Circular SIDC code triple into one (the same reasoning used throughout
this appendix): Area Target (240801/240802/240803, a bare name with NO
fixed prefix - unlike most other prefixed areas in this appendix,
confirmed by its own EXAMPLE column showing only a raw designation like
"PC9008"), Series or Group of Targets (240805, also a bare name -
its own template shows individual target-designator crosses inside the
boundary, each one a SEPARATE already-covered point/line/area target
feature the user places on this module's own other layers, not part of
this boundary's own drawn geometry, so only the boundary + name is
built - and its name sits ON the top of that boundary with the line
masked around it, as all four of its own examples draw it, not centred
inside like every other area here), Smoke (240806 present/240807 planned - folds cleanly onto this
project's own existing status field, since the standard's own two codes
ARE exactly a present/planned pair, unlike this appendix's other
"genuinely separate code, not status-driven" fixed-dash constructions;
fixed "SMOKE" label plus an optional name), Bomb Area (240808, fixed
"BOMB" label, no name field in the standard's own template), Fire
Support Area (241001/241002/241003, "FSA" prefix + optional name).

**Two entries skipped outright**: **Rectangular Target - Single Target
(240804, AEGIS Only)** needs a fixed compound icon (a diamond outline
with a permanently-upright cross-target glyph centred inside) anchored
to one point with a fixed orientation regardless of the area's own
rotation - a genuinely different, AEGIS-combat-system-specific
construction from this project's usual freeform-polygon model, the
same "(AEGIS only)" curation already applied throughout H8/H9's own
Maritime Control Measures mini-phase.

Military Cartography Tools
"""

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
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    POINT_AFFILIATION_LABELS,
    STATUS_LABELS,
    _PLAIN_DESIGNATION_LABEL_EXPRESSION,
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


LINES_LAYER_NAME = "Target Control Measures (Lines)"
AREAS_LAYER_NAME = "Target Control Measures (Areas)"
POINTS_LAYER_NAME = "Target Control Measures (Points)"

__all__ = [
    "LINES_LAYER_NAME",
    "AREAS_LAYER_NAME",
    "POINTS_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AREA_MEASURE_TYPE_LABELS",
    "POINT_ENTITY_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_target_control_measures_lines_layer",
    "create_target_control_measures_areas_layer",
    "create_target_control_measures_points_layer",
    "add_target_control_measures_lines_layer",
    "add_target_control_measures_areas_layer",
    "add_target_control_measures_points_layer",
]

LINE_MEASURE_TYPE_LABELS = {
    "linear_target": "Linear Target",
    "linear_smoke_target": "Linear Smoke Target",
    "final_protective_fire": "Final Protective Fire (FPF)",
}

# Linear Smoke Target and Final Protective Fire both draw a two-line
# label straddling the line - the designation ABOVE it, the fixed word
# ("SMOKE"/"FPF") BELOW - which is what the OnLine placement flag gives
# for free, since it centres the whole block vertically on the line.
#
# **A blank designation has to stay a blank LINE, not disappear.** Drop
# it and the label collapses to one line, which OnLine then centres ON
# the line, striking it through - the maintainer's own report ("in case
# user does not provide any unique designation, the render overlaps the
# lines, so maybe default to a ' ' fixed blank space?"). nullif(...,'')
# turns an empty field into NULL so coalesce can substitute the space.
_BLANK_LINE_DESIGNATION = (
    "coalesce(nullif(" + _PLAIN_DESIGNATION_LABEL_EXPRESSION + ", ''), ' ')"
)

_LINE_DESIGNATION_LABEL_EXPRESSION = (
    "CASE "
    "WHEN \"measure_type\" = 'linear_target' THEN "
    "CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    " WHEN \"measure_type\" = 'linear_smoke_target' THEN "
    f"{_BLANK_LINE_DESIGNATION} || '\\n' || 'SMOKE'"
    " WHEN \"measure_type\" = 'final_protective_fire' THEN "
    f"{_BLANK_LINE_DESIGNATION} || '\\n' || 'FPF'"
    " ELSE '' END"
)

# Linear Target carries a single-line label and its own example (page
# 526, "LA2961") puts it clear ABOVE the line - "unique designation
# should be above the line not on it". The other two straddle instead,
# so they keep the shared OnLine default.
_ABOVE_LINE_TYPES = ("linear_target",)

_STRADDLING_LINE_TYPES = ("linear_smoke_target", "final_protective_fire")



def _end_tick_layer(placement):

    """
    A small perpendicular tick at each line end - the same
    QgsMarkerLineSymbolLayer "line"-shape-at-angle-0 technique already
    confirmed for maneuver_control_measures.py's own Phase Line -
    reused here since Linear Target/Linear Smoke Target/Final
    Protective Fire's own EXAMPLE columns all show the same genuine
    black end tick.
    """

    tick_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "line",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "outline_width": "0.6",
            "size": "3",
            "angle": "0",
        }
    )

    _apply_affiliation_color(
        tick_marker.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    tick_layer = QgsMarkerLineSymbolLayer(True)

    tick_layer.setSubSymbol(
        tick_marker
    )

    tick_layer.setPlacements(
        placement
    )

    return tick_layer


def _ticked_line_symbol():

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        0.4
    )

    _apply_affiliation_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    for placement in (
        Qgis.MarkerLinePlacement.FirstVertex,
        Qgis.MarkerLinePlacement.LastVertex,
    ):

        symbol.appendSymbolLayer(
            _end_tick_layer(placement)
        )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "linear_target": _ticked_line_symbol,
    "linear_smoke_target": _ticked_line_symbol,
    "final_protective_fire": _ticked_line_symbol,
}


AREA_MEASURE_TYPE_LABELS = {
    "area_target": "Area Target",
    "series_or_group_of_targets": "Series or Group of Targets",
    "smoke": "Smoke",
    "bomb_area": "Bomb Area",
    "fire_support_area": "Fire Support Area (FSA)",
}

_AREA_DESIGNATION_LABEL_EXPRESSION = (
    "CASE "
    "WHEN \"measure_type\" IN ('area_target', 'series_or_group_of_targets') THEN "
    "CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    " WHEN \"measure_type\" = 'smoke' THEN "
    "CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" {_PLAIN_DESIGNATION_LABEL_EXPRESSION} || '\\n' ELSE '' END"
    " || 'SMOKE'"
    " WHEN \"measure_type\" = 'bomb_area' THEN 'BOMB'"
    " WHEN \"measure_type\" = 'fire_support_area' THEN "
    "'FSA' || CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" ' ' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    " ELSE '' END"
)


# Series or Group of Targets is the only area here whose own label sits
# ON its boundary rather than inside it (its examples - "OWL", "RED",
# "C7F", "M9W" on page 531 - all straddle the top of the outline with
# the line broken around them), so it is the only one that needs a
# maskable outline.
_SERIES_OR_GROUP_OUTLINE_SYMBOL_LAYER_ID = "series_or_group_outline"

_MASKED_AREA_SYMBOL_LAYER_IDS = [
    _SERIES_OR_GROUP_OUTLINE_SYMBOL_LAYER_ID,
]

# Top-centre of the shape's own bounding box. Unlike H7's freeform
# zones, this only has to be ON the boundary rather than strictly
# INSIDE a possibly-concave one, so the bounding box is enough and
# mct_area_label_anchor()'s clipping is not needed.
_SERIES_OR_GROUP_LABEL_ANCHOR = (
    "make_point("
    "(x_min($geometry) + x_max($geometry)) / 2,"
    " y_max($geometry)"
    ")"
)


def _series_or_group_symbol():

    symbol = _status_driven_area_outline_symbol()

    symbol.symbolLayer(0).setId(
        _SERIES_OR_GROUP_OUTLINE_SYMBOL_LAYER_ID
    )

    return symbol


_AREA_SYMBOL_BUILDERS = {
    "area_target": _status_driven_area_outline_symbol,
    "series_or_group_of_targets": _series_or_group_symbol,
    "smoke": _status_driven_area_outline_symbol,
    "bomb_area": _status_driven_area_outline_symbol,
    "fire_support_area": _status_driven_area_outline_symbol,
}


def _measure_type_filter(measure_types):

    return " OR ".join(
        f"\"measure_type\" = '{measure_type}'"
        for measure_type in measure_types
    )


def _configure_lines_labeling(layer):

    """
    Two placements, so two rules (2026-08-12, from the maintainer's own
    live testing):

    - **Linear Target sits ABOVE the line** - "unique designation should
      be above the line not on it". Its label is a single line, and the
      shared OnLine default centres a single line ON the line, striking
      it through. AboveLine lifts it clear, matching its own example.
    - **Linear Smoke Target and Final Protective Fire straddle it**,
      designation above and "SMOKE"/"FPF" below, which is what OnLine
      gives for free on a two-line label - and what both their own
      examples show ("VB1910"/"SMOKE", "QC1968"/"FPF"). Final Protective
      Fire had no designation at all until now; it does, on the same
      terms as Smoke, per the maintainer.
    """

    above_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _LINE_DESIGNATION_LABEL_EXPRESSION,
            line_placement_flags=Qgis.LabelLinePlacementFlag.AboveLine
        )
    )

    above_rule.setFilterExpression(
        _measure_type_filter(_ABOVE_LINE_TYPES)
    )

    straddling_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _LINE_DESIGNATION_LABEL_EXPRESSION
        )
    )

    straddling_rule.setFilterExpression(
        _measure_type_filter(_STRADDLING_LINE_TYPES)
    )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    root_rule.appendChild(above_rule)
    root_rule.appendChild(straddling_rule)

    layer.setLabeling(
        QgsRuleBasedLabeling(root_rule)
    )

    layer.setLabelsEnabled(
        True
    )


def _configure_areas_labeling(layer):

    """
    Four of the five areas label centred inside the shape. Series or
    Group of Targets labels ON its own boundary instead, at the top,
    with the outline masked so the line breaks around the text -
    "the unique designator should be on the perimeter with suitable
    mask so that line does not overlap the text", and what its own
    examples on page 531 draw.

    Both rules declare the same masked-id list: masking is configured
    per QGIS layer rather than per rule, and differing lists make QGIS
    keep one arbitrarily. It is a harmless no-op for the centred rule,
    whose text sits nowhere near the outline.
    """

    centred_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            _AREA_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_MASKED_AREA_SYMBOL_LAYER_IDS
        )
    )

    # Explicit filter rather than setIsElse(True) - an else-flagged
    # rule's own sub-provider still labels the rows the other rule
    # matched, which would give every Series or Group feature a second,
    # centred label. Established in c2_measures.py's own area labelling.
    centred_rule.setFilterExpression(
        "\"measure_type\" IS NULL"
        " OR \"measure_type\" != 'series_or_group_of_targets'"
    )

    perimeter_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            _AREA_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_MASKED_AREA_SYMBOL_LAYER_IDS,
            # Wider than the 1.2 default. QGIS's mask is GLYPH-shaped,
            # not a box, so at the default buffer the outline still
            # showed through the enclosed counter of a round letter -
            # an "OWL" label had the boundary line visible inside its
            # own "O" (caught by render; the mask looked fine
            # everywhere else). A wider buffer closes those counters.
            mask_size_mm=2.4,
            label_geometry_expression=_SERIES_OR_GROUP_LABEL_ANCHOR,
            quadrant=Qgis.LabelQuadrantPosition.Over
        )
    )

    perimeter_rule.setFilterExpression(
        _measure_type_filter(("series_or_group_of_targets",))
    )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    root_rule.appendChild(centred_rule)
    root_rule.appendChild(perimeter_rule)

    layer.setLabeling(
        QgsRuleBasedLabeling(root_rule)
    )

    layer.setLabelsEnabled(
        True
    )


def create_target_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Table H-XVII's own 3 line measure
    types - see this module's own docstring for the full list.
    """

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
            QgsField("length_km", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    measure_type_idx = layer.fields().indexOf("measure_type")

    layer.setEditorWidgetSetup(
        measure_type_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(LINE_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        measure_type_idx,
        QgsDefaultValue("'linear_target'")
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


def create_target_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Table H-XVII's own 5 area measure
    types - see this module's own docstring for the full list and for
    which Irregular/Rectangle/Circular code triples were folded into
    each one.
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
            QgsField("perimeter_km", QMetaType.Type.Double),
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
        QgsDefaultValue("'area_target'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("area_km2"),
        QgsDefaultValue("mct_area_km2($geometry)", True)
    )

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("perimeter_km"),
        QgsDefaultValue("mct_perimeter_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _AREA_SYMBOL_BUILDERS)
    )

    _configure_areas_labeling(layer)

    return layer


def add_target_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_target_control_measures_lines_layer
    )


def add_target_control_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_target_control_measures_areas_layer
    )


# --------------------------------------------------------------------
# Points (Table H-XVII's own point vocabulary, printed pages 525-536) -
# milsymbol-rendered icons, not hand-built symbology. Moved here
# 2026-08-12 out of the shared control_measure_points.py layer, the
# same per-table convention every other H.5.x group now follows.
# --------------------------------------------------------------------

# Nine entries, in the table's own code order, grouped by its own
# sub-headings. Every one was already in sidc.py under these exact
# codes and already rendered correctly - the "missing" report was about
# them being hard to find in a flat ~44-entry shared dropdown, plus
# Fire Support Station specifically drawing too small to spot (see
# _POINT_SIZE_MULTIPLIERS).
#
POINT_ENTITY_LABELS = {
    # Point Targets
    "point_target": "Point/Single Target",
    "nuclear_target": "Nuclear Target",
    # Naval Gunfire
    "fire_support_station": "Fire Support Station (FSS)",
    # Fires Points
    "firing_point": "Firing Point",
    "hide_point": "Hide Point",
    "launch_point": "Launch Point",
    "reload_point": "Reload Point",
    "survey_control_point": "Survey Control Point",
}

# NOT dict(AFFILIATION_LABELS), which is what this was until
# 2026-08-12. That shared dict carries a fifth value, "Unspecified
# (black)", correct for the hand-drawn lines/areas layers - where
# affiliation only picks a Qt colour - but not a SIDC standard
# identity, so on this milsymbol-rendered Points layer choosing it made
# build_sidc() raise and milsymbol drew its unknown-icon fallback. The
# default here was already 'friend', so nothing was broken as shipped;
# the attribute form simply offered one menu entry that silently broke
# the symbol. See POINT_AFFILIATION_LABELS in _control_measure_shared.py.
_POINT_AFFILIATION_LABELS = POINT_AFFILIATION_LABELS

_POINT_STATUS_LABELS = dict(STATUS_LABELS)

_POINTS_DEFAULT_MARKER_SIZE_MM = 8.0

# Fire Support Station draws its own "FSS" text OUTSIDE the X glyph, to
# the right, so milsymbol's viewBox for it is 158 wide where its
# siblings' are 108 - and QGIS reads a marker's size as its WIDTH, so at
# a fixed 8mm the X itself draws at about two-thirds their scale. That
# is the whole of the "Fire support station symbol is missing" report:
# the entity, its code and its rendering were all already correct, it
# was just small enough to overlook. 158/108 restores the X to the same
# on-screen size as any other icon here.
#
# Same class of problem as airspace_control_measures.py's own Pop-Up
# Point, and measured the same way (probe render, reading the drawn
# path's real extent rather than eyeballing it).
_POINT_SIZE_MULTIPLIERS = {
    "fire_support_station": 158.0 / 108.0,
}

_POINT_SIZE_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"entity\" = '{entity}' THEN {_POINTS_DEFAULT_MARKER_SIZE_MM * multiplier}"
    for entity, multiplier in _POINT_SIZE_MULTIPLIERS.items()
) + f" ELSE {_POINTS_DEFAULT_MARKER_SIZE_MM} END"

# The other half of the same asymmetry: because "FSS" hangs to the
# right, the X's own centre (x=100, measured off the rendered path) sits
# 25 viewBox units LEFT of the viewBox centre (x=125) that QGIS puts the
# feature's coordinate on. The standard anchors the X - "the center
# point defines/is the center of the symbol" - so the marker shifts
# right by those 25 units, expressed as a fraction of its own width so
# it tracks _POINT_SIZE_MULTIPLIERS rather than going stale.
_FIRE_SUPPORT_STATION_OFFSET_RATIO = 25.0 / 158.0

_POINT_OFFSET_EXPRESSION = (
    "CASE WHEN \"entity\" = 'fire_support_station' THEN '"
    + "%.4f" % (
        _POINTS_DEFAULT_MARKER_SIZE_MM
        * _POINT_SIZE_MULTIPLIERS["fire_support_station"]
        * _FIRE_SUPPORT_STATION_OFFSET_RATIO
    )
    + ",0' ELSE '0,0' END"
)

# Firing/Hide/Launch/Reload/Survey Control Point all share the box+cone
# construction whose own anchor is the TIP at the bottom (rendered
# viewBox 56 -64 88 168, identical to Point of Departure's, which
# offensive_control_measures.py already anchors this way). The four
# target/station icons are centred instead.
_POINT_VERTICAL_ANCHOR_EXPRESSION = (
    "CASE WHEN \"entity\" IN ("
    "'firing_point','hide_point','launch_point',"
    "'reload_point','survey_control_point'"
    ") THEN 'bottom' ELSE 'center' END"
)

_POINTS_SIDC_EXPRESSION = (
    "mct_sidc_svg(mct_build_sidc("
    "\"affiliation\",\"entity\",'control_measure','unspecified',"
    "\"status\",false),"
    "upper(coalesce(\"unique_designation\",'')),"
    "'uniqueDesignation'"
    ")"
)


def _configure_points_attribute_form(layer):

    fields = layer.fields()

    affiliation_idx = fields.indexOf("affiliation")
    entity_idx = fields.indexOf("entity")
    status_idx = fields.indexOf("status")

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_POINT_AFFILIATION_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        entity_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(POINT_ENTITY_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        status_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_POINT_STATUS_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(affiliation_idx, QgsDefaultValue("'friend'"))
    layer.setDefaultValueDefinition(entity_idx, QgsDefaultValue("'point_target'"))
    layer.setDefaultValueDefinition(status_idx, QgsDefaultValue("'present'"))


def _build_points_renderer():

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(
        _POINTS_DEFAULT_MARKER_SIZE_MM
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(_POINTS_SIDC_EXPRESSION)
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        QgsProperty.fromExpression(_POINT_SIZE_EXPRESSION)
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Offset,
        QgsProperty.fromExpression(_POINT_OFFSET_EXPRESSION)
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.VerticalAnchor,
        QgsProperty.fromExpression(_POINT_VERTICAL_ANCHOR_EXPRESSION)
    )

    symbol.changeSymbolLayer(
        0,
        svg_layer
    )

    return QgsSingleSymbolRenderer(symbol)


def create_target_control_measures_points_layer(name=POINTS_LAYER_NAME):

    """
    A fresh, empty point layer for Table H-XVII's own nine point
    entries - see POINT_ENTITY_LABELS for the list and for what the
    move out of control_measure_points.py did and did not change.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        name,
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("entity", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
        ]
    )

    layer.updateFields()

    _configure_points_attribute_form(layer)

    layer.setRenderer(
        _build_points_renderer()
    )

    return layer


def add_target_control_measures_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_target_control_measures_points_layer
    )
