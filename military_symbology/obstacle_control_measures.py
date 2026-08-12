# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.21 (Table H-XIX, "Obstacle control measure
symbols") - Mini-Phase H15/H16, and the largest single table in this
appendix-by-appendix pass.

**This module currently holds the AUDIT only** (batch B0, 2026-08-12).
No layers or symbols are built yet; they arrive batch by batch (tasks
#40-#46), each one reading TABLE_H_XIX_INVENTORY below for its own
slice. The layers deliberately do NOT exist yet rather than shipping
empty ones into the plugin menu - the first of them lands with B1's
point vocabulary, which is the first batch with anything to place.

**Scope: printed pages 573-603** (internal PDF 589-619), 75 code rows.
The table's own header runs to 603 - a code-range guess stops short at
602 and loses Raft Site (290800), the last row.

**Two structural findings that shape every later batch:**

1. **The code prefix does NOT identify the table.** 28xxxx and 29xxxx
   codes are shared with Table H-XX (Field Fortification: Shelter
   280900-281200, Fort) and Table H-XXI (CBRN: events 281300-281808).
   Anything scoped by code prefix rather than by PAGE RANGE will
   silently drag two other tables in. TABLE_H_XIX_INVENTORY is scoped
   by page range for exactly this reason.

2. **The prefix does not reliably give geometry either.** The table's
   own parent rows suggest 28xxxx = Points and 29xxxx = Lines, and that
   mostly holds - but **Overhead Wire (282003) is a LINE** ("requires
   at least two anchor points... to define the line") despite its
   28xxxx code, and the 27xxxx family is a genuine mix of areas, lines
   and points. Every geometry below marked CONFIRMED was read off that
   entry's own template picture and draw rules; the few marked ASSUMED
   were classified by family and must be checked when their batch is
   built.

**Colour: obstacles are GREEN, not affiliation-coloured** - the project
maintainer's own note opening this mini-phase, and visible directly in
the table's own EXAMPLE column, which renders Obstacle Belt, Obstacle
Zone, Obstacle Free Zone, Obstacle Restricted Zone, Mined Area, Decoy
Mined Area and the enemy minefields all in green rather than in the
affiliation hue H.5.3 would give. This is a documented departure from
the affiliation colouring every other H.5.x group in this project uses,
so it gets its own helper (_apply_obstacle_color) rather than quietly
reusing _apply_affiliation_color. The maintainer has flagged that there
are exceptions and will name them per batch - so the helper takes the
green as a default that a caller can override, rather than hard-coding
it everywhere.

**Findings that contradicted the initial batch plan**, all from
reading template pictures rather than the PDF's text layer (which is
badly OCR-mangled throughout this table - "Obstacle Fl'ee Zone",
"Cnters and Blown Bridges", "Une Cluste1"):

- **The obstacle zones are not a plain outline.** Obstacle Belt/Zone/
  Free Zone/Restricted Zone all draw a SERRATED (sawtooth) boundary,
  and Obstacle Restricted Zone adds a hatched fill on top. They cannot
  reuse _status_driven_area_outline_symbol() unchanged.
- **Most of the minefield family are POINTS, not areas.** Completed/
  Planned/Known Enemy/Suspected/Dummy Minefield (270701-270705) each
  say "requires one anchor point... Size/Shape: Static" - a fixed-size
  box of mine glyphs. Only Dummy Minefield Dynamic (270706) and Dynamic
  Depiction (270707) are freeform areas.
- **Mined Area and its decoy variants label their own PERIMETER** with
  repeating "M" glyphs, so they need a marker line on the boundary, not
  a plain outline plus a centred label.
- **Abatis (280100) is a LINE, not a point** - caught by the
  maintainer's own audit and confirmed against its template ("requires
  at least two anchor points... to define the line", drawn as a toothed
  line). B0 had it as a point purely because it sits under the
  "Protection Points" heading - the exact trap finding 2 above warns
  about, walked into on the first pass. Moved to B4, where the toothed-
  line technique already belongs.
- **290400 is "Mine Cluster", not "Line Cluster"** - also the
  maintainer's catch. B0 read the PDF's own "Une Cluste1" as "Line";
  it is "Mine". A name taken from mangled OCR rather than a picture.

**Reconciled 2026-08-12 against the maintainer's own independent
audit.** Both passes arrived at the SAME 65 buildable entries from 75
code rows - the strongest evidence either is complete. That audit also
supplied per-entry COLOUR and Field T requirements, both now carried in
the inventory.

**Colour rules from that audit**, over and above the green default:

- **BLACK**: the three Obstacle Bypass variants, Bridge or Gap, UXO
  Area, Antitank Ditch Reinforced with Antitank Mines, Antitank Wall,
  and Lane.
- **Outline green with BLACK text** ("OT" in the audit's own
  shorthand): the four obstacle zones and Obstacle Line.
- Everything else defaults to green.
- **The user must be able to switch any obstacle to black.** That is a
  per-feature choice, so the layers need a colour field defaulting to
  each measure type's own value above - not a hard-coded symbol colour.
  Settle before B1 builds the first layer.

**OPEN QUESTIONS for the maintainer**, recorded rather than guessed:

