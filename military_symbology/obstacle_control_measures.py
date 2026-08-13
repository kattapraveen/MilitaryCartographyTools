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
    QgsFieldConstraints,
    QgsFillSymbol,
    QgsFontMarkerSymbolLayer,
    QgsGeometryGeneratorSymbolLayer,
    QgsLinePatternFillSymbolLayer,
    QgsLineSymbol,
    QgsMapUnitScale,
    QgsMarkerLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbol,
    QgsSymbolLayer,
    QgsVectorLayer,
)

import math

from collections import namedtuple

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
    # -- Water crossing sites. Bridge and Assault Crossing DID end up
    #    sharing one builder, and one dropdown entry, when B7 was built
    #    - see B7_CROSSINGS_MEASURE_TYPE_LABELS.
    #
    #    **The whole B7 family defaults to BLACK, not the table's usual
    #    green** - the maintainer's own call when the batch was built
    #    ("b7 all default colour black not green"). A crossing site is
    #    not itself an obstacle, which is what the green is for; Lane
    #    was already black in the original audit and the rest now match
    #    it. Per-feature override still available like everywhere else.
    "271300": _e("Assault Crossing", LINE, B7_CROSSINGS, CONFIRMED, BLACK),
    "271400": _e("Bridge", LINE, B7_CROSSINGS, CONFIRMED, BLACK),
    "271500": _e("Ford Easy", LINE, B7_CROSSINGS, CONFIRMED, BLACK),
    "271600": _e("Ford Difficult", LINE, B7_CROSSINGS, CONFIRMED, BLACK),
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
    # Black with the rest of B7 - see the water crossing block above.
    "282003": _e("Overhead Wire", LINE, B7_CROSSINGS, CONFIRMED, BLACK),
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
    "290700": _e("Ferry", LINE, B7_CROSSINGS, ASSUMED, BLACK),
    "290800": _e("Raft Site", LINE, B7_CROSSINGS, CONFIRMED, BLACK),
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

# Icons whose stroke the maintainer asked to thicken after smoke-
# testing B1: "the lines are too faint, can we increase the thickness
# of lines by 80%?". Scoped to the ones they named rather than applied
# across the layer - the filled icons (the mines proper) already read
# clearly and would only get muddier.
#
# NOTE Fixed and Prefabricated Obstacle is a FILLED triangle, not an
# outline like the other four; it is included because the maintainer
# listed it, but the change is barely visible there by construction.
_THICKER_STROKE_ENTITIES = (
    "booby_trap",
    "unspecified_mine",
    "obstacle_fixed_prefabricated",
    "obstacle_movable",
    "obstacle_movable_prefabricated",
)

_THICKER_STROKE_FACTOR = 1.8

_POINT_STROKE_SCALE_EXPRESSION = (
    "CASE WHEN \"entity\" IN ("
    + ", ".join(f"'{e}'" for e in _THICKER_STROKE_ENTITIES)
    + f") THEN {_THICKER_STROKE_FACTOR} ELSE 1 END"
)

_POINTS_SIDC_EXPRESSION = (
    "mct_sidc_svg(mct_build_sidc("
    "\"affiliation\",\"entity\",'control_measure','unspecified',"
    "\"status\",false),"
    "upper(coalesce(\"unique_designation\",'')),"
    "'uniqueDesignation',"
    + _POINT_MONO_COLOR_EXPRESSION + ","
    + _POINT_STROKE_SCALE_EXPRESSION +
    ")"
)

_POINTS_DEFAULT_MARKER_SIZE_MM = 8.0

# QGIS reads an SVG marker's size as its WIDTH, so an icon with a wider
# viewBox draws its own artwork smaller at the same marker size. Both
# entries here are measured off the real rendered SVG, not guessed -
# the same technique that fixed Pop-Up Point and Fire Support Station.
#
# Antipersonnel Mine with Directional Effects carries an arrow outside
# its circle, giving it a 148-wide viewBox where its plain sibling has
# 108 - which is exactly the maintainer's report that "the circle has
# become too small, can we match it with the size of circle of
# antipersonnel mine". 148/108 restores the circle to the same drawn
# size.
#
# The Towers are a plain +30% at the maintainer's request.
_POINT_SIZE_MULTIPLIERS = {
    "antipersonnel_mine_directional": 148.0 / 108.0,
    "tower_low": 1.3,
    "tower_high": 1.3,
}

_POINT_SIZE_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"entity\" = '{entity}'"
    f" THEN {_POINTS_DEFAULT_MARKER_SIZE_MM * multiplier}"
    for entity, multiplier in _POINT_SIZE_MULTIPLIERS.items()
) + f" ELSE {_POINTS_DEFAULT_MARKER_SIZE_MM} END"

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
        QgsSymbolLayer.Property.Size,
        QgsProperty.fromExpression(_POINT_SIZE_EXPRESSION)
    )

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
    # 0.62 of the marker width cleared the glyph, but the maintainer
    # found the gap too wide in live testing and asked to "reduce
    # distance closer to tower by 60%" - so 40% of what it was.
    settings.xOffset = _POINTS_DEFAULT_MARKER_SIZE_MM * 0.62 * 0.4

    # Raised to sit level with the TOP of the tower rather than its
    # middle - the maintainer's own follow-up, "the number in towers
    # should be aligned with the top not center of glyph".
    #
    # Derived from the tower's own drawn height rather than typed as a
    # millimetre constant, so it tracks the +30% size change above and
    # any later one: QGIS sizes the marker by WIDTH, and both Tower
    # icons have a 108x98 viewBox, so the drawn height is width*98/108.
    # A NEGATIVE yOffset moves a label up here (confirmed by render,
    # not assumed - the sign is the opposite of what it reads like).
    tower_size_mm = (
        _POINTS_DEFAULT_MARKER_SIZE_MM
        * _POINT_SIZE_MULTIPLIERS["tower_low"]
    )

    tower_height_mm = tower_size_mm * (98.0 / 108.0)

    settings.yOffset = -tower_height_mm * 0.38

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

