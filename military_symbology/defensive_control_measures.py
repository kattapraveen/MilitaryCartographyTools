# -*- coding: utf-8 -*-

"""
Builds a ready-to-use Defensive Control Measures layer - MIL-STD-2525D
Appendix H.5.12.1 (Table H-VIII, "Areas"), the third H.5.x logical group
after c2_measures.py (H.5.5/H.5.9/H.5.10) and maneuver_control_measures.py
(H.5.11) - see c2_measures.py's own docstring for the full "why a
separate module per logical group" rationale and _control_measure_
shared.py for the cross-group helpers this module reuses.

**Mini-Phase H4, 2026-08-09.** H.5.12 splits into two tables:
  - **Table H-VIII (Defensive control measure symbols, H.5.12.1
    "Areas")** - every entry in it is an AREA, no lines at all, unlike
    c2_measures.py/maneuver_control_measures.py which both needed a
    Lines layer too. This module has no Lines layer - "own layer(s)",
    not necessarily a matched Lines/Areas pair every time.
  - **Table H-IX (Observation post, H.5.12.2)** - every one of its 7
    entries (Unspecified/Specified/Reconnaissance/Forward Observer/
    CBRN/Sensor-Listening/Combat Outpost, plus Target Reference Point,
    which the table's own running header keeps grouped under "TABLE
    H-IX...Continued" despite reading thematically like a Fire Support
    measure) is a single-anchor-point symbol, rendered through
    milsymbol.js the same way `military_symbology/unit_layer.py`/
    `control_measure_points.py` do (a different rendering mechanism
    entirely from Table H-VIII's own hand-built QGIS fill symbology
    above - see this module's own POINTS_LAYER_NAME section).

**2026-08-10, Table H-IX moved into its own dedicated layer here.**
Originally left inside the shared, ~90-entry `control_measure_points.py`
dropdown (the "confirmed already present" note this docstring used to
carry) - the project maintainer reported this made the 7 entries hard to
actually find while testing, and asked for a dedicated layer here,
matching every other H.5.x group's own "own layer(s)" convention (see
c2_measures.py's own docstring for why that convention exists at all).
The 7 entries were removed from control_measure_points.py's own
dropdown at the same time (not left duplicated in both places - the
underlying SIDC codes in sidc.py are untouched, so this only changes
which layer's dropdown offers them, not how they render or any
already-digitized feature's own data). Not yet formally cross-checked
entry-by-entry against Table H-IX's own template pictures the way Table
H-VI was flagged pending in task #33 - worth the same kind of follow-up
audit, not urgent.

**Two entries skipped outright, not silently dropped** (see
_AREA_SYMBOL_BUILDERS' own comment for the full reasoning): **Contain**
(151204) and **Retain** (151205) are both PROCEDURAL circle/arc
constructions - Retain in particular is defined by a CENTER point plus a
RADIUS point (not a freeform boundary), a spiked circle with a
30-degree gap whose opening direction has real meaning ("on the friendly
side of the symbol") that a generic user-drawn polygon can't capture
the same way an arbitrary freeform boundary can for every other area
type here. This doesn't fit this module's (and every other H.5.x area
module's) "one polygon feature, one symbol" pattern the way Battle
Position/Strong Point/Engagement Area all do - deferred, the same
"doesn't fit the model" call already made for H3's own Offset-Unit/
Limited Access Area entries.

**Battle Position's own three Status/"Prepared" variants** (151200
Present, 151201 Planned, 151202 "Prepared (P) but not Occupied") don't
map cleanly onto the shared "status" field's own two values the way
every other H group's status pairs have so far - "Prepared but not
Occupied" is dashed (like Planned) PLUS an extra "(P) " prefix on the
name, not a genuinely third line style. Modelled as the existing shared
Present/Planned status field (solid/dashed) PLUS a new, this-module-only
"prepared" field (a plain Yes/No toggle) that adds the "(P) " prefix
when set - matches the standard's own construction (Present, Planned,
and Planned+Prepared are 3 real combinations; a fourth, Present+
Prepared, isn't in the standard's own examples but isn't prohibited
either, so this doesn't block it).

Battle Position and Strong Point both carry a Field B echelon amplifier
(Table D-III, the same vocabulary/glyphs Boundary already uses in
c2_measures.py) - reuses `_control_measure_shared.py`'s own
ECHELON_LABELS/`_configure_echelon_field`/`_ECHELON_CHARACTER_
EXPRESSION` directly rather than reinventing them.

**One new hand-built technique**: Strong Point's own spiked/toothed
perimeter (151203) - a QgsMarkerLineSymbolLayer repeating a "line"-shape
marker (the SAME shape/angle convention already confirmed for Phase
Line's own end tick in maneuver_control_measures.py - angle=0 is
perpendicular for a rotate-with-line marker, not angle=90, despite what
the angle's own name suggests) at a tight interval AROUND THE WHOLE
outline instead of just at two ends - render-and-compare confirmed this
reads as a clean spiked border, closely matching the standard's own
template picture.

**2026-08-10 live-testing follow-up, two real construction bugs fixed**:
  - The Field B echelon glyph was rendering as a second line of Battle
    Position's/Strong Point's own floating, polygon-centred name label
    (_AREA_DESIGNATION_LABEL_EXPRESSION's own earlier version) - the
    standard's own template shows it sitting IN the perimeter line
    itself, with a real gap cut around it, the same masked-line-gap
    construction c2_measures.py's own Boundary uses. Moved to its own
    separate, masked label anchored at the polygon's own origin point
    (its first digitized vertex) - see
    _configure_area_designation_labeling()'s own docstring for the full
    construction (a label geometry generator, not the feature's own
    polygon geometry).
  - Strong Point's own tick marks straddled the perimeter line
    symmetrically (half inside, half outside) instead of pointing
    outward only - fixed with the same ring-winding-order lesson
    Fortified Area's own crenellated outline already taught
    (maneuver_control_measures.py): wrap the tick layer in a
    QgsGeometryGeneratorSymbolLayer using `force_rhr($geometry)` to
    guarantee a fixed winding direction, then a fixed marker offset
    reliably means "outward" for every feature - see
    _strong_point_symbol()'s own docstring.

**2026-08-10, second live-testing follow-up, two more real bugs fixed**:
  - Battle Position's own "Prepared but not occupied" checkbox rendered
    a SOLID perimeter unless the separate "status" field was ALSO
    switched to Planned by hand - wrong, since a dedicated field exists
    for exactly this variant. _battle_position_symbol() now uses its own
    _BATTLE_POSITION_LINE_STYLE_EXPRESSION (dashed when EITHER "status"
    is planned OR "prepared" is set) instead of the shared
    _status_driven_area_outline_symbol()'s status-only expression.
  - Strong Point's own tick marks (fixed above) were, once fixed,
    crowding right over the echelon glyph at the origin point - the
    masked gap only cut through the OUTLINE, not the separate tick
    layer, which kept drawing teeth through the label. See
    _configure_area_designation_labeling()'s own docstring for the fix
    (mask the tick layer too, with a wider mask_size_mm).

Military Cartography Tools
"""

