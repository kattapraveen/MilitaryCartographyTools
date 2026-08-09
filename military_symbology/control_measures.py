# -*- coding: utf-8 -*-

"""
Builds ready-to-use control-measure layers - one for line-type measures,
one for area-type measures - each styled via a QgsRuleBasedRenderer keyed
on a "measure_type" field, mirroring grid/mgrs_sub_grid.py's own
rule-based renderer pattern.

**2026-08-09: trimmed down to only what the appendix-by-appendix
completion plan has actually re-verified against the real standard so
far.** Both layers previously carried ~26 measure types built during an
earlier, less rigorous stage-based pass (2026-07-xx original five, then
2026-08-07's H.5.11-H.5.14/H.5.26 batch) - none of that work had been
checked against the standard's own template PICTURES the way the
appendix-by-appendix pass now requires (render the actual PDF page,
compare against the plugin's own offscreen render), and Mini-Phase H0's
own re-audit of just ONE of those 26 (Boundary) found it was built
entirely wrong (an invented dash-dash-dot pattern with no echelon/
designation content at all - see _boundary_symbol()'s own docstring).
Rather than leave 25 more unverified measure types sitting in the same
dropdown as the one that's actually been checked - which made it hard to
tell, while testing, whether a given shape was "real" or still a
placeholder - every measure type this module doesn't yet have a verified
answer for was removed outright (not commented out; git history has the
old code if a future sub-phase wants to compare against it). Each
Appendix H sub-phase (H1-H22, see docs/roadmap.md) adds its own measure
types back in, freshly built against the real template pictures, as it's
completed - the same discipline every other appendix (B-G, J, L) already
went through, just applied to control measures for the first time here.
Right now that means exactly one line measure type (Boundary, H.5.5) and
zero area measure types - Objective/NAI, Battle Position, Strong Point,
etc. all belong to sub-phases that haven't run yet.

The COLOURING is verified directly against the standard's own H.5.1.1.1/
H.5.3 Coloring rules (read from the actual MIL-STD-2525D PDF, not a
paraphrase). This module uses its own AFFILIATION_LABELS vocabulary -
friend/hostile/neutral/unknown, PLUS "unspecified" (a 5th value sidc.py's
own point-symbol AFFILIATIONS deliberately doesn't have - see that
constant's own comment) - and colours friend=blue, hostile=red,
neutral=green, unknown=yellow, unspecified=black (also the default
affiliation) - a data-defined colour expression applied on top of each
measure type's own shape, not a rule-tree branch per affiliation.
_apply_affiliation_color() wires this the same way for every symbol
layer; none hardcode black.

Two separate layers, not one, because a QgsVectorLayer is always a single
geometry type - there's no "LineString or Polygon" layer in QGIS.

**2026-08-09: Mini-Phase H0 (H.5.1-H.5.4 general rules + H.5.5
Boundaries)**, the first mini-phase of the appendix-by-appendix
completion plan's own Appendix H pass (see docs/roadmap.md). Re-auditing
H.5.1-H.5.4 against the actual standard text (not assumed from the
previous pass) found two real, general defects, both fixed here:
  - **H.5.1.1.1/H.5.3 Coloring was wrong for neutral/unknown affiliation**
    - see AFFILIATION_LABELS/DEFAULT_AFFILIATION's own comments for the
    full citation and fix (neutral=green, unknown=yellow, not both
    folded into "black as standard").
  - **H.5.4 Labeling's "all text labeling shall be in upper case
    letters" was never implemented** - now applied via upper() in every
    designation label expression (_PLAIN_DESIGNATION_LABEL_EXPRESSION/
    _BOUNDARY_DESIGNATION_LABEL_EXPRESSION), regardless of what case the
    user actually types.
Two further H fields - STATUS_LABELS (H.5.1.1.3/Table H-I: present=
solid, planned=dashed) and ECHELON_LABELS (H.5.1.1.6, Table D-III of the
Land appendix) - were added to the Lines layer's schema, since Boundary
needs both; every future measure type can reuse the same two fields
rather than each reinventing them. Boundary itself was rebuilt from an
invented dash-dash-dot placeholder into the real Table H-III
construction: a status-driven solid/dashed line (see
_STATUS_LINE_STYLE_EXPRESSION) with the near designation, Field B
echelon glyph (Table D-III), and far designation stacked as one repeating
label along the line, QGIS's own Selective Masking cutting a genuine
gap in the line under whatever that label renders - see
_boundary_symbol()'s and _configure_designation_labeling()'s own
docstrings for the construction (including two earlier, wrong echelon-
glyph attempts before masking) and what's still approximated (an
interval-based repeat standing in for the standard's own per-segment
repeat rule, no attempt at Figure H-3's compass-relative label rotation,
no monochrome "ENY" fallback). sidc.py's own ECHELONS (and every
point-symbol layer's Echelon dropdown, via _point_symbol_layer.py's
_ECHELON_LABELS) gained the three highest Table D-III levels - Army
Group, Theater, Command - that had been missing entirely since
sub-phase 10.1, found while reading H.5.1.1.6's own cross-reference to
that table.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsLineSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsRuleBasedRenderer,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsSymbolLayerReference,
    QgsTextMaskSettings,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ..core._layer_utils import add_layer_at_default_position
from ..core.text_format import build_text_format


LINES_LAYER_NAME = "Tactical Graphics - Control Measures (Lines)"
AREAS_LAYER_NAME = "Tactical Graphics - Control Measures (Areas)"

LABEL_FONT_SIZE = 9

# H.5.5 Boundaries is the only line measure type re-verified against the
# real standard so far (Mini-Phase H0) - see this module's own docstring
# for why every other measure type from the earlier, unverified pass was
# removed rather than left alongside it.
LINE_MEASURE_TYPE_LABELS = {
    "boundary": "Boundary",
}

# No area measure type has been through the appendix-by-appendix
# re-verification pass yet - Objective/NAI (H.5.9/H.5.10, Mini-Phase H2),
# Battle Position/Strong Point/Engagement Area (H.5.12.1, Mini-Phase H4),
# Assembly Area (H.5.11, Mini-Phase H3), and Encirclement (H.5.14,
# Mini-Phase H6) all belong to sub-phases that haven't run yet - see this
# module's own docstring.
AREA_MEASURE_TYPE_LABELS = {}

# Keys match sidc.py's own AFFILIATIONS (the same "standard identity"
# concept MIL-STD-2525D uses for units) PLUS one extra value,
# "unspecified", that sidc.py's own AFFILIATIONS deliberately does not
# have - see DEFAULT_AFFILIATION's own comment for why control measures
# genuinely need a 5th value point symbols don't.
AFFILIATION_LABELS = {
    "friend": "Friend",
    "hostile": "Hostile",
    "neutral": "Neutral",
    "unknown": "Unknown",
    "unspecified": "Unspecified (black)",
}

# **2026-08-09 correction, found while re-auditing H.5.1-H.5.4 for
# Appendix H's Mini-Phase H0**: the actual standard text (H.5.1.1.1
# Standard identity (color rules)) reads "For color systems, control
# measures shall be black, blue (friendly), red (hostile), green
# (neutral or obstacles), or yellow (unknown or ... CBRN ...)" - five
# colours, four of them paired one-to-one with an affiliation and the
# fifth (black) standing alone with no affiliation named at all. The
# previous version of this module (and DEFAULT_AFFILIATION="unknown")
# read that black as a blanket "everything except friend/hostile"
# fallback, which is wrong on two counts: it silently miscoloured every
# neutral control measure (should be green) and every unknown one
# (should be yellow) as black, and it had no way to express the
# standard's actual 5th colour (a control measure with no standard
# identity asserted at all) without hijacking "unknown" for double duty.
# Point symbols don't have this problem (milsymbol.js already correctly
# renders friend=blue/hostile=red/neutral=green/unknown=yellow per the
# base standard's own Table XV/XVI, with no "black" option at all - see
# sidc.py) - only control measures get a genuine 5th colour, per this
# appendix's own H.5.1.1.1 text, which is why AFFILIATION_LABELS is
# intentionally NOT identical to sidc.py's AFFILIATIONS any more (see
# TestAffiliationLabelsCoverSidcsAffiliations in tests/test_control_
# measures.py for the guard this implies instead of a strict equality
# check).
DEFAULT_AFFILIATION = "unspecified"

_AFFILIATION_COLOR_EXPRESSION = (
    "CASE "
    "WHEN \"affiliation\" = 'friend' THEN color_rgb(0, 0, 255) "
    "WHEN \"affiliation\" = 'hostile' THEN color_rgb(255, 0, 0) "
    "WHEN \"affiliation\" = 'neutral' THEN color_rgb(0, 255, 0) "
    "WHEN \"affiliation\" = 'unknown' THEN color_rgb(255, 255, 0) "
    "ELSE color_rgb(0, 0, 0) "
    "END"
)

# Per H.5.1.1.3 Status/Table H-I: linear and area control measures are
# solid when "present" and dashed when "planned"/"anticipated"/
# "suspected"/"on order" (the standard's own text notes exceptions,
# e.g. counterattack, drawn dashed even when present - not modelled
# here, since no counterattack measure type exists yet). Added to the
# Lines layer's schema in Mini-Phase H0 (2026-08-09) because Boundary's
# own rebuild needs it (Table H-III has explicit Present/Planned rows
# per affiliation); every future line measure type can reuse this same
# field rather than reinventing it.
STATUS_LABELS = {
    "present": "Present",
    "planned": "Planned / Anticipated / On Order",
}

DEFAULT_STATUS = "present"

_STATUS_LINE_STYLE_EXPRESSION = (
    "CASE WHEN \"status\" = 'planned' THEN 'dash' ELSE 'solid' END"
)

# Per H.5.1.1.6 Echelon indicator: "used to show the element echelon on
# boundary lines, lines and areas... listed in table D-III of the land
# appendix" - the same 14-level vocabulary sidc.py's own ECHELONS uses
# for point symbols (extended 2026-08-09 to cover all of Table D-III,
# see that dict's own comment), reused here by KEY (not value - Table
# D-III's glyphs, not the SIDC numeric echelon/mobility codes, are what
# actually gets drawn on a boundary line). Added to the Lines layer's
# schema in Mini-Phase H0 for Boundary; every future line/area measure
# type can reuse this same field rather than reinventing it.
ECHELON_LABELS = {
    "team_crew": "Team/Crew",
    "squad": "Squad",
    "section": "Section",
    "platoon": "Platoon/Detachment",
    "company": "Company/Battery/Troop",
    "battalion": "Battalion/Squadron",
    "regiment": "Regiment/Group",
    "brigade": "Brigade",
    "division": "Division",
    "corps": "Corps",
    "army": "Army",
    "army_group": "Army Group",
    "theater": "Theater",
    "command": "Command",
}

# Table D-III's own literal amplifier glyphs (not the SIDC numeric
# echelon codes - see ECHELON_LABELS' own comment). "Ø" (team/crew) and
# "•"/"••"/"•••" (squad/section/platoon) are exactly what the standard's
# own table prints, confirmed by rendering the actual PDF page (172) as
# an image rather than trusting extracted text (which OCRs "Ø" as "0"
# and "•" as "."). "++" (Command) is likewise the standard's own glyph,
# not this project's invention.
_ECHELON_GLYPHS = {
    "team_crew": "Ø",
    "squad": "•",
    "section": "••",
    "platoon": "•••",
    "company": "I",
    "battalion": "II",
    "regiment": "III",
    "brigade": "X",
    "division": "XX",
    "corps": "XXX",
    "army": "XXXX",
    "army_group": "XXXXX",
    "theater": "XXXXXX",
    "command": "++",
}

# Resolves "echelon" to its Table D-III glyph as plain text - embedded
# as the middle line of _BOUNDARY_DESIGNATION_LABEL_EXPRESSION below (not
# a font-marker Character property; see _boundary_symbol()'s own comment
# for why the echelon glyph is rendered as part of the label, not a
# separate symbol layer).
_ECHELON_CHARACTER_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"echelon\" = '{key}' THEN '{glyph}'"
    for key, glyph in _ECHELON_GLYPHS.items()
) + " ELSE '' END"

# _boundary_symbol()'s own line symbol layer's stable id - referenced by
# _configure_designation_labeling()'s own QgsSymbolLayerReference so the
# boundary label's mask knows which symbol layer to cut a hole in.
_BOUNDARY_LINE_SYMBOL_LAYER_ID = "boundary_line"


def _apply_affiliation_color(symbol_layer, properties):

    """
    Makes the given symbol_layer's colour properties (e.g. StrokeColor,
    FillColor) data-defined by _AFFILIATION_COLOR_EXPRESSION, so every
    control measure's own "affiliation" attribute drives its colour
    automatically - the same data-defined-property pattern
    unit_layer.py's own SIDC rendering already uses, rather than
    QgsRuleBasedRenderer rules per affiliation (which would multiply
    the existing measure_type rule tree by every affiliation value for
    no benefit, since only colour - not shape - varies by affiliation).
    """

    color_property = QgsProperty.fromExpression(_AFFILIATION_COLOR_EXPRESSION)

    for property_key in properties:

        symbol_layer.setDataDefinedProperty(
            property_key,
            color_property
        )


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _value_map_with_none(labels, none_label="(Not shown)"):

    """
    Same as _value_map(), plus a leading `none_label` -> "" entry - same
    "no value selected must be an explicit, selectable option" reasoning
    as _point_symbol_layer.py's own helper of the same name (this
    module's echelon field, used only by Boundary so far, has no
    equivalent reason to force a value onto every other measure type).
    """

    result = {none_label: ""}

    result.update(_value_map(labels))

    return result


def _boundary_symbol():

    """
    Table H-III. Rebuilt 2026-08-09 (Mini-Phase H0) after comparing the
    previous version - an invented dash-dash-dot pattern with no
    echelon/designation content at all - against the actual template
    picture (page 395): a Present boundary is a plain SOLID line and a
    Planned/On Order one is DASHED (H.5.1.1.3/Table H-I, see
    _STATUS_LINE_STYLE_EXPRESSION).

    The Field B echelon amplifier and the two units' own designations
    (Field T/AS) are NOT built here as symbol layers at all - see
    _configure_designation_labeling()'s own comment for why they're all
    folded into a single, masked, repeating LABEL instead. This function
    only builds the line itself, but gives its one symbol layer a stable
    `.setId()` (_BOUNDARY_LINE_SYMBOL_LAYER_ID) so that label masking can
    target it specifically by reference.

    This function went through three real, wrong attempts at the
    echelon glyph before landing on labelling+masking, each one caught by
    the project maintainer rendering a real boundary over a non-white
    (terrain) background rather than QGIS's own white canvas default -
    text alone never surfaced any of these, only rendering did:
      1. A bordered white square behind the glyph (obviously a box
         against colour - Table H-III's own EXAMPLE column shows a clean
         line GAP, no box of any kind).
      2. Dropping just the border, keeping a solid white fill (still
         plainly a flat white rectangle against anything but a white
         background - the fill itself was the problem, not the outline).
      3. A white HALO around the glyph's own character outline (a stroke
         on QgsFontMarkerSymbolLayer, no background shape at all) - closer
         in spirit, but QGIS's own font-glyph stroke rendering produced a
         messy, spiky white burst around "X" rather than a clean hourglass
         gap, confirmed by the maintainer's own live-QGIS screenshot (not
         reproduced in this project's own offscreen renders, which looked
         fine - real-world font rendering differed enough to matter).
    The actual fix: QGIS's own Selective Masking feature
    (QgsTextMaskSettings + QgsSymbolLayerReference) - the label engine
    genuinely cuts a hole in the referenced symbol layer's own rendered
    geometry, in the exact shape of the rendered text, at every position
    the text renders in the entire label pass. This lets whatever is
    actually underneath (terrain, imagery, other layers) show through
    correctly, is crisp for any glyph width (no adjacent-character
    blur), and requires no bespoke shape-fitting per echelon level - the
    correct tool for this job, not an approximation of one.
    """

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

    line_layer.setId(
        _BOUNDARY_LINE_SYMBOL_LAYER_ID
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "boundary": _boundary_symbol,
}

_AREA_SYMBOL_BUILDERS = {}


def _build_rule_based_renderer(root_symbol, symbol_builders):

    root_rule = QgsRuleBasedRenderer.Rule(None)

    for measure_type, build_symbol in symbol_builders.items():

        rule = QgsRuleBasedRenderer.Rule(
            build_symbol()
        )

        rule.setFilterExpression(
            f'"measure_type" = \'{measure_type}\''
        )

        rule.setLabel(
            measure_type
        )

        root_rule.appendChild(
            rule
        )

    return QgsRuleBasedRenderer(root_rule)


def _configure_affiliation_field(layer):

    """
    Shared by both layers - a "Friend"/"Hostile"/"Neutral"/"Unknown"/
    "Unspecified (black)" ValueMap dropdown driving
    _AFFILIATION_COLOR_EXPRESSION, defaulting to DEFAULT_AFFILIATION
    ("unspecified", which renders black - see that constant's own
    comment for why this is a genuine 5th value, not "unknown" doing
    double duty).
    """

    affiliation_idx = layer.fields().indexOf("affiliation")

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(AFFILIATION_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        affiliation_idx,
        QgsDefaultValue(f"'{DEFAULT_AFFILIATION}'")
    )


def _configure_status_field(layer):

    """
    "Present"/"Planned / Anticipated / On Order" ValueMap dropdown - see
    STATUS_LABELS' own comment for scope (Lines layer only so far, wired
    into rendering for "boundary" only so far).
    """

    status_idx = layer.fields().indexOf("status")

    layer.setEditorWidgetSetup(
        status_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(STATUS_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        status_idx,
        QgsDefaultValue(f"'{DEFAULT_STATUS}'")
    )


def _configure_echelon_field(layer):

    """
    Table D-III echelon amplifier ValueMap dropdown, defaulting to blank
    (no echelon glyph shown) - see ECHELON_LABELS' own comment for scope.
    """

    echelon_idx = layer.fields().indexOf("echelon")

    layer.setEditorWidgetSetup(
        echelon_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map_with_none(ECHELON_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        echelon_idx,
        QgsDefaultValue("''")
    )


# Per H.5.4 Labeling: "All text labeling shall be in upper case
# letters" - found unimplemented while re-auditing H.5.1-H.5.4 for
# Mini-Phase H0 (2026-08-09); wrapping the label expression in upper()
# applies it uniformly regardless of what case the user actually types
# into unique_designation/far_designation, for every measure type on
# both layers (a pure display-expression change, no risk to any measure
# type's own shape/colour choices, unlike STATUS_LABELS/ECHELON_LABELS
# above which are deliberately scoped to "boundary" only for now).
_PLAIN_DESIGNATION_LABEL_EXPRESSION = 'upper("unique_designation")'

# Table H-III shows THREE things stacked at each anchor-point segment:
# the near unit's Field T/AS above, the Field B echelon amplifier in a
# gap in the line, and the far unit's Field T/AS below - built here as a
# single 3-line label rather than a separate marker for the echelon glyph
# (see _boundary_symbol()'s own comment for the two earlier, wrong
# attempts at a separate marker), with QGIS's own Selective Masking
# cutting the actual line-gap around whatever this label renders (see
# _configure_designation_labeling()'s own comment). The echelon line and
# the far-designation line are each independently optional - CASE
# expressions add them only when populated, so a boundary with no
# echelon selected still gets a clean 2-line (or 1-line, with no far
# designation either) label instead of a blank middle row. upper() wraps
# only the two text fields (H.5.4's own "all caps" rule is about TEXT
# labeling, not the echelon's own graphic amplifier - see
# _PLAIN_DESIGNATION_LABEL_EXPRESSION's own comment), not the glyph
# itself (harmless either way for "X"/"Ø"/"++", but scoped correctly on
# principle). Falls through to the plain expression for every other
# measure type (which has no reason to ever populate echelon/
# far_designation), so nothing here changes their own rendering.
_BOUNDARY_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'boundary' THEN "
    "upper(\"unique_designation\")"
    " || CASE WHEN \"echelon\" IS NOT NULL AND \"echelon\" != ''"
    " THEN '\\n' || (" + _ECHELON_CHARACTER_EXPRESSION + ") ELSE '' END"
    " || CASE WHEN \"far_designation\" IS NOT NULL AND \"far_designation\" != ''"
    " THEN '\\n' || upper(\"far_designation\") ELSE '' END"
    " ELSE upper(\"unique_designation\") END"
)

# How often the boundary label (and the line-gap masked around it)
# repeats along a digitized boundary - approximates Table H-III's own
# "the line segment between each pair of anchor points will repeat all
# information" rule, which is genuinely per-SEGMENT (one repeat per
# digitized vertex pair, regardless of segment length) - QGIS's own
# label repeat is interval-based (evenly spaced by real screen distance,
# not tied to vertex positions), so this is a practical approximation of
# the standard's own per-segment rule rather than an exact match, the
# same "recognisable, not exact" standard this module applies elsewhere.
# Picked at a size that reads clearly repeated on a real multi-segment
# boundary without crowding a short one - confirmed by rendering one.
_BOUNDARY_LABEL_REPEAT_DISTANCE_MM = 80


def _configure_designation_labeling(
    layer,
    placement,
    label_expression,
    repeat_distance_mm=None,
    masked_symbol_layer_ids=None
):

    """
    `masked_symbol_layer_ids`, when given, enables QGIS's own Selective
    Masking on this label: the label engine cuts an exact hole (in the
    shape of whatever text actually renders) in each named symbol
    layer - referenced by the stable `.setId()` given when that symbol
    layer was built (see _boundary_symbol()'s own `.setId()` call) - of
    THIS SAME layer (a QgsSymbolLayerReference is layer-scoped by
    `layer.id()`, but there is nothing layer-specific about masking a
    different layer's symbol; this module only ever needs to mask its
    own line, so that's the only case built here). This is what actually
    fixed Boundary's own "gap in the line" requirement, after two
    symbol-layer-only attempts both failed for different reasons - see
    _boundary_symbol()'s own comment for the full history.
    """

    settings = QgsPalLayerSettings()

    settings.fieldName = label_expression

    settings.isExpression = True

    settings.placement = placement

    if repeat_distance_mm is not None:

        settings.repeatDistance = repeat_distance_mm
        settings.repeatDistanceUnit = Qgis.RenderUnit.Millimeters

    if placement == Qgis.LabelPlacement.Line:

        # QGIS's own default line-placement flags are AboveLine |
        # MapOrientation - the whole (possibly multi-line) label always
        # sits entirely above the line, never straddling it. That broke
        # _BOUNDARY_DESIGNATION_LABEL_EXPRESSION's own near/far split
        # (both lines rendered above the echelon gap, with "far" nearly
        # touching it) - flagged during manual testing. OnLine instead
        # centres the whole label block vertically ON the line/anchor
        # point, so a multi-line label naturally straddles it (earlier
        # rows above, later rows below) - confirmed by rendering a real
        # boundary feature both ways side by side, not assumed from the
        # flag's own name.
        settings.lineSettings().setPlacementFlags(
            Qgis.LabelLinePlacementFlag.OnLine
        )

    text_format = build_text_format(LABEL_FONT_SIZE)

    if masked_symbol_layer_ids:

        mask_settings = QgsTextMaskSettings()

        mask_settings.setEnabled(True)

        mask_settings.setSize(
            1.2
        )

        mask_settings.setSizeUnit(
            Qgis.RenderUnit.Millimeters
        )

        mask_settings.setMaskedSymbolLayers(
            [
                QgsSymbolLayerReference(layer.id(), symbol_layer_id)
                for symbol_layer_id in masked_symbol_layer_ids
            ]
        )

        text_format.setMask(
            mask_settings
        )

    settings.setFormat(
        text_format
    )

    layer.setLabeling(
        QgsVectorLayerSimpleLabeling(settings)
    )

    layer.setLabelsEnabled(
        True
    )


def create_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for control measures - a "measure_type"
    ValueMap dropdown (currently just Boundary - see this module's own
    docstring) plus a "unique_designation" text field, labelled directly
    on each line. Digitized with QGIS's own native "Add Line Feature"
    tool - see this module's own docstring and unit_layer.py's for why
    no custom drawing tool exists.

    "status"/"echelon"/"far_designation" were added 2026-08-09 (Mini-
    Phase H0) for Boundary's own rebuild - see STATUS_LABELS/
    ECHELON_LABELS' own comments for why they're general-purpose H
    fields present on the schema for every measure type, but so far only
    wired into rendering for "boundary" specifically.
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
            QgsField("echelon", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
            QgsField("far_designation", QMetaType.Type.QString),
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
        QgsDefaultValue("'boundary'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)
    _configure_echelon_field(layer)

    # applyOnUpdate=True ("Recalculate value on update") keeps this in
    # sync as the line is reshaped, not just at initial digitizing -
    # confirmed live via QgsVectorLayerUtils.createFeature() (what the
    # GUI's own "Add Line Feature" tool calls) and via a geometry-only
    # edit through updateFeature()/commitChanges().
    layer.setDefaultValueDefinition(
        layer.fields().indexOf("length_km"),
        QgsDefaultValue("mct_length_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _LINE_SYMBOL_BUILDERS)
    )

    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.Line,
        _BOUNDARY_DESIGNATION_LABEL_EXPRESSION,
        repeat_distance_mm=_BOUNDARY_LABEL_REPEAT_DISTANCE_MM,
        masked_symbol_layer_ids=[_BOUNDARY_LINE_SYMBOL_LAYER_ID]
    )

    return layer


def create_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for area-type control measures - same
    shape as create_control_measures_lines_layer(). Currently has zero
    measure types (see this module's own docstring) - AREA_MEASURE_TYPE_
    LABELS fills in as future H-subphases are completed. Digitized with
    QGIS's own native "Add Polygon Feature" tool.
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
        QgsDefaultValue("''")
    )

    _configure_affiliation_field(layer)

    # applyOnUpdate=True - see create_control_measures_lines_layer()'s
    # own comment on length_km for why, and
    # expressions/military_symbology_functions.py's _distance_area()
    # docstring for why these expressions take only $geometry, not
    # $geometry + @layer.
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

    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.OverPoint,
        _PLAIN_DESIGNATION_LABEL_EXPRESSION
    )

    return layer


def default_insert_position(project, layer):

    """
    Top of the layer tree - matches unit_layer.py's own convention for
    an operational overlay meant to sit above whatever base terrain
    rendering is underneath.
    """

    root = project.layerTreeRoot()

    root.insertLayer(
        0,
        layer
    )


def _add_layer_if_absent(iface, name, create_layer):

    """
    Shared guard for both add_control_measures_lines_layer()/
    add_control_measures_areas_layer() - see unit_layer.py's own
    add_unit_layer() for why a control-measures layer must never be
    silently replaced the way a generate_*() layer would be: its
    content is hand-drawn operational data, not derived from a DEM/AO,
    so a second click must warn rather than risk destroying it.
    """

    project = QgsProject.instance()

    if project.mapLayersByName(name):

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            f'A "{name}" layer already exists - use the Layers panel '
            "to work with it, or rename it first if you want a second "
            "one."
        )

        return None

    layer = create_layer()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )


def add_control_measures_lines_layer(iface):

    return _add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_control_measures_lines_layer
    )


def add_control_measures_areas_layer(iface):

    return _add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_control_measures_areas_layer
    )