# How many mine glyphs scatter across a dynamic minefield, and how they
# are kept apart. Both distances are fractions of the shape's own size
# (see mct_scatter_points), so one setting reads the same on a small
# minefield and a large one.
#
# The count is an upper bound, not a promise: a long thin sliver takes
# fewer mines rather than being crammed or left empty.
_DYNAMIC_MINE_COUNT = 7
_DYNAMIC_MINE_GAP_FRACTION = 0.26
_DYNAMIC_MINE_INSET_FRACTION = 0.14


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
    that is a claim about the ground, not a styling detail.

    **CONFIRMED by the maintainer 2026-08-12** ("the dummy minefield
    and dynamic are fine, no problem") after smoke-testing B3. Recorded
    here because the audit document still reads "merge", and a later
    pass working from it would otherwise file this as a defect.
    """

    symbol = QgsFillSymbol.createSimple({"style": "no"})

    symbol.changeSymbolLayer(0, _area_outline_layer())

    # NOT QgsRandomMarkerFillSymbolLayer, which this used first. That
    # layer clips the POINTS to the polygon, so a glyph centred near
    # the edge still hangs over the boundary, and it has no minimum
    # separation, so glyphs collide - "should not touch the perimeter,
    # should not touch each other" (the maintainer, on seeing it).
    # mct_scatter_points() does both, and is seeded per feature so the
    # arrangement does not crawl on every pan and zoom.
    # TWO passes over the SAME placement, taking alternate points, so a
    # combined anti-personnel/anti-tank field mixes both glyphs across
    # the area. A single pass drew only the primary type, which breaks
    # the maintainer's own rule that anything drawing more than one
    # glyph alternates. _minefield_glyph_sidc_expression() already has
    # exactly the right semantics: it alternates by slot for a combined
    # type and repeats the same glyph for a single one, so a
    # single-type field still fills both passes.
    for remainder in (0, 1):

        scatter = QgsGeometryGeneratorSymbolLayer.create({})

        scatter.setSymbolType(QgsSymbol.SymbolType.Marker)

        scatter.setGeometryExpression(
            f"mct_scatter_points($geometry, {_DYNAMIC_MINE_COUNT},"
            f" {_DYNAMIC_MINE_GAP_FRACTION},"
            f" {_DYNAMIC_MINE_INSET_FRACTION}, 2, {remainder})"
        )

        glyph = QgsSvgMarkerSymbolLayer("")

        glyph.setSize(_MINE_GLYPH_SIZE_MM)

        glyph.setDataDefinedProperty(
            QgsSymbolLayer.Property.Name,
            QgsProperty.fromExpression(
                _minefield_glyph_sidc_expression(remainder)
            )
        )

        scatter.setSubSymbol(QgsMarkerSymbol([glyph]))

        symbol.appendSymbolLayer(scatter)

    if dummy:

        chevron_generator = QgsGeometryGeneratorSymbolLayer.create({})

        chevron_generator.setSymbolType(QgsSymbol.SymbolType.Line)

        # ABOVE the shape, not inside it - the template puts Dummy
        # Minefield's chevron clear of the boundary, unlike Decoy Mined
        # Area, which centres it.
        # Half-span 0.5 - the full width of the shape, corner to
        # corner. The maintainer's own note: sitting ABOVE the area
        # rather than inside it, the chevron should "extend to the
        # horizontal extent of the area", where the two Decoy Mined
        # Area variants keep the default narrow span because theirs is
        # drawn inside the boundary.
        chevron_generator.setGeometryExpression(
            "translate(mct_decoy_chevron($geometry, 0.5), 0,"
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


def _set_mine_field_aliases(layer):

    """
    Names the three mine fields after the standard's own field letters,
    so the attribute form says what each one is without the user having
    to cross-reference the table.
    """

    aliases = {
        "mine_type": "Mine type (Field A)",
        "mine_indicator": "Scatterable mines (Field H)",
        "self_destruct_dtg": "Self-destruct time (Field W)",
    }

    for name, alias in aliases.items():

        index = layer.fields().indexOf(name)

        if index >= 0:
            layer.setFieldAlias(index, alias)


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

    layer.setEditorWidgetSetup(
        fields.indexOf("mine_indicator"),
        QgsEditorWidgetSetup(
            "ValueMap", {"map": _value_map(MINE_INDICATOR_LABELS)}
        )
    )

    _set_mine_field_aliases(layer)

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
# Field H, and NOT free text - the standard's own Note on printed page
# 592 gives it exactly two possible values: "If only scatterable mines
# are within the minefield, the H field will be filled with an 'S'; a
# '+S' will be used if there is a mix of scatterable and other mines as
# appropriate and a self-destruct time will be posted in the W field
# for the scatterable mines."
#
# It was a free-text box until the maintainer smoke-tested B2 and asked
# what it was for - which is the answer that a two-value vocabulary
# should never have been typed by hand. Now a dropdown, so the field
# states its own meaning at the point of use.
MINE_INDICATOR_LABELS = {
    "": "(none - no scatterable mines)",
    "S": "S - scatterable mines only",
    "+S": "+S - scatterable mixed with other mines",
}

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


# The mine glyphs are built with a FIXED standard identity, not the
# feature's own `affiliation`.
#
# This is the fix for "the glyphs are broken i.e. ?" on Mined Area and
# Dynamic Depiction (2026-08-12). Both live on the AREAS layer, whose
# affiliation field correctly defaults to "unspecified" - that is the
# lines/areas vocabulary, and right for a hand-drawn outline, where the
# fifth value means "draw it black". But it is NOT a SIDC standard
# identity, so feeding it to build_sidc() raised, mct_build_sidc()
# returned the KeyError message as if it were a SIDC, and milsymbol
# drew its unknown-icon fallback for every glyph.
#
# Rather than change that layer's affiliation vocabulary (it needs the
# fifth value) the glyphs simply stop depending on it. Nothing is lost:
# monoColor repaints these icons green or black from the `colour` field
# regardless, and an unframed control-measure icon takes no other cue
# from its standard identity - so the affiliation was never visible
# here in the first place.
_MINE_GLYPH_AFFILIATION = "friend"

def _mine_glyph_sidc_expression(slot):

    """
    The SIDC for the glyph in position `slot` (0-based) of the A field.

    Returns an empty string when this mine type has no glyph for that
    slot - a single-type field leaves slot 1 empty - which the caller
    turns into a zero-size marker rather than a broken symbol.

    Carries the same stroke thickening B1's own outline icons got: the
    maintainer found the Antipersonnel Mine's "ears" and the Unspecified
    Mine's circle too faint here too, and asked for them "in line with
    B1". These glyphs draw smaller than a B1 marker (5mm against 8mm),
    so the thin strokes read fainter still.
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
        f" '{_MINE_GLYPH_AFFILIATION}', " + entity_expression + ","
        " 'control_measure', 'unspecified', 'present', false),"
        " '', '', " + _POINT_MONO_COLOR_EXPRESSION + ","
        f" {_THICKER_STROKE_FACTOR}) END"
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

_MASKED_MINEFIELD_BOX_LAYER_ID = "minefield_box"

_MINEFIELD_BOX_WIDTH_MM = 15.0

# The two enemy variants draw a WIDER box. Their "ENY" fields sit on
# the vertical sides, and at the standard width the text reached inward
# far enough to cover the outer mine glyphs (caught by render). The
# standard's own picture shows the same thing - its enemy box is wider
# than the plain one, for exactly this reason.
_MINEFIELD_ENEMY_BOX_WIDTH_MM = 21.0
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
        f" '{_MINE_GLYPH_AFFILIATION}', " + entity_expression + ","
        " 'control_measure', 'unspecified', 'present', false),"
        " '', '', " + _POINT_MONO_COLOR_EXPRESSION + ","
        f" {_THICKER_STROKE_FACTOR}) END"
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

    # The id the "ENY" labels mask against - they sit ON the box's own
    # vertical sides, so the line has to break through them.
    box_layer.setId(_MASKED_MINEFIELD_BOX_LAYER_ID)

    box_layer.setShape(QgsEllipseSymbolLayer.Shape.Rectangle)

    box_layer.setSymbolWidth(_MINEFIELD_BOX_WIDTH_MM)
    box_layer.setSymbolHeight(_MINEFIELD_BOX_HEIGHT_MM)

    enemy_clause = " OR ".join(
        f"\"measure_type\" = '{t}'" for t in _MINEFIELD_ENEMY_TYPES
    )

    box_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Width,
        QgsProperty.fromExpression(
            f"CASE WHEN {enemy_clause}"
            f" THEN {_MINEFIELD_ENEMY_BOX_WIDTH_MM}"
            f" ELSE {_MINEFIELD_BOX_WIDTH_MM} END"
        )
    )

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

    # The ENY labels ride the enemy box's own (wider) sides; H and W
    # are centred so the width does not matter to them.
    half_width = _MINEFIELD_ENEMY_BOX_WIDTH_MM * 0.5

    # "ENY" sits ON each vertical side of the box, centred over the
    # line rather than clear of it - the maintainer's own correction
    # after smoke-testing B3, and what the template draws: the box's
    # own side is interrupted where the field sits. So the offset is
    # exactly half the width (no clearance gap) and the quadrant is
    # Over, with the box masked so the line breaks through the text.
    rules = (
        (_MINEFIELD_FIELD_H_EXPRESSION, Qgis.LabelQuadrantPosition.Above,
         0.0, -(half_height + 1.6)),
        (_MINEFIELD_FIELD_W_EXPRESSION, Qgis.LabelQuadrantPosition.Below,
         0.0, half_height + 1.6),
        (_MINEFIELD_ENY_EXPRESSION, Qgis.LabelQuadrantPosition.Over,
         -half_width, 0.0),
        (_MINEFIELD_ENY_EXPRESSION, Qgis.LabelQuadrantPosition.Over,
         half_width, 0.0),
    )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    for expression, quadrant, x_offset, y_offset in rules:

        # One shared mask list on EVERY rule, not just the two that
        # need it: masking is configured per LAYER, and rules declaring
        # different lists make QGIS keep one arbitrarily. It is a
        # harmless no-op for the H and W labels, which sit clear.
        settings = _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            expression,
            masked_symbol_layer_ids=[_MASKED_MINEFIELD_BOX_LAYER_ID],
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

    layer.setEditorWidgetSetup(
        fields.indexOf("mine_indicator"),
        QgsEditorWidgetSetup(
            "ValueMap", {"map": _value_map(MINE_INDICATOR_LABELS)}
        )
    )

    _set_mine_field_aliases(layer)

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


# ============================================================
# Batch B4 - wire obstacles (Lines)
# ============================================================

LINES_LAYER_NAME = "Obstacle Control Measures (Lines)"

# Table H-XIX's own wire-obstacle family, printed pages 586-587.
#
# 290300 ("Wire Obstacles") is NOT here: its template cell reads "N/A",
# so it is a heading row, not a symbol - the same parent-row trap the
# module docstring warns about, and the reason this vocabulary is
# written out rather than derived from a code prefix.
WIRE_MEASURE_TYPE_LABELS = {
    "unspecified_wire_obstacle": "Unspecified Wire Obstacle",
    "single_fence": "Single Fence",
    "double_fence": "Double Fence",
    "double_apron_fence": "Double Apron Fence",
    "low_wire_fence": "Low Wire Fence",
    "high_wire_fence": "High Wire Fence",
    "single_concertina": "Single Concertina",
    "double_strand_concertina": "Double Strand Concertina",
    "triple_strand_concertina": "Triple Strand Concertina",
}

# The toothed-line obstacles, which share the wire family's own
# construction - a line carrying a repeating glyph - and so are built
# by the same code rather than by a parallel mechanism.
TOOTHED_MEASURE_TYPE_LABELS = {
    "abatis": "Abatis",
    "obstacle_line": "Obstacle Line",
    "antitank_ditch_reinforced":
        "Antitank Ditch Reinforced with Antitank Mines",
    "antitank_ditch_under_construction": "Antitank Ditch - Under Construction",
    "antitank_ditch_completed": "Antitank Ditch - Completed",
    "antitank_wall": "Antitank Wall",
}

TOOTHED_MEASURE_TYPE_CODES = {
    "abatis": "280100",
    "obstacle_line": "290100",
    "antitank_ditch_reinforced": "290203",
    "antitank_ditch_under_construction": "290201",
    "antitank_ditch_completed": "290202",
    "antitank_wall": "290204",
}

WIRE_MEASURE_TYPE_CODES = {
    "unspecified_wire_obstacle": "290301",
    "single_fence": "290302",
    "double_fence": "290303",
    "double_apron_fence": "290304",
    "low_wire_fence": "290305",
    "high_wire_fence": "290306",
    "single_concertina": "290307",
    "double_strand_concertina": "290308",
    "triple_strand_concertina": "290309",
}

# The maintainer's own reading of the manual, which is far simpler
# than the first build assumed. Every one of the nine is "a series of
# Xs" (or of 0s), and they differ ONLY in three things:
#
#   glyph    - a cross, a pair of crosses, or an oval
#   gap      - the space between glyphs, in multiples of a glyph width
#   lines    - which straight lines run through the series, given as
#              offsets in half-glyph-heights: 0 is through the middle,
#              +1 along the bottom of the glyphs, -1 along their top
#
# The first build guessed at nine separate shapes from the template
# pictures and got several wrong. This table is the maintainer's own
# description, transcribed, and is the single source of truth for all
# nine symbols.
_WireSpec = namedtuple("_WireSpec", "glyph gap lines")

_WIRE_SPECS = {
    # A series of crosses, nothing else.
    "unspecified_wire_obstacle": _WireSpec("cross", 1.5, ()),
    # Widely spaced crosses with a line through their middle.
    "single_fence": _WireSpec("cross", 4.0, (0,)),
    # Pairs of crosses - 0.5 apart within a pair, 3 between pairs -
    # with a line through the middle. The gap here is between PAIRS;
    # the 0.5 inside a pair is baked into the double_cross glyph.
    "double_fence": _WireSpec("double_cross", 3.0, (0,)),
    # The unspecified series, with a line through it.
    "double_apron_fence": _WireSpec("cross", 1.5, (0,)),
    # The unspecified series sitting ON a line.
    "low_wire_fence": _WireSpec("cross", 1.5, (1,)),
    # The unspecified series between two lines.
    "high_wire_fence": _WireSpec("cross", 1.5, (-1, 1)),
    # Low Wire Fence with ovals instead of crosses.
    "single_concertina": _WireSpec("oval", 1.5, (1,)),
    # ...plus a second line through the middle of the ovals.
    "double_strand_concertina": _WireSpec("oval", 1.5, (0, 1)),
    # High Wire Fence with ovals instead of crosses.
    "triple_strand_concertina": _WireSpec("oval", 1.5, (-1, 1)),

    # The toothed obstacles. Their glyph sits ON the line rather than
    # straddling it, so the line offset is 0 and the tooth's own
    # geometry does the standing-off - see _WIRE_GLYPH_GEOMETRY, where
    # each tooth's base is at the bottom of its box.
    #
    # "The teeth point toward enemy forces" (the standard's own note on
    # both ditches and the wall): a marker line rotates its glyph to
    # follow the line, so which side they point to follows the order
    # the anchor points were digitized in - exactly what the standard's
    # own Orientation rule says.
    # The ditches are a LINE BUILT OF TRIANGLES - bases touching end to
    # end, with no separate straight line drawn at all. So the gap is 0
    # (the triangles tile) and there are no line layers. The
    # maintainer's own correction; the first build drew spaced teeth
    # standing off a drawn line, which is a different symbol.
    "antitank_ditch_under_construction": _WireSpec("ditch_tooth", 0.0, ()),
    "antitank_ditch_completed": _WireSpec("ditch_tooth_filled", 0.0, ()),
    # The wall IS its line: a continuous "--v--v--" profile tiled at
    # gap 0, so no separate line layer. See the glyph's own comment for
    # how the tile keeps one side length of flat between Vs.
    "antitank_wall": _WireSpec("wall_vee", 0.0, ()),
    # The antitank wall's profile inverted - triangles up instead of
    # down. It also carries Field T below the line (see
    # _configure_lines_labeling).
    "obstacle_line": _WireSpec("obstacle_line_vee", 0.0, ()),
}