import math

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFillSymbol,
    QgsGeometryGeneratorSymbolLayer,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)

from qgis.PyQt.QtCore import QMetaType, QPointF
from qgis.PyQt.QtGui import QColor

from ..core.text_format import build_text_format

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    ECHELON_LABELS,
    POINT_AFFILIATION_LABELS,
    STATUS_LABELS,
    _ECHELON_CHARACTER_EXPRESSION,
    _PLAIN_DESIGNATION_LABEL_EXPRESSION,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_echelon_field,
    _configure_status_field,
    _status_driven_area_outline_symbol,
    _value_map,
    _value_map_with_none,
    add_layer_if_absent,
)


AREAS_LAYER_NAME = "Defensive Control Measures (Areas)"
POINTS_LAYER_NAME = "Defensive Control Measures (Points)"

__all__ = [
    "AREAS_LAYER_NAME",
    "POINTS_LAYER_NAME",
    "AREA_MEASURE_TYPE_LABELS",
    "POINT_ENTITY_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "ECHELON_LABELS",
    "create_defensive_control_measures_areas_layer",
    "add_defensive_control_measures_areas_layer",
    "create_defensive_control_measures_points_layer",
    "add_defensive_control_measures_points_layer",
]

# Table H-VIII, H.5.12.1. "Contain"/"Retain" (151204/151205) are
# deliberately excluded - see module docstring.
AREA_MEASURE_TYPE_LABELS = {
    "battle_position": "Battle Position",
    "strong_point": "Strong Point",
    "engagement_area": "Engagement Area (EA)",
}

_PREPARED_LABELS = {
    "P": "Prepared but not occupied",
}

# Battle Position's/Strong Point's own outline symbol layers' stable ids -
# referenced by _configure_area_designation_labeling()'s own masked echelon
# label rule below, so the label engine knows which symbol layer to cut a
# real gap in (same QgsSymbolLayerReference-by-id mechanism c2_measures.py's
# own Boundary uses - see _control_measure_shared.py's own
# _build_pal_layer_settings() docstring).
_BATTLE_POSITION_OUTLINE_SYMBOL_LAYER_ID = "battle_position_outline"
_STRONG_POINT_OUTLINE_SYMBOL_LAYER_ID = "strong_point_outline"
_STRONG_POINT_TICK_SYMBOL_LAYER_ID = "strong_point_tick"

