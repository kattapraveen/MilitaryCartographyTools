# -*- coding: utf-8 -*-

"""
Builds ready-to-use Maneuver Control Measures layers - MIL-STD-2525D
Appendix H.5.11 (Table H-VII), the second H.5.x logical group after
c2_measures.py's own H.5.5/H.5.9/H.5.10 - see that module's own
docstring for the full "why a separate module per logical group"
rationale and _control_measure_shared.py for the genuinely cross-group
helpers this module reuses (affiliation/status field config and
colouring, the rule-based renderer/labeling builders, the status-driven
area outline, the fixed-end-label line-marker helper).

**Mini-Phase H3, 2026-08-09.** Table H-VII (pages 410-419) - read
template/draw-rules/example for every entry before building it, per the
project maintainer's own explicit instruction this mini-phase (fewer
errors than batch-reading a whole appendix at once). Confirmed first,
directly against the vendored milsymbol.js source (grepped for every
control measure name in this table and for symbol-set-25/tactical-
graphics support generally): milsymbol.js has ZERO support for any of
these - it is a point-icon-only renderer (confirmed: no "MultiPoint"/
"tactical graphic" string anywhere in its own source, zero literal
symbol-set-25 codes), so every measure type here is 100% hand-built
QGIS symbology, the same as c2_measures.py's own Boundary/Light Line.

**Scope decisions made with the project maintainer before building**
(see docs/roadmap.md's own H3 entry for the full reasoning):
  - **Occupied Assembly Area with Offset Unit/Units (150301/150302)
    skipped outright, not silently dropped** - needs a SECOND connected
    geometry (a leader line to an external point/icon) that doesn't fit
    this module's "one feature, one symbol" model the way every other
    entry here does - deferred to a future pass if compound area+point+
    leader geometry is ever genuinely needed.
  - **Line of Contact (140200), despite the standard's own DRAW RULES
    text describing it as "created when both the friendly and enemy
    forward line of troops symbols are displayed" (a compositing
    outcome, not its own SIDC-coded symbol), IS built as its own
    selectable measure type** - the maintainer's own explicit request,
    since hand-placing two perfectly parallel FLOT features to get this
    effect isn't practical for a user. See _line_of_contact_symbol()'s
    own comment.
  - **Field N ("Hostile (Enemy)", literal fixed text "ENY") is not
    rendered at all** - per Table VII's own field definition (5.3.4)
    this is a monochrome-only fallback marker; this plugin is a colour
    system and already conveys hostile via the existing Affiliation
    field's own red colouring (H.5.1.1.1), so a literal "ENY" box would
    just duplicate what colour already shows. Confirmed directly by the
    maintainer (their own words: "if colour coded, then ENY is not
    required... only in grayscale ENY is written"). Nothing in this
    module defaults any field to the literal text "ENY".
  - **"Occupied Assembly Area" (150300) folded into "Assembly Area"
    (150200), and "Friendly Area"/"Enemy Area" (150101/150103) folded
    into one plain "Area" (matching Table H-VII's own generic 150100
    header code)** - each pair's own TEMPLATE column is visually
    identical (the standard's own note on Occupied Assembly Area's
    example confirms the unit icon shown there "is not part of this
    control measure symbol"), and the only thing that DID visually
    distinguish Friendly/Enemy Area was the now-omitted Field N box -
    once that's gone, offering two dropdown entries that always render
    pixel-identically added little value. The Affiliation field already
    covers what "friendly" vs "enemy" would have shown.
  - **Status-pair codes folded into ONE measure type using the existing
    shared "status" field** wherever the underlying shape doesn't
    actually change between Present/Planned - matching Boundary/Light
    Line's own established precedent - rather than modelling every one
    of the table's own present/planned SIDC code pairs as separate
    dropdown entries: FLOT, and every area type here. FEBA (140400) and
    Proposed FEBA (140401) fold the same way, once the DRAW RULES text
    is read carefully - see _feba_symbol()'s own comment for why the
    "3 anchor points vs 2" distinction the standard notes doesn't
    actually need separate symbol-building code (the apex, if any,
    comes from whatever vertices the user themselves digitizes, exactly
    like every other line/area in this appendix).

**2026-08-09 correction pass, after the maintainer's own live QGIS
testing** (see docs/roadmap.md's own H3 follow-up entry for the full
narrative):
  - **FLOT was wrongly split into flot_friendly/flot_enemy** - it is
    ONE symbol for both, differentiated only by the existing
    Affiliation field's own colour, exactly like every other line/area
    here. Folded into a single `flot` measure type.
  - **FLOT's own arcs were wrongly drawn with `Shape.SemiCircle`**,
    which QGIS renders as a closed half-disc - its own stroked outline
    includes the flat diameter edge as a straight "chord" closing the
    shape, which the maintainer's own live rendering caught as an
    unwanted line the standard's own open-crescent shape doesn't have.
    Switched to `Shape.HalfArc` (a genuinely open arc, no chord) - see
    _arc_marker_layer()'s own comment.
  - **Line of Contact (140200) is now built as its own measure type**
    at the maintainer's own explicit request (see the scope-decisions
    section above) - two of the same arc chains, offset a small gap
    apart, bulging toward each other, always black.
  - **Phase Line's own perpendicular end tick was removed** - re-reading
    the standard's own EXAMPLE column at the maintainer's own
    instruction showed the tick was this project's own misreading of
    illustrative grey annotation as real symbol geometry, the same
    mistake already caught once for Light Line's own up-arrow callout
    in c2_measures.py. Phase Line is just the line with "PL <name>" at
    each end, nothing more.
  - **Fortified Area's crenellated outline was rebuilt** - the earlier
    version (a single row of Square markers spaced apart along a plain
    outline) read as a beaded chain of floating squares with visible
    gaps, not the standard's own continuous castellated silhouette (the
    maintainer's own side-by-side comparison against the standard's own
    "TANGO" example caught this). A follow-up rebuild (two staggered
    chains of touching squares) fixed the gap but broke down on a real
    curved/multi-vertex boundary rather than a synthetic rectangle -
    still a styling trick, not real geometry. Replaced with a genuine
    computed crenellated outline via a new mct_crenellate_outline()
    expression function and a QgsGeometryGeneratorSymbolLayer - see
    _fortified_area_symbol()'s own comment.
  - **Limited Access Area (151100) is now built** (previously skipped
    entirely) as a hatched-fill freeform area, the same technique as
    this appendix's other hatched areas - the standard's own separate
    leader-line-plus-point-icon detail is dropped as a documented
    simplification, see _limited_access_area_symbol()'s own comment.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFillSymbol,
    QgsGeometryGeneratorSymbolLayer,
    QgsFontMarkerSymbolLayer,
    QgsLinePatternFillSymbolLayer,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, QPointF
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    STATUS_LABELS,
    _PLAIN_DESIGNATION_LABEL_EXPRESSION,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_designation_labeling,
    _configure_status_field,
    _end_label_layer,
    _status_driven_area_outline_symbol,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "Maneuver Control Measures (Lines)"
AREAS_LAYER_NAME = "Maneuver Control Measures (Areas)"

__all__ = [
    "LINES_LAYER_NAME",
    "AREAS_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AREA_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_maneuver_control_measures_lines_layer",
    "create_maneuver_control_measures_areas_layer",
    "add_maneuver_control_measures_lines_layer",
    "add_maneuver_control_measures_areas_layer",
]

# Table H-VII, H.5.11.1 (Lines). Category headers (140000 "Maneuver
# Lines", 140100 "Forward Line of Troops") are excluded.
LINE_MEASURE_TYPE_LABELS = {
    "flot": "Forward Line of Troops (FLOT)",
    "line_of_contact": "Line of Contact (LOC)",
    "phase_line": "Phase Line (PL)",
    "feba": "Forward Edge of the Battle Area (FEBA)",
    "principal_direction_of_fire": "Principal Direction of Fire",
}

# Table H-VII, H.5.11.2 (Areas). Category headers (150000 "Maneuver
# Areas", 150100 "Area", 150500 "Action Area") are excluded; Occupied
# Assembly Area (150300) folded into Assembly Area, Friendly/Enemy Area
# (150101/150103) folded into plain Area, Offset-Unit variants
# (150301/150302) skipped entirely - see module docstring for the
# reasoning behind each.
AREA_MEASURE_TYPE_LABELS = {
    "area": "Area",
    "assembly_area": "Assembly Area (AA)",
    "joint_tactical_action_area": "Joint Tactical Action Area (JTAA)",
    "submarine_action_area": "Submarine Action Area (SAA)",
    "submarine_generated_action_area": "Submarine-Generated Action Area (SGSA)",
    "drop_zone": "Drop Zone (DZ)",
    "extraction_zone": "Extraction Zone (EZ)",
    "landing_zone": "Landing Zone (LZ)",
    "pickup_zone": "Pickup Zone (PZ)",
    "fortified_area": "Fortified Area",
    "limited_access_area": "Limited Access Area (LAA)",
}

# FLOT's own coiled crescent line is drawn as a stroked HalfArc outline
# (see _wavy_line_symbol()'s own comment), not a QgsSimpleLineSymbolLayer
# - so the shared module's own _STATUS_LINE_STYLE_EXPRESSION ('dash'/
# 'solid') doesn't apply; the template's own Planned row shows a DOTTED
# version of the identical shape, not a dashed one, so this is a
# genuinely different (but same-shaped) CASE expression, not a reuse of
# the shared one. Also reused by Line of Contact below.
_FLOT_STROKE_STYLE_EXPRESSION = (
    "CASE WHEN \"status\" = 'planned' THEN 'dot' ELSE 'solid' END"
)


def _arc_marker_layer(interval_mm, offset_mm=0.0, angle=0, fixed_color=None, size_mm=6):

    """
    One continuous chain of open semicircular arcs along a line - the
    shared building block for Forward Line of Troops and Line of
    Contact. Uses `QgsSimpleMarkerSymbolLayerBase.Shape.HalfArc` (an
    open arc), NOT `Shape.SemiCircle` (a closed half-DISC, whose own
    stroked outline includes the flat diameter edge as a straight
    "chord" closing the shape) - the maintainer's own live QGIS testing
    caught the SemiCircle version rendering that unwanted chord line,
    which HalfArc doesn't draw at all.

    `angle` rotates which way the arc bulges (0 = default orientation;
    180 = the mirror image) - used by Line of Contact to make its own
    two offset copies bulge toward each other. `offset_mm` shifts the
    whole chain perpendicular to the base line (also for Line of
    Contact, to place the friendly/enemy chains a visible gap apart
    instead of directly on top of the digitized line). `fixed_color`,
    when given, hardcodes the stroke colour instead of the usual
    affiliation-driven one - Line of Contact's own enemy-side chain is
    always red, not affiliation-driven (see _line_of_contact_symbol()'s
    own comment). `size_mm` is the arc's own diameter - defaults to 6
    (the original size both measure types shipped with), overridden by
    both FLOT and Line of Contact to 3.6mm (-40%, 2026-08-10) after the
    project maintainer's own live testing found the original size too
    big for both.
    """

    arc_layer = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.HalfArc,
        size_mm
    )

    arc_layer.setColor(
        QColor(0, 0, 0, 0)
    )

    arc_layer.setStrokeWidth(
        0.5
    )

    arc_layer.setAngle(
        angle
    )

    if fixed_color is not None:

        arc_layer.setStrokeColor(
            fixed_color
        )

    else:

        _apply_affiliation_color(
            arc_layer,
            [QgsSymbolLayer.Property.StrokeColor]
        )

    arc_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_FLOT_STROKE_STYLE_EXPRESSION)
    )

    arc_marker = QgsMarkerSymbol()

    arc_marker.changeSymbolLayer(
        0,
        arc_layer
    )

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(
        arc_marker
    )

    marker_line.setPlacements(
        Qgis.MarkerLinePlacement.Interval
    )

    marker_line.setInterval(
        interval_mm
    )

    marker_line.setIntervalUnit(
        Qgis.RenderUnit.Millimeters
    )

    if offset_mm:

        marker_line.setOffset(
            offset_mm
        )

        marker_line.setOffsetUnit(
            Qgis.RenderUnit.Millimeters
        )

    return marker_line


# Both FLOT's and Line of Contact's own arcs render at this size
# (2026-08-10: reduced from the original 6mm, -40%, after the project
# maintainer's own live testing found the original too big for both).
_ARC_SIZE_MM = 6 * 0.6


def _flot_symbol():

    """
    Table H-VII, H.5.11.1 (codes 140101/102 Friendly, 140103/104 Enemy).
    **A single measure type, not split by affiliation** - the
    maintainer's own correction: FLOT is one and the same symbol for
    friendly and enemy, differentiated only by the existing Affiliation
    field's own colour (black/unspecified by default, blue for friend,
    red for hostile - H.5.1.1.1), the same way every other line/area in
    this appendix already works. A single continuous chain of touching
    open arcs (interval == the arc's own size, so consecutive crescents
    touch with no gap) - the maintainer's own correction: the "wider gap
    for Enemy" this project built earlier was wrong, both render as one
    unbroken coil.
    """

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        _arc_marker_layer(_ARC_SIZE_MM, size_mm=_ARC_SIZE_MM)
    )

    return symbol


def _line_of_contact_symbol():

    """
    Table H-VII, code 140200. Not a separate SIDC-coded symbol in the
    standard's own text (its own DRAW RULES describe it as the visual
    outcome of a friendly FLOT and an enemy FLOT placed adjacent), but
    the maintainer asked for it as its own selectable measure type here
    since building it by hand (placing two real FLOT features exactly
    parallel) is impractical for a user. Two offset copies of the same
    arc chain, a gap apart, bulging toward EACH OTHER across that gap -
    ")(" - the friendly-side chain bulges toward the enemy (away from
    friendly territory), the enemy-side chain (red) bulges toward
    friendly (away from enemy territory).

    **2026-08-10 correction, found by the project maintainer's own live
    testing**: alongside the same -40% arc size reduction FLOT got, the
    friendly-side chain's own fixed colour changed from black to BLUE
    (the enemy-side chain stays fixed red - neither is affiliation-
    driven, since both sides are always shown at once regardless of the
    feature's own Affiliation value), and the gap between the two chains
    - which had gone through several earlier rounds (3mm read as
    touching; 6mm read as too much; settled on 4.5mm) - was reduced
    again to a "very slight, barely discernible" separation now that the
    arcs themselves are smaller.
    """

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        _arc_marker_layer(
            _ARC_SIZE_MM,
            offset_mm=2.2,
            angle=0,
            fixed_color=QColor(0, 0, 255),
            size_mm=_ARC_SIZE_MM
        )
    )

    symbol.appendSymbolLayer(
        _arc_marker_layer(
            _ARC_SIZE_MM,
            offset_mm=-2.2,
            angle=180,
            fixed_color=QColor(255, 0, 0),
            size_mm=_ARC_SIZE_MM
        )
    )

    return symbol


def _end_designation_label_layer(placement, prefix):

    """
    Like _control_measure_shared.py's own _end_label_layer(), but the
    font marker's own Character is DATA-DEFINED (`QgsSymbolLayer.
    Property.Character`, evaluated per feature) instead of a fixed
    literal - for Phase Line's own "PL" + the user's own name, which
    (unlike FEBA's fixed "FEBA") has to show DIFFERENT text at each end
    depending on what the user actually typed. Routing this through the
    Lines layer's general along-line PAL label instead (the way Phase
    Line's own name was first tried) put a single "PL ECHO" wherever
    PAL found room along the line - usually nowhere near either end,
    unlike the standard's own template, which pairs the label with the
    tick at EACH end specifically. A data-defined end marker fixes
    that the same way a fixed one already does for FEBA/Light Line.
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

    font_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Character,
        QgsProperty.fromExpression(
            f"'{prefix}' || CASE WHEN \"unique_designation\" IS NOT NULL"
            " AND \"unique_designation\" != '' THEN"
            f" ' ' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
        )
    )

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

    label_layer = QgsMarkerLineSymbolLayer(True)

    label_layer.setSubSymbol(
        label_marker
    )

    label_layer.setPlacements(
        placement
    )

    return label_layer


def _phase_line_symbol():

    """
    Table H-VII, code 140300, page 413. "A line utilized for control
    and coordination of military operations, usually a terrain feature
    extending across the zone of action." A plain status-driven solid/
    dashed line (H.5.1.1.3) with "PL" + the user's own name at each end
    (see _end_designation_label_layer()'s own comment for why this needs
    a data-defined symbol-layer marker rather than the general along-
    line PAL label every other measure type here uses).

    **2026-08-09 correction (maintainer's own live QGIS testing)**: an
    earlier version of this symbol also drew a perpendicular tick at
    each end, reading the standard's own EXAMPLE column as if it showed
    real end-of-line geometry. It doesn't - the maintainer confirmed
    Phase Line is just the line itself with "PL <name>" at each end, no
    tick, and flagged that this project had (again) mis-read illustrative
    grey/annotation content in the standard's own picture as if it were
    drawn symbol geometry - the same category of mistake as Light Line's
    own up-arrow callout in c2_measures.py. Tick removed.
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
            _end_designation_label_layer(placement, "PL")
        )

    return symbol


def _feba_symbol():

    """
    Table H-VII, code 140400, page 413. "The foremost limits of a
    series of areas in which ground combat units are deployed..." A
    plain status-driven solid/dashed line with a fixed "FEBA" label at
    each end (see _control_measure_shared.py's own _end_label_layer()) -
    confirmed against the EXAMPLE column (page 413) that "FEBA" itself
    is drawn in solid black at each end with NO tick, unlike Phase Line
    (the nearby grey "PL KING"/boxed echelon amplifier shown alongside
    it in the example are a different, illustrative boundary line for
    context, not part of FEBA's own symbol).

    **140401 "Proposed or On Order FEBA" is NOT a separate measure
    type here** - re-reading the DRAW RULES column (shared across both
    140400 and 140401's own rows) shows the "3 anchor points, point 2
    defines the apex" language is guidance for how the USER should
    digitize a forward-bulging shape, not something this module's own
    symbol needs to construct: the apex (if the user gives one) already
    comes from whichever vertices they draw, exactly like Boundary's
    own middle vertices. The only real difference between 140400/140401
    is present-vs-planned line style, which the existing shared
    "status" field already drives - see _STATUS_LINE_STYLE_EXPRESSION's
    own comment.
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
            _end_label_layer(placement, "FEBA")
        )

    return symbol


def _principal_direction_of_fire_symbol():

    """
    Table H-VII, code 140500, page 414. A plain black line drawn
    through the user's own 3 digitized vertices (PT2 -> PT1 -> PT3 per
    the standard's own point order, which also sets the symbol's
    orientation) with an arrowhead at each end (FirstVertex/LastVertex)
    - the "V" shape comes naturally from the line passing back through
    the shared vertex PT1, no geometry-generator/compound construction
    needed. No status field used - the table shows a single code with
    no separate Planned variant.

    **2026-08-09 correction (maintainer's own live QGIS testing)**: only
    the arrowhead at the FIRST point the user clicks (PT2, FirstVertex)
    is rotated 180 degrees from its own original default - the
    LastVertex arrow (PT3) is left at its own default orientation
    unchanged. An earlier attempt at this fix rotated BOTH arrows,
    which the maintainer caught and corrected; the two ends are not
    symmetric here.

    **No vertex label** - Field A's own boxed "A" (Table VII/5.3.4's
    master field list) marks where a separate weapon/unit symbol is
    meant to sit at the shared vertex, not literal text to render. An
    earlier version of this symbol drew a plain "A" character there as
    a placeholder; the maintainer asked for it to be dropped until that
    symbol-at-the-vertex feature is actually built - just the line and
    its two arrowheads for now.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        0.5
    )

    _apply_affiliation_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    for placement, angle in (
        (Qgis.MarkerLinePlacement.FirstVertex, 180),
        (Qgis.MarkerLinePlacement.LastVertex, 0),
    ):

        arrow_marker = QgsMarkerSymbol.createSimple(
            {
                "name": "filled_arrowhead",
                "color": "0,0,0",
                "outline_color": "0,0,0",
                "size": "4",
                "angle": str(angle),
            }
        )

        _apply_affiliation_color(
            arrow_marker.symbolLayer(0),
            [QgsSymbolLayer.Property.FillColor, QgsSymbolLayer.Property.StrokeColor]
        )

        arrow_layer = QgsMarkerLineSymbolLayer(True)

        arrow_layer.setSubSymbol(
            arrow_marker
        )

        arrow_layer.setPlacements(
            placement
        )

        symbol.appendSymbolLayer(
            arrow_layer
        )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "flot": _flot_symbol,
    "line_of_contact": _line_of_contact_symbol,
    "phase_line": _phase_line_symbol,
    "feba": _feba_symbol,
    "principal_direction_of_fire": _principal_direction_of_fire_symbol,
}


def _fortified_area_symbol():

    """
    Table H-VII, code 151000, page 419. Two earlier attempts at this
    symbol's own crenellated/castellated outline both used
    QgsMarkerLineSymbolLayer styling tricks (a single row of spaced
    Square markers, then two staggered offset rows of touching ones) -
    both read as a beaded chain of floating squares rather than the
    standard's own continuous castellated silhouette once tested on a
    real digitized (curved, multi-vertex) boundary, not just a synthetic
    rectangle - the maintainer's own side-by-side comparison against the
    standard's own "TANGO" example, on a real map, caught this both
    times. A genuine geometry construction was needed instead: this
    symbol's own outline is a QgsGeometryGeneratorSymbolLayer that
    replaces the polygon's own boundary with
    expressions/military_symbology_functions.py's own
    mct_crenellate_outline($geometry, 14) - a real square-wave path
    walked around the ring (see that function's own comment for the
    algorithm) - rendered as a plain stroked line, not a fill.
    """

    outline_marker = QgsLineSymbol()

    outline_layer = outline_marker.symbolLayer(0)

    outline_layer.setWidth(
        0.3
    )

    _apply_affiliation_color(
        outline_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    generator_layer = QgsGeometryGeneratorSymbolLayer.create({})

    generator_layer.setGeometryExpression(
        "mct_crenellate_outline($geometry, 14)"
    )

    generator_layer.setSymbolType(
        Qgis.SymbolType.Line
    )

    generator_layer.setSubSymbol(
        outline_marker
    )

    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
        }
    )

    symbol.changeSymbolLayer(
        0,
        generator_layer
    )

    return symbol


def _limited_access_area_symbol():

    """
    Table H-VII, code 151100, page 419. A freeform area with a genuine
    diagonal hatched fill (its own template's fill is drawn hatched
    throughout, not a plain outline) - the same QgsLinePatternFillSymbol
    Layer-over-status-driven-outline technique already used for this
    appendix's other hatched areas (airspace_control_measures.py's own
    Weapons Free Zone, fire_support_coordination_measures.py's own No
    Fire Area).

    **Simplified from the standard's own full construction**: the
    standard's own template also shows a separate "LAA point symbol"
    (an oval-on-a-pin icon carrying Field A) connected to the area's own
    boundary by a straight leader line - a second, separately-anchored
    piece of geometry linked to the area, the same "doesn't fit this
    project's one-feature-one-symbol model" reasoning already applied to
    Occupied Assembly Area's own Offset Unit variants. Only the hatched
    boundary itself is built here; the leader line and separate point
    icon are dropped.
    """

    symbol = _status_driven_area_outline_symbol()

    hatch_layer = QgsLinePatternFillSymbolLayer()

    hatch_layer.setLineAngle(
        45
    )

    hatch_layer.setDistance(
        2.5
    )

    hatch_layer.setLineWidth(
        0.2
    )

    hatch_layer.setColor(
        QColor(0, 0, 0)
    )

    _apply_affiliation_color(
        hatch_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    symbol.appendSymbolLayer(
        hatch_layer
    )

    return symbol


_AREA_SYMBOL_BUILDERS = {
    "area": _status_driven_area_outline_symbol,
    "assembly_area": _status_driven_area_outline_symbol,
    "joint_tactical_action_area": _status_driven_area_outline_symbol,
    "submarine_action_area": _status_driven_area_outline_symbol,
    "submarine_generated_action_area": _status_driven_area_outline_symbol,
    "drop_zone": _status_driven_area_outline_symbol,
    "extraction_zone": _status_driven_area_outline_symbol,
    "landing_zone": _status_driven_area_outline_symbol,
    "pickup_zone": _status_driven_area_outline_symbol,
    "fortified_area": _fortified_area_symbol,
    "limited_access_area": _limited_access_area_symbol,
}

# Table H-VII's own examples: "AA BLUE", "DZ HAWK", "EZ ROCK",
# "LZ SILVER", "PZ WOLF" - identical "prefix + optional name" pattern
# to c2_measures.py's own AO/NAI/TAI. "area" and "fortified_area" are
# deliberately excluded here - "area" gets no label at all (see module
# docstring for why Friendly/Enemy Area were folded together), and
# "fortified_area" falls through to a plain, unprefixed name (its own
# template shows a bare "T" box, no fixed abbreviation, matching
# c2_measures.py's own Airfield Zone precedent).
_AREA_LABEL_PREFIXES = {
    "assembly_area": "AA",
    "drop_zone": "DZ",
    "extraction_zone": "EZ",
    "landing_zone": "LZ",
    "pickup_zone": "PZ",
    "limited_access_area": "LAA",
}

# JTAA/SAA/SGSA (150501/150502/150503) share one "PREFIX-name" format
# (a hyphen, not a space, per the standard's own "JTAA-02" example) plus
# an optional second line for the DTG range (Fields W/W1) when BOTH
# dtg_start and dtg_end are populated - "051030-051600Z" in the
# standard's own example.
_ACTION_AREA_PREFIXES = {
    "joint_tactical_action_area": "JTAA",
    "submarine_action_area": "SAA",
    "submarine_generated_action_area": "SGSA",
}

_AREA_DESIGNATION_LABEL_EXPRESSION = (
    "CASE "
    + " ".join(
        f"WHEN \"measure_type\" = '{measure_type}' THEN "
        f"'{prefix}-' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION}"
        " || CASE WHEN \"dtg_start\" IS NOT NULL AND \"dtg_start\" != ''"
        " AND \"dtg_end\" IS NOT NULL AND \"dtg_end\" != ''"
        " THEN '\\n' || \"dtg_start\" || '-' || \"dtg_end\" || 'Z'"
        " ELSE '' END"
        for measure_type, prefix in _ACTION_AREA_PREFIXES.items()
    )
    + " "
    + " ".join(
        f"WHEN \"measure_type\" = '{measure_type}' THEN "
        f"'{prefix}' || CASE WHEN \"unique_designation\" IS NOT NULL"
        " AND \"unique_designation\" != '' THEN"
        f" ' ' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
        for measure_type, prefix in _AREA_LABEL_PREFIXES.items()
    )
    + " WHEN \"measure_type\" = 'area' THEN ''"
    + f" ELSE {_PLAIN_DESIGNATION_LABEL_EXPRESSION} END"
)


def create_maneuver_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Maneuver Control Measures (Table
    H-VII) - see this module's own docstring for the full measure-type
    list and what was scoped out. Digitized with QGIS's own native "Add
    Line Feature" tool.
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
        QgsDefaultValue("'phase_line'")
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

    # No general along-line label - every measure type here either
    # shows nothing (FLOT, Line of Contact) or its own fixed/data-
    # defined symbol-layer end-marker instead (Phase Line's "PL "+name,
    # FEBA's fixed "FEBA", Principal Direction of Fire's "A") - FEBA
    # does NOT also show an optional unique_designation, per the
    # maintainer's own correction ("there is no unique designation in
    # FEBA").

    return layer


def create_maneuver_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for area-type Maneuver Control
    Measures - same shape as create_maneuver_control_measures_lines_
    layer(). "dtg_start"/"dtg_end" (Fields W/W1) are on the schema for
    every measure type, like status/affiliation, but only wired into
    rendering for JTAA/SAA/SGSA so far - see _AREA_DESIGNATION_LABEL_
    EXPRESSION's own comment.
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
            QgsField("dtg_start", QMetaType.Type.QString),
            QgsField("dtg_end", QMetaType.Type.QString),
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
        QgsDefaultValue("'area'")
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

    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.OverPoint,
        _AREA_DESIGNATION_LABEL_EXPRESSION
    )

    return layer


def add_maneuver_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_maneuver_control_measures_lines_layer
    )


def add_maneuver_control_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_maneuver_control_measures_areas_layer
    )