# The width (and height) of a single cross or oval.
_WIRE_GLYPH_SIZE_MM = 3.0

# The space between the two crosses of a Double Fence pair, in glyph
# widths. Given explicitly by the maintainer (0.5 first, then 0.25),
# and deliberately NOT scaled by _WIRE_GAP_SCALE below - that factor
# tunes the gap BETWEEN pairs, which is a different number.
_WIRE_PAIR_GAP = 0.25

# double_cross holds two crosses plus the gap between them, and QGIS
# sizes an SVG marker by its WIDTH - so it is drawn that much larger to
# keep each cross the same size as every other glyph here. Derived from
# _WIRE_PAIR_GAP rather than written down, so the marker size and the
# glyph's own viewBox cannot disagree.
_WIRE_GLYPH_WIDTH_MULTIPLIERS = {"double_cross": 2 + _WIRE_PAIR_GAP}

# How much of each end of the line the glyphs leave clear.
_WIRE_END_TRIM = 0.04

# How far tiling glyphs overlap their neighbour, to close the hairline
# a butt join leaves.
_WIRE_TILE_OVERLAP_MM = 0.12

# Every gap in _WIRE_SPECS is multiplied by this before it is drawn -
# the maintainer asked to "reduce the gap between the Xs and 0s across
# the board by 40%" after seeing them rendered.
#
# Applied as ONE factor rather than by editing the nine numbers,
# deliberately: those numbers are a transcription of the maintainer's
# own description of the manual and a test asserts they still match it,
# so tuning how it looks must not quietly rewrite what it says. The
# 0.5 spacing WITHIN a Double Fence pair is not scaled - that one was
# specified as an explicit figure and is baked into the paired glyph.
_WIRE_GAP_SCALE = 0.6


# Abatis is the one line obstacle here that is NOT a repeating glyph:
# a single hump just after the first anchor point, then straight line
# for the rest - "_^____" in the maintainer's own notation, with the
# hump's legs meeting the line. So it gets its own builder rather than
# a _WireSpec.
# Where the kink sits along the line, and how big it is - both as
# fractions of the line's own length, so the symbol scales with the
# feature.
_ABATIS_KINK_AT = 0.10
_ABATIS_KINK_SIZE = 0.06


def _abatis_symbol():

    """
    Abatis (280100) - a single triangular KINK near the start of the
    line, then straight for the rest.

    The kink is real geometry (mct_abatis_line), not a marker riding
    the line: a marker leaves the straight line running underneath it,
    which closes the triangle. The maintainer's own correction - "it is
    like a kink in the beginning of line, not a full triangle".
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression(
        f"mct_abatis_line($geometry, {_ABATIS_KINK_AT},"
        f" {_ABATIS_KINK_SIZE})"
    )

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line_layer)

    generator.setSubSymbol(inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, generator)

    return symbol


# Mine Cluster (290400): "user clicks two points, connect it with a
# dashed line, make a semi-circle over it" - the maintainer's own
# construction, corrected twice the same day. First, the height:
# "radius 1/3... of the line connecting the two points" (not 1/2, the
# standard's own printed figure). Then the span: "you are trimming the
# line instead of extending the semi-circle, the user when he clicks
# pt1 and pt2 expects the mine cluster to span that much, not reduce" -
# so the dome's own horizontal extent is now LOCKED to the full PT1-PT2
# click, and "1/3" survives only as its height (see
# mct_mine_cluster_arc's own docstring for why that makes it a half-
# ELLIPSE, not a true semicircle). Also: "make the dashes slightly
# longer say by 40% and increase the space between them by 50%".
_MINE_CLUSTER_ARC_HEIGHT_FRACTION = 1.0 / 3.0

# Qt's own default DashLine pattern - confirmed by probing a real QPen
# rather than assumed - is [4, 2] in units of the pen's own width, i.e.
# dash 4x the stroke width, gap 2x. That was this symbol's original,
# unnamed pattern (a bare setPenStyle(DashLine)); the maintainer's own
# "+40% dash, +50% gap" is applied to THAT baseline, not to some other
# round number, so the two numbers stay traceable to Qt's own default.
_MINE_CLUSTER_DASH_MM = _AREA_OUTLINE_WIDTH_MM * 4.0 * 1.4
_MINE_CLUSTER_GAP_MM = _AREA_OUTLINE_WIDTH_MM * 2.0 * 1.5


def _mine_cluster_dashed_line_layer():

    """
    The one dash pattern both of Mine Cluster's own symbol layers
    share - broken out so the straight line and the arc cannot drift
    into two different-looking dashes.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    line_layer.setUseCustomDashPattern(True)

    line_layer.setCustomDashPatternUnit(Qgis.RenderUnit.Millimeters)

    line_layer.setCustomDashVector(
        [_MINE_CLUSTER_DASH_MM, _MINE_CLUSTER_GAP_MM]
    )

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    return line_layer


def _mine_cluster_symbol():

    """
    Mine Cluster (290400) - a dashed straight line at the feature's own
    full PT1-PT2 length, plus a dashed half-ellipse over it
    (mct_mine_cluster_arc) whose own horizontal span matches that same
    length exactly, so it touches both clicked points - "the user...
    expects the mine cluster to span that much, not reduce". Always
    dashed, in both present and planned status - fixed iconography, not
    driven by "status", the same "always dashed" treatment already used
    for Maritime's own Bearing Line, Acoustic (Ambiguous) and the Decoy
    chevrons.
    """

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, _mine_cluster_dashed_line_layer())

    arc_inner = QgsLineSymbol()

    arc_inner.changeSymbolLayer(0, _mine_cluster_dashed_line_layer())

    arc_generator = QgsGeometryGeneratorSymbolLayer.create({})

    arc_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    arc_generator.setGeometryExpression(
        f"mct_mine_cluster_arc($geometry,"
        f" {_MINE_CLUSTER_ARC_HEIGHT_FRACTION})"
    )

    arc_generator.setSubSymbol(arc_inner)

    symbol.appendSymbolLayer(arc_generator)

    return symbol


def _trip_wire_symbol():

    """
    Trip Wire (290500) - two clicked anchor points (PT1, PT2), built
    from the maintainer's own dictated construction rather than the
    standard's own template picture (see mct_trip_wire_geometry's own
    docstring for the exact wording and why it replaced an earlier,
    3-point reading): the main PT1-PT2 line, two perpendicular
    crossbars at 1/7 and 1/2 of the way along it, and a 90 degree
    anticlockwise arc at PT2. Unlike Mine Cluster, the standard's own
    draw rules carry no "always dashed" note for this symbol, so it
    follows the ordinary H.5.1.1.3 present/planned rule like the rest
    of the wire family - solid when present, dashed when planned.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression("mct_trip_wire_geometry($geometry)")

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line_layer)

    generator.setSubSymbol(inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, generator)

    return symbol


# B5 - obstacle effects (270501-270504), all four now built. Table
# H-XIX's own hardest batch: Block and Turn started from the standard's
# own draw-rules TEXT (mct_block_geometry/mct_turn_arc, both verified
# by hand-worked examples before being trusted - see their own
# docstrings, though Turn's own first construction was later replaced
# entirely, see that function's own docstring). Disrupt and Fix waited
# for the maintainer's own dictated construction rather than a guessed
# one - their own draw rules give no numeric ratio for the shapes
# shown, only a picture (the same call this project has made before on
# fiddly shapes, and it was faster again this time).
#
# NEITHER "disrupt" NOR "fix" may ever reuse a measure_type key from
# Table H-XXIV (Mission Tasks, H21, not yet built) even though that
# table has its own same-named entries - they are DIFFERENT SIDCs on a
# different table, and conflating them is the exact bug the maintainer
# found and fixed in the old stage-based pass (see this module's own
# batch-B0 audit notes). Checked now, empty: nothing in this codebase
# defines "disrupt"/"fix"/"block"/"turn" outside this module today.
def _block_symbol():

    """
    Block (270501) - a "T": crossbar PT1-PT2, stem from the crossbar's
    own midpoint out to PT3's own perpendicular distance
    (mct_block_geometry). No "always dashed" note in the standard's own
    draw rules, so ordinary present/planned styling.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression("mct_block_geometry($geometry)")

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line_layer)

    generator.setSubSymbol(inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, generator)

    return symbol