# Battle Position's own "Prepared but not occupied" variant (151202) is
# drawn DASHED, the same as Planned - not a genuinely third line style
# (see module docstring). The shared _STATUS_LINE_STYLE_EXPRESSION only
# looks at "status", so a feature with "prepared" set but "status" left
# at its own default ("present") rendered with a solid perimeter -
# wrong, and easy to hit precisely because a dedicated "prepared" field
# exists at all, inviting a user to set ONLY that and leave "status"
# untouched. Found by the project maintainer's own live testing.
_BATTLE_POSITION_LINE_STYLE_EXPRESSION = (
    "CASE WHEN \"status\" = 'planned' OR \"prepared\" = 'P'"
    " THEN 'dash' ELSE 'solid' END"
)


def _battle_position_symbol():

    # Table H-VIII, code 151200 (and 151201/151202 - see module
    # docstring for why all three fold into this one measure type via
    # the shared status field plus this module's own "prepared" field).
    # Same plain outline shape as every other area here, but with its
    # own line-style expression (see _BATTLE_POSITION_LINE_STYLE_
    # EXPRESSION) rather than _status_driven_area_outline_symbol()'s
    # shared one - only the label differs otherwise (name + optional
    # "(P) " prefix). The echelon glyph no longer renders here at all -
    # see _configure_area_designation_labeling()'s own docstring for why
    # it moved to a separate, masked, on-perimeter label instead of a
    # second line floating inside this symbol's own name label.
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
        QgsProperty.fromExpression(_BATTLE_POSITION_LINE_STYLE_EXPRESSION)
    )

    outline_layer.setId(
        _BATTLE_POSITION_OUTLINE_SYMBOL_LAYER_ID
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


def _strong_point_symbol():

    """
    Table H-VIII, code 151203, page 421. "A key point in a defensive
    position usually strongly fortified and heavily armed with
    automatic weapons, around which other positions are grouped for its
    protection." Same status-driven outline as every other area here,
    plus a spiked/toothed perimeter.

    **2026-08-10 correction, found by the project maintainer's own live
    testing**: the tick marker's own "line" shape is centred on its own
    anchor point, so it straddled the boundary line symmetrically (half
    the tick INSIDE the polygon, half outside) - the template picture
    (page 421) shows spikes pointing outward only, none crossing into
    the interior. Fixing this needed the same lesson already learned for
    Fortified Area's own crenellated outline in maneuver_control_
    measures.py: which perpendicular direction is "outward" depends on
    the ring's own winding order, which QGIS's native polygon digitizing
    tool does NOT normalize (a user clicking clockwise vs.
    counter-clockwise flips it), so a single fixed offset sign can't be
    correct for every feature. The fix is the same one used there but
    applied to symbol styling rather than geometry: wrap the tick
    marker-line layer alone (not the plain outline layer, which doesn't
    care about winding) in a QgsGeometryGeneratorSymbolLayer whose own
    geometry expression is `force_rhr($geometry)` - QGIS's own
    right-hand-rule normalizer, which guarantees every exterior ring
    winds the same fixed direction regardless of how it was digitized.
    With that guaranteed, a fixed marker offset of half the tick's own
    length (confirmed outward, not inward, by rendering) reliably shifts
    the whole tick from straddling the line to sitting entirely outside
    it, for any Strong Point feature.
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

    outline_layer.setId(
        _STRONG_POINT_OUTLINE_SYMBOL_LAYER_ID
    )

    tick_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "line",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "outline_width": "0.5",
            "size": "2.5",
            "angle": "0",
        }
    )

    _apply_affiliation_color(
        tick_marker.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    # Shifts the tick's own anchor outward by half its own length, so
    # instead of spanning from -1.25mm to +1.25mm across the line (the
    # old symmetric straddle), it spans from 0mm (right on the line) to
    # +2.5mm outward - see this function's own docstring for why the
    # sign is only reliably "outward" once force_rhr() below has fixed
    # the ring's winding order.
    tick_marker.symbolLayer(0).setOffset(
        QPointF(0, -1.25)
    )

    tick_layer = QgsMarkerLineSymbolLayer(True)

    tick_layer.setId(
        _STRONG_POINT_TICK_SYMBOL_LAYER_ID
    )

    tick_layer.setSubSymbol(
        tick_marker
    )

    tick_layer.setPlacements(
        Qgis.MarkerLinePlacement.Interval
    )

    tick_layer.setInterval(
        3
    )

    tick_layer.setIntervalUnit(
        Qgis.RenderUnit.Millimeters
    )

    tick_sub_symbol = QgsLineSymbol()

    tick_sub_symbol.changeSymbolLayer(
        0,
        tick_layer
    )

    tick_generator_layer = QgsGeometryGeneratorSymbolLayer.create({})

    tick_generator_layer.setGeometryExpression(
        "force_rhr($geometry)"
    )

    tick_generator_layer.setSymbolType(
        Qgis.SymbolType.Line
    )

    tick_generator_layer.setSubSymbol(
        tick_sub_symbol
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

    symbol.appendSymbolLayer(
        tick_generator_layer
    )

    return symbol


def _engagement_area_symbol():

    # Table H-VIII, code 151300, page 424. "An area where the commander
    # intends to contain and destroy an enemy force..." Plain
    # status-driven outline, same as Battle Position - the example's
    # own grey "hedgehog" unit markers around it are illustrative
    # context, not part of this control measure.
    return _status_driven_area_outline_symbol()


_AREA_SYMBOL_BUILDERS = {
    "battle_position": _battle_position_symbol,
    "strong_point": _strong_point_symbol,
    "engagement_area": _engagement_area_symbol,
}

# Battle Position/Strong Point are each labelled with an optional name
# (Field T, Battle Position's own additionally prefixed "(P) " when
# "prepared" is set - see module docstring) INSIDE the polygon, same as
# every other area here. Engagement Area uses the simpler single-line
# "prefix + optional name" pattern already established for AO/NAI/TAI/
# Assembly Area/etc.
#
# **2026-08-10 correction, found by the project maintainer's own live
# testing**: an earlier version of this expression also appended the
# Field B echelon glyph (Table D-III) as a second line of this SAME
# floating, polygon-centred label. The template picture (page 420/421)
# shows the echelon glyph sitting IN the perimeter line itself, with a
# real gap cut in the line around it - the same "masked line-gap"
# construction c2_measures.py's own Boundary uses for its own echelon
# amplifier, not a second line of centred text. See
# _configure_area_designation_labeling()'s own docstring for the actual
# fix - the echelon glyph now renders as a wholly separate, masked label
# anchored on the perimeter, not as part of this expression at all.
_AREA_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'battle_position' THEN "
    "CASE WHEN \"prepared\" = 'P' THEN '(P) ' ELSE '' END"
    f" || {_PLAIN_DESIGNATION_LABEL_EXPRESSION}"
    " WHEN \"measure_type\" = 'strong_point' THEN "
    f"{_PLAIN_DESIGNATION_LABEL_EXPRESSION}"
    " WHEN \"measure_type\" = 'engagement_area' THEN "
    "'EA' || CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" ' ' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    " ELSE '' END"
)

# The echelon glyph itself (Table D-III) - just the character, no name/
# prefix, since it renders as its own separate label (see
# _configure_area_designation_labeling()). Only battle_position/
# strong_point ever populate "echelon" at all (Engagement Area has no
# Field B in the standard's own table), so no measure_type CASE is
# needed here the way _AREA_DESIGNATION_LABEL_EXPRESSION needs one - the
# rule this feeds is itself filtered to those two measure types (see
# below), and the field is blank by default for every other type.
_ECHELON_ON_PERIMETER_LABEL_EXPRESSION = _ECHELON_CHARACTER_EXPRESSION


def _configure_area_designation_labeling(layer):

    """
    Two independent labels per feature, not one - see this module's own
    _AREA_DESIGNATION_LABEL_EXPRESSION comment for why. QGIS's own
    QgsRuleBasedLabeling (already used for this same "more than one
    label config on one layer" need by c2_measures.py's own Airfield
    Zone) gives each label its own independent provider, so a single
    Battle Position/Strong Point feature gets BOTH its name label (rule
    1, unfiltered - applies to every measure type, matching this
    layer's previous single-label behaviour for Engagement Area) AND its
    own echelon label (rule 2, filtered to just those two measure types
    with a non-blank echelon).

    The echelon label is anchored at the polygon's own ORIGIN point -
    its first digitized vertex, `point_n($geometry, 1)` - per the
    project maintainer's own explicit instruction ("take the origin
    point as the place to insert the echelon"), via a label geometry
    generator (QgsPalLayerSettings.geometryGenerator*) rather than the
    feature's own polygon geometry, the labeling-engine equivalent of
    the QgsGeometryGeneratorSymbolLayer technique already used elsewhere
    in this project (e.g. c2_measures.py's own Airfield Zone icon,
    maneuver_control_measures.py's own Fortified Area outline) - the
    label is positioned exactly like a point label (Qgis.LabelPlacement.
    OverPoint) would be, just fed a computed point instead of a real
    point feature. Qgis.LabelQuadrantPosition.Over centres the label on
    that point in both axes (not offset to one side, the default for a
    point label) so it straddles the perimeter line evenly - the same
    effect c2_measures.py's own OnLine line-placement flag gives
    Boundary's own repeating label, achieved differently here because
    this echelon label is a single fixed point, not a placement running
    along the whole line.

    `masked_symbol_layer_ids` (see _build_pal_layer_settings()'s own
    docstring) cuts the actual gap in whichever of Battle Position's/
    Strong Point's own outline symbol layers the rendered feature
    actually uses - all three ids are always passed, since QGIS's
    masking simply finds no matching symbol layer (a harmless no-op) for
    whichever ones a given feature ISN'T using.

    **2026-08-10 correction, found by the project maintainer's own live
    testing**: Strong Point's own tick marks (_STRONG_POINT_TICK_
    SYMBOL_LAYER_ID) aren't part of the outline symbol layer at all - a
    separate QgsMarkerLineSymbolLayer placed at a fixed interval,
    unaware of where the echelon label's own masked gap falls - so the
    original version of this rule, which only masked the outline, left
    the nearby teeth still drawing right through the glyph. Adding the
    tick layer's own id to this same masked list cuts the gap through
    the ticks too, and a larger `mask_size_mm` (the default 1.2mm was
    tuned for masking a single plain line, not a toothed one) gives
    enough clearance that the couple of ticks closest to the origin
    point don't crowd the glyph's own edges.
    """

    name_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            _AREA_DESIGNATION_LABEL_EXPRESSION
        )
    )

    echelon_settings = _build_pal_layer_settings(
        layer,
        Qgis.LabelPlacement.OverPoint,
        _ECHELON_ON_PERIMETER_LABEL_EXPRESSION,
        masked_symbol_layer_ids=[
            _BATTLE_POSITION_OUTLINE_SYMBOL_LAYER_ID,
            _STRONG_POINT_OUTLINE_SYMBOL_LAYER_ID,
            _STRONG_POINT_TICK_SYMBOL_LAYER_ID,
        ],
        mask_size_mm=3.0
    )

    echelon_settings.geometryGeneratorEnabled = True

    echelon_settings.geometryGenerator = "point_n($geometry, 1)"

    echelon_settings.geometryGeneratorType = Qgis.GeometryType.Point

    echelon_settings.pointSettings().setQuadrant(
        Qgis.LabelQuadrantPosition.Over
    )

    echelon_rule = QgsRuleBasedLabeling.Rule(
        echelon_settings
    )

    echelon_rule.setFilterExpression(
        "\"measure_type\" IN ('battle_position', 'strong_point')"
        " AND \"echelon\" IS NOT NULL AND \"echelon\" != ''"
    )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    root_rule.appendChild(
        name_rule
    )

    root_rule.appendChild(
        echelon_rule
    )

    layer.setLabeling(
        QgsRuleBasedLabeling(root_rule)
    )

    layer.setLabelsEnabled(
        True
    )


def create_defensive_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Defensive Control Measures (Table
    H-VIII) - see this module's own docstring for the full measure-type
    list and what was scoped out (Contain/Retain, Table H-IX). "echelon"
    reuses the same Table D-III vocabulary/field config as c2_measures.
    py's own Boundary; "prepared" is new here (Battle Position's own
    "(P)" prefix - see module docstring).
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
            QgsField("echelon", QMetaType.Type.QString),
            QgsField("prepared", QMetaType.Type.QString),
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
        QgsDefaultValue("'battle_position'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)
    _configure_echelon_field(layer)

    prepared_idx = layer.fields().indexOf("prepared")

    layer.setEditorWidgetSetup(
        prepared_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map_with_none(_PREPARED_LABELS, "No")}
        )
    )

    layer.setDefaultValueDefinition(
        prepared_idx,
        QgsDefaultValue("''")
    )

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

    _configure_area_designation_labeling(
        layer
    )

    return layer


def add_defensive_control_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_defensive_control_measures_areas_layer
    )


# Table H-IX (Observation post, H.5.12.2) - see module docstring for why
# this moved out of the shared control_measure_points.py layer into its
# own dedicated one here. Rendered through milsymbol.js (mct_build_sidc/
# mct_sidc_svg), the SAME mechanism control_measure_points.py itself
# uses - a completely different rendering pipeline from Table H-VIII's
# own hand-built QGIS line/fill symbology above, so this section is
# self-contained rather than reusing any of this module's own Areas
# helpers.
POINT_ENTITY_LABELS = {
    "observation_post": "Observation Post/Outpost",
    "observation_post_reconnaissance": "Observation Post - Reconnaissance",
    "observation_post_forward_observer": "Observation Post - Forward Observer/Spotter",
    "observation_post_cbrn": "Observation Post - CBRN",
    "observation_post_sensor_listening": "Observation Post - Sensor/Listening Post",
    "observation_post_combat": "Observation Post - Combat Outpost",
    "target_reference_point": "Target Reference Point",
}

# H.5.3's own affiliation rule for POINT control measures is the base
# standard's ordinary friend/hostile/neutral/unknown vocabulary (no
# "unspecified" 5th value) - milsymbol.js already renders it correctly
# with no extra code needed, exactly as control_measure_points.py's own
# docstring documents; this is deliberately NOT the same
# AFFILIATION_LABELS this module's own Areas layer imports from
# _control_measure_shared (that 5-value, "unspecified"-inclusive set is
# specific to the hand-built line/fill symbology's own data-defined
# colour expression, a different rendering mechanism entirely).
# The four real SIDC standard identities - see
# POINT_AFFILIATION_LABELS in _control_measure_shared.py for why a
# Points layer must not use the lines/areas AFFILIATION_LABELS.
_POINT_AFFILIATION_LABELS = POINT_AFFILIATION_LABELS

_POINT_STATUS_LABELS = {
    "present": "Present",
    "planned": "Planned",
}

DEFAULT_POINT_MARKER_SIZE_MM = 8.0

# Literal 'control_measure'/'unspecified'/false for the symbol_set/
# echelon/headquarters positions mct_build_sidc() still requires - this
# layer has no fields for them, matching control_measure_points.py's own
# _SIDC_EXPRESSION exactly (H.5.1.1 control-measure amplifiers don't
# include echelon/headquarters for this point family). The
# "unique_designation" field IS passed through, upper-cased per H.5.4
# Labeling - see c2_measures.py's own _POINT_SIDC_EXPRESSION comment for
# the 2026-08-10 fixes this needed (both the field being ignored
# entirely at first, and then not being upper-cased).
_POINT_SIDC_EXPRESSION = (
    "mct_sidc_svg(mct_build_sidc("
    "\"affiliation\",\"entity\",'control_measure','unspecified',"
    "\"status\",false"
    "),upper(coalesce(\"unique_designation\",'')))"
)

# **2026-08-10, live-testing follow-up, two real bugs found in Table
# H-IX's own six Observation Post entities** (Target Reference Point,
# the table's 7th entry, is unaffected by either - see each one's own
# comment below for why).
#
# **Bug 1 - unique designation never rendered at all.** Unlike the box
# +cone family in c2_measures.py (which had the wrong milsymbol.js
# text-slot NAME), these six entities have NO text-slot position
# config in milsymbol.js at all - confirmed by reading vendor/
# milsymbol.js's own control-measure position-config table directly:
# `t[160100]={},t[160200]={},t[160201]={},t[160202]={},t[160203]={},
# t[160204]={},t[160205]={}` - every one of them is a genuinely EMPTY
# object, unlike Target Reference Point's own `t[160300]=
# {uniqueDesignation:{...}}` right next to them, which DOES have one
# (and already renders correctly, untouched here). Passing text into
# mct_sidc_svg() for any of the six achieves nothing - milsymbol has no
# coordinates to place it at. Table H-IX's own template picture (page
# 425) shows the "(Specified)" variant's own type letter sitting near
# the triangle's own visual centre (right where the template's own
# "CENTER POINT" arrow points), so a real QGIS point label - not a
# milsymbol-drawn one - placed directly over the feature's own point is
# the right fix, matching the picture closely enough ("recognisable,
# not exact" for placement, same standard the rest of this project
# holds decorative/secondary detail to). See
# _configure_points_labeling() below.
_OBSERVATION_POST_ENTITIES_WITHOUT_A_MILSYMBOL_TEXT_SLOT = (
    "'observation_post', 'observation_post_reconnaissance', "
    "'observation_post_forward_observer', 'observation_post_cbrn', "
    "'observation_post_sensor_listening', 'observation_post_combat'"
)

_POINTS_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"entity\" IN ("
    + _OBSERVATION_POST_ENTITIES_WITHOUT_A_MILSYMBOL_TEXT_SLOT
    + ") THEN upper(coalesce(\"unique_designation\",'')) ELSE '' END"
)

# A real point label needs its own (small) font size - every other
# label this project builds sits on a line or fills an area several
# times this layer's own 8mm marker size, so the shared LABEL_FONT_SIZE
# (9pt, _control_measure_shared.py) badly overflowed the triangle on a
# first render (confirmed live, not assumed).
#
# **2026-08-10 follow-up**: the project maintainer's own live testing
# found the shared 3.5pt size unreadable specifically for "Observation
# Post/Outpost" (the plain, unspecified variant - an otherwise EMPTY
# triangle, so it has the most room of any entity here) and asked for
# 8pt there; Forward Observer/Spotter (confirmed fixed the same round)
# was left as-is. Bumping the SHARED size to 8pt for every entity would
# have crowded the other five, which all have their own interior glyph
# (line/dot/squiggle) sharing the triangle with the text already - so
# this is a per-entity data-defined size (see _POINTS_LABEL_FONT_SIZE_
# EXPRESSION below) rather than a single constant, the plain variant
# gets the maintainer's own requested 8pt, the rest keep the smaller
# size that already fits them.
_POINTS_LABEL_FONT_SIZE = 3.5

_POINTS_LABEL_FONT_SIZE_LARGE = 8.0

_POINTS_LABEL_FONT_SIZE_EXPRESSION = (
    "CASE WHEN \"entity\" = 'observation_post'"
    f" THEN {_POINTS_LABEL_FONT_SIZE_LARGE} ELSE {_POINTS_LABEL_FONT_SIZE} END"
)

# **Bug 2 - Forward Observer/Spotter's own diagonal line missing.**
# milsymbol.js's own icn["TP.FORWARD OBSERVER POSITION"] (vendor/
# milsymbol.js, sourced from milsymbol-3.0.4's own src/iconparts/
# tactical-points.js) draws only the triangle outline and the filled
# dot - confirmed by rendering the actual SIDC and reading the returned
# SVG directly (`<path d="m 100,45 48,83 H 52.4 Z">` for the triangle,
# `<path d="m 115,100 c ...">` for the dot, nothing else). The
# standard's own template picture (page 425) clearly shows a THIRD
# element: a diagonal line from the triangle's bottom-left vertex,
# through the dot, to the midpoint of the triangle's own right edge -
# the exact same diagonal Reconnaissance Outpost's own icon
# (160201, "TP.OBSERVATION POST/RECONNAISSANCE") already draws on its
# own (`M 52.3687,127.5 123.816,86.2499`), just without a dot on it.
# A genuine gap in the vendored third-party library, not a slot-naming
# mismatch this time - there's nothing to configure our way out of.
#
# Rather than hand-patching the vendored milsymbol.js file (a real,
# citable MIT-licensed third party artifact - see THIRD_PARTY_NOTICES.md
# - not something this project edits in place), the missing line is
# added as our own extra marker layer drawn BENEATH the SVG icon layer,
# the same "milsymbol is missing a stroke, add our own layer for just
# this one entity" technique c2_measures.py's own Distress Call diagonal
# anchor line already established (LayerEnabled data-defined per
# entity) - drawn BENEATH rather than above the SVG this time, so the
# dot (part of the SVG's own single image) sits on TOP of the line,
# matching the template picture, rather than covering it.
#
# The two endpoints below are milsymbol's own local SVG coordinates
# (confirmed live via render_symbol_svg(), not eyeballed from the
# rendered picture): triangle apex (100,45), bottom-right (148,128),
# bottom-left (52.4,128) - the line runs from the bottom-left vertex to
# the midpoint of the apex-to-bottom-right edge, (124,86.5). The SVG
# marker's own default anchor (unchanged here, no VerticalAnchor
# override - the standard's own template explicitly marks this family's
# anchor as "CENTER POINT") is the declared viewBox's own bounding-box
# centre, local (100,95) - confirmed by rendering a real feature and
# checking where it lands relative to the feature's own digitized point.
_OP_FORWARD_OBSERVER_LOCAL_ANCHOR = (100.0, 95.0)
_OP_FORWARD_OBSERVER_LOCAL_START = (52.4, 128.0)
_OP_FORWARD_OBSERVER_LOCAL_END = (124.0, 86.5)

# mm-per-local-unit at DEFAULT_POINT_MARKER_SIZE_MM, measured
# empirically rather than assumed from the SVG's own declared
# width="108"/height="118" attributes (neither one alone, used as a
# straightforward "size maps to this dimension" guess, matched closely
# enough to trust): rendered a real 8mm feature, isolated the filled
# dot's own pixel bounding box (a filled shape measures far more
# precisely than a thin stroked outline, which anti-aliases into an
# ambiguous edge), and solved for the scale from its known local
# radius of 15 units against its measured rendered pixel radius.
_OP_LOCAL_UNITS_TO_MM = DEFAULT_POINT_MARKER_SIZE_MM / 103.08


def _forward_observer_anchor_line_geometry():

    """
    Returns (length_mm, angle_degrees, offset) for the Forward Observer
    diagonal line's own QgsSimpleMarkerSymbolLayer, derived from the
    local SVG coordinates above rather than hand-measured off a
    picture - see this module's own "Bug 2" comment above.

    Unlike c2_measures.py's own Distress Call diagonal (whose anchor
    sits AT one literal end of its own line, so its offset is simply
    "half the line's own length, along its own axis"), this family's
    anchor - the SVG's own bbox centre, local (100,95) - is close to
    but not actually ON the line at all (the line's own true midpoint
    is close to the dot's centre, local (100,100)), so the target
    offset has to be computed directly from both endpoints rather than
    from the angle alone. The same "pre-rotate by the inverse of the
    layer's own angle, so QGIS's own forward rotation of `offset` lands
    it correctly" step still applies - see _distress_call_anchor_line_
    offset()'s own comment in c2_measures.py for the confirmed rotation
    convention this reuses (QgsSimpleMarkerSymbolLayer's `angle` rotates
    both the drawn Shape.Line - vertical at angle=0 - and its own
    `offset`, as a standard counter-clockwise rotation of the (x, y)
    vector in screen coordinates).
    """

    anchor_x, anchor_y = _OP_FORWARD_OBSERVER_LOCAL_ANCHOR
    start_x, start_y = _OP_FORWARD_OBSERVER_LOCAL_START
    end_x, end_y = _OP_FORWARD_OBSERVER_LOCAL_END

    delta_x = end_x - start_x
    delta_y = end_y - start_y

    length_mm = math.hypot(delta_x, delta_y) * _OP_LOCAL_UNITS_TO_MM

    # Shape.Line is vertical (direction (0, 1)) at angle=0 - the angle
    # that rotates it to point along (delta_x, delta_y) instead.
    angle_radians = math.atan2(-delta_x, delta_y)

    final_x = ((start_x + end_x) / 2 - anchor_x) * _OP_LOCAL_UNITS_TO_MM
    final_y = ((start_y + end_y) / 2 - anchor_y) * _OP_LOCAL_UNITS_TO_MM

    inverse = -angle_radians

    offset = QPointF(
        final_x * math.cos(inverse) - final_y * math.sin(inverse),
        final_x * math.sin(inverse) + final_y * math.cos(inverse),
    )

    return length_mm, math.degrees(angle_radians), offset


def _forward_observer_anchor_line_layer():

    length_mm, angle_degrees, offset = _forward_observer_anchor_line_geometry()

    # Built directly via the concrete QgsSimpleMarkerSymbolLayer class,
    # not extracted from a QgsMarkerSymbol.createSimple() wrapper - see
    # c2_measures.py's own _distress_call_anchor_line_layer() docstring
    # for the dangling-reference segfault that pattern caused there.
    line_layer = QgsSimpleMarkerSymbolLayer()

    line_layer.setShape(
        QgsSimpleMarkerSymbolLayerBase.Shape.Line
    )

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setStrokeColor(
        QColor(0, 0, 0)
    )

    line_layer.setStrokeWidth(
        0.5
    )

    line_layer.setSize(
        length_mm
    )

    line_layer.setAngle(
        angle_degrees
    )

    line_layer.setOffset(
        offset
    )

    line_layer.setOffsetUnit(
        Qgis.RenderUnit.Millimeters
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.LayerEnabled,
        QgsProperty.fromExpression(
            "\"entity\" = 'observation_post_forward_observer'"
        )
    )

    return line_layer


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
    layer.setDefaultValueDefinition(entity_idx, QgsDefaultValue("'observation_post'"))
    layer.setDefaultValueDefinition(status_idx, QgsDefaultValue("'present'"))


def _build_points_renderer():

    # Two symbol layers: the Forward Observer diagonal line FIRST (so it
    # draws underneath - see this module's own "Bug 2" comment for why
    # the ordering matters here, the opposite of c2_measures.py's own
    # Distress Call anchor line), then the QgsSvgMarkerSymbolLayer whose
    # own path is data-defined per feature via _POINT_SIDC_EXPRESSION -
    # same mechanism as control_measure_points.py's own
    # _build_renderer(), already confirmed live to work. The line layer
    # is a no-op for every other entity via its own LayerEnabled
    # data-defined property.
    symbol = QgsMarkerSymbol()

    symbol.changeSymbolLayer(
        0,
        _forward_observer_anchor_line_layer()
    )

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(
        DEFAULT_POINT_MARKER_SIZE_MM
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(_POINT_SIDC_EXPRESSION)
    )

    symbol.appendSymbolLayer(
        svg_layer
    )

    return QgsSingleSymbolRenderer(symbol)


def _configure_points_labeling(layer):

    """
    A real QGIS point label for the six Observation Post entities
    milsymbol.js has no text-slot position config for at all - see this
    module's own "Bug 1" comment above _POINTS_DESIGNATION_LABEL_
    EXPRESSION for the full finding. Placed directly OVER the feature's
    own point (Qgis.LabelPlacement.OverPoint + Quadrant.Over, offset
    (0, 0)) - the SVG marker's own default anchor is already the icon's
    visual centre (see _OP_FORWARD_OBSERVER_LOCAL_ANCHOR's own comment),
    which is where the standard's own template picture shows this
    family's text sitting too, so no extra offset is needed to land
    close to the picture.
    """

    settings = QgsPalLayerSettings()

    settings.fieldName = _POINTS_DESIGNATION_LABEL_EXPRESSION

    settings.isExpression = True

    settings.placement = Qgis.LabelPlacement.OverPoint

    settings.pointSettings().setQuadrant(
        Qgis.LabelQuadrantPosition.Over
    )

    text_format = build_text_format(
        _POINTS_LABEL_FONT_SIZE,
        bold=True
    )

    settings.setFormat(
        text_format
    )

    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Size,
        QgsProperty.fromExpression(_POINTS_LABEL_FONT_SIZE_EXPRESSION)
    )

    layer.setLabeling(
        QgsVectorLayerSimpleLabeling(settings)
    )

    layer.setLabelsEnabled(
        True
    )


def create_defensive_control_measures_points_layer(name=POINTS_LAYER_NAME):

    """
    A fresh, empty point layer for Table H-IX (Observation post,
    H.5.12.2) - see module docstring for why this is a separate layer
    from the Areas one above rather than a shared "Defensive Control
    Measures" layer covering both geometry types (QGIS layers are always
    a single geometry type, same reason c2_measures.py/maneuver_control_
    measures.py each split Lines from Areas).
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

    _configure_points_labeling(layer)

    return layer


def add_defensive_control_measures_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_defensive_control_measures_points_layer
    )
