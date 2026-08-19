# -*- coding: utf-8 -*-

"""
Shared helpers/constants for every Appendix H control-measure layer
module - factored out of control_measures.py on 2026-08-09, when that
single module (which had been accreting every H.5.x logical section's
own measure types into one shared "Control Measures (Lines)"/"(Areas)"
pair - see c2_measures.py's own docstring) was split by the project
maintainer's own request: each H.5.x logical group (C2 Measures,
Maneuver, Defensive, Offensive, Airspace, Maritime, Deception, Fire
Support, Targets, Target Acquisition, Obstacles, Field Fortification,
CBRN, Sustainment, Supply, Mission Tasks, Intelligence) gets its own
dedicated layer(s) and its own module - c2_measures.py is the first one,
covering H.5.5/H.5.9/H.5.10 (Table H-III/H-IV/H-V) - the same "own
layer, own icon" principle Appendices B-L already follow for their point
symbols, rather than one shared layer per geometry type growing to cover
the entire appendix.

Everything here is genuinely general across ALL of those future groups,
not specific to any one of them: the H.5.1-H.5.4 general construction
rules (affiliation colouring, present/planned line style, the Table
D-III echelon amplifier, the H.5.4 upper-case labelling rule) apply to
control measures as a whole, not to C2 Measures alone - see
_apply_affiliation_color()'s/_STATUS_LINE_STYLE_EXPRESSION's/
ECHELON_LABELS' own comments for the standard's own citations. Mirrors
the existing precedent set by _point_symbol_layer.py, the equivalent
shared-helper module for Appendices B-L's own point-symbol layers (a
leading underscore marks both as private, cross-module-only helpers, not
part of this plugin's own public API).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsFillSymbol,
    QgsFontMarkerSymbolLayer,
    QgsLabelLineSettings,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsRuleBasedRenderer,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsSymbolLayerReference,
    QgsTextMaskSettings,
    QgsVectorLayerSimpleLabeling,
)

from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QColor

from ..core._layer_utils import add_layer_at_default_position
from ..core.text_format import build_text_format


LABEL_FONT_SIZE = 9

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
# intentionally NOT identical to sidc.py's AFFILIATIONS any more.
DEFAULT_AFFILIATION = "unspecified"

# The POINTS counterpart, and deliberately NOT AFFILIATION_LABELS.
#
# The comment above already spells out why control measures get a fifth
# "unspecified" value that sidc.py's own AFFILIATIONS does not have,
# and even notes that point symbols do not have that problem - but it
# never provided the points-side vocabulary to go with the observation.
# So the only shared affiliation helper available was the lines/areas
# one, and the H-XIX Points layer reached for it. That is the whole of
# the 2026-08-12 "every obstacle point renders as unknown" bug: a
# POINTS layer feeds `affiliation` into build_sidc(), where SIDC digit
# 4 has only the four real standard identities, so the shared default
# ("unspecified") made build_sidc() raise, mct_build_sidc() returned
# the KeyError MESSAGE as if it were a SIDC, and milsymbol drew its own
# unknown-icon fallback for every entity alike.
#
# Written out in the dropdown order the Points layers already showed
# (friend/hostile/neutral/unknown) rather than derived from
# AFFILIATIONS' own key order, so adopting this shared dict does not
# quietly reshuffle any existing layer's menu. Coverage is pinned by
# test instead - test_control_measure_shared.py asserts these keys are
# exactly AFFILIATIONS' keys, so a future standard identity cannot be
# added to sidc.py and silently missed here, and no value can be
# offered that build_sidc() would reject.
POINT_AFFILIATION_LABELS = {
    "friend": "Friend",
    "hostile": "Hostile",
    "neutral": "Neutral",
    "unknown": "Unknown",
}

DEFAULT_POINT_AFFILIATION = "friend"

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
# here, since no counterattack measure type exists yet).
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
# for point symbols, reused here by KEY (not value - Table D-III's
# glyphs, not the SIDC numeric echelon/mobility codes, are what actually
# gets drawn on a control measure).
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

# Resolves "echelon" to its Table D-III glyph as plain text - a CASE
# expression any group module can embed directly in its own label
# expression (see c2_measures.py's own
# _BOUNDARY_DESIGNATION_LABEL_EXPRESSION for the pattern).
_ECHELON_CHARACTER_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"echelon\" = '{key}' THEN '{glyph}'"
    for key, glyph in _ECHELON_GLYPHS.items()
) + " ELSE '' END"

# Per H.5.4 Labeling: "All text labeling shall be in upper case
# letters" - found unimplemented while re-auditing H.5.1-H.5.4 for
# Mini-Phase H0 (2026-08-09); wrapping a label expression in upper()
# applies it uniformly regardless of what case the user actually types.
_PLAIN_DESIGNATION_LABEL_EXPRESSION = 'upper("unique_designation")'


def stabilised_point_size_expression(size_expression, svg_expression):

    """
    `size_expression`, scaled so the ICON stays exactly the same size
    when a unique designation is typed into it.

    **QGIS sizes an SVG marker by its WIDTH, and milsymbol widens an
    icon's declared box to take in whatever amplifier text it carries.**
    So at a fixed marker size, adding a designation SHRINKS the symbol
    it belongs to. Multiplying by (amplified width / plain width)
    cancels that exactly: the icon keeps the size it has with no text,
    and the text hangs outside it, which is how the standard's own
    examples draw amplifiers anyway.

    First fixed in _point_symbol_layer.py on 2026-08-13, after the
    maintainer's report on Table H-XXI - "now the symbol size is
    reducing when the Field T is added - inconsistent from a UI point
    of view". **That fix only reached layers built through the shared
    point-layer builder**, and seven modules in this appendix build
    their own point renderer instead; every one of them still shrank.
    Reported again 2026-08-14 against Table H-VI's own Checkpoint and
    Contact Point, and fixed here, once, for all of them.

    `svg_expression` is the module's own complete `mct_sidc_svg(...)`
    call. Both widths are derived from it rather than passed
    separately, so the two can never drift apart: the amplified one is
    that same call routed to mct_sidc_svg_width(), and the plain one is
    its `mct_build_sidc(...)` argument alone.

    **The ratio is guarded, and that is not defensive padding.** QGIS
    short-circuits a whole function call to NULL the moment any
    argument is NULL, so one unset attribute on a feature - an
    affiliation left empty on a hand-edited layer, say - would null the
    ratio and take the size expression with it, silently dropping any
    per-entity multiplier back to the layer's base size. nullif() also
    covers a width of 0, which is what mct_sidc_svg_width() returns for
    a SIDC it cannot render. Either way the fallback is 1: no
    compensation, rather than no size.
    """

    sidc_expression = _build_sidc_argument(svg_expression)

    amplified = svg_expression.replace(
        "mct_sidc_svg(", "mct_sidc_svg_width(", 1
    )

    return (
        f"({size_expression}) * coalesce({amplified}"
        f" / nullif(mct_sidc_svg_width({sidc_expression}), 0), 1)"
    )


def configure_rotation_and_scale_fields(layer):

    """
    Configures an already-added "rotation" (degrees, clockwise from
    north) and "scale" (percent of the symbol's own base size, 100 =
    unchanged) field with QGIS's "Range" spin-box editor widget, a
    sensible default, and a field alias naming the unit - the U-2
    (build tracker) convention every point-symbol layer wanting
    rotation/scale should share.

    **Shared here from the start, unlike stabilised_point_size_
    expression() (see that function's own docstring)** - that fix only
    reached layers built through _point_symbol_layer.py's shared
    builder at first, and seven modules building their own point
    renderer each had to be found and fixed separately later. U-2's
    first landing (2026-08-19) was in that same shared builder; this
    helper exists so the SECOND caller (U-4, obstacle_control_
    measures.py) reuses the exact same widget config instead of a
    second hand-copied version that could quietly drift from it, and so
    do the rest of the module's own now-deferred follow-up pass.

    Caller adds the two QgsField()s itself first (this project's
    per-module attribute-list conventions differ too much to standardise
    that half too) - this only configures the widget/default/alias for
    fields that already exist on the layer.
    """

    fields = layer.fields()

    rotation_idx = fields.indexOf("rotation")

    layer.setEditorWidgetSetup(
        rotation_idx,
        QgsEditorWidgetSetup(
            "Range",
            {
                "Min": 0.0,
                "Max": 360.0,
                "Step": 1.0,
                "Precision": 1,
                "Style": "SpinBox",
                "AllowNull": False,
            }
        )
    )

    layer.setDefaultValueDefinition(rotation_idx, QgsDefaultValue("0"))

    layer.setFieldAlias(rotation_idx, "Rotation (°, clockwise from north)")

    scale_idx = fields.indexOf("scale")

    layer.setEditorWidgetSetup(
        scale_idx,
        QgsEditorWidgetSetup(
            "Range",
            {
                "Min": 10.0,
                "Max": 400.0,
                "Step": 5.0,
                "Precision": 0,
                "Style": "SpinBox",
                "AllowNull": False,
            }
        )
    )

    layer.setDefaultValueDefinition(scale_idx, QgsDefaultValue("100"))

    layer.setFieldAlias(scale_idx, "Scale (% of symbol's own size)")


def _build_sidc_argument(svg_expression):

    """
    The `mct_build_sidc(...)` call inside `svg_expression`, matched by
    counting parentheses rather than by a regex - the argument itself
    contains nested calls and quoted strings, and a lazy regex stops at
    the first ')' inside one.
    """

    start = svg_expression.index("mct_build_sidc(")

    depth = 0

    for offset, character in enumerate(svg_expression[start:], start):

        if character == "(":
            depth += 1

        elif character == ")":

            depth -= 1

            if depth == 0:
                return svg_expression[start:offset + 1]

    raise ValueError(
        "unbalanced mct_build_sidc() in: " + svg_expression
    )


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
    as _point_symbol_layer.py's own helper of the same name.
    """

    result = {none_label: ""}

    result.update(_value_map(labels))

    return result


def _configure_affiliation_field(layer):

    """
    Shared across every H control-measure layer - a "Friend"/"Hostile"/
    "Neutral"/"Unknown"/"Unspecified (black)" ValueMap dropdown driving
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


def _configure_point_affiliation_field(layer):

    """
    The POINTS counterpart to _configure_affiliation_field(): the four
    real SIDC standard identities only, defaulting to 'friend'.

    Any layer whose `affiliation` field reaches build_sidc() - i.e.
    every milsymbol-rendered Points layer - must use this one, NOT
    _configure_affiliation_field(), which is for the hand-drawn lines
    and areas layers where affiliation only picks a Qt colour. See
    POINT_AFFILIATION_LABELS for what goes wrong otherwise.
    """

    affiliation_idx = layer.fields().indexOf("affiliation")

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(POINT_AFFILIATION_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        affiliation_idx,
        QgsDefaultValue(f"'{DEFAULT_POINT_AFFILIATION}'")
    )


def _configure_status_field(layer):

    """
    "Present"/"Planned / Anticipated / On Order" ValueMap dropdown - see
    STATUS_LABELS' own comment for the standard's own citation.
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


def _status_driven_area_outline_symbol():

    """
    A plain unfilled, status-driven solid/dashed outline (H.5.1.1.3/
    Table H-I; that rule's own text explicitly covers "area control
    measures", not just linear ones) - the base shape shared by most
    area-type control measures across every H.5.x group so far
    (c2_measures.py's own Area of Operations/Named+Target Area of
    Interest/Airfield Zone, Mini-Phase H2), factored out here
    (2026-08-09) so H3's own maneuver-area module can reuse it too
    rather than duplicating it - what usually differs between area
    types using this base shape is only the label and, occasionally, a
    centred icon added on top (see each module's own area-symbol
    functions).
    """

    outline_layer = QgsSimpleLineSymbolLayer()

    outline_layer.setColor(
        QColor(0, 0, 0)
    )

    outline_layer.setWidth(
        0.4
    )

    _apply_affiliation_color(
        outline_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    outline_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
        }
    )

    symbol.changeSymbolLayer(
        0,
        outline_layer
    )

    return symbol


