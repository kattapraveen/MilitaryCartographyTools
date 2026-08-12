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

**Three geometry findings that contradicted the initial batch plan**,
all from reading template pictures rather than the PDF's text layer
(which is badly OCR-mangled throughout this table - "Obstacle Fl'ee
Zone", "Cnters and Blown Bridges", "Une Cluste1·"):

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


# Geometry classes used below.
AREA = "area"
LINE = "line"
POINT = "point"
PARENT = "parent"          # a heading row; template column reads "N/A"

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

# code -> (name, geometry, batch, verified)
#
# Names come from the template pictures where the PDF's text layer is
# mangled. Two the text layer got outright wrong, worth flagging since
# a later reader would otherwise trust them: 271500 is "Ford Easy", not
# "Ferry" (the OCR renders it "~~ry"), and 290700 is the actual Ferry.
TABLE_H_XIX_INVENTORY = {
    # -- Obstacle zones (serrated boundary; Restricted adds a hatch) --
    "270100": ("Obstacle Belt", AREA, B2_ZONES, CONFIRMED),
    "270200": ("Obstacle Zone", AREA, B2_ZONES, CONFIRMED),
    "270300": ("Obstacle Free Zone", AREA, B2_ZONES, CONFIRMED),
    "270400": ("Obstacle Restricted Zone", AREA, B2_ZONES, CONFIRMED),
    # -- Obstacle effects --
    "270500": ("Obstacle Effects", PARENT, B5_EFFECTS, CONFIRMED),
    "270501": ("Block", LINE, B5_EFFECTS, CONFIRMED),
    "270502": ("Disrupt", LINE, B5_EFFECTS, CONFIRMED),
    "270503": ("Fix", LINE, B5_EFFECTS, ASSUMED),
    "270504": ("Turn", LINE, B5_EFFECTS, ASSUMED),
    # -- Obstacle bypass --
    "270600": ("Obstacle Bypass", PARENT, B6_ROADBLOCKS, ASSUMED),
    "270601": ("Obstacle Bypass Easy", LINE, B6_ROADBLOCKS, CONFIRMED),
    "270602": ("Obstacle Bypass Difficult", LINE, B6_ROADBLOCKS, CONFIRMED),
    "270603": ("Obstacle Bypass Impossible", LINE, B6_ROADBLOCKS, CONFIRMED),
    # -- Minefields (mostly fixed-size POINTS, not areas) --
    "270700": ("Minefield", PARENT, B3_MINEFIELDS, ASSUMED),
    "270701": ("Completed Minefield", POINT, B3_MINEFIELDS, CONFIRMED),
    "270702": ("Planned Minefield", POINT, B3_MINEFIELDS, CONFIRMED),
    "270703": ("Known Enemy Minefield", POINT, B3_MINEFIELDS, CONFIRMED),
    "270704": ("Suspected or Templated Enemy Minefield", POINT,
               B3_MINEFIELDS, CONFIRMED),
    "270705": ("Dummy Minefield", POINT, B3_MINEFIELDS, CONFIRMED),
    "270706": ("Dummy Minefield, Dynamic", AREA, B3_MINEFIELDS, CONFIRMED),
    "270707": ("Dynamic Depiction", AREA, B3_MINEFIELDS, CONFIRMED),
    # -- Mined areas (repeating "M" glyphs around the perimeter) --
    "270800": ("Mined Area", AREA, B2_ZONES, CONFIRMED),
    "270900": ("Decoy Mined Area", AREA, B2_ZONES, CONFIRMED),
    "270901": ("Decoy Mined Area, Fenced", AREA, B2_ZONES, CONFIRMED),
    "271000": ("Unexploded Explosive Ordnance (UXO) Area", AREA,
               B2_ZONES, CONFIRMED),
    # -- Gaps, roadblocks, craters --
    "271100": ("Bridge or Gap", LINE, B6_ROADBLOCKS, CONFIRMED),
    "271200": ("Roadblocks, Craters and Blown Bridges", PARENT,
               B6_ROADBLOCKS, CONFIRMED),
    "271201": ("Planned", LINE, B6_ROADBLOCKS, CONFIRMED),
    "271202": ("Explosives, State of Readiness 1 (Safe)", LINE,
               B6_ROADBLOCKS, CONFIRMED),
    "271203": ("Explosives, State of Readiness 2 (Armed)", LINE,
               B6_ROADBLOCKS, ASSUMED),
    "271204": ("Roadblock Complete (Executed)", LINE, B6_ROADBLOCKS, ASSUMED),
    # -- Water crossing sites --
    "271300": ("Assault Crossing", LINE, B7_CROSSINGS, CONFIRMED),
    "271400": ("Bridge", LINE, B7_CROSSINGS, CONFIRMED),
    "271500": ("Ford Easy", LINE, B7_CROSSINGS, CONFIRMED),
    "271600": ("Ford Difficult", LINE, B7_CROSSINGS, CONFIRMED),
    # -- Protection points --
    "280000": ("Protection Points", PARENT, B1_POINTS, CONFIRMED),
    "280100": ("Abatis", POINT, B1_POINTS, CONFIRMED),
    "280200": ("Antipersonnel Mine", POINT, B1_POINTS, CONFIRMED),
    "280201": ("Antipersonnel Mine with Directional Effects", POINT,
               B1_POINTS, ASSUMED),
    "280300": ("Antitank Mine", POINT, B1_POINTS, ASSUMED),
    "280400": ("Antitank Mine with Anti-handling Device", POINT,
               B1_POINTS, ASSUMED),
    "280500": ("Wide Area Antitank Mine", POINT, B1_POINTS, ASSUMED),
    "280600": ("Unspecified Mine", POINT, B1_POINTS, ASSUMED),
    "280700": ("Booby Trap", POINT, B1_POINTS, ASSUMED),
    "280800": ("Engineer Regulating Point", POINT, B1_POINTS, ASSUMED),
    "281900": ("Tetrahedrons, Dragons Teeth and Other Similar Obstacles",
               PARENT, B1_POINTS, CONFIRMED),
    "281901": ("Fixed and Prefabricated", POINT, B1_POINTS, ASSUMED),
    "281902": ("Movable", POINT, B1_POINTS, ASSUMED),
    "281903": ("Movable and Prefabricated", POINT, B1_POINTS, ASSUMED),
    "282000": ("Vertical Obstructions", PARENT, B1_POINTS, CONFIRMED),
    "282001": ("Tower, Low", POINT, B1_POINTS, ASSUMED),
    "282002": ("Tower, High", POINT, B1_POINTS, ASSUMED),
    # The one 28xxxx code that is NOT a point - see module docstring.
    "282003": ("Overhead Wire", LINE, B7_CROSSINGS, CONFIRMED),
    # -- Protection lines --
    "290000": ("Protection Lines", PARENT, B4_WIRE, CONFIRMED),
    "290100": ("Obstacle Line", LINE, B4_WIRE, ASSUMED),
    "290200": ("Antitank Obstacles", PARENT, B4_WIRE, ASSUMED),
    "290201": ("Antitank Ditch - Under Construction", LINE, B4_WIRE, ASSUMED),
    "290202": ("Antitank Ditch - Completed", LINE, B4_WIRE, ASSUMED),
    "290203": ("Antitank Ditch Reinforced with Antitank Mines", LINE,
               B4_WIRE, ASSUMED),
    "290204": ("Antitank Wall", LINE, B4_WIRE, ASSUMED),
    "290300": ("Wire Obstacles", PARENT, B4_WIRE, ASSUMED),
    "290301": ("Unspecified", LINE, B4_WIRE, ASSUMED),
    "290302": ("Single Fence", LINE, B4_WIRE, ASSUMED),
    "290303": ("Double Fence", LINE, B4_WIRE, ASSUMED),
    "290304": ("Double Apron Fence", LINE, B4_WIRE, ASSUMED),
    "290305": ("Low Wire Fence", LINE, B4_WIRE, ASSUMED),
    "290306": ("High Wire Fence", LINE, B4_WIRE, ASSUMED),
    "290307": ("Single Concertina", LINE, B4_WIRE, ASSUMED),
    "290308": ("Double Strand Concertina", LINE, B4_WIRE, ASSUMED),
    "290309": ("Triple Strand Concertina", LINE, B4_WIRE, ASSUMED),
    "290400": ("Line Cluster", LINE, B7_CROSSINGS, ASSUMED),
    "290500": ("Trip Wire", LINE, B7_CROSSINGS, ASSUMED),
    "290600": ("Lane", LINE, B7_CROSSINGS, ASSUMED),
    "290700": ("Ferry", LINE, B7_CROSSINGS, ASSUMED),
    "290800": ("Raft Site", LINE, B7_CROSSINGS, CONFIRMED),
}


def inventory_for_batch(batch):

    """
    The buildable entries a given batch owns - parent heading rows
    excluded, since they have no template to draw.
    """

    return {
        code: entry
        for code, entry in TABLE_H_XIX_INVENTORY.items()
        if entry[2] == batch and entry[1] != PARENT
    }


def buildable_inventory():

    return {
        code: entry
        for code, entry in TABLE_H_XIX_INVENTORY.items()
        if entry[1] != PARENT
    }