def _turn_symbol():

    """
    Turn (270504) - rebuilt 2026-08-13 to the maintainer's own dictated
    construction (see mct_turn_arc's own docstring for the exact
    wording and why it replaced a first, standard-text-only reading): a
    quadratic Bezier curve from PT1 through control point PT2 to PT3,
    arrowhead at PT3. The arrowhead itself reuses the plain UNFILLED-
    chevron-at-LastVertex technique already established for Direction
    of Attack (offensive_control_measures.py's own
    _direction_of_attack_symbol) - QgsSimpleMarkerSymbolLayerBase.
    Shape.ArrowHead, transparent fill, stroke-only, rotated with the
    line's own local end direction. No "always dashed" note here
    either - ordinary present/planned line.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression("mct_turn_arc($geometry)")

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line_layer)

    generator.setSubSymbol(inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, generator)

    chevron_marker = QgsMarkerSymbol()

    chevron_layer = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead,
        6
    )

    chevron_layer.setColor(QColor(0, 0, 0, 0))

    chevron_layer.setStrokeWidth(_AREA_OUTLINE_WIDTH_MM * 1.5)

    _apply_obstacle_color(
        chevron_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    chevron_marker.changeSymbolLayer(0, chevron_layer)

    chevron_line_layer = QgsMarkerLineSymbolLayer(True)

    chevron_line_layer.setSubSymbol(chevron_marker)

    chevron_line_layer.setPlacements(Qgis.MarkerLinePlacement.LastVertex)

    # The chevron must sit on the CURVE's own last point (PT3, the
    # tip), not the feature's raw, undrawn 3-vertex geometry (PT1, PT2,
    # PT3) - LastVertex on that happens to also land on PT3 today, but
    # only because PT3 is already the raw geometry's own last vertex;
    # relying on that coincidence is what caused the ORIGINAL version
    # of this bug (the tip landed on PT2 back when PT2, not PT3, was
    # the construction's own endpoint). Every symbol layer evaluates
    # against the feature's OWN geometry independently unless it is
    # itself wrapped in a generator, so this one needs its own, even
    # though it draws the identical curve the line layer above already
    # generated.
    chevron_inner = QgsLineSymbol()

    chevron_inner.changeSymbolLayer(0, chevron_line_layer)

    chevron_generator = QgsGeometryGeneratorSymbolLayer.create({})

    chevron_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    chevron_generator.setGeometryExpression("mct_turn_arc($geometry)")

    chevron_generator.setSubSymbol(chevron_inner)

    symbol.appendSymbolLayer(chevron_generator)

    return symbol


def _disrupt_symbol():

    """
    Disrupt (270502) - the maintainer's own dictated construction (see
    mct_disrupt_geometry's own docstring for the exact wording): a
    base (PT1-PT2, no arrowhead) plus three perpendicular arrows, each
    with its own arrowhead at the tip. Two geometry-generator layers,
    both reading the SAME feature: one for the whole thing (base +
    arrows, for the plain line) and one scoped to just the arrows (for
    the arrowhead markers) - the base must not get an arrowhead of its
    own, which a single shared geometry would risk (its own last
    vertex, PT2, sits exactly at Arrow A's own start point).
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression("mct_disrupt_geometry($geometry)")

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line_layer)

    generator.setSubSymbol(inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, generator)

    chevron_marker = QgsMarkerSymbol()

    chevron_layer = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead,
        6
    )

    chevron_layer.setColor(QColor(0, 0, 0, 0))

    chevron_layer.setStrokeWidth(_AREA_OUTLINE_WIDTH_MM * 1.5)

    _apply_obstacle_color(
        chevron_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    chevron_marker.changeSymbolLayer(0, chevron_layer)

    chevron_line_layer = QgsMarkerLineSymbolLayer(True)

    chevron_line_layer.setSubSymbol(chevron_marker)

    chevron_line_layer.setPlacements(Qgis.MarkerLinePlacement.LastVertex)

    # Scoped to the three arrows ONLY (mct_disrupt_arrow_tips), not the
    # combined geometry above - a LastVertex placement over the full
    # base+arrows geometry would also mark the base's own last vertex
    # (PT2), which is not an arrow tip at all.
    chevron_inner = QgsLineSymbol()

    chevron_inner.changeSymbolLayer(0, chevron_line_layer)

    chevron_generator = QgsGeometryGeneratorSymbolLayer.create({})

    chevron_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    chevron_generator.setGeometryExpression(
        "mct_disrupt_arrow_tips($geometry)"
    )

    chevron_generator.setSubSymbol(chevron_inner)

    symbol.appendSymbolLayer(chevron_generator)

    return symbol


def _fix_symbol():

    """
    Fix (270503) - the maintainer's own dictated construction (see
    mct_fix_geometry's own docstring for the exact wording and the
    60-degree apex-angle assumption it makes): a single generated path,
    flat-toothed-flat, from PT1 to PT2, ending in a FILLED arrowhead at
    PT2 ("end the line segment at PT2 with an arrowhead... filled
    arrowhead") - unlike Block/Disrupt/Turn's own UNFILLED chevron, per
    the maintainer's own explicit request here.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression("mct_fix_geometry($geometry)")

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line_layer)

    generator.setSubSymbol(inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, generator)

    arrow_marker = QgsMarkerSymbol()

    arrow_layer = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHeadFilled,
        6
    )

    _apply_obstacle_color(
        arrow_layer,
        [
            QgsSymbolLayer.Property.FillColor,
            QgsSymbolLayer.Property.StrokeColor,
        ],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    arrow_marker.changeSymbolLayer(0, arrow_layer)

    arrow_line_layer = QgsMarkerLineSymbolLayer(True)

    arrow_line_layer.setSubSymbol(arrow_marker)

    arrow_line_layer.setPlacements(Qgis.MarkerLinePlacement.LastVertex)

    # Same reason as Turn/Disrupt's own arrowheads: LastVertex must see
    # the GENERATED path's own last point (PT2), not the feature's raw
    # 3-vertex geometry, so it needs its own generator wrapper too.
    arrow_inner = QgsLineSymbol()

    arrow_inner.changeSymbolLayer(0, arrow_line_layer)

    arrow_generator = QgsGeometryGeneratorSymbolLayer.create({})

    arrow_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    arrow_generator.setGeometryExpression("mct_fix_geometry($geometry)")

    arrow_generator.setSubSymbol(arrow_inner)

    symbol.appendSymbolLayer(arrow_generator)

    return symbol


# Antitank Ditch Reinforced with Antitank Mines: "a line with filled
# triangles pointing downward, the triangles alternating with anti-tank
# mine" - the maintainer's own description. Two interleaved series, so
# it cannot be a _WireSpec (which has one glyph and one interval).
_REINFORCED_PITCH_MM = 3.0


def _antitank_ditch_reinforced_symbol():

    symbol = QgsLineSymbol()

    # Unlike the plain ditches, this one DOES draw a line - "a line
    # with filled triangles pointing downward, the triangles
    # alternating with anti-tank mine".
    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    symbol.changeSymbolLayer(0, line_layer)

    first = False

    for offset_along, glyph_expression, size in (
        (
            0.0,
            "mct_wire_glyph_svg('ditch_tooth_filled_down', "
            + _POINT_MONO_COLOR_EXPRESSION + ")",
            _WIRE_GLYPH_SIZE_MM,
        ),
        (
            _REINFORCED_PITCH_MM,
            # A real milsymbol antitank mine, the same icon batch B1
            # draws as a point - not a hand-drawn lookalike. Fixed
            # standard identity for the same reason the mine glyphs in
            # B2/B3 use one: this layer's affiliation vocabulary
            # includes "unspecified", which is not a SIDC value.
            "mct_sidc_svg(mct_build_sidc('"
            + _MINE_GLYPH_AFFILIATION + "', 'antitank_mine',"
            " 'control_measure', 'unspecified', 'present', false),"
            " '', '', " + _POINT_MONO_COLOR_EXPRESSION + ", "
            + str(_THICKER_STROKE_FACTOR) + ")",
            _WIRE_GLYPH_SIZE_MM * 1.4,
        ),
    ):

        glyph = QgsSvgMarkerSymbolLayer("")

        glyph.setSize(size)

        glyph.setDataDefinedProperty(
            QgsSymbolLayer.Property.Name,
            QgsProperty.fromExpression(glyph_expression)
        )

        # The triangles hang below the line, so their base sits on it.
        glyph.setOffset(QPointF(0.0, _WIRE_GLYPH_SIZE_MM * 0.5))
        glyph.setOffsetUnit(Qgis.RenderUnit.Millimeters)

        marker_line = QgsMarkerLineSymbolLayer()

        # Both series share one pitch and are half a pitch apart, which
        # is what makes them alternate.
        marker_line.setInterval(_REINFORCED_PITCH_MM * 2)
        marker_line.setIntervalUnit(Qgis.RenderUnit.Millimeters)

        marker_line.setOffsetAlongLine(offset_along)
        marker_line.setOffsetAlongLineUnit(Qgis.RenderUnit.Millimeters)

        marker_line.setSubSymbol(QgsMarkerSymbol([glyph]))

        if first:
            symbol.changeSymbolLayer(0, marker_line)
            first = False
        else:
            symbol.appendSymbolLayer(marker_line)

    return symbol


def _wire_obstacle_symbol(measure_type):

    """
    One wire obstacle, built from its own _WireSpec.

    A symbol per measure type rather than one shared symbol: the number
    of straight lines genuinely varies (none, one, or two), and that is
    a different set of symbol layers, not a different expression.
    """

    spec = _WIRE_SPECS[measure_type]

    width_multiplier = _WIRE_GLYPH_WIDTH_MULTIPLIERS.get(spec.glyph, 1.0)

    glyph_width_mm = _WIRE_GLYPH_SIZE_MM * width_multiplier

    symbol = QgsLineSymbol()

    first = True

    for line_offset in spec.lines:

        line_layer = QgsSimpleLineSymbolLayer()

        line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

        # Offsets are in half-glyph-heights, so +1 puts the line along
        # the bottom of the glyphs and -1 along their top.
        line_layer.setOffset(line_offset * _WIRE_GLYPH_SIZE_MM * 0.5)
        line_layer.setOffsetUnit(Qgis.RenderUnit.Millimeters)

        _apply_obstacle_color(
            line_layer,
            [QgsSymbolLayer.Property.StrokeColor],
            _AREA_OUTLINE_COLOR_EXPRESSION
        )

        line_layer.setDataDefinedProperty(
            QgsSymbolLayer.Property.StrokeStyle,
            QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
        )

        if first:
            symbol.changeSymbolLayer(0, line_layer)
            first = False
        else:
            symbol.appendSymbolLayer(line_layer)

    glyph = QgsSvgMarkerSymbolLayer("")

    glyph.setSize(glyph_width_mm)

    glyph.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            f"mct_wire_glyph_svg('{spec.glyph}', "
            + _POINT_MONO_COLOR_EXPRESSION
            + f", {_WIRE_PAIR_GAP})"
        )
    )

    marker_line = QgsMarkerLineSymbolLayer()

    # Centre-to-centre: one glyph width plus the gap the manual gives.
    interval_mm = (
        glyph_width_mm
        + spec.gap * _WIRE_GAP_SCALE * _WIRE_GLYPH_SIZE_MM
    )

    if spec.gap == 0:
        # The tiling obstacles (both ditches, the antitank wall) butt
        # their glyphs edge to edge to form one continuous profile.
        # Placed at exactly one glyph width apart they leave a hairline
        # gap at every join - antialiasing at the marker's own box edge
        # - which the maintainer saw as "a slight gap in the line
        # halfway between each triangle". A sliver of overlap closes it.
        interval_mm -= _WIRE_TILE_OVERLAP_MM

    marker_line.setInterval(interval_mm)

    marker_line.setIntervalUnit(Qgis.RenderUnit.Millimeters)

    marker_line.setSubSymbol(QgsMarkerSymbol([glyph]))

    # The glyphs run along a TRIMMED copy of the line while the
    # straight lines above are drawn on the full geometry, so the line
    # always extends beyond the first and last glyph - the maintainer's
    # own note, "the line should always be longer or extend beyond the
    # Xs or 0s".
    #
    # offsetAlongLine was tried first and is not enough: it insets the
    # FIRST glyph only, and a render showed Single Fence still ending
    # flush, because markers land at fixed intervals from the start and
    # the last one can fall exactly on the final vertex. Trimming the
    # geometry bounds both ends by construction.
    #
    # The trim is a fraction of the line's own length rather than a
    # millimetre distance, because line_substring() works in layer
    # units - so it stays proportionate at any scale.
    trimmed = QgsGeometryGeneratorSymbolLayer.create({})

    trimmed.setSymbolType(QgsSymbol.SymbolType.Line)

    trimmed.setGeometryExpression(
        f"line_substring($geometry, length($geometry) * {_WIRE_END_TRIM},"
        f" length($geometry) * {1.0 - _WIRE_END_TRIM})"
    )

    glyph_line_symbol = QgsLineSymbol()

    glyph_line_symbol.changeSymbolLayer(0, marker_line)

    trimmed.setSubSymbol(glyph_line_symbol)

    if first:
        # Unspecified Wire Obstacle and the two ditches draw no line at
        # all, so the glyph series IS the symbol rather than an
        # addition to it - and with no line to overhang them, it keeps
        # the full geometry.
        trimmed.setGeometryExpression("$geometry")
        symbol.changeSymbolLayer(0, trimmed)
    else:
        # The glyphs go UNDERNEATH the straight lines, not on top.
        # Painted over them, each glyph's own transparent box nibbles a
        # hairline out of the line where its edge falls - visible as
        # "a slight gap in the line halfway between each triangle" on
        # the antitank wall, which the maintainer spotted. Everything
        # here is one colour, so the order is invisible otherwise.
        symbol.insertSymbolLayer(0, trimmed)

    return symbol


# The arrowhead size the whole of B5 uses, in millimetres. For B6's
# bypass family this is now a CEILING rather than a fixed size (see
# _obstacle_bypass_chevron_generator).
_CHEVRON_SIZE_MM = 6

# How much of its own arrow's length each bypass arrowhead takes up.
# The maintainer asked for the arrowhead to shrink with a small
# obstacle "upto the current size which will be the max" but named no
# proportion, so this is a placement call - the one number in this
# correction that wasn't dictated.
_BYPASS_CHEVRON_ARROW_FRACTION = 0.25


def _obstacle_bypass_chevron_generator(geometry_expression):

    """
    Shared unfilled-chevron arrowhead generator, keyed to whichever
    geometry expression the caller's own line layers already use -
    same LastVertex-needs-its-own-generator reasoning as Turn/Disrupt.

    The marker is sized in MAP UNITS, as a fraction of the arrow it
    sits on, and capped at _CHEVRON_SIZE_MM through QgsMapUnitScale -
    so it scales with the drawn obstacle and tops out at the fixed
    size the first build used: "the arrow head dimension remains same
    whether i draw a small obstacle or big... arrowhead should also
    become small if the lines are small, upto the current size which
    will be the max."
    """

    chevron_marker = QgsMarkerSymbol()

    chevron_layer = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead,
        _CHEVRON_SIZE_MM
    )

    chevron_layer.setColor(QColor(0, 0, 0, 0))

    chevron_layer.setStrokeWidth(_AREA_OUTLINE_WIDTH_MM * 1.5)

    chevron_layer.setSizeUnit(Qgis.RenderUnit.MapUnits)

    capped = QgsMapUnitScale()
    capped.maxSizeMMEnabled = True
    capped.maxSizeMM = _CHEVRON_SIZE_MM

    chevron_layer.setSizeMapUnitScale(capped)

    chevron_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        QgsProperty.fromExpression(
            "mct_obstacle_bypass_arrow_length($geometry) * "
            f"{_BYPASS_CHEVRON_ARROW_FRACTION}"
        )
    )

    _apply_obstacle_color(
        chevron_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    chevron_marker.changeSymbolLayer(0, chevron_layer)

    chevron_line_layer = QgsMarkerLineSymbolLayer(True)

    chevron_line_layer.setSubSymbol(chevron_marker)

    chevron_line_layer.setPlacements(Qgis.MarkerLinePlacement.LastVertex)

    chevron_inner = QgsLineSymbol()

    chevron_inner.changeSymbolLayer(0, chevron_line_layer)

    chevron_generator = QgsGeometryGeneratorSymbolLayer.create({})

    chevron_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    chevron_generator.setGeometryExpression(geometry_expression)

    chevron_generator.setSubSymbol(chevron_inner)

    return chevron_generator


def _obstacle_bypass_symbol(rear_expression):

    """
    Shared by the Obstacle Bypass family (270601-270603): two arrows
    (mct_obstacle_bypass_arrows, tips at PT1/PT2) plus a rear
    line/decoration that is the one thing each variant changes
    (`rear_expression`). Always BLACK per the module's own audit
    ("symbol only, size set by the user, BLACK") - the one line-
    obstacle family that overrides the green default outright rather
    than per-feature. Ordinary status-driven present/planned dash, like
    B5's own obstacle effects - nothing in the standard's own draw
    rules says otherwise.
    """

    rear_layer = QgsSimpleLineSymbolLayer()

    rear_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        rear_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    rear_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    rear_generator = QgsGeometryGeneratorSymbolLayer.create({})

    rear_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    rear_generator.setGeometryExpression(rear_expression)

    rear_inner = QgsLineSymbol()

    rear_inner.changeSymbolLayer(0, rear_layer)

    rear_generator.setSubSymbol(rear_inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, rear_generator)

    arrows_layer = QgsSimpleLineSymbolLayer()

    arrows_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        arrows_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    arrows_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    arrows_generator = QgsGeometryGeneratorSymbolLayer.create({})

    arrows_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    arrows_generator.setGeometryExpression(
        "mct_obstacle_bypass_arrows($geometry)"
    )

    arrows_inner = QgsLineSymbol()

    arrows_inner.changeSymbolLayer(0, arrows_layer)

    arrows_generator.setSubSymbol(arrows_inner)

    symbol.appendSymbolLayer(arrows_generator)

    symbol.appendSymbolLayer(
        _obstacle_bypass_chevron_generator(
            "mct_obstacle_bypass_arrows($geometry)"
        )
    )

    return symbol


def _obstacle_bypass_easy_symbol():

    return _obstacle_bypass_symbol("mct_obstacle_bypass_rear_easy($geometry)")


def _obstacle_bypass_difficult_symbol():

    return _obstacle_bypass_symbol(
        "mct_obstacle_bypass_rear_difficult($geometry)"
    )


def _obstacle_bypass_impossible_symbol():

    return _obstacle_bypass_symbol(
        "mct_obstacle_bypass_rear_impossible($geometry)"
    )


# Bridge or Gap's cross-section, all in MILLIMETRES on the page rather
# than in layer units - "keep the gap at a fixed unit rather than
# making it length of line dependent, as such it is a linear feature,
# so the width increasing with the length is not practical" (the
# maintainer, after two length-proportional versions). The channel is
# 4.56mm wide (their own number, replacing a first millimetre cut at
# 6mm: "make the bridge width 4.56mm, 6mm is too much"), which still
# clears the 9pt label - about 3.2mm - that sits inside it.
_BRIDGE_CHANNEL_MM = 4.56
_BRIDGE_HALF_CHANNEL_MM = _BRIDGE_CHANNEL_MM / 2.0
_BRIDGE_FLARE_MM = 3.0
_BRIDGE_FLARE_ANGLE_DEG = 30

# QGIS sizes an SVG marker by its WIDTH, and mct_bridge_flare_svg emits
# a viewBox exactly 2*run wide - so setting the marker to that many
# millimetres makes one viewBox unit one millimetre, which is what
# keeps the wings meeting the parallel lines exactly.
_BRIDGE_FLARE_MARKER_MM = (
    2.0 * _BRIDGE_FLARE_MM * math.cos(math.radians(_BRIDGE_FLARE_ANGLE_DEG))
)


def _bridge_flare_layer(at_end):

    """One end cap of Bridge or Gap - the pair of outward wings - as a
    rotating SVG marker on the centreline's first or last vertex."""

    marker = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(_BRIDGE_FLARE_MARKER_MM)

    # _POINT_MONO_COLOR_EXPRESSION, not _AREA_OUTLINE_COLOR_EXPRESSION:
    # this colour goes into SVG markup, so it has to be a CSS colour
    # ("rgb(0,0,0)"). The outline expression is built from color_rgb(),
    # which evaluates to a bare "0,0,0" - fine for a QGIS colour
    # property, silently invalid inside an SVG, which renders the glyph
    # as nothing at all.
    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            "mct_bridge_flare_svg({colour}, {half}, {flare}, {angle},"
            " {stroke}, {at_end})".format(
                colour=_POINT_MONO_COLOR_EXPRESSION,
                half=_BRIDGE_HALF_CHANNEL_MM,
                flare=_BRIDGE_FLARE_MM,
                angle=_BRIDGE_FLARE_ANGLE_DEG,
                stroke=_AREA_OUTLINE_WIDTH_MM,
                at_end="true" if at_end else "false",
            )
        )
    )

    marker.changeSymbolLayer(0, svg_layer)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(
        Qgis.MarkerLinePlacement.LastVertex if at_end
        else Qgis.MarkerLinePlacement.FirstVertex
    )

    # Follow the centreline's own bearing, so the wings stay square to
    # the channel however the feature was drawn.
    marker_line.setRotateSymbols(True)

    return marker_line