def _end_label_layer(placement, character, rotate_with_line=True):

    """
    A small font-marker label (`character`, e.g. "LL"/"FEBA") at the
    given line end (FirstVertex/LastVertex), offset above the line so it
    doesn't overlap the line's own stroke - factored out of
    c2_measures.py (2026-08-09, alongside _status_driven_area_outline_
    symbol() above) so other line measure types with the same "fixed
    abbreviation at each end, no tick" convention (this module's own
    FEBA, for instance) can reuse it too.

    `rotate_with_line` (True by default, preserving every existing
    caller's own behaviour unchanged) controls whether the label turns
    to follow the line's own tangent or always renders upright.
    **2026-08-12**, per the project maintainer's own report against
    maneuver_control_measures_2.py's own Bridgehead Line: "the label on
    both ends should be straight, in our case one of the labels is
    inverted". Confirmed by render - with rotation on, a line digitized
    right-to-left has BOTH its labels rendered upside-down (and pushed
    below the line rather than above it, since the perpendicular offset
    rotates with the same frame), and an angled end segment tilts its
    own label to match. Passing `rotate_with_line=False` turns the
    marker line's own rotateSymbols flag off, so the label stays upright
    regardless of the line's own drawn direction; the offset then reads
    in plain screen space, which is what "straight" needs. Scoped per
    caller rather than changed globally - other measure types using this
    helper (Light Line, FEBA, Holding Line, Release Line) keep their own
    existing behaviour until each is reviewed on its own, per this
    project's standing "one symbol at a time" convention.

    **2026-08-09 correction (found while building c2_measures.py's own
    Light Line)**: an earlier version of this helper also drew a short
    perpendicular "tick" mark at each end, reading Table H-IV's own
    TEMPLATE column as if the up-arrows connecting a label to the line
    were a drawn tick that's part of the symbol. The project maintainer
    corrected this: those arrows are the same kind of pointer/callout
    used throughout this appendix's own diagrams to show where a label
    attaches or which point is PT1 vs PT2 - not geometry to be rendered.
    General lesson, confirmed again while reading Table H-VII for H3:
    NOT every line measure type in this appendix omits a real tick the
    same way Light Line does - Phase Line's own EXAMPLE column (page
    411) shows a genuine BLACK bracket/tick touching each end, distinct
    from a separate GREY illustrative boundary-line annotation below it
    - so this decision has to be checked per measure type against the
    actual EXAMPLE column's colours, not assumed from Light Line's own
    precedent. Measure types that DO need a real tick use a different
    helper (see this module's own end-tick construction, added for
    Phase Line).
    """

    font_layer = QgsFontMarkerSymbolLayer()

    font_layer.setFontFamily(
        "Arial"
    )

    font_layer.setSize(
        3.5
    )

    font_layer.setColor(
        QColor(0, 0, 0)
    )

    font_layer.setCharacter(
        character
    )

    # With `rotate_with_line` on, the offset is in the marker's own
    # tangent-rotated frame, so a plain Y offset moves perpendicular to
    # the line - negative Y confirmed (by rendering both signs) to be
    # the one that reads above the line rather than below it for a
    # left-to-right line. With it off, the same negative Y reads in
    # plain screen space and is simply "up", which is what an upright
    # label wants either way.
    font_layer.setOffset(
        QPointF(0, -2.5)
    )

    _apply_affiliation_color(
        font_layer,
        [QgsSymbolLayer.Property.FillColor]
    )

    label_marker = QgsMarkerSymbol()

    label_marker.changeSymbolLayer(
        0,
        font_layer
    )

    label_layer = QgsMarkerLineSymbolLayer(rotate_with_line)

    label_layer.setSubSymbol(
        label_marker
    )

    label_layer.setPlacements(
        placement
    )

    return label_layer


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


