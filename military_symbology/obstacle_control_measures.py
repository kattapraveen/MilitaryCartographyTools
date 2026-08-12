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

1. **Mine Cluster (290400) and Trip Wire (290500)** are listed in the
   audit as "symbol/point", but their own templates require TWO and
   THREE anchor points respectively ("points 1 and 2 define the corners
   of the symbol"). They are held here as LINEs on that basis - fixed
   glyphs whose size and orientation come from clicked points. If the
   intent was a single-click fixed-size symbol instead, B4 changes.
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

from qgis.core import QgsProperty


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
    # Three anchor points per its own template, so likewise a line.
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