def _bridge_or_gap_symbol():

    """
    Bridge or Gap (271100) - rebuilt twice on 2026-08-13. First from
    the maintainer's own correction to a build that had read 4
    independently-clicked anchor points off the standard's own
    template: "user will click only two points PT1 and PT2, make two
    parallel lines and require unique designation Field T, so the gap
    between the lines will be slightly more than the text, wings or
    flares at both ends, outwards at 30deg." Then again when the
    channel was still being derived from the line's own length: "keep
    the gap at a fixed unit rather than making it length of line
    dependent, as such it is a linear feature, so the width increasing
    with the length is not practical."

    So the whole cross-section is now fixed in MILLIMETRES and none of
    it is generated geometry: mct_bridge_or_gap_geometry hands back the
    bare PT1-PT2 centreline, two line layers draw the parallel lines by
    offsetting it +/- half a channel in millimetres, and each end cap's
    pair of wings is a millimetre-sized rotating SVG marker
    (_bridge_flare_layer). A geometry generator could not do any of
    this - it works in layer units and cannot see page units.

    BLACK per the module's own audit. Field T is a SOFT requirement for
    this measure_type - see the constraint in the layer factory below.
    """

    return _parallel_channel_symbol(dashed=False, flares=True)


# Every symbol in the crossing family draws on the SAME centreline
# helper - the first two clicked points. mct_bridge_or_gap_geometry is
# named for the entry that first needed it (B6's Bridge or Gap), but
# it is the shared one now: B7's Bridge/Assault Crossing, Ford Easy,
# Ford Difficult, Lane, Ferry, Raft Site and Overhead Wire all take
# exactly the same two points.
_CROSSING_CENTRELINE = "mct_bridge_or_gap_geometry($geometry)"