def _build_pal_layer_settings(
    layer,
    placement,
    label_expression,
    repeat_distance_mm=None,
    masked_symbol_layer_ids=None,
    mask_size_mm=1.2,
    line_anchor_percent=None,
    anchor_text_point=None,
    line_placement_flags=None,
    label_geometry_expression=None,
    quadrant=None
):

    """
    `label_geometry_expression` (None by default - every existing caller
    labels the feature's own geometry) replaces the geometry PAL places
    the label against, via QGIS's own label geometry generator. Added
    2026-08-12 for Table H-XIII's own zones, whose labels the standard
    puts in the polygon's own top-left corner rather than at its centre
    - see mct_area_label_anchor(). `quadrant` goes with it: which corner
    of the text sits on that anchor point (OverPoint placement only).

    Every label built here is AFFILIATION-COLOURED: its own Colour
    property is data-defined from _AFFILIATION_COLOR_EXPRESSION, so the
    text follows H.5.3's own friend/hostile/neutral/unknown hue rules
    the same way the drawn line/outline beside it already does.
    2026-08-12 - raised against maneuver_control_measures_2.py's own
    Airhead Line first ("change the colour as per affiliation for the
    airhead line also"), where a black label sat beside a blue line;
    when the same mismatch was pointed out to apply to every other
    simple-labelling caller in this appendix, the maintainer's own
    instruction was "do it for all", so this is unconditional rather
    than an opt-in flag. Direction of Attack's own Field T family
    already had the equivalent, set per-rule on its own
    QgsRuleBasedLabeling tree - those per-rule calls still run AFTER
    this one and overwrite the same property key, which is what keeps
    Enemy's own forced red (_OFFENSIVE_LINE_COLOR_EXPRESSION) winning
    over the plain affiliation hue.

    NOTE this colours LABELS only. Structural glyphs drawn as symbol
    layers - Field N, Axis of Advance's own airborne-modifier humps -
    stay fixed black deliberately; see _unit_context_icon_layer()'s own
    docstring for that reasoning.

    `masked_symbol_layer_ids`, when given, enables QGIS's own Selective
    Masking on this label: the label engine cuts an exact hole (in the
    shape of whatever text actually renders) in each named symbol
    layer - referenced by the stable `.setId()` given when that symbol
    layer was built - of THIS SAME layer (a QgsSymbolLayerReference is
    layer-scoped by `layer.id()`, but there is nothing layer-specific
    about masking a different layer's symbol; every group module so far
    only ever needs to mask its own lines, so that's the only case built
    here). Masking is configured ONCE per QGIS layer, on the one shared
    QgsTextFormat every measure type's own label uses (there's no
    per-rule text format) - so `masked_symbol_layer_ids` is a LIST: every
    line measure type whose own label should cut a real gap needs its
    line's own id added to it. This is what actually fixed Boundary's
    own "gap in the line" requirement in c2_measures.py, after two
    symbol-layer-only attempts both failed for different reasons - see
    that module's own _boundary_symbol() comment for the full history.

    `mask_size_mm` defaults to 1.2 (a bare buffer around the rendered
    text itself, right for a label masking a single plain line/outline).
    Defensive Control Measures' own Strong Point overrides this larger -
    its echelon label masks not just the outline but ALSO the toothed
    perimeter's own tick marks (see defensive_control_measures.py's own
    _configure_area_designation_labeling() comment), and a couple of
    those ticks sit close enough to the origin point that the default
    buffer left them poking into the glyph - found by the project
    maintainer's own live testing.

    `line_anchor_percent`/`anchor_text_point` (placement == Line only,
    both None by default - every existing caller's own along-whole-line
    or centred-on-feature behaviour is unchanged): pins the label to a
    FIXED fraction of the line's own length (0.0 = start, 1.0 = end)
    instead of QGIS's own default "best along-line position" search,
    with Qgis.LabelLineAnchorType... - actually QgsLabelLineSettings.
    AnchorType.Strict, so the anchor is honoured exactly rather than
    treated as a hint. Direction of Attack - Friendly Aviation's own
    Field T is the first user of this (2026-08-11) - "just behind the
    arrow head... in line with the arrow shaft" needs the label pinned
    near the line's own end, not wherever QGIS's own default search
    happens to prefer.
    """

    settings = QgsPalLayerSettings()

    settings.fieldName = label_expression

    settings.isExpression = True

    settings.placement = placement

    if repeat_distance_mm is not None:

        settings.repeatDistance = repeat_distance_mm
        settings.repeatDistanceUnit = Qgis.RenderUnit.Millimeters

    if placement in (Qgis.LabelPlacement.Line, Qgis.LabelPlacement.Horizontal):

        # Qgis.LabelPlacement.Horizontal joined Line here 2026-08-12,
        # for Table H-XIV's own Bearing Line family: it is QGIS's own
        # "place along the line but keep the text upright" mode, and it
        # honours exactly the same lineSettings() the Line mode does
        # (anchor, placement flags), so everything below applies to it
        # unchanged. Line rotates its label to follow the feature;
        # Horizontal does not, which is the whole reason that family
        # uses it - "the orientation has to be straight at all times and
        # not along the line", the maintainer's own words.
        #
        # QGIS's own default line-placement flags are AboveLine |
        # MapOrientation - the whole (possibly multi-line) label always
        # sits entirely above the line, never straddling it. OnLine
        # instead centres the whole label block vertically ON the line/
        # anchor point, so a multi-line label naturally straddles it -
        # see c2_measures.py's own _BOUNDARY_DESIGNATION_LABEL_
        # EXPRESSION comment for why this mattered there.
        #
        # OnLine stays the default here because that straddling IS the
        # requirement for Boundary's own near/far designation pair, and
        # because every masked-label caller (Direction of Attack's own
        # Field T family) relies on the label sitting ON the line and
        # cutting its own gap in it. `line_placement_flags` overrides it
        # for the cases that genuinely want the text clear of the line -
        # 2026-08-12, maneuver_control_measures_2.py's own Airhead Line:
        # "the text is overlapping the line, it should be above the
        # line" (the maintainer's own words). That label has no mask of
        # its own, so OnLine left the line drawn straight through the
        # glyphs.
        settings.lineSettings().setPlacementFlags(
            line_placement_flags
            if line_placement_flags is not None
            else Qgis.LabelLinePlacementFlag.OnLine
        )

        if line_anchor_percent is not None:

            settings.lineSettings().setAnchorType(
                QgsLabelLineSettings.AnchorType.Strict
            )

            settings.lineSettings().setLineAnchorPercent(
                line_anchor_percent
            )

            if anchor_text_point is not None:

                settings.lineSettings().setAnchorTextPoint(
                    anchor_text_point
                )

    text_format = build_text_format(LABEL_FONT_SIZE)

    if masked_symbol_layer_ids:

        mask_settings = QgsTextMaskSettings()

        mask_settings.setEnabled(True)

        mask_settings.setSize(
            mask_size_mm
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

    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Color,
        QgsProperty.fromExpression(_AFFILIATION_COLOR_EXPRESSION)
    )

    if label_geometry_expression is not None:

        settings.geometryGenerator = label_geometry_expression
        settings.geometryGeneratorEnabled = True
        settings.geometryGeneratorType = Qgis.GeometryType.Point

    if quadrant is not None:

        settings.pointSettings().setQuadrant(quadrant)

    return settings