1. ~~Mine Cluster (290400) and Trip Wire (290500)~~ **SETTLED
   2026-08-12: both are LINES.** The audit had listed them as
   "symbol/point", but their own templates require TWO and THREE anchor
   points respectively ("points 1 and 2 define the corners of the
   symbol"), and the maintainer confirmed lines. They are fixed glyphs
   whose size and orientation come from clicked points.

   **Trip Wire's construction is the awkward one** and is expected to
   need working out at build time rather than following B4's shared
   marker-line helper: its three anchor points define a vertical
   straight portion (PT1-PT2), a horizontal extent (PT3), AND a 90
   degree arc at the bottom whose radius is the PT1-PT2-to-PT3
   distance. Flagged by the maintainer as "slightly complex, we will
   figure it out when it comes to that" - so B4 should budget for it
   separately rather than assuming it drops into the shared helper.
2. **Four code typos in the audit**, read as intended rather than
   literally: Block "2700501" -> 270501; Antitank Mine "280202" ->
   280300 (280202 does not exist); UXO Area "2701000" -> 271000;
   Suspected/Templated Enemy Minefield "270702" -> 270704 (270702 is
   Planned Minefield, listed separately in the same audit).
3. **"OT"** is read as "outline green, text black", from the audit's
   own "outline green, text black (OT - for this)".

**The minefield family is specified beyond the standard.** The audit
calls for each minefield to offer a MINE TYPE choice (antipersonnel /
antitank / unspecified / combination, placed alternately when
combined), and for Completed Minefield to accept either a single symbol
or a digitized line closed into an irregular rectangle and filled with
mine glyphs. Planned Minefield folds into Completed as a dashed
variant; Known Enemy adds masked "ENY" at the edges; Suspected keeps
its own entry with a dashed perimeter; Dummy Minefield Dynamic and
Dynamic Depiction merge into one area whose mines scatter randomly.
None of that is in the standard - it is a deliberate extension, and B3
owns it.

Military Cartography Tools
"""

from qgis.core import (
    QgsCentroidFillSymbolLayer,
    QgsDefaultValue,
    QgsEllipseSymbolLayer,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFillSymbol,
    QgsFontMarkerSymbolLayer,
    QgsGeometryGeneratorSymbolLayer,
    QgsLinePatternFillSymbolLayer,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsRandomMarkerFillSymbolLayer,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbol,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, QPointF, Qt
from qgis.PyQt.QtGui import QColor

from qgis.core import Qgis

from ._control_measure_shared import (
    POINT_AFFILIATION_LABELS,
    STATUS_LABELS,
    _STATUS_LINE_STYLE_EXPRESSION,
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_status_field,
    _value_map,
    add_layer_if_absent,
)

from qgis.core import QgsPalLayerSettings, QgsVectorLayerSimpleLabeling


# Table H-XIX draws in green rather than in the affiliation hue - see
# module docstring. Kept as a plain expression (not a data-defined
# affiliation CASE) because the colour genuinely does not vary by
# affiliation here.
OBSTACLE_GREEN_EXPRESSION = "color_rgb(0, 155, 0)"


def _apply_obstacle_color(symbol_layer, properties,
                          color_expression=OBSTACLE_GREEN_EXPRESSION):

    """
    The obstacle-table counterpart to _control_measure_shared.py's own
    _apply_affiliation_color(): sets the given colour properties from
    an expression, defaulting to this table's own green.

    `color_expression` is a parameter rather than a constant because
    the maintainer has flagged that a few entries in this table are
    exceptions to the green rule and will name them as each batch comes
    up - those callers pass _AFFILIATION_COLOR_EXPRESSION (or whatever
    the exception turns out to be) instead of taking the default.
    """

    color_property = QgsProperty.fromExpression(color_expression)

    for property_key in properties:

        symbol_layer.setDataDefinedProperty(
            property_key,
            color_property
        )


# Geometry classes.
AREA = "area"
LINE = "line"
POINT = "point"
PARENT = "parent"          # a heading row; template column reads "N/A"

# Colour. The table-wide default is green (see module docstring).
# OUTLINE_GREEN_TEXT_BLACK is the maintainer's own "OT" shorthand from
# the 2026-08-12 audit: the drawn outline green, the label black. Every
# entry the audit left unstated falls back to GREEN.
GREEN = "green"
BLACK = "black"
OUTLINE_GREEN_TEXT_BLACK = "outline-green-text-black"

# Whether the entry's own template shows a Field T box.
FIELD_T = True
NO_FIELD_T = False

# Which batch (task #40-#46) owns each entry - see docs/roadmap.md.
B1_POINTS = "B1"
B2_ZONES = "B2"
B3_MINEFIELDS = "B3"
B4_WIRE = "B4"
B5_EFFECTS = "B5"
B6_ROADBLOCKS = "B6"
B7_CROSSINGS = "B7"

# CONFIRMED = geometry read off that entry's own template picture and
# draw rules. ASSUMED = classified from its family's parent row only,
# and to be verified when its batch is built.
CONFIRMED = True
ASSUMED = False


def _e(name, geometry, batch, verified=ASSUMED,
       colour=GREEN, field_t=NO_FIELD_T):

    return {
        "name": name,
        "geometry": geometry,
        "batch": batch,
        "verified": verified,
        "colour": colour,
        "field_t": field_t,
    }


# The full Table H-XIX inventory, reconciled 2026-08-12 against the
# project maintainer's own independent audit. Where the two disagreed,
# the entry was re-read from its own template picture and the outcome
# is recorded in the comment beside it.
#
# Both audits independently arrived at the SAME 65 buildable entries out
# of 75 code rows, which is the strongest evidence either is complete.
TABLE_H_XIX_INVENTORY = {
    # -- Obstacle zones: serrated boundary, Field T, outline green /
    #    text black. Restricted Zone additionally masks its label.
    "270100": _e("Obstacle Belt", AREA, B2_ZONES, CONFIRMED,
                 OUTLINE_GREEN_TEXT_BLACK, FIELD_T),
    "270200": _e("Obstacle Zone", AREA, B2_ZONES, CONFIRMED,
                 OUTLINE_GREEN_TEXT_BLACK, FIELD_T),
    "270300": _e("Obstacle Free Zone", AREA, B2_ZONES, CONFIRMED,
                 OUTLINE_GREEN_TEXT_BLACK, FIELD_T),
    "270400": _e("Obstacle Restricted Zone", AREA, B2_ZONES, CONFIRMED,
                 OUTLINE_GREEN_TEXT_BLACK, FIELD_T),
    # -- Obstacle effects: symbol only, size set by the user, green.
    "270500": _e("Obstacle Effects", PARENT, B5_EFFECTS, CONFIRMED),
    "270501": _e("Block", LINE, B5_EFFECTS, CONFIRMED, GREEN),
    "270502": _e("Disrupt", LINE, B5_EFFECTS, CONFIRMED, GREEN),
    "270503": _e("Fix", LINE, B5_EFFECTS, ASSUMED, GREEN),
    "270504": _e("Turn", LINE, B5_EFFECTS, ASSUMED, GREEN),
    # -- Obstacle bypass: symbol only, size set by the user, BLACK.
    "270600": _e("Obstacle Bypass", PARENT, B6_ROADBLOCKS),
    "270601": _e("Obstacle Bypass Easy", LINE, B6_ROADBLOCKS, CONFIRMED, BLACK),
    "270602": _e("Obstacle Bypass Difficult", LINE, B6_ROADBLOCKS,
                 CONFIRMED, BLACK),
    "270603": _e("Obstacle Bypass Impossible", LINE, B6_ROADBLOCKS,
                 CONFIRMED, BLACK),
    # -- Minefields. See the module docstring's own minefield note for
    #    the mine-type selection the maintainer specified; the geometry
    #    here is what the STANDARD draws, which the build deliberately
    #    extends.
    "270700": _e("Minefield", PARENT, B3_MINEFIELDS),
    "270701": _e("Completed Minefield", POINT, B3_MINEFIELDS, CONFIRMED, GREEN),
    "270702": _e("Planned Minefield", POINT, B3_MINEFIELDS, CONFIRMED, GREEN),
    "270703": _e("Known Enemy Minefield", POINT, B3_MINEFIELDS,
                 CONFIRMED, GREEN),
    "270704": _e("Suspected or Templated Enemy Minefield", POINT,
                 B3_MINEFIELDS, CONFIRMED, GREEN),
    "270705": _e("Dummy Minefield", POINT, B3_MINEFIELDS, CONFIRMED, GREEN),
    "270706": _e("Dummy Minefield, Dynamic", AREA, B3_MINEFIELDS,
                 CONFIRMED, GREEN),
    "270707": _e("Dynamic Depiction", AREA, B3_MINEFIELDS, CONFIRMED, GREEN),
    # -- Mined areas: "M" glyphs repeat around the perimeter.
    "270800": _e("Mined Area", AREA, B2_ZONES, CONFIRMED, GREEN),
    "270900": _e("Decoy Mined Area", AREA, B2_ZONES, CONFIRMED, GREEN),
    "270901": _e("Decoy Mined Area, Fenced", AREA, B2_ZONES, CONFIRMED, GREEN),
    "271000": _e("Unexploded Explosive Ordnance (UXO) Area", AREA,
                 B2_ZONES, CONFIRMED, BLACK),
    # -- Gaps, roadblocks, craters --
    "271100": _e("Bridge or Gap", LINE, B6_ROADBLOCKS, CONFIRMED,
                 BLACK, FIELD_T),
    "271200": _e("Roadblocks, Craters and Blown Bridges", PARENT,
                 B6_ROADBLOCKS, CONFIRMED),
    "271201": _e("Planned Roadblock", LINE, B6_ROADBLOCKS, CONFIRMED, GREEN),
    "271202": _e("Roadblock, Explosives State of Readiness 1 (Safe)", LINE,
                 B6_ROADBLOCKS, CONFIRMED, GREEN),
    "271203": _e("Roadblock, Explosives State of Readiness 2 (Passable)",
                 LINE, B6_ROADBLOCKS, ASSUMED, GREEN),
    "271204": _e("Roadblock Complete (Executed)", LINE, B6_ROADBLOCKS,
                 ASSUMED, GREEN),
    # -- Water crossing sites. The maintainer's audit notes Bridge is
    #    the same construction as Assault Crossing and could share one
    #    builder - a scope call for B7, not folded here, since they
    #    remain two distinct SIDCs.
    "271300": _e("Assault Crossing", LINE, B7_CROSSINGS, CONFIRMED),
    "271400": _e("Bridge", LINE, B7_CROSSINGS, CONFIRMED),
    "271500": _e("Ford Easy", LINE, B7_CROSSINGS, CONFIRMED),
    "271600": _e("Ford Difficult", LINE, B7_CROSSINGS, CONFIRMED),
    # -- Protection points --
    "280000": _e("Protection Points", PARENT, B1_POINTS, CONFIRMED),
    # Abatis is a LINE, not a point - the maintainer's audit caught this
    # and the template confirms it ("requires at least two anchor
    # points... to define the line", drawn as a toothed line). B0 had it
    # as a point purely because it sits under the "Protection Points"
    # heading, which is the exact trap the module docstring warns about.
    "280100": _e("Abatis", LINE, B4_WIRE, CONFIRMED, GREEN),
    "280200": _e("Antipersonnel Mine", POINT, B1_POINTS, CONFIRMED),
    "280201": _e("Antipersonnel Mine with Directional Effects", POINT,
                 B1_POINTS),
    "280300": _e("Antitank Mine", POINT, B1_POINTS),
    "280400": _e("Antitank Mine with Anti-handling Device", POINT, B1_POINTS),
    "280500": _e("Wide Area Antitank Mine", POINT, B1_POINTS),
    "280600": _e("Unspecified Mine", POINT, B1_POINTS),
    "280700": _e("Booby Trap", POINT, B1_POINTS),
    "280800": _e("Engineer Regulating Point", POINT, B1_POINTS,
                 ASSUMED, GREEN, FIELD_T),
    "281900": _e("Tetrahedrons, Dragons Teeth and Other Similar Obstacles",
                 PARENT, B1_POINTS, CONFIRMED),
    "281901": _e("Fixed and Prefabricated", POINT, B1_POINTS),
    "281902": _e("Movable", POINT, B1_POINTS),
    "281903": _e("Movable and Prefabricated", POINT, B1_POINTS),
    "282000": _e("Vertical Obstructions", PARENT, B1_POINTS, CONFIRMED),
    "282001": _e("Tower, Low", POINT, B1_POINTS, ASSUMED, GREEN, FIELD_T),
    "282002": _e("Tower, High", POINT, B1_POINTS, ASSUMED, GREEN, FIELD_T),
    # Symbol + line together, kept on the Lines layer overall.
    "282003": _e("Overhead Wire", LINE, B7_CROSSINGS, CONFIRMED),
    # -- Protection lines --
    "290000": _e("Protection Lines", PARENT, B4_WIRE, CONFIRMED),
    "290100": _e("Obstacle Line", LINE, B4_WIRE, ASSUMED,
                 OUTLINE_GREEN_TEXT_BLACK, FIELD_T),
    "290200": _e("Antitank Obstacles", PARENT, B4_WIRE),
    "290201": _e("Antitank Ditch - Under Construction", LINE, B4_WIRE,
                 ASSUMED, GREEN),
    "290202": _e("Antitank Ditch - Completed", LINE, B4_WIRE, ASSUMED, GREEN),
    "290203": _e("Antitank Ditch Reinforced with Antitank Mines", LINE,
                 B4_WIRE, ASSUMED, BLACK),
    "290204": _e("Antitank Wall", LINE, B4_WIRE, ASSUMED, BLACK),
    "290300": _e("Wire Obstacles", PARENT, B4_WIRE),
    "290301": _e("Unspecified Wire Obstacle", LINE, B4_WIRE, ASSUMED, GREEN),
    "290302": _e("Single Fence", LINE, B4_WIRE, ASSUMED, GREEN),
    "290303": _e("Double Fence", LINE, B4_WIRE, ASSUMED, GREEN),
    "290304": _e("Double Apron Fence", LINE, B4_WIRE, ASSUMED, GREEN),
    "290305": _e("Low Wire Fence", LINE, B4_WIRE, ASSUMED, GREEN),
    "290306": _e("High Wire Fence", LINE, B4_WIRE, ASSUMED, GREEN),
    "290307": _e("Single Concertina", LINE, B4_WIRE, ASSUMED, GREEN),
    "290308": _e("Double Strand Concertina", LINE, B4_WIRE, ASSUMED, GREEN),
    "290309": _e("Triple Strand Concertina", LINE, B4_WIRE, ASSUMED, GREEN),
    # "Mine Cluster", not "Line Cluster" - the maintainer's audit caught
    # the name; B0 had misread the PDF's "Une Cluste1·" as Line. Its own
    # template needs TWO anchor points ("points 1 and 2 define the
    # corners of the symbol"), so it is digitized as a line even though
    # it draws as one fixed glyph - see OPEN QUESTIONS in the docstring.
    "290400": _e("Mine Cluster", LINE, B4_WIRE, CONFIRMED, GREEN),
    # Three anchor points per its own template, so likewise a line -
    # confirmed by the maintainer. Its construction is the awkward one
    # in B4: PT1-PT2 give a vertical straight portion, PT3 the
    # horizontal extent, plus a 90 degree arc at the bottom whose radius
    # is the distance from the PT1-PT2 line to PT3. Budget for it
    # separately from the shared marker-line helper.
    "290500": _e("Trip Wire", LINE, B4_WIRE, CONFIRMED, GREEN),
    "290600": _e("Lane", LINE, B7_CROSSINGS, ASSUMED, BLACK),
    "290700": _e("Ferry", LINE, B7_CROSSINGS),
    "290800": _e("Raft Site", LINE, B7_CROSSINGS, CONFIRMED),
}


def inventory_for_batch(batch):

    """
    The buildable entries a given batch owns - parent heading rows
    excluded, since they have no template to draw.
    """

    return {
        code: entry
        for code, entry in TABLE_H_XIX_INVENTORY.items()
        if entry["batch"] == batch and entry["geometry"] != PARENT
    }


def buildable_inventory():

    return {
        code: entry
        for code, entry in TABLE_H_XIX_INVENTORY.items()
        if entry["geometry"] != PARENT
    }


# --------------------------------------------------------------------
# Points (batch B1) - Table H-XIX's own protection points, rendered
# through milsymbol like every other Points layer in this pass.
# --------------------------------------------------------------------

POINTS_LAYER_NAME = "Obstacle Control Measures (Points)"

# The 13 point entries B1 owns. Abatis (280100) and Overhead Wire
# (282003) are NOT here despite their 28xxxx codes - both are lines
# (see the module docstring) and belong to B4 and B7. Abatis stays on
# the shared control_measure_points.py layer meanwhile, so it does not
# vanish from every dropdown between batches; B4 removes it there when
# it builds the line version.
POINT_ENTITY_LABELS = {
    "antipersonnel_mine": "Antipersonnel Mine",
    "antipersonnel_mine_directional": "Antipersonnel Mine with Directional Effects",
    "antitank_mine": "Antitank Mine",
    "antitank_mine_anti_handling": "Antitank Mine with Anti-handling Device",
    "wide_area_antitank_mine": "Wide Area Antitank Mine",
    "unspecified_mine": "Unspecified Mine",
    "booby_trap": "Booby Trap",
    "engineer_regulating_point": "Engineer Regulating Point",
    "obstacle_fixed_prefabricated": "Fixed and Prefabricated Obstacle",
    "obstacle_movable": "Movable Obstacle",
    "obstacle_movable_prefabricated": "Movable and Prefabricated Obstacle",
    "tower_low": "Tower, Low",
    "tower_high": "Tower, High",
}

# Per the maintainer: obstacles are green by default, but "user should
# have the ability to change colour to black if he wants to". So colour
# is a per-FEATURE field, not a per-measure-type constant - the default
# comes from the inventory, the user can override it on any feature.
COLOUR_LABELS = {
    GREEN: "Green (default)",
    BLACK: "Black",
}

_OBSTACLE_GREEN_RGB = "rgb(0,155,0)"
_OBSTACLE_BLACK_RGB = "rgb(0,0,0)"

# milsymbol owns a point icon's own colour and applies H.5.3's
# affiliation rule to it, so the obstacle points cannot take the
# data-defined colour the hand-built lines and areas use. Its own
# `monoColor` option recolours the whole icon instead - confirmed by
# probe to change stroke AND fill, needing no post-processing - which
# lets the points follow the same per-feature choice as everything else
# in this table rather than being the one exception.
# The same green/black choice as a real colour, for the label engine.
_POINT_LABEL_COLOR_EXPRESSION = (
    f"CASE WHEN \"colour\" = '{BLACK}' THEN color_rgb(0, 0, 0)"
    " ELSE color_rgb(0, 155, 0) END"
)

_POINT_MONO_COLOR_EXPRESSION = (
    f"CASE WHEN \"colour\" = '{BLACK}' THEN '{_OBSTACLE_BLACK_RGB}'"
    f" ELSE '{_OBSTACLE_GREEN_RGB}' END"
)

_POINTS_SIDC_EXPRESSION = (
    "mct_sidc_svg(mct_build_sidc("
    "\"affiliation\",\"entity\",'control_measure','unspecified',"
    "\"status\",false),"
    "upper(coalesce(\"unique_designation\",'')),"
    "'uniqueDesignation',"
    + _POINT_MONO_COLOR_EXPRESSION +
    ")"
)

_POINTS_DEFAULT_MARKER_SIZE_MM = 8.0

# NOT _control_measure_shared.py's own AFFILIATION_LABELS, and NOT its
# _configure_affiliation_field() - both of which this layer originally
# reused, which is the whole of the "every obstacle point renders as
# unknown" bug (2026-08-12, caught by the maintainer's own live smoke
# test).
#
# That shared pair is built for the hand-drawn LINES and AREAS layers,
# where `affiliation` only ever picks a Qt colour. For them
# "unspecified" is a genuine fifth value meaning "draw it black", and
# DEFAULT_AFFILIATION is exactly that. But a POINTS layer feeds
# `affiliation` into build_sidc(), and SIDC digit 4 has only the four
# real standard identities - "unspecified" is not one of them. So every
# point digitized without touching the dropdown got the shared default,
# build_sidc() raised KeyError, mct_build_sidc() returned the error
# MESSAGE as if it were a SIDC, and milsymbol drew its own unknown-icon
# fallback (an inverted "?") for all 13 entities alike. The green was
# real - monoColor is applied regardless of whether the icon resolved -
# which is what made the failure look like a colouring quirk rather
# than a broken SIDC.
#
# Same four-value dict and same 'friend' default as every other Points
# layer in this pass (c2_measures, defensive_control_measures,
# offensive_control_measures).
# The four real SIDC standard identities - see
# POINT_AFFILIATION_LABELS in _control_measure_shared.py for why a
# Points layer must not use the lines/areas AFFILIATION_LABELS.
_POINT_AFFILIATION_LABELS = POINT_AFFILIATION_LABELS

# Affiliation has no VISIBLE effect on this particular layer - monoColor
# repaints the whole icon green or black per the feature's own `colour`
# field - but it still has to be a valid SIDC value, because it decides
# whether there is an icon to repaint at all.

_POINT_STATUS_LABELS = dict(STATUS_LABELS)


def _configure_points_attribute_form(layer):

    fields = layer.fields()

    affiliation_idx = fields.indexOf("affiliation")
    entity_idx = fields.indexOf("entity")
    status_idx = fields.indexOf("status")
    colour_idx = fields.indexOf("colour")

    layer.setEditorWidgetSetup(
        entity_idx,
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(POINT_ENTITY_LABELS)})
    )

    layer.setEditorWidgetSetup(
        colour_idx,
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(COLOUR_LABELS)})
    )

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_POINT_AFFILIATION_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        status_idx,
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(_POINT_STATUS_LABELS)})
    )

    layer.setDefaultValueDefinition(affiliation_idx, QgsDefaultValue("'friend'"))
    layer.setDefaultValueDefinition(status_idx, QgsDefaultValue("'present'"))

    layer.setDefaultValueDefinition(
        entity_idx, QgsDefaultValue("'antipersonnel_mine'")
    )

    # Every B1 entry is green in the inventory, so a plain default is
    # right here. A batch with mixed defaults should drive this from
    # TABLE_H_XIX_INVENTORY's own "colour" instead.
    layer.setDefaultValueDefinition(colour_idx, QgsDefaultValue(f"'{GREEN}'"))


def _build_points_renderer():

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(_POINTS_DEFAULT_MARKER_SIZE_MM)

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(_POINTS_SIDC_EXPRESSION)
    )

    symbol.changeSymbolLayer(0, svg_layer)

    return QgsSingleSymbolRenderer(symbol)


# Tower, Low (282001) and Tower, High (282002) both REQUIRE a unique
# designation per the maintainer's own audit - and milsymbol has no
# text slot for either icon at all. Probed all six of its text options
# against both codes: none is accepted, and their rendered SVG contains
# no <text> element to hang one on. So unlike every other Points layer
# in this pass, the designation cannot ride inside the icon here and
# needs a real PAL label beside it.
#
# Engineer Regulating Point (280800) also requires one but DOES accept
# `uniqueDesignation`, so it keeps the normal in-icon route and is
# deliberately excluded from this label - otherwise it would show its
# designation twice.
_NO_TEXT_SLOT_ENTITIES = ("tower_low", "tower_high")

_TOWER_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"entity\" IN ("
    + ", ".join(f"'{e}'" for e in _NO_TEXT_SLOT_ENTITIES)
    + ") THEN upper(coalesce(\"unique_designation\",'')) ELSE '' END"
)


def _configure_points_labeling(layer):

    """
    Draws the unique designation beside the two Tower icons, which
    milsymbol gives no text slot for - see
    _TOWER_DESIGNATION_LABEL_EXPRESSION. Every other entity here returns
    an empty string and so is not labelled.
    """

    settings = _build_pal_layer_settings(
        layer,
        Qgis.LabelPlacement.OverPoint,
        _TOWER_DESIGNATION_LABEL_EXPRESSION,
        quadrant=Qgis.LabelQuadrantPosition.Right
    )

    # _build_pal_layer_settings() colours every label it builds by
    # AFFILIATION - made unconditional back in H-XII, when the
    # maintainer's instruction was "do it for all". Obstacles are the
    # first group where that is wrong: this label has to follow the
    # feature's own green/black choice like the icon beside it, not turn
    # blue because the feature is friendly. Overridden after the fact
    # rather than by adding another flag to the shared helper, so no
    # existing caller changes.
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Color,
        QgsProperty.fromExpression(_POINT_LABEL_COLOR_EXPRESSION)
    )

    # Push the text clear of the icon. The Right quadrant alone anchors
    # it at the feature's own point, which put it straight over an 8mm
    # marker (caught by render). NOTE this needs xOffset, not dist -
    # `dist` is the radius for AroundPoint placement and is ignored by
    # OverPoint, which is why setting it moved nothing.
    settings.xOffset = _POINTS_DEFAULT_MARKER_SIZE_MM * 0.62
    settings.offsetUnits = Qgis.RenderUnit.Millimeters

    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))

    layer.setLabelsEnabled(True)


def create_obstacle_control_measures_points_layer(name=POINTS_LAYER_NAME):

    """
    A fresh, empty point layer for Table H-XIX's own protection points
    (batch B1) - see POINT_ENTITY_LABELS for the 13 entries and for the
    two 28xxxx codes that are lines and live elsewhere.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(f"Point?crs={crs.authid()}", name, "memory")

    layer.dataProvider().addAttributes(
        [
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("entity", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("colour", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
        ]
    )

    layer.updateFields()

    _configure_points_attribute_form(layer)

    layer.setRenderer(_build_points_renderer())

    _configure_points_labeling(layer)

    return layer


def add_obstacle_control_measures_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_obstacle_control_measures_points_layer
    )


# ============================================================
# Batch B2 - obstacle zones and the mined-area family (Areas)
# ============================================================

AREAS_LAYER_NAME = "Obstacle Control Measures (Areas)"

# measure_type -> the standard's own code, kept HERE rather than in
# sidc.py's own ENTITIES.
#
# sidc.py's ENTITIES["control_measure"] is the milsymbol-rendered POINT
# vocabulary only - every hand-drawn line/area measure type in this
# appendix (Fire Support's own "ffa"/"nfa", C2's Area of Operations,
# and so on) carries its code in module-level data like this instead.
# B2's first pass put these eight in ENTITIES and a standing test
# caught it immediately: that test asserts every entity in ENTITIES is
# offered by SOME point dropdown, and an area type never can be.
AREA_MEASURE_TYPE_CODES = {
    "obstacle_belt": "270100",
    "obstacle_zone": "270200",
    "obstacle_free_zone": "270300",
    "obstacle_restricted_zone": "270400",
    "mined_area": "270800",
    "decoy_mined_area": "270900",
    "decoy_mined_area_fenced": "270901",
    "uxo_area": "271000",
    "minefield_dynamic": "270707",
    "minefield_dynamic_dummy": "270706",
}

# The 8 buildable area rows on printed pages 573-574 and 592-593.
# 270500 (Obstacle Effects) and 270700 (Minefields) are PARENT rows
# whose own template cell reads "N/A" - they are headings, not
# symbols, and are excluded here exactly as the inventory has them.
AREA_MEASURE_TYPE_LABELS = {
    "obstacle_belt": "Obstacle Belt",
    "obstacle_zone": "Obstacle Zone",
    "obstacle_free_zone": "Obstacle Free Zone",
    "obstacle_restricted_zone": "Obstacle Restricted Zone",
    "mined_area": "Mined Area",
    "decoy_mined_area": "Decoy Mined Area",
    "decoy_mined_area_fenced": "Decoy Mined Area, Fenced",
    "uxo_area": "Unexploded Explosive Ordnance (UXO) Area",
    "minefield_dynamic": "Minefield - Dynamic Depiction",
    "minefield_dynamic_dummy": "Minefield - Dummy, Dynamic",
}

# The four serrated zones, kept as a named group because three separate
# things key off exactly this set: the serrated outline, Field T being
# required, and the audit's own "OT" (outline green, TEXT BLACK) rule.
_SERRATED_ZONE_TYPES = (
    "obstacle_belt",
    "obstacle_zone",
    "obstacle_free_zone",
    "obstacle_restricted_zone",
)

# The mined-area family: a plain boundary that repeats "M" around its
# own perimeter, rather than a serrated one.
_MINED_AREA_TYPES = (
    "mined_area",
    "decoy_mined_area",
    "decoy_mined_area_fenced",
)

# Teeth around the whole perimeter. Matches mct_crenellate_outline()'s
# own default and the template's own rough tooth density (the Obstacle
# Belt picture counts ~14 around its boundary).
_ZONE_TOOTH_COUNT = 14

_AREA_OUTLINE_WIDTH_MM = 0.4


def _area_default_colour_expression():

    """
    B1 could default `colour` to a plain 'green' because every one of
    its entries was green. B2 is the first batch with MIXED defaults -
    UXO Area is black where the rest are green - so this is the CASE
    that B1's own comment said a later batch would need, and it is
    DERIVED from TABLE_H_XIX_INVENTORY rather than restated, so the
    audit stays the single source of truth for colour.

    OUTLINE_GREEN_TEXT_BLACK resolves to green here: it describes the
    OUTLINE, and the black half of it is the LABEL's business (see
    _AREA_LABEL_COLOR_EXPRESSION).
    """

    cases = []

    for measure_type, code in AREA_MEASURE_TYPE_CODES.items():

        entry = TABLE_H_XIX_INVENTORY[code]

        colour = BLACK if entry["colour"] == BLACK else GREEN

        cases.append(
            f"WHEN \"measure_type\" = '{measure_type}' THEN '{colour}'"
        )

    return "CASE " + " ".join(cases) + f" ELSE '{GREEN}' END"


_AREA_OUTLINE_COLOR_EXPRESSION = (
    f"CASE WHEN \"colour\" = '{BLACK}' THEN color_rgb(0, 0, 0)"
    " ELSE color_rgb(0, 155, 0) END"
)

# "OT" in the maintainer's own audit - outline green, text black. So
# the four zones' labels are black even though their outline is green.
# Every other area type's label simply follows its own colour field.
_AREA_LABEL_COLOR_EXPRESSION = (
    "CASE WHEN \"measure_type\" IN ("
    + ", ".join(f"'{t}'" for t in _SERRATED_ZONE_TYPES)
    + ") THEN color_rgb(0, 0, 0)"
    f" WHEN \"colour\" = '{BLACK}' THEN color_rgb(0, 0, 0)"
    " ELSE color_rgb(0, 155, 0) END"
)


def _area_outline_layer():

    """
    The status-driven solid/dashed outline every area here shares
    (H.5.1.1.3/Table H-I). NOT _control_measure_shared.py's own
    _status_driven_area_outline_symbol(): that one colours by
    AFFILIATION, and obstacles colour by the feature's own green/black
    choice instead (see this module's docstring).
    """

    outline_layer = QgsSimpleLineSymbolLayer()

    # The id every label rule masks against - see
    # _MASKED_AREA_SYMBOL_LAYER_ID.
    outline_layer.setId(_MASKED_AREA_SYMBOL_LAYER_ID)

    outline_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        outline_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    outline_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    return outline_layer


def _serrated_outline_layer(outward=True):

    """
    The four obstacle zones' own sawtooth boundary, as a real geometry
    construction (mct_serrate_outline) inside a geometry generator -
    not a QgsMarkerLineSymbolLayer of triangles.

    That choice is not a preference: maneuver_control_measures.py's own
    Fortified Area went through two marker-line attempts first and both
    produced a "beaded chain of floating shapes" rather than a
    continuous silhouette, which is why mct_crenellate_outline() exists.
    Serration has exactly the same requirement, so it reuses exactly
    that approach.
    """

    generator_layer = QgsGeometryGeneratorSymbolLayer.create({})

    generator_layer.setSymbolType(QgsSymbol.SymbolType.Line)

    generator_layer.setGeometryExpression(
        f"mct_serrate_outline($geometry, {_ZONE_TOOTH_COUNT},"
        f" {'true' if outward else 'false'})"
    )

    line_symbol = QgsLineSymbol()

    line_symbol.changeSymbolLayer(0, _area_outline_layer())

    generator_layer.setSubSymbol(line_symbol)

    return generator_layer


def _serrated_zone_symbol(hatched=False, outward=True):

    """
    The four obstacle zones. Two axes of difference, not one:

    - `outward` - Obstacle Belt and Obstacle Zone spike their teeth
      OUTWARD; Obstacle Free Zone and Obstacle Restricted Zone cut them
      INWARD, as notches bitten out of the shape. Caught by the project
      maintainer against the template pictures after the first build
      drew all four outward.
    - `hatched` - Obstacle Restricted Zone is the only one of the four
      the standard fills.
    """

    symbol = QgsFillSymbol.createSimple({"style": "no"})

    if hatched:

        hatch_layer = QgsLinePatternFillSymbolLayer()

        # Masked as well as the outline: Obstacle Restricted Zone is
        # the one filled area here, and its Field T sits right on the
        # hatch. Same reasoning as No Fire Area in
        # fire_support_coordination_measures.py.
        hatch_layer.setId(_MASKED_AREA_HATCH_LAYER_ID)

        hatch_layer.setLineAngle(45)
        hatch_layer.setDistance(2.5)

        # The colour MUST go on the sub-symbol's own line layer, not on
        # the pattern-fill layer itself, where QGIS silently ignores it.
        # This exact bug shipped twice before (Weapons Free Zone, then
        # No Fire Area) - see this project's own roadmap.
        hatch_line = hatch_layer.subSymbol().symbolLayer(0)

        hatch_line.setWidth(0.25)

        _apply_obstacle_color(
            hatch_line,
            [QgsSymbolLayer.Property.StrokeColor],
            _AREA_OUTLINE_COLOR_EXPRESSION
        )

        # The hatch has to fill the SERRATED shape, not the user's own
        # polygon, or the teeth sit outside the fill. make_polygon()
        # closes the serrated ring back into an area to hatch.
        hatch_generator = QgsGeometryGeneratorSymbolLayer.create({})

        hatch_generator.setSymbolType(QgsSymbol.SymbolType.Fill)

        hatch_generator.setGeometryExpression(
            "make_polygon(mct_serrate_outline($geometry,"
            f" {_ZONE_TOOTH_COUNT}, {'true' if outward else 'false'}))"
        )

        hatch_fill = QgsFillSymbol.createSimple({"style": "no"})
        hatch_fill.changeSymbolLayer(0, hatch_layer)

        hatch_generator.setSubSymbol(hatch_fill)

        symbol.changeSymbolLayer(0, hatch_generator)
        symbol.appendSymbolLayer(_serrated_outline_layer(outward))

    else:

        symbol.changeSymbolLayer(0, _serrated_outline_layer(outward))

    return symbol


def _plain_area_symbol(mine_glyphs=False):

    """
    Mined Area, both Decoy variants and UXO Area: a plain boundary. The
    "M" glyphs the mined-area family repeats around that boundary are
    LABELS, not symbol layers - see _configure_areas_labeling() for why.

    `mine_glyphs` adds Mined Area's own Field A (batch B3): the
    standard fills it with "the type of mine(s) contained in the
    minefield". Per the maintainer, an AREA shows just one glyph of
    each selected type - the alternating treatment is for line
    features - so a combined field draws two side by side and every
    other type draws one, centred.
    """

    symbol = QgsFillSymbol.createSimple({"style": "no"})

    symbol.changeSymbolLayer(0, _area_outline_layer())

    if mine_glyphs:

        glyph_symbol = QgsMarkerSymbol(_mine_glyph_marker_layers())

        centroid_layer = QgsCentroidFillSymbolLayer()

        # pointOnSurface, not the true centroid: a concave or
        # crescent-shaped minefield puts its centroid outside itself,
        # which would float the A field off the symbol entirely.
        centroid_layer.setPointOnSurface(True)

        centroid_layer.setSubSymbol(glyph_symbol)

        symbol.appendSymbolLayer(centroid_layer)

    return symbol


def _decoy_chevron_layer():

    """
    The dashed inverted-V both Decoy variants draw at their centre -
    the only thing distinguishing a decoy from a real Mined Area, whose
    boundary and "M" glyphs are otherwise identical. Real map-unit
    geometry (see mct_decoy_chevron) so it scales with the polygon, as
    the standard's own draw rules require of this block.
    """

    generator_layer = QgsGeometryGeneratorSymbolLayer.create({})

    generator_layer.setSymbolType(QgsSymbol.SymbolType.Line)

    generator_layer.setGeometryExpression("mct_decoy_chevron($geometry)")

    chevron_line = QgsSimpleLineSymbolLayer()

    chevron_line.setWidth(_AREA_OUTLINE_WIDTH_MM)

    # Dashed in the template regardless of status - this is part of the
    # decoy's own iconography, not the H.5.1.1.3 present/planned rule,
    # so it is set outright rather than driven by "status".
    chevron_line.setPenStyle(Qt.PenStyle.DashLine)

    _apply_obstacle_color(
        chevron_line,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_symbol = QgsLineSymbol()

    line_symbol.changeSymbolLayer(0, chevron_line)

    generator_layer.setSubSymbol(line_symbol)

    return generator_layer


def _fence_marker_layer():

    """
    The "X" marks repeating around Decoy Mined Area, Fenced - the fence
    itself. A QgsMarkerLineSymbolLayer is fine here, unlike for the "M"
    glyphs: the X's do NOT interrupt the boundary in the template (it
    is dashed and simply runs behind them), so nothing needs masking,
    and masking is the only reason the M's had to become PAL labels.
    """

    fence_marker = QgsFontMarkerSymbolLayer("Arial", "X", 2.6)

    _apply_obstacle_color(
        fence_marker,
        [QgsSymbolLayer.Property.FillColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    marker_line = QgsMarkerLineSymbolLayer()

    marker_line.setInterval(6.0)

    marker_line.setSubSymbol(QgsMarkerSymbol([fence_marker]))

    return marker_line


def _decoy_mined_area_symbol(fenced=False):

    """
    Decoy Mined Area (270900) and Decoy Mined Area, Fenced (270901).
    Both carry the chevron; the fenced variant additionally dashes its
    boundary and repeats "X" fence marks around it.
    """

    symbol = QgsFillSymbol.createSimple({"style": "no"})

    outline_layer = _area_outline_layer()

    if fenced:

        # The fenced variant's boundary is dashed in the template
        # whatever its status, so this overrides the status-driven
        # solid/dashed rule rather than sitting alongside it.
        outline_layer.setDataDefinedProperty(
            QgsSymbolLayer.Property.StrokeStyle,
            QgsProperty.fromExpression("'dash'")
        )

    symbol.changeSymbolLayer(0, outline_layer)

    if fenced:
        symbol.appendSymbolLayer(_fence_marker_layer())

    symbol.appendSymbolLayer(_decoy_chevron_layer())

    return symbol


_DYNAMIC_MINEFIELD_TYPES = ("minefield_dynamic", "minefield_dynamic_dummy")

# How many mine glyphs scatter across a dynamic minefield. Fixed count
# rather than density-based so the symbol reads the same at any zoom,
# and a fixed seed so it does not reshuffle on every repaint.
_DYNAMIC_MINE_COUNT = 7
_DYNAMIC_MINE_SEED = 20250812


def _dynamic_minefield_symbol(dummy=False):

    """
    Dynamic Depiction (270707) and Dummy Minefield, Dynamic (270706) -
    the two minefields drawn as freeform areas rather than a static
    box, so their mines scatter across the shape instead of sitting in
    a row.

    Kept as TWO measure types, deliberately departing from the
    maintainer's own audit, which asked for them to merge into one.
    Merging would conflate a DUMMY minefield with a real one: the
    dashed chevron is the only thing that says "this is a decoy", and
    that is a claim about the ground, not a styling detail. Raised for
    the maintainer to overrule if they still want the merge.
    """

    symbol = QgsFillSymbol.createSimple({"style": "no"})

    symbol.changeSymbolLayer(0, _area_outline_layer())

    scatter = QgsRandomMarkerFillSymbolLayer()

    scatter.setPointCount(_DYNAMIC_MINE_COUNT)
    scatter.setSeed(_DYNAMIC_MINE_SEED)
    scatter.setClipPoints(True)

    # One glyph slot only: a scattered field mixes the two types across
    # the area rather than pairing them, so slot 0's own alternation is
    # not what is wanted here - each scattered glyph is the field's
    # primary type.
    scatter.setSubSymbol(QgsMarkerSymbol(_mine_glyph_marker_layers(slots=1)))

    symbol.appendSymbolLayer(scatter)

    if dummy:

        chevron_generator = QgsGeometryGeneratorSymbolLayer.create({})

        chevron_generator.setSymbolType(QgsSymbol.SymbolType.Line)

        # ABOVE the shape, not inside it - the template puts Dummy
        # Minefield's chevron clear of the boundary, unlike Decoy Mined
        # Area, which centres it.
        chevron_generator.setGeometryExpression(
            "translate(mct_decoy_chevron($geometry), 0,"
            " (y_max($geometry) - y_min($geometry)) * 0.82)"
        )

        chevron_line = QgsSimpleLineSymbolLayer()

        chevron_line.setWidth(_AREA_OUTLINE_WIDTH_MM)
        chevron_line.setPenStyle(Qt.PenStyle.DashLine)

        _apply_obstacle_color(
            chevron_line,
            [QgsSymbolLayer.Property.StrokeColor],
            _AREA_OUTLINE_COLOR_EXPRESSION
        )

        chevron_symbol = QgsLineSymbol()
        chevron_symbol.changeSymbolLayer(0, chevron_line)

        chevron_generator.setSubSymbol(chevron_symbol)

        symbol.appendSymbolLayer(chevron_generator)

    return symbol


_AREA_SYMBOL_BUILDERS = {
    "obstacle_belt": _serrated_zone_symbol,
    "obstacle_zone": _serrated_zone_symbol,
    "obstacle_free_zone": lambda: _serrated_zone_symbol(outward=False),
    "obstacle_restricted_zone": lambda: _serrated_zone_symbol(
        hatched=True, outward=False
    ),
    "mined_area": lambda: _plain_area_symbol(mine_glyphs=True),
    "decoy_mined_area": _decoy_mined_area_symbol,
    "decoy_mined_area_fenced": lambda: _decoy_mined_area_symbol(fenced=True),
    "uxo_area": _plain_area_symbol,
    "minefield_dynamic": _dynamic_minefield_symbol,
    "minefield_dynamic_dummy": lambda: _dynamic_minefield_symbol(dummy=True),
}


# --- Labels -------------------------------------------------------

# Field T. The four zones require it (the maintainer's own audit); the
# mined-area family and UXO Area do not carry one at all.
_AREA_DESIGNATION_EXPRESSION = (
    "upper(coalesce(\"unique_designation\", ''))"
)

# Fields W/W1, same "dtg_start"/"dtg_end" names and same two-line split
# already used by c2_measures.py's own Boundary, maneuver_control_
# measures.py's own action areas and offensive_control_measures.py's
# own Axis of Advance - not a new naming scheme. Obstacle Free Zone and
# Obstacle Restricted Zone are the two that draw them (printed pages
# 573-574); Belt and Zone show Field T alone.
_AREA_DTG_TYPES = ("obstacle_free_zone", "obstacle_restricted_zone")

_AREA_DTG_EXPRESSION = (
    "CASE WHEN \"measure_type\" IN ("
    + ", ".join(f"'{t}'" for t in _AREA_DTG_TYPES)
    + ") AND \"dtg_start\" IS NOT NULL AND \"dtg_start\" != ''"
    " AND \"dtg_end\" IS NOT NULL AND \"dtg_end\" != ''"
    " THEN '\\n' || \"dtg_start\" || ' -\\n' || \"dtg_end\""
    " ELSE '' END"
)

# Obstacle Free Zone is the one zone whose template carries a literal
# word above Field T ("FREE"). A real PAL label CAN hold newlines (the
# no-multi-line limitation offensive_control_measures.py documents is
# specific to QgsFontMarkerSymbolLayer, which is not what this is), so
# the whole stack is one expression rather than stacked marker layers.
_ZONE_LABEL_EXPRESSION = (
    "trim("
    "CASE WHEN \"measure_type\" = 'obstacle_free_zone' THEN 'FREE\\n' ELSE '' END"
    f" || {_AREA_DESIGNATION_EXPRESSION}"
    f" || {_AREA_DTG_EXPRESSION}"
    ")"
)

# The mined-area family repeats "M" around its own perimeter. These are
# PAL labels, not a QgsMarkerLineSymbolLayer of "M" glyphs, for one
# reason: the template breaks the boundary line at every M, and QGIS's
# Selective Masking is the only tool in this codebase that cuts a hole
# in a symbol layer - and it works on PAL labels only. A font marker
# has no QgsTextMaskSettings at all (established in c2_measures.py's own
# Boundary work, which went through three wrong tools before landing on
# masking).
_MINED_AREA_PERIMETER_EXPRESSION = (
    "CASE WHEN \"measure_type\" IN ("
    + ", ".join(f"'{t}'" for t in _MINED_AREA_TYPES)
    + ") THEN 'M' ELSE '' END"
)

# FOUR fixed anchors rather than a repeating label along the perimeter.
# The first attempt used Qgis.LabelPlacement.Line with a repeat
# distance, and a render showed why that is wrong twice over: the
# labels ROTATE with the boundary (the template draws every M
# upright), and the count drifts with the polygon's size where the
# template shows exactly four, one per side.
#
# Each anchor is snapped onto the real boundary with closest_point(),
# not used as a raw bounding-box corner: for anything non-rectangular
# a bbox point sits off the shape, which would float the M away from
# the line it is supposed to interrupt.
_MINED_AREA_M_ANCHORS = (
    "closest_point(boundary($geometry),"
    " make_point((x_min($geometry) + x_max($geometry)) / 2, y_max($geometry)))",
    "closest_point(boundary($geometry),"
    " make_point((x_min($geometry) + x_max($geometry)) / 2, y_min($geometry)))",
    "closest_point(boundary($geometry),"
    " make_point(x_min($geometry), (y_min($geometry) + y_max($geometry)) / 2))",
    "closest_point(boundary($geometry),"
    " make_point(x_max($geometry), (y_min($geometry) + y_max($geometry)) / 2))",
)

# Mined Area's own Fields H and W, per the standard's own Note on
# printed page 592: H takes "S" (only scatterable mines) or "+S" (a
# mix), and W takes the self-destruct time for scatterable mines. Both
# are plain text there.
#
# The template's THIRD field, A, is deliberately NOT built here. A is
# "graphics ... filled with the type of mine(s)", and mine-type
# selection is exactly the extension the maintainer's audit assigns to
# batch B3 ("the minefield family is specified beyond the standard").
# Building a placeholder here would only be torn out by B3.
_MINED_AREA_FIELD_H_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'mined_area'"
    " THEN upper(coalesce(\"mine_indicator\", '')) ELSE '' END"
)

_MINED_AREA_FIELD_W_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'mined_area'"
    " THEN upper(coalesce(\"self_destruct_dtg\", '')) ELSE '' END"
)

# UXO Area draws "UXO" at each END of the shape, not at its centre -
# left and right, exactly as its template does (printed page 593). Same
# bounding-box anchor technique as the PAA perimeter labels in
# fire_support_coordination_measures.py.
_UXO_ANCHORS = (
    "make_point(x_min($geometry), (y_min($geometry) + y_max($geometry)) / 2)",
    "make_point(x_max($geometry), (y_min($geometry) + y_max($geometry)) / 2)",
)

_UXO_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'uxo_area' THEN 'UXO' ELSE '' END"
)

# Every label on this layer masks the same thing: the shared outline.
# One combined list on EVERY rule, because masking is configured per
# LAYER, not per rule - rules declaring different lists make QGIS log
# "Different sets of symbol layers are masked by different sources!"
# and keep one arbitrarily.
_MASKED_AREA_SYMBOL_LAYER_ID = "obstacle_area_outline"
_MASKED_AREA_HATCH_LAYER_ID = "obstacle_area_hatch"

_MASKED_AREA_LAYER_IDS = [
    _MASKED_AREA_SYMBOL_LAYER_ID,
    _MASKED_AREA_HATCH_LAYER_ID,
]


def _labelled_rule(layer, expression, filter_expression,
                   placement=Qgis.LabelPlacement.OverPoint,
                   y_offset_mm=None, **kwargs):

    """
    One rule of this layer's labelling tree, with the obstacle colour
    rule applied.

    NOTE the settings object is held in its own variable before its
    data-defined properties are touched. _build_pal_layer_settings()
    returns by value and chaining off it (settings.format().mask()...)
    lets the temporary's C++ object be collected mid-expression, which
    segfaults the interpreter - hit repeatedly on this project.
    """

    settings = _build_pal_layer_settings(
        layer,
        placement,
        expression,
        masked_symbol_layer_ids=_MASKED_AREA_LAYER_IDS,
        **kwargs
    )

    # _build_pal_layer_settings() colours every label by AFFILIATION.
    # Obstacles follow the feature's own green/black choice instead,
    # and the four zones' text is black regardless ("OT" in the audit).
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Color,
        QgsProperty.fromExpression(_AREA_LABEL_COLOR_EXPRESSION)
    )

    # Quadrant alone anchors the label AT the point, so Mined Area's
    # own Field H and Field W landed on top of each other and PAL
    # dropped one of them (caught by render - both expressions
    # evaluated fine). This needs yOffset, NOT `dist`: `dist` is the
    # radius for AroundPoint placement and is ignored by OverPoint.
    #
    # Sign convention confirmed BY RENDER, not assumed: a POSITIVE
    # yOffset moves the label DOWN here, so Field H (which the template
    # puts above the centre) takes a negative one.
    if y_offset_mm is not None:

        settings.yOffset = y_offset_mm
        settings.offsetUnits = Qgis.RenderUnit.Millimeters

    rule = QgsRuleBasedLabeling.Rule(settings)

    rule.setFilterExpression(filter_expression)

    return rule


def _configure_areas_labeling(layer):

    """
    Four different label PLACEMENTS on one layer, which is why this is
    a rule tree rather than one shared QgsPalLayerSettings:

    - the four zones label once, centred (Field T, plus "FREE" and the
      W/W1 window where the template shows them);
    - the mined-area family repeats a masked "M" around its perimeter;
    - Mined Area adds Field H above and Field W below that centre;
    - UXO Area labels "UXO" at its left and right extremes instead.

    Every filter is explicit and mutually exclusive - setIsElse(True)
    does NOT suppress a rule, because each rule gets its own
    sub-provider and an else-flagged one still labels the rows the
    other rules matched (double labels).
    """

    zone_filter = (
        "\"measure_type\" IN ("
        + ", ".join(f"'{t}'" for t in _SERRATED_ZONE_TYPES)
        + ")"
    )

    mined_filter = (
        "\"measure_type\" IN ("
        + ", ".join(f"'{t}'" for t in _MINED_AREA_TYPES)
        + ")"
    )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    root_rule.appendChild(
        _labelled_rule(layer, _ZONE_LABEL_EXPRESSION, zone_filter)
    )

    # "M" around the perimeter. Placement Line on a polygon layer
    # follows the ring; the repeat distance is what makes it repeat
    # rather than label once.
    for anchor in _MINED_AREA_M_ANCHORS:

        root_rule.appendChild(
            _labelled_rule(
                layer,
                _MINED_AREA_PERIMETER_EXPRESSION,
                mined_filter,
                label_geometry_expression=anchor,
                quadrant=Qgis.LabelQuadrantPosition.Over,
            )
        )

    root_rule.appendChild(
        _labelled_rule(
            layer,
            _MINED_AREA_FIELD_H_EXPRESSION,
            "\"measure_type\" = 'mined_area'",
            quadrant=Qgis.LabelQuadrantPosition.Above,
            y_offset_mm=-4.5,
        )
    )

    root_rule.appendChild(
        _labelled_rule(
            layer,
            _MINED_AREA_FIELD_W_EXPRESSION,
            "\"measure_type\" = 'mined_area'",
            quadrant=Qgis.LabelQuadrantPosition.Below,
            y_offset_mm=4.5,
        )
    )

    for anchor in _UXO_ANCHORS:

        root_rule.appendChild(
            _labelled_rule(
                layer,
                _UXO_LABEL_EXPRESSION,
                "\"measure_type\" = 'uxo_area'",
                label_geometry_expression=anchor,
                quadrant=Qgis.LabelQuadrantPosition.Over,
            )
        )

    layer.setLabeling(QgsRuleBasedLabeling(root_rule))

    layer.setLabelsEnabled(True)


def create_obstacle_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Table H-XIX's own 8 area measure
    types (batch B2) - see AREA_MEASURE_TYPE_LABELS.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(f"Polygon?crs={crs.authid()}", name, "memory")

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("colour", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
            QgsField("dtg_start", QMetaType.Type.QString),
            QgsField("dtg_end", QMetaType.Type.QString),
            QgsField("mine_type", QMetaType.Type.QString),
            QgsField("mine_indicator", QMetaType.Type.QString),
            QgsField("self_destruct_dtg", QMetaType.Type.QString),
            QgsField("area_km2", QMetaType.Type.Double),
            QgsField("perimeter_km", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    fields = layer.fields()

    layer.setEditorWidgetSetup(
        fields.indexOf("measure_type"),
        QgsEditorWidgetSetup(
            "ValueMap", {"map": _value_map(AREA_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        fields.indexOf("colour"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(COLOUR_LABELS)})
    )

    layer.setEditorWidgetSetup(
        fields.indexOf("mine_type"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(MINE_TYPE_LABELS)})
    )

    # Affiliation plays no part in an obstacle's own colour (see this
    # module's docstring), but it is still on the schema so an obstacle
    # can carry a standard identity like every other control measure.
    # This layer is hand-drawn, not milsymbol-rendered, so the
    # lines/areas vocabulary - the one WITH "Unspecified (black)" - is
    # the correct one here, unlike on the Points layer.
    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setDefaultValueDefinition(
        fields.indexOf("measure_type"), QgsDefaultValue("'obstacle_belt'")
    )

    layer.setDefaultValueDefinition(
        fields.indexOf("colour"),
        QgsDefaultValue(_area_default_colour_expression(), True)
    )

    layer.setDefaultValueDefinition(
        fields.indexOf("mine_type"),
        QgsDefaultValue(f"'{DEFAULT_MINE_TYPE}'")
    )

    layer.setDefaultValueDefinition(
        fields.indexOf("area_km2"),
        QgsDefaultValue("mct_area_km2($geometry)", True)
    )

    layer.setDefaultValueDefinition(
        fields.indexOf("perimeter_km"),
        QgsDefaultValue("mct_perimeter_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _AREA_SYMBOL_BUILDERS)
    )

    _configure_areas_labeling(layer)

    return layer


def add_obstacle_control_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_obstacle_control_measures_areas_layer
    )


# ============================================================
# Batch B3 - mine types, and the minefield family
# ============================================================

# The mine-type choice the maintainer's own audit adds on top of the
# standard. The standard itself says only that the A field is
# "graphics ... filled with the type of mine(s) contained in the
# minefield (see mine types listed in this appendix)" - it never
# enumerates a picker. This is that picker.
#
# Modelled as a FIELD rather than as extra measure types, deliberately.
# The alternative considered (and rejected with the maintainer) was one
# measure type per combination - "mined area - antipersonnel", "mined
# area - antitank", and so on. Three reasons it lost:
#
#  1. It does not remove the hard part. The combined variant still has
#     to alternate two glyphs along a line either way.
#  2. measure_type maps 1:1 onto the standard's own code and a test
#     pins that. Four Mined Area variants would all claim 270800.
#  3. Minefield STATE (completed/enemy/suspected/dummy) is a separate
#     axis, so splitting by type too gives ~15-20 dropdown entries for
#     one family - the "otherwise the list is too long" problem the
#     maintainer already raised on Table H-XIV.
MINE_TYPE_LABELS = {
    "antipersonnel": "Anti-personnel",
    "antitank": "Anti-tank",
    "unknown": "Unknown",
    "antipersonnel_antitank": "Anti-personnel and anti-tank",
}

DEFAULT_MINE_TYPE = "unknown"

# Each mine type's own glyph, reusing batch B1's OWN point entities
# rather than drawing anything new - and these are exactly the three
# icons the standard's own examples show inside the A field (the filled
# circle with horns, the plain filled circle, and the open circle).
_MINE_TYPE_ENTITIES = {
    "antipersonnel": "antipersonnel_mine",
    "antitank": "antitank_mine",
    "unknown": "unspecified_mine",
}

# A combined field shows one of each. The maintainer's rule for how
# many to draw differs by geometry: "in case of areas, just one symbol
# each of the selected mines is adequate, in case of line features -
# alternating mines is a must."
_MINE_TYPE_SEQUENCE = {
    "antipersonnel": ("antipersonnel",),
    "antitank": ("antitank",),
    "unknown": ("unknown",),
    "antipersonnel_antitank": ("antipersonnel", "antitank"),
}


def _mine_glyph_sidc_expression(slot):

    """
    The SIDC for the glyph in position `slot` (0-based) of the A field.

    Returns an empty string when this mine type has no glyph for that
    slot - a single-type field leaves slot 1 empty - which the caller
    turns into a zero-size marker rather than a broken symbol.
    """

    cases = []

    for mine_type, sequence in _MINE_TYPE_SEQUENCE.items():

        if slot >= len(sequence):
            continue

        entity = _MINE_TYPE_ENTITIES[sequence[slot]]

        cases.append(
            f"WHEN \"mine_type\" = '{mine_type}' THEN '{entity}'"
        )

    entity_expression = "CASE " + " ".join(cases) + " ELSE '' END"

    return (
        "CASE WHEN (" + entity_expression + ") = '' THEN ''"
        " ELSE mct_sidc_svg(mct_build_sidc("
        "\"affiliation\", " + entity_expression + ","
        " 'control_measure', 'unspecified', 'present', false),"
        " '', '', " + _POINT_MONO_COLOR_EXPRESSION + ") END"
    )


def _mine_glyph_present_expression(slot):

    """1 when this mine type fills glyph slot `slot`, else 0."""

    filled = [
        mine_type
        for mine_type, sequence in _MINE_TYPE_SEQUENCE.items()
        if slot < len(sequence)
    ]

    return (
        "CASE WHEN \"mine_type\" IN ("
        + ", ".join(f"'{t}'" for t in filled)
        + ") THEN 1 ELSE 0 END"
    )


_MINE_GLYPH_SIZE_MM = 5.0

# Half the gap between the two glyphs of a combined field. A
# single-glyph field centres instead, so the offset collapses to 0.
_MINE_GLYPH_SPREAD_MM = 3.2


def _mine_glyph_offset_expression(slot):

    """
    Slot 0 sits left of centre and slot 1 right of centre when BOTH are
    drawn; a single glyph centres. Data-defined rather than fixed,
    because the same symbol serves both cases.
    """

    combined = [
        mine_type
        for mine_type, sequence in _MINE_TYPE_SEQUENCE.items()
        if len(sequence) > 1
    ]

    sign = -1 if slot == 0 else 1

    return (
        "CASE WHEN \"mine_type\" IN ("
        + ", ".join(f"'{t}'" for t in combined)
        + f") THEN {sign * _MINE_GLYPH_SPREAD_MM} ELSE 0 END"
    )


def _mine_glyph_marker_layers(slots=2):

    """
    The A field: `slots` milsymbol glyphs, each driven by the feature's
    own mine_type.

    Every slot is always present as a symbol layer; an unused one is
    given size 0 rather than being omitted, because a symbol's layers
    are fixed at build time while mine_type varies per feature.
    """

    layers = []

    for slot in range(slots):

        marker = QgsSvgMarkerSymbolLayer("")

        marker.setSize(_MINE_GLYPH_SIZE_MM)

        marker.setDataDefinedProperty(
            QgsSymbolLayer.Property.Name,
            QgsProperty.fromExpression(_mine_glyph_sidc_expression(slot))
        )

        marker.setDataDefinedProperty(
            QgsSymbolLayer.Property.Size,
            QgsProperty.fromExpression(
                f"{_mine_glyph_present_expression(slot)}"
                f" * {_MINE_GLYPH_SIZE_MM}"
            )
        )

        marker.setDataDefinedProperty(
            QgsSymbolLayer.Property.Offset,
            QgsProperty.fromExpression(
                f"format('%1,0', {_mine_glyph_offset_expression(slot)})"
            )
        )

        layers.append(marker)

    return layers


MINEFIELDS_LAYER_NAME = "Obstacle Control Measures (Minefields)"

# Four measure types for the table's own five minefield point codes.
#
# Completed (270701) and Planned (270702) are ONE type here, split by
# the `status` field: their templates are identical apart from a solid
# versus dashed box, which is exactly what H.5.1.1.3's own present/
# planned rule already drives everywhere else in this appendix. The
# maintainer's audit asked for precisely this fold ("Planned Minefield
# folds into Completed as a dashed variant").
#
# Known Enemy (270703) and Suspected/Templated (270704) stay separate
# rather than folding the same way - also the audit's own call. They
# differ by more than line style in practice, and "suspected" is not
# the same claim as "planned".
MINEFIELD_MEASURE_TYPE_LABELS = {
    "minefield": "Minefield (Completed / Planned)",
    "minefield_known_enemy": "Minefield - Known Enemy",
    "minefield_suspected": "Minefield - Suspected or Templated Enemy",
    "minefield_dummy": "Minefield - Dummy",
}

MINEFIELD_MEASURE_TYPE_CODES = {
    "minefield": ("270701", "270702"),
    "minefield_known_enemy": ("270703",),
    "minefield_suspected": ("270704",),
    "minefield_dummy": ("270705",),
}

# The two enemy variants label "ENY" at each side of the box - Field N
# in the template, which the standard's own EXAMPLE column fills in as
# "ENY" (unlike the "N" boxes on Decoy Mined Area, Fenced, which its
# example leaves empty; those stay unbuilt for that reason).
_MINEFIELD_ENEMY_TYPES = ("minefield_known_enemy", "minefield_suspected")

# Always dashed regardless of status - "suspected" is the claim the
# dashes encode here, and Dummy/Known Enemy are drawn solid.
_MINEFIELD_ALWAYS_DASHED = ("minefield_suspected",)

_MINEFIELD_BOX_WIDTH_MM = 15.0
_MINEFIELD_BOX_HEIGHT_MM = 6.5

# Three glyphs in a row inside the box, as every one of the standard's
# own minefield examples draws it.
_MINEFIELD_GLYPH_SLOTS = 3
_MINEFIELD_GLYPH_PITCH_MM = 4.4


def _minefield_glyph_sidc_expression(slot):

    """
    The glyph in box position `slot`. A single-type field repeats the
    same glyph three times, matching the standard's own examples; a
    combined field ALTERNATES - the maintainer's rule that alternating
    "is a must" wherever more than one glyph is drawn.
    """

    alternating = "antipersonnel" if slot % 2 == 0 else "antitank"

    cases = [
        f"WHEN \"mine_type\" = 'antipersonnel_antitank'"
        f" THEN '{_MINE_TYPE_ENTITIES[alternating]}'"
    ]

    for mine_type, entity in _MINE_TYPE_ENTITIES.items():

        cases.append(f"WHEN \"mine_type\" = '{mine_type}' THEN '{entity}'")

    entity_expression = "CASE " + " ".join(cases) + " ELSE '' END"

    return (
        "CASE WHEN (" + entity_expression + ") = '' THEN ''"
        " ELSE mct_sidc_svg(mct_build_sidc("
        "\"affiliation\", " + entity_expression + ","
        " 'control_measure', 'unspecified', 'present', false),"
        " '', '', " + _POINT_MONO_COLOR_EXPRESSION + ") END"
    )


def _minefield_box_layer():

    """
    The fixed-size box every minefield point draws.

    QgsEllipseSymbolLayer, not QgsSimpleMarkerSymbolLayer: the box is
    WIDER than it is tall (measured off the template at roughly 2.3:1)
    and a simple marker only has one `size`. The ellipse layer takes an
    independent width and height in millimetres, which is also what
    "Size/Shape: Static" requires - a fixed screen size, not one
    derived from anchor points. Confirmed to behave identically on
    QGIS 3.44 and 4.2.
    """

    box_layer = QgsEllipseSymbolLayer()

    box_layer.setShape(QgsEllipseSymbolLayer.Shape.Rectangle)

    box_layer.setSymbolWidth(_MINEFIELD_BOX_WIDTH_MM)
    box_layer.setSymbolHeight(_MINEFIELD_BOX_HEIGHT_MM)

    box_layer.setFillColor(QColor(0, 0, 0, 0))
    box_layer.setStrokeWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        box_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    always_dashed = " OR ".join(
        f"\"measure_type\" = '{t}'" for t in _MINEFIELD_ALWAYS_DASHED
    )

    box_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(
            f"CASE WHEN {always_dashed} THEN 'dash'"
            f" ELSE {_STATUS_LINE_STYLE_EXPRESSION} END"
        )
    )

    return box_layer


def _minefield_symbol(dummy=False):

    """
    A minefield point: the box, three mine glyphs inside it, and - for
    Dummy Minefield - a dashed chevron above, the same decoy mark the
    Decoy Mined Area carries.
    """

    layers = [_minefield_box_layer()]

    first = -_MINEFIELD_GLYPH_PITCH_MM

    for slot in range(_MINEFIELD_GLYPH_SLOTS):

        marker = QgsSvgMarkerSymbolLayer("")

        marker.setSize(_MINE_GLYPH_SIZE_MM)

        marker.setDataDefinedProperty(
            QgsSymbolLayer.Property.Name,
            QgsProperty.fromExpression(_minefield_glyph_sidc_expression(slot))
        )

        marker.setOffset(
            QPointF(first + slot * _MINEFIELD_GLYPH_PITCH_MM, 0.0)
        )

        marker.setOffsetUnit(Qgis.RenderUnit.Millimeters)

        layers.append(marker)

    if dummy:

        # An inline SVG, not a QGIS marker shape: none of them is a
        # symmetric open V. ArrowHead was tried first and rendered as a
        # diagonal arrow (caught by render); a Triangle would close the
        # bottom edge the template leaves open. See
        # mct_decoy_chevron_svg().
        chevron = QgsSvgMarkerSymbolLayer("")

        chevron.setSize(_MINEFIELD_BOX_WIDTH_MM * 0.78)

        chevron.setDataDefinedProperty(
            QgsSymbolLayer.Property.Name,
            QgsProperty.fromExpression(
                f"mct_decoy_chevron_svg({_POINT_MONO_COLOR_EXPRESSION})"
            )
        )

        # The SVG's viewBox is 100x60, so at width W its own height is
        # 0.6W - half of that, plus half the box, puts it clear above.
        chevron_width = _MINEFIELD_BOX_WIDTH_MM * 0.78

        chevron.setOffset(
            QPointF(
                0.0,
                -(_MINEFIELD_BOX_HEIGHT_MM * 0.5 + chevron_width * 0.30 + 1.0)
            )
        )

        chevron.setOffsetUnit(Qgis.RenderUnit.Millimeters)

        layers.append(chevron)

    return QgsMarkerSymbol(layers)


_MINEFIELD_SYMBOL_BUILDERS = {
    "minefield": _minefield_symbol,
    "minefield_known_enemy": _minefield_symbol,
    "minefield_suspected": _minefield_symbol,
    "minefield_dummy": lambda: _minefield_symbol(dummy=True),
}


_MINEFIELD_FIELD_H_EXPRESSION = "upper(coalesce(\"mine_indicator\", ''))"

_MINEFIELD_FIELD_W_EXPRESSION = "upper(coalesce(\"self_destruct_dtg\", ''))"

_MINEFIELD_ENY_EXPRESSION = (
    "CASE WHEN \"measure_type\" IN ("
    + ", ".join(f"'{t}'" for t in _MINEFIELD_ENEMY_TYPES)
    + ") THEN 'ENY' ELSE '' END"
)


def _configure_minefields_labeling(layer):

    """
    Field H above the box, Field W below it, and "ENY" at each side for
    the two enemy variants.

    Offsets are in millimetres and sized off the box, because the box
    is a fixed screen-size symbol - a map-unit offset would drift
    across the symbol as the user zooms.
    """

    half_height = _MINEFIELD_BOX_HEIGHT_MM * 0.5
    half_width = _MINEFIELD_BOX_WIDTH_MM * 0.5

    rules = (
        (_MINEFIELD_FIELD_H_EXPRESSION, Qgis.LabelQuadrantPosition.Above,
         0.0, -(half_height + 1.6)),
        (_MINEFIELD_FIELD_W_EXPRESSION, Qgis.LabelQuadrantPosition.Below,
         0.0, half_height + 1.6),
        (_MINEFIELD_ENY_EXPRESSION, Qgis.LabelQuadrantPosition.Left,
         -(half_width + 1.2), 0.0),
        (_MINEFIELD_ENY_EXPRESSION, Qgis.LabelQuadrantPosition.Right,
         half_width + 1.2, 0.0),
    )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    for expression, quadrant, x_offset, y_offset in rules:

        settings = _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            expression,
            quadrant=quadrant
        )

        settings.xOffset = x_offset
        settings.yOffset = y_offset
        settings.offsetUnits = Qgis.RenderUnit.Millimeters

        settings.dataDefinedProperties().setProperty(
            QgsPalLayerSettings.Property.Color,
            QgsProperty.fromExpression(_AREA_OUTLINE_COLOR_EXPRESSION)
        )

        root_rule.appendChild(QgsRuleBasedLabeling.Rule(settings))

    layer.setLabeling(QgsRuleBasedLabeling(root_rule))

    layer.setLabelsEnabled(True)


def create_obstacle_control_measures_minefields_layer(
    name=MINEFIELDS_LAYER_NAME
):

    """
    Table H-XIX's own minefield POINTS (batch B3) - five codes over
    four measure types, each a fixed-size box of mine glyphs placed on
    one anchor point.

    Their own layer rather than more entries on the B1 Points layer:
    those are single milsymbol icons behind one SVG marker, while these
    are hand-built composites (a box, three glyphs and sometimes a
    chevron) needing a rule-based renderer and their own fields.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(f"Point?crs={crs.authid()}", name, "memory")

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("colour", QMetaType.Type.QString),
            QgsField("mine_type", QMetaType.Type.QString),
            QgsField("mine_indicator", QMetaType.Type.QString),
            QgsField("self_destruct_dtg", QMetaType.Type.QString),
        ]
    )

    layer.updateFields()

    fields = layer.fields()

    layer.setEditorWidgetSetup(
        fields.indexOf("measure_type"),
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(MINEFIELD_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        fields.indexOf("mine_type"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(MINE_TYPE_LABELS)})
    )

    layer.setEditorWidgetSetup(
        fields.indexOf("colour"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(COLOUR_LABELS)})
    )

    # Hand-built, not milsymbol-rendered, so `affiliation` never reaches
    # build_sidc() for the BOX - but it does for the mine glyphs inside
    # it, which are real milsymbol icons. So this layer needs the POINTS
    # affiliation vocabulary, not the lines/areas one.
    layer.setEditorWidgetSetup(
        fields.indexOf("affiliation"),
        QgsEditorWidgetSetup(
            "ValueMap", {"map": _value_map(POINT_AFFILIATION_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        fields.indexOf("status"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(STATUS_LABELS)})
    )

    layer.setDefaultValueDefinition(
        fields.indexOf("measure_type"), QgsDefaultValue("'minefield'")
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("affiliation"), QgsDefaultValue("'friend'")
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("status"), QgsDefaultValue("'present'")
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("colour"), QgsDefaultValue(f"'{GREEN}'")
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("mine_type"), QgsDefaultValue(f"'{DEFAULT_MINE_TYPE}'")
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _MINEFIELD_SYMBOL_BUILDERS)
    )

    _configure_minefields_labeling(layer)

    return layer


def add_obstacle_control_measures_minefields_layer(iface):

    return add_layer_if_absent(
        iface,
        MINEFIELDS_LAYER_NAME,
        create_obstacle_control_measures_minefields_layer
    )