def _crossing_generator(sub_symbol_layer):

    """Wrap one symbol layer in a generator keyed to the shared
    centreline. Every layer needs its own - a generator transforms
    geometry only for itself, never for its siblings."""

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, sub_symbol_layer)

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression(_CROSSING_CENTRELINE)

    generator.setSubSymbol(inner)

    return generator


# The Fords' own dashes. Qt's own DashLine baseline is [4, 2] in pen
# widths (probed, not guessed - the same baseline Mine Cluster's
# pattern is derived from); the maintainer asked for twice the dash
# length and said nothing about the gap, so only the 4 is doubled.
_FORD_DASH_MM = _AREA_OUTLINE_WIDTH_MM * 4.0 * 2.0
_FORD_GAP_MM = _AREA_OUTLINE_WIDTH_MM * 2.0


def _parallel_channel_symbol(dashed, flares, midpoint_layer=None):

    """
    The two-parallel-lines construction shared by Bridge or Gap
    (271100), Bridge/Assault Crossing (271400 + 271300), Ford Easy
    (271500) and Ford Difficult (271600).

    All four take TWO clicked points and hold the channel at a fixed
    _BRIDGE_CHANNEL_MM, per the maintainer's own ruling that a linear
    feature's cross-section must not scale with its length. The
    standard gives Bridge and the Fords a third anchor point for width
    instead; that was dropped deliberately and at their direction
    ("Fixed mm, 2 clicks"), so all four stay consistent and every one
    of them can hold its own label.

    `dashed` is the Fords' own heavy dashes; `flares` is the outward
    end-wing pair Bridge draws and the Fords do not; `midpoint_layer`
    is Ford Difficult's own zigzag.
    """

    symbol = QgsLineSymbol()

    for index, sign in enumerate((1.0, -1.0)):

        line_layer = QgsSimpleLineSymbolLayer()

        line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

        _apply_obstacle_color(
            line_layer,
            [QgsSymbolLayer.Property.StrokeColor],
            _AREA_OUTLINE_COLOR_EXPRESSION
        )

        if dashed:
            # A fixed dash, not the status-driven one: the Fords are
            # dashed in the standard's own template whatever their
            # planned/present status, the same way the roadblock state
            # variants are.
            #
            # Custom rather than Qt's own DashLine, because the
            # maintainer found that default too fine here: "dashes are
            # too small, increase length of dashes by 2 time". Same
            # traceable-baseline approach Mine Cluster already uses -
            # Qt's own default is [4, 2] in pen widths, so the dash is
            # doubled off that and the gap left alone.
            line_layer.setUseCustomDashPattern(True)
            line_layer.setCustomDashPatternUnit(Qgis.RenderUnit.Millimeters)
            line_layer.setCustomDashVector(
                [_FORD_DASH_MM, _FORD_GAP_MM]
            )
        else:
            line_layer.setDataDefinedProperty(
                QgsSymbolLayer.Property.StrokeStyle,
                QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
            )

        line_layer.setOffset(sign * _BRIDGE_HALF_CHANNEL_MM)

        line_layer.setOffsetUnit(Qgis.RenderUnit.Millimeters)

        generator = _crossing_generator(line_layer)

        if index == 0:
            symbol.changeSymbolLayer(0, generator)
        else:
            symbol.appendSymbolLayer(generator)

    if flares:

        for at_end in (False, True):

            symbol.appendSymbolLayer(
                _crossing_generator(_bridge_flare_layer(at_end))
            )

    if midpoint_layer is not None:

        symbol.appendSymbolLayer(_crossing_generator(midpoint_layer))

    return symbol


def _bridge_symbol():

    """
    Bridge (271400) AND Assault Crossing (271300) - one symbol for
    both, at the maintainer's own instruction: "assault crossing, merge
    it with the bridge i.e. just add the heading since it is same as
    bridge." Their templates really are identical, and once Bridge lost
    its third anchor point (see _parallel_channel_symbol) so are their
    constructions.

    Geometrically this is also the same as B6's Bridge or Gap (271100),
    which stays a separate entry because it means a different thing -
    a gap in a minefield rather than a water crossing - and defaults to
    a different colour.
    """

    return _parallel_channel_symbol(dashed=False, flares=True)


# Ford Difficult's own zigzag, crossing the channel at its midpoint.
# Its length spans the channel and overhangs it at both ends, which is
# what makes it read as crossing rather than sitting inside.
_FORD_ZIGZAG_MM = _BRIDGE_CHANNEL_MM * 2.0
_FORD_ZIGZAG_AMPLITUDE_MM = 1.1
_FORD_ZIGZAG_TEETH = 4


def _ford_zigzag_layer():

    """Ford Difficult's own zigzag as a rotating SVG marker at the
    centreline's midpoint - millimetre-sized like everything else in
    this family, so it doesn't grow with the ford's own length."""

    marker = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(_FORD_ZIGZAG_MM)

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            "mct_ford_zigzag_svg({colour}, {length}, {amplitude}, {teeth},"
            " {stroke})".format(
                colour=_POINT_MONO_COLOR_EXPRESSION,
                length=_FORD_ZIGZAG_MM,
                amplitude=_FORD_ZIGZAG_AMPLITUDE_MM,
                teeth=_FORD_ZIGZAG_TEETH,
                stroke=_AREA_OUTLINE_WIDTH_MM,
            )
        )
    )

    marker.changeSymbolLayer(0, svg_layer)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(Qgis.MarkerLinePlacement.CentralPoint)

    marker_line.setRotateSymbols(True)

    return marker_line


def _ford_easy_symbol():

    """Ford Easy (271500) - the channel drawn as two dashed lines, no
    end wings."""

    return _parallel_channel_symbol(dashed=True, flares=False)


def _ford_difficult_symbol():

    """Ford Difficult (271600) - Ford Easy plus a zigzag across the
    channel at its own midpoint, which is the only thing the standard
    varies between the two."""

    return _parallel_channel_symbol(
        dashed=True, flares=False, midpoint_layer=_ford_zigzag_layer()
    )


# Lane/Ferry/Raft Site all say the symbol "varies only in length", so
# their end decorations are a FIXED size rather than a proportion -
# the same principle the channel above follows.
_CROSSING_ARROW_MM = 5.0


def _crossing_end_marker_layer(at_end, filled):

    """
    The end decoration shared by Lane/Raft Site (290600 + 290800) and
    Ferry (290700).

    **The open ones are not arrowheads** - they OPEN outward, vertex on
    the line's own end and both arms splaying away from it, which the
    maintainer drew as `>-----<`. The first build had them the other
    way round (vertex off the end, arms trailing back, i.e. an arrow
    pointing out) and it was wrong: the template's own shape is a "Y"
    at each end, and its draw rules say only that "the lines of the
    arrowhead will form an acute angle", never that it points anywhere.

    QGIS rotates a marker to the LINE's direction at both ends rather
    than reversing it at the start, and its own ArrowHead glyph points
    ALONG that direction - so getting `>-----<` means spinning the LAST
    vertex by 180, not the first. Ferry keeps a real arrow at each end
    ("the arrowheads will be filled-in versions of a common
    arrowhead"), so its heads point outward the ordinary way.
    """

    marker = QgsMarkerSymbol()

    shape = (
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHeadFilled if filled
        else QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead
    )

    head = QgsSimpleMarkerSymbolLayer(shape, _CROSSING_ARROW_MM)

    if filled:
        _apply_obstacle_color(
            head,
            [
                QgsSymbolLayer.Property.FillColor,
                QgsSymbolLayer.Property.StrokeColor,
            ],
            _AREA_OUTLINE_COLOR_EXPRESSION
        )
    else:
        head.setColor(QColor(0, 0, 0, 0))
        head.setStrokeWidth(_AREA_OUTLINE_WIDTH_MM * 1.5)
        _apply_obstacle_color(
            head,
            [QgsSymbolLayer.Property.StrokeColor],
            _AREA_OUTLINE_COLOR_EXPRESSION
        )

    marker.changeSymbolLayer(0, head)

    # Ferry's filled heads point outward the ordinary way (spin the
    # START); the open ones open outward, which is the opposite (spin
    # the END). See this function's own docstring.
    if filled != at_end:
        marker.setAngle(180)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(
        Qgis.MarkerLinePlacement.LastVertex if at_end
        else Qgis.MarkerLinePlacement.FirstVertex
    )

    marker_line.setRotateSymbols(True)

    return marker_line