def _configure_designation_labeling(
    layer,
    placement,
    label_expression,
    repeat_distance_mm=None,
    masked_symbol_layer_ids=None,
    line_anchor_percent=None,
    anchor_text_point=None,
    line_placement_flags=None,
    label_geometry_expression=None,
    quadrant=None
):

    settings = _build_pal_layer_settings(
        layer,
        placement,
        label_expression,
        repeat_distance_mm,
        masked_symbol_layer_ids,
        line_anchor_percent=line_anchor_percent,
        anchor_text_point=anchor_text_point,
        line_placement_flags=line_placement_flags,
        label_geometry_expression=label_geometry_expression,
        quadrant=quadrant
    )

    layer.setLabeling(
        QgsVectorLayerSimpleLabeling(settings)
    )

    layer.setLabelsEnabled(
        True
    )


def default_insert_position(project, layer):

    """
    Top of the layer tree - matches unit_layer.py's own convention for
    an operational overlay meant to sit above whatever base terrain
    rendering is underneath. Inserted collapsed (2026-08-18, UI
    request): most of these layers render via QgsRuleBasedRenderer,
    one rule per placement, so an expanded node can show many legend
    rows - and a single Control Measures click routinely adds two or
    three layers (Lines/Areas/Points) at once, which stacks up fast in
    a project with several groups added.
    """

    root = project.layerTreeRoot()

    node = root.insertLayer(
        0,
        layer
    )

    node.setExpanded(False)


def add_layer_if_absent(iface, name, create_layer):

    """
    Shared guard for every group module's own add_*_layer() functions -
    see unit_layer.py's own add_unit_layer() for why a control-measures
    layer must never be silently replaced the way a generate_*() layer
    would be: its content is hand-drawn operational data, not derived
    from a DEM/AO, so a second click must warn rather than risk
    destroying it.
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
