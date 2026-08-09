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
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsRuleBasedRenderer,
    QgsSymbolLayerReference,
    QgsTextMaskSettings,
    QgsVectorLayerSimpleLabeling,
)

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
    masked_symbol_layer_ids=None
):

    """
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
        # sits entirely above the line, never straddling it. OnLine
        # instead centres the whole label block vertically ON the line/
        # anchor point, so a multi-line label naturally straddles it -
        # see c2_measures.py's own _BOUNDARY_DESIGNATION_LABEL_
        # EXPRESSION comment for why this mattered there.
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

    return settings


def _configure_designation_labeling(
    layer,
    placement,
    label_expression,
    repeat_distance_mm=None,
    masked_symbol_layer_ids=None
):

    settings = _build_pal_layer_settings(
        layer,
        placement,
        label_expression,
        repeat_distance_mm,
        masked_symbol_layer_ids
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
    rendering is underneath.
    """

    root = project.layerTreeRoot()

    root.insertLayer(
        0,
        layer
    )


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