def _shaft_with_end_arrows_symbol(filled):

    """
    Lane/Raft Site (290600 + 290800) and Ferry (290700) - a plain shaft
    between the two clicked points with an end decoration at each end.

    **Lane and Raft Site are ONE entry**, not two. Their templates are
    identical and their draw rules are word for word identical; the
    only difference in the whole table is that Lane carries the W/W1
    width amplifiers. They were built as two entries sharing a builder
    at first; the maintainer then folded them together the same way as
    Bridge and Assault Crossing - "since same construction, put them in
    one option itself like bridge/assault crossing". The designation
    stays optional either way ("the unique designation is a choice by
    the user so it can be filled or not"), so the merged entry loses
    nothing Raft Site had.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, _crossing_generator(line_layer))

    for at_end in (False, True):

        symbol.appendSymbolLayer(
            _crossing_generator(
                _crossing_end_marker_layer(at_end, filled)
            )
        )

    return symbol


def _lane_symbol():

    """Lane AND Raft Site - see _shaft_with_end_arrows_symbol for why
    they are one entry."""

    return _shaft_with_end_arrows_symbol(filled=False)


def _ferry_symbol():

    return _shaft_with_end_arrows_symbol(filled=True)


# Overhead Wire's own pylons. The standard draws a transmission tower
# at each end and numbers nothing about it, so no glyph is invented
# here - one is reused from the SIDC vocabulary, which the maintainer's
# own question surfaced ("is there any sidc for tower?"). Their pick
# after seeing both candidates was Land Installation's
# Telecommunications Tower (121203) over this table's own Tower High
# (282002) - it is the pylon this symbol actually means.
#
# NOTE the symbol set travels with the entity: 121203 is a
# land_installation code, not a control_measure one, so build_sidc has
# to be told which set to use or it produces a valid-looking SIDC for
# the wrong symbol.
_OVERHEAD_WIRE_TOWER_ENTITY = "telecommunications_tower"
_OVERHEAD_WIRE_TOWER_SYMBOL_SET = "land_installation"

# The same size the Points layer draws its own tower icons at, rather
# than a number of this symbol's own.
_OVERHEAD_WIRE_TOWER_MM = _POINTS_DEFAULT_MARKER_SIZE_MM


def _overhead_wire_tower_layer():

    """
    A pylon on EVERY vertex of the wire, not just its two ends - "the
    tower should be marked at every point user clicks... a
    multi-segment line will have a tower at every point/vertex", which
    is also what the standard's own draw rules say ("additional points
    can be defined to extend the line") and what its example picture
    shows: a three-tower run with a bend at the middle pylon.
    """

    marker = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(_OVERHEAD_WIRE_TOWER_MM)

    # Affiliation and status are FIXED literals, NOT this layer's own
    # fields. That was the bug in the first cut: the Lines layer's
    # affiliation vocabulary includes "unspecified" (and defaults to
    # it), which build_sidc rejects outright - it returns an error
    # STRING rather than a SIDC, so every tower rendered as garbage.
    # The glyph is structural and takes its colour from the obstacle
    # colour expression anyway, so it has no business reading an
    # affiliation. Same fixed-literal pattern the mine glyphs already
    # use (_MINE_GLYPH_AFFILIATION).
    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            # Trailing `false` drops milsymbol's own frame: 121203 is
            # a Land Installation code and so renders framed, and a
            # framed installation box at every vertex is not the bare
            # pylon Table H-XIX's own Overhead Wire template draws.
            "mct_sidc_svg(mct_build_sidc("
            " '{affiliation}', '{entity}', '{symbol_set}',"
            " 'unspecified', 'present', false), '', '',"
            " {colour}, 1.0, false)".format(
                affiliation=_MINE_GLYPH_AFFILIATION,
                entity=_OVERHEAD_WIRE_TOWER_ENTITY,
                symbol_set=_OVERHEAD_WIRE_TOWER_SYMBOL_SET,
                colour=_POINT_MONO_COLOR_EXPRESSION,
            )
        )
    )

    marker.changeSymbolLayer(0, svg_layer)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(Qgis.MarkerLinePlacement.Vertex)

    # Towers stand upright regardless of which way the wire runs.
    marker_line.setRotateSymbols(False)

    return marker_line


def _overhead_wire_symbol():

    """
    Overhead Wire (282003) - a plain line with a pylon on every vertex.
    The one B7 entry that is a LINE despite its 28xxxx code, which is
    the trap this module's own docstring opens with.

    Unlike the rest of the crossing family this draws the feature's OWN
    geometry rather than the first-two-points centreline: the standard
    lets this one run over as many anchor points as the user wants, so
    trimming it would throw away every vertex past the second.
    """

    symbol = QgsLineSymbol()

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    symbol.changeSymbolLayer(0, line_layer)

    symbol.appendSymbolLayer(_overhead_wire_tower_layer())

    return symbol


def _roadblock_line_layer(dashed):

    layer = QgsSimpleLineSymbolLayer()

    layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    if dashed:
        layer.setPenStyle(Qt.PenStyle.DashLine)

    return layer


def _roadblock_symbol(main_dashed, parallel_dashed):

    """
    Shared by Planned (271201, both lines dashed), Explosives State of
    Readiness 1/Safe (271202, one line solid, one dashed) and
    Explosives State of Readiness 2/Passable (271203, both solid) - the
    standard's own three "state" variants of the same two-line
    construction (mct_roadblock_main_line / mct_roadblock_parallel_line:
    "points 1 and 2 determine the centerline... point 3 determines its
    width"). Fixed dash per variant, not status-driven - the variant
    itself already encodes a real-world readiness state, not present/
    planned. Roadblock Complete (271204) adds a second, rotated pair
    (see _roadblock_complete_symbol).

    **No arrowheads anywhere in this family.** The first build gave
    every variant one, reading the "PT 1 ->" / "PT 2 ->" / "PT 3 ->"
    arrows in the standard's own TEMPLATE column as drawn geometry.
    They are annotation pointers - the table uses them throughout to
    label anchor points - and the EXAMPLE column, which renders the
    real symbol, shows plain lines with no arrowhead at all. This is
    the same misreading that put an invented tick on Light Line back
    in H2; the maintainer caught both.
    """

    symbol = QgsLineSymbol()

    main_generator = QgsGeometryGeneratorSymbolLayer.create({})

    main_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    main_generator.setGeometryExpression("mct_roadblock_main_line($geometry)")

    main_inner = QgsLineSymbol()

    main_inner.changeSymbolLayer(0, _roadblock_line_layer(main_dashed))

    main_generator.setSubSymbol(main_inner)

    symbol.changeSymbolLayer(0, main_generator)

    parallel_generator = QgsGeometryGeneratorSymbolLayer.create({})

    parallel_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    parallel_generator.setGeometryExpression(
        "mct_roadblock_parallel_line($geometry)"
    )

    parallel_inner = QgsLineSymbol()

    parallel_inner.changeSymbolLayer(
        0, _roadblock_line_layer(parallel_dashed)
    )

    parallel_generator.setSubSymbol(parallel_inner)

    symbol.appendSymbolLayer(parallel_generator)

    return symbol


def _roadblock_planned_symbol():

    return _roadblock_symbol(main_dashed=True, parallel_dashed=True)


def _roadblock_readiness_1_symbol():

    return _roadblock_symbol(main_dashed=False, parallel_dashed=True)


def _roadblock_readiness_2_symbol():

    return _roadblock_symbol(main_dashed=False, parallel_dashed=False)


def _roadblock_complete_symbol():

    """
    Roadblock Complete/Executed (271204) - the ordinary roadblock pair
    (main line + parallel line, both solid) PLUS that same pair
    rotated 50 degrees about its own centre, so the two pairs cross
    (mct_roadblock_complete_geometry). No arrowheads, for the same
    reason as the rest of the family - see _roadblock_symbol's own
    docstring. Read off the standard's own picture rather than a
    numbered draw rule (this entry is ASSUMED, not CONFIRMED, in the
    module's own audit).
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_obstacle_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor],
        _AREA_OUTLINE_COLOR_EXPRESSION
    )

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression("mct_roadblock_complete_geometry($geometry)")

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line_layer)

    generator.setSubSymbol(inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, generator)

    return symbol


# B4 is now fully built (17 of 17) - all of Table H-XIX's own line
# obstacles this project's audit confirmed buildable.
#
# Mine Cluster and Trip Wire are neither the wire family nor the
# toothed family, so each gets its own small dict rather than folding
# into either - fixed constructions (a generated arc, a generated
# hooked path), nothing repeating along a line.
MINE_CLUSTER_MEASURE_TYPE_LABELS = {
    "mine_cluster": "Mine Cluster",
}

MINE_CLUSTER_MEASURE_TYPE_CODES = {
    "mine_cluster": "290400",
}

TRIP_WIRE_MEASURE_TYPE_LABELS = {
    "trip_wire": "Trip Wire",
}

TRIP_WIRE_MEASURE_TYPE_CODES = {
    "trip_wire": "290500",
}

# B5 - obstacle effects, all 4 now built (270501-270504). Disrupt and
# Fix were held back at first (their own draw rules give no numeric
# ratio for the shape shown, only a picture) until the maintainer gave
# their own exact construction for each - see mct_disrupt_geometry's
# and mct_fix_geometry's own docstrings for the dictated wording.
B5_EFFECTS_MEASURE_TYPE_LABELS = {
    "block": "Block",
    "disrupt": "Disrupt",
    "fix": "Fix",
    "turn": "Turn",
}

B5_EFFECTS_MEASURE_TYPE_CODES = {
    "block": "270501",
    "disrupt": "270502",
    "fix": "270503",
    "turn": "270504",
}

# B6 - bypasses and roadblocks, all 8 now built (270601-270603,
# 271100, 271201-271204). The Obstacle Bypass family is BLACK, not
# green - the module's own audit flagged this before any of these were
# built. Roadblock Complete (271204) is ASSUMED, not CONFIRMED - its
# own construction was read off the standard's own picture rather than
# a numbered draw rule (see mct_roadblock_complete_geometry's own
# docstring).
B6_ROADBLOCKS_MEASURE_TYPE_LABELS = {
    "obstacle_bypass_easy": "Obstacle Bypass Easy",
    "obstacle_bypass_difficult": "Obstacle Bypass Difficult",
    "obstacle_bypass_impossible": "Obstacle Bypass Impossible",
    "bridge_or_gap": "Bridge or Gap",
    "roadblock_planned": "Roadblock - Planned",
    "roadblock_readiness_1": "Roadblock - Explosives State of Readiness 1 (Safe)",
    "roadblock_readiness_2": (
        "Roadblock - Explosives State of Readiness 2 (Passable)"
    ),
    "roadblock_complete": "Roadblock Complete (Executed)",
}

B6_ROADBLOCKS_MEASURE_TYPE_CODES = {
    "obstacle_bypass_easy": "270601",
    "obstacle_bypass_difficult": "270602",
    "obstacle_bypass_impossible": "270603",
    "bridge_or_gap": "271100",
    "roadblock_planned": "271201",
    "roadblock_readiness_1": "271202",
    "roadblock_readiness_2": "271203",
    "roadblock_complete": "271204",
}

# B7 - water crossing sites and the last of Table H-XIX's own lines,
# closing the table out.
#
# TWO deliberate merges here, both confirmed with the maintainer rather
# than assumed:
#
# - **Bridge (271400) and Assault Crossing (271300) are ONE entry** -
#   "assault crossing, merge it with the bridge i.e. just add the
#   heading since it is same as bridge". Their templates are identical
#   and, once Bridge lost its third anchor point, so are their
#   constructions. This is the same one-measure-type-covers-two-codes
#   shape the minefield family already uses (see
#   MINEFIELD_MEASURE_TYPE_CODES), and _B7_MERGED_CODES below records
#   the code that would otherwise look missing from the build.
#
# - **Lane (290600) and Raft Site (290800) are ONE entry** - their
#   templates AND their draw rules are word for word the same, the only
#   difference in the whole table being that Lane carries the W/W1
#   width amplifiers. They shipped as two entries sharing a builder at
#   first; the maintainer folded them together on review, for the same
#   reason as Bridge/Assault Crossing - "since same construction, put
#   them in one option itself like bridge/assault crossing". The
#   designation is optional on this layer anyway ("the unique
#   designation is a choice by the user so it can be filled or not"),
#   so nothing Raft Site had is lost by merging.
B7_CROSSINGS_MEASURE_TYPE_LABELS = {
    "bridge": "Bridge / Assault Crossing",
    "ford_easy": "Ford - Easy",
    "ford_difficult": "Ford - Difficult",
    "lane": "Lane / Raft Site",
    "ferry": "Ferry",
    "overhead_wire": "Overhead Wire",
}

B7_CROSSINGS_MEASURE_TYPE_CODES = {
    "bridge": "271400",
    "ford_easy": "271500",
    "ford_difficult": "271600",
    "lane": "290600",
    "ferry": "290700",
    "overhead_wire": "282003",
}

# Codes a measure type covers BEYOND its own primary one. Kept
# explicit so a coverage check can tell "deliberately merged" apart
# from "quietly dropped" - the failure this module's own audit tests
# are built to catch.
_B7_MERGED_CODES = {
    "bridge": ("271300",),
    "lane": ("290800",),
}

LINE_MEASURE_TYPE_LABELS = dict(WIRE_MEASURE_TYPE_LABELS)
LINE_MEASURE_TYPE_LABELS.update(TOOTHED_MEASURE_TYPE_LABELS)
LINE_MEASURE_TYPE_LABELS.update(MINE_CLUSTER_MEASURE_TYPE_LABELS)
LINE_MEASURE_TYPE_LABELS.update(TRIP_WIRE_MEASURE_TYPE_LABELS)
LINE_MEASURE_TYPE_LABELS.update(B5_EFFECTS_MEASURE_TYPE_LABELS)
LINE_MEASURE_TYPE_LABELS.update(B6_ROADBLOCKS_MEASURE_TYPE_LABELS)
LINE_MEASURE_TYPE_LABELS.update(B7_CROSSINGS_MEASURE_TYPE_LABELS)

LINE_MEASURE_TYPE_CODES = dict(WIRE_MEASURE_TYPE_CODES)
LINE_MEASURE_TYPE_CODES.update(TOOTHED_MEASURE_TYPE_CODES)
LINE_MEASURE_TYPE_CODES.update(MINE_CLUSTER_MEASURE_TYPE_CODES)
LINE_MEASURE_TYPE_CODES.update(TRIP_WIRE_MEASURE_TYPE_CODES)
LINE_MEASURE_TYPE_CODES.update(B5_EFFECTS_MEASURE_TYPE_CODES)
LINE_MEASURE_TYPE_CODES.update(B6_ROADBLOCKS_MEASURE_TYPE_CODES)
LINE_MEASURE_TYPE_CODES.update(B7_CROSSINGS_MEASURE_TYPE_CODES)

_LINE_SYMBOL_BUILDERS = {
    measure_type: (
        lambda measure_type=measure_type: _wire_obstacle_symbol(measure_type)
    )
    for measure_type in LINE_MEASURE_TYPE_LABELS
    if measure_type not in (
        "abatis", "antitank_ditch_reinforced", "mine_cluster", "trip_wire",
        "block", "disrupt", "fix", "turn",
        "obstacle_bypass_easy", "obstacle_bypass_difficult",
        "obstacle_bypass_impossible", "bridge_or_gap", "roadblock_planned",
        "roadblock_readiness_1", "roadblock_readiness_2",
        "roadblock_complete",
        "bridge", "ford_easy", "ford_difficult", "lane", "ferry",
        "overhead_wire",
    )
}

_LINE_SYMBOL_BUILDERS["abatis"] = _abatis_symbol
_LINE_SYMBOL_BUILDERS["antitank_ditch_reinforced"] = (
    _antitank_ditch_reinforced_symbol
)
_LINE_SYMBOL_BUILDERS["mine_cluster"] = _mine_cluster_symbol
_LINE_SYMBOL_BUILDERS["trip_wire"] = _trip_wire_symbol
_LINE_SYMBOL_BUILDERS["block"] = _block_symbol
_LINE_SYMBOL_BUILDERS["disrupt"] = _disrupt_symbol
_LINE_SYMBOL_BUILDERS["fix"] = _fix_symbol
_LINE_SYMBOL_BUILDERS["turn"] = _turn_symbol
_LINE_SYMBOL_BUILDERS["obstacle_bypass_easy"] = _obstacle_bypass_easy_symbol
_LINE_SYMBOL_BUILDERS["obstacle_bypass_difficult"] = (
    _obstacle_bypass_difficult_symbol
)
_LINE_SYMBOL_BUILDERS["obstacle_bypass_impossible"] = (
    _obstacle_bypass_impossible_symbol
)
_LINE_SYMBOL_BUILDERS["bridge_or_gap"] = _bridge_or_gap_symbol
_LINE_SYMBOL_BUILDERS["roadblock_planned"] = _roadblock_planned_symbol
_LINE_SYMBOL_BUILDERS["roadblock_readiness_1"] = _roadblock_readiness_1_symbol
_LINE_SYMBOL_BUILDERS["roadblock_readiness_2"] = _roadblock_readiness_2_symbol
_LINE_SYMBOL_BUILDERS["roadblock_complete"] = _roadblock_complete_symbol
_LINE_SYMBOL_BUILDERS["bridge"] = _bridge_symbol
_LINE_SYMBOL_BUILDERS["ford_easy"] = _ford_easy_symbol
_LINE_SYMBOL_BUILDERS["ford_difficult"] = _ford_difficult_symbol
_LINE_SYMBOL_BUILDERS["lane"] = _lane_symbol
_LINE_SYMBOL_BUILDERS["ferry"] = _ferry_symbol
_LINE_SYMBOL_BUILDERS["overhead_wire"] = _overhead_wire_symbol


def _line_default_colour_expression():

    cases = []

    for measure_type, code in LINE_MEASURE_TYPE_CODES.items():

        entry = TABLE_H_XIX_INVENTORY[code]

        colour = BLACK if entry["colour"] == BLACK else GREEN

        cases.append(
            f"WHEN \"measure_type\" = '{measure_type}' THEN '{colour}'"
        )

    return "CASE " + " ".join(cases) + f" ELSE '{GREEN}' END"


# Obstacle Line and Bridge or Gap are the line obstacles carrying
# Field T. Obstacle Line's own audit "OT" applies: outline green, TEXT
# BLACK - Bridge or Gap is BLACK outright, so it needs no separate
# colour case in _configure_lines_labeling below (the label already
# reuses the one fixed black).
_OBSTACLE_LINE_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" IN ("
    "'obstacle_line', 'bridge_or_gap', 'bridge', 'ford_easy',"
    " 'ford_difficult', 'lane')"
    " THEN upper(coalesce(\"unique_designation\", '')) ELSE '' END"
)

# Everything that draws a channel puts its label INSIDE it; Obstacle
# Line and Lane keep theirs below. Lane's own W/W1 amplifiers are what
# distinguish it from Raft Site, which draws identically and carries no
# label at all.
_CHANNEL_LABEL_TYPES = (
    "bridge_or_gap", "bridge", "ford_easy", "ford_difficult",
)


# Obstacle Line's label sits BELOW its own line; Bridge or Gap's sits
# ON it - which puts it inside the channel between the two parallel
# lines, since the clicked geometry the label follows is the symbol's
# own centreline ("the text is below the line - it should be within
# the parallel lines"). Data-defined rather than two labelling rules,
# because everything else about the two is identical.
#
# The tokens are QGIS's own two-letter codes, NOT the readable names -
# this property's help text spells them out as
# "OL=On line|AL=Above line|BL=Below line|LO=Respect line
# orientation". Passing 'on_line' is silently accepted and drops the
# label entirely, which is how the first cut of this shipped a Bridge
# or Gap with no designation at all.
_LINE_PLACEMENT_FLAGS_EXPRESSION = (
    "CASE WHEN \"measure_type\" IN ("
    + ", ".join(f"'{t}'" for t in _CHANNEL_LABEL_TYPES)
    + ") THEN 'OL' ELSE 'BL' END"
)


def _configure_lines_labeling(layer):

    settings = _build_pal_layer_settings(
        layer,
        Qgis.LabelPlacement.Line,
        _OBSTACLE_LINE_LABEL_EXPRESSION,
        line_placement_flags=Qgis.LabelLinePlacementFlag.BelowLine
    )

    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Color,
        QgsProperty.fromExpression("color_rgb(0, 0, 0)")
    )

    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.LinePlacementOptions,
        QgsProperty.fromExpression(_LINE_PLACEMENT_FLAGS_EXPRESSION)
    )

    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))

    layer.setLabelsEnabled(True)


def create_obstacle_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    Table H-XIX's own line obstacles - batch B4 (all 17), batch B5's
    obstacle effects (all 4) and batch B6's bypasses/roadblocks (all
    8), sharing this one layer.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(f"LineString?crs={crs.authid()}", name, "memory")

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("colour", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
            QgsField("length_km", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    fields = layer.fields()

    layer.setEditorWidgetSetup(
        fields.indexOf("measure_type"),
        QgsEditorWidgetSetup(
            "ValueMap", {"map": _value_map(LINE_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        fields.indexOf("colour"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(COLOUR_LABELS)})
    )

    # Hand-drawn, so the lines/areas affiliation vocabulary is the
    # right one here - and nothing on this layer feeds build_sidc(),
    # unlike the minefield boxes, whose mine glyphs do.
    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setDefaultValueDefinition(
        fields.indexOf("measure_type"),
        QgsDefaultValue("'unspecified_wire_obstacle'")
    )

    # Derived from TABLE_H_XIX_INVENTORY, like the Areas layer's own -
    # this batch is another with MIXED defaults (the antitank wall and
    # the reinforced ditch are black in the maintainer's audit, the
    # rest green).
    layer.setDefaultValueDefinition(
        fields.indexOf("colour"),
        QgsDefaultValue(_line_default_colour_expression(), True)
    )

    layer.setDefaultValueDefinition(
        fields.indexOf("length_km"),
        QgsDefaultValue("mct_length_km($geometry)", True)
    )

    # "require unique designation Field T" - Bridge or Gap is the one
    # line obstacle where Field T is prompted for rather than purely
    # freeform-optional (every other Field T entry, e.g. Obstacle Line,
    # stays optional).
    #
    # SOFT, not hard: "you have made field T mandatory, not required"
    # (the maintainer, correcting the first cut). A hard constraint
    # BLOCKS the save outright, which is the right strength for the
    # Maritime Points layer's group/entity pair - a mismatch there
    # renders the wrong symbol - but wrong here, where a missing
    # designation only means an unlabelled bridge. Soft flags the
    # field in the form and still lets the feature be saved.
    designation_idx = fields.indexOf("unique_designation")

    layer.setConstraintExpression(
        designation_idx,
        "\"measure_type\" != 'bridge_or_gap'"
        " OR (unique_designation IS NOT NULL AND unique_designation != '')",
        "Bridge or Gap should carry a unique designation (Field T)."
    )

    layer.setFieldConstraint(
        designation_idx,
        QgsFieldConstraints.Constraint.ConstraintExpression,
        QgsFieldConstraints.ConstraintStrength.ConstraintStrengthSoft
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _LINE_SYMBOL_BUILDERS)
    )

    _configure_lines_labeling(layer)

    return layer


def add_obstacle_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_obstacle_control_measures_lines_layer
    )
