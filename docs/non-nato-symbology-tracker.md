# Non-NATO Symbology — Rules Record

**Frozen reference, not an active checklist.** This started as a
rule-by-rule tracker (with a companion interactive HTML checklist,
since dropped once its job was done - the rules that mattered are
captured here). From this point on, remaining rules are worked out
directly during implementation rather than specified upfront; this
file stays as the record of what was already settled before that
switch. Lives on the `non-nato-symbology` branch; not part of `main`
until this work is ready to integrate - not merged piecemeal, so as
not to ship a half-specified symbology scheme, and not until it
reaches roughly 80-90% complete (the maintainer's own bar). *(This
branch's own `docs/roadmap.md` predates that explanation - it was
never written there; this paragraph is the record of it instead.)*

This is a rules record, not a design doc — capture what the maintainer
says here verbatim/close to verbatim, not an interpretation of it.

**Current scope (as of 2026-08-31): Land, plus a Land-scoped slice of
SIGINT (Jammer/Radar only), narrowed to a reviewed, final list of
entities per category** (see "Required entities" below) **and a
reviewed, final list of Control Measure Points.** Every other domain
(Air, Sea Surface, Subsurface, Space, Cyberspace, Activities, Mine
Warfare, and the rest of SIGINT) has been reviewed against the catalog
and marked not required outright — not deferred, genuinely out of
scope for this work. Rules below were worked out against two reference
documents the maintainer supplied —
`reference/non-nato/MIL-STD-2525D_Symbol_Catalog.pdf` and
`reference/non-nato/symbol_check_sheets.html` (both gitignored, kept
locally only, same as the rest of `reference/`).

---

## Required entities (reviewed 2026-08-31)

Generated a checkbox-per-icon HTML check sheet (`nonnato_check_sheet.html`)
covering every Land Unit, Land Equipment, SIGINT Land and Control
Measure Point APP-6E entity, built standalone from milsymbol.js
directly (real SIDCs via the plugin's own `build_sidc()`, no plugin
UI/QGIS involved) - the generating script and the sheet itself live
only in an ephemeral scratchpad, not committed anywhere in this repo,
so regenerating one later means rebuilding that script from this
description rather than finding it on disk. Sent out for review by
email: each checkbox's toggle writes the actual `checked` CONTENT
ATTRIBUTE, not just the DOM property, specifically because a plain
property change is invisible to a browser's "Save Page As" and would
have silently lost every tick on the way back - verified this
round-trips correctly even with the browser's own storage completely
disabled.
Two reviewed copies came back and were parsed for which boxes ended up
checked - one covering the original 393-icon sheet, a second covering
just the Control Measure Points section added afterward. Zero overlap
in what each touched (the second file had nothing checked outside its
own new section), so there was nothing to reconcile - just a plain
union.

**This supersedes the earlier "accept every entity as a candidate"
framing** (the fill-exception/blanket-policy notes under Units below)
**with a concrete, final build list.** Only the entities below get
built for non-NATO symbology; everything else in APP-6E's Land
Unit/Land Equipment/Control Measure vocabulary is excluded. The
maintainer said there will be further changes communicated as the
build proceeds - this list is the reviewed starting point, not
necessarily the last word.

**Land Unit (21 of 187, one with no APP-6E equivalent - see below):**
Air Defence, Ammunition, Amphibious, Armour, Armoured/Assault
Engineers, Army Aviation, Artillery, Counterintelligence, EME,
Electronic Warfare, **Enemy (Info Unknown)** *(new, no entity key -
see Icon modifications below)*, Engineer, Infantry, Light
Armour/Recce & Support (Tracked), Medical, Mechanised Infantry,
Military Intelligence, Military Police, Parachute, Signal,
Special Operations Forces. *(Displayed with British spelling per the
rule below - these are the same APP-6E entities, keys unchanged.)*

**Renamed 2026-08-31** (entity key unchanged in every case, display
label only):
- `armor_mechanized` "Armour Mechanized" -> **Armour**
- `armored_mechanized_tracked` "Armoured Mechanized Tracked" ->
  **Mechanised Infantry**
- `field_artillery` "Field Artillery" -> **Artillery**
- `mechanized` "Mechanized" -> **Armoured/Assault Engineers**
- `maintenance` "Maintenance" -> **EME**
- `reconnaissance_cavalry_scout` "Reconnaissance Cavalry Scout" ->
  **Light Armour/Recce & Support (Tracked)** *(the maintainer wrote
  "Armout" - confirmed 2026-08-31 as a typo for "Armour")*
- `aviation_fixed_wing` "Aviation Fixed Wing" -> **Army Aviation**
  *(newly added, replacing the entity below)*

**Swapped 2026-08-31**: `army_aviation_aviation_rotary_wing` dropped -
no longer required. `aviation_fixed_wing` added in its place and
renamed to Army Aviation (above) - the "Army Aviation" name moves from
the rotary-wing entity to the fixed-wing one. Count stays at 20.

**Renamed 2026-09-02**: `parachute_rigger` "Parachute Rigger" ->
**Parachute** (entity key, composite-icon fixup, and its own SIDC all
unchanged - display label only).

**Icon modifications 2026-08-31** (glyph changes, not just relabelling
- verified by standalone rendering, both confirmed by the maintainer
against actual before/after SVGs):

- **Army Aviation** (`aviation_fixed_wing`): its icon is a filled
  bowtie/propeller shape - one of the hardcoded-fill exceptions from
  the full sweep above, where `fill:false` has no effect. **This one
  is a deliberate carve-out from that blanket accept-as-is policy**:
  swap it to stroke-only (`fill="none"`, same stroke colour/width it
  already carries) instead of leaving it filled. Visually this turns
  the solid bowtie into a hollow figure-of-8 outline. Mechanically:
  the fix is a straight fill/stroke swap on that one `<path>`, nothing
  else about the icon changes.
- **Parachute** (`parachute_rigger`, renamed from "Parachute Rigger"
  2026-09-02 - see below): composite icon. Add the
  Infantry glyph's own frame content (the rectangle's two diagonals,
  crossing at the centroid) as a base layer, then take the existing
  parachute glyph (a dome + two lines converging to a point, bounding
  box roughly 40 wide x 38.75 tall in milsymbol's internal path-space,
  centered close to the frame's own centroid already) and place a
  shrunk copy of it entirely in the lower wedge - the triangular
  region below the centroid, bounded by the two diagonals and the
  frame's bottom edge. Shrink factor: 20% (scale 0.8) around the
  glyph's own bounding-box center. Verified with the real geometry
  before rendering: the wedge's width at height y (in path-space,
  centroid at y=100, frame bottom at y=150) is `3*(y-100)`, so the
  shrunk shape's top edge needs to sit no higher than y~110.67 to
  clear the wedge - the confirmed placement (top edge at y=114.5,
  transform `translate(20, 49.5) scale(0.8)` relative to the original
  path) sits comfortably inside that, wedge width 43.5 against a
  32-wide shape at the shape's own narrowest (top) point, growing
  wider below. Stroke width compensated inside the scaled group
  (3.75 pre-scale -> 3 effective) so the parachute's lines stay the
  same visual weight as the rest of the icon, per the settled "line
  weight unchanged from NATO" rule rather than shrinking along with
  the shape.

**Amphibious's own oval removed, 2026-09-02**: "i want the oval inside
the rectangle removed - so the result is only the rectangle and the
wave". `amphibious`'s real milsymbol glyph is a stadium-shaped oval
(`M125,80 C150,80 150,120 125,120 L75,120 C50,120 50,80 75,80 Z`)
layered above a multi-hump wave path - the oval's own path is a fixed
signature, stripped out entirely (`nonnato_symbol_engine.
remove_amphibious_oval()`), leaving the frame and the wave untouched.

**Air Defence Artillery, added 2026-09-02** (Land Unit's count moves
to 22, entities-with-no-APP-6E-equivalent-of-their-own moves to two -
Enemy (Info Unknown) and this one): "use the Air Defence Glyph and add
a dot in the center (basically Air Defence and Artillery glyphs
merged)". Confirmed by rendering both real entities directly: Air
Defence's own glyph is the frame plus one arc path
(`M25,150 C25,110 175,110 175,150`); Artillery's own glyph is the frame
plus one filled centre dot (`<circle cx="100" cy="100" r="15">`, same
class as Field Artillery's dot noted elsewhere in this doc). The merge
renders Air Defence's real SIDC unchanged and adds that exact circle on
top as a fixup - `nonnato_symbol_engine.add_artillery_center_dot()`,
keyed to a synthetic entity (`AIR_DEFENSE_ARTILLERY_ENTITY =
"nonnato_air_defense_artillery"`, same "nonnato_"-prefixed, collision-
proof convention the synthetic mine family already uses) that resolves
to the real `air_defense` key only at SIDC-build time
(`_UNIT_ENTITY_KEY_ALIASES`, mirroring SIGINT Radar's own alias
mechanism on the Land Equipment side) - so the dot never leaks onto a
plain Air Defence render.

**Air Force, added 2026-09-03** (Land Unit's count moves to 23,
entities-with-no-APP-6E-equivalent-of-their-own moves to three): "use
the Army Aviation glyph, the figure of 8 is open on the right - so +-30
deg at 90deg i.e. 60 to 120 deg - keep the arc open, rest of the figure
of eight remains". Army Aviation's own hollow figure-of-8
(`hollow_army_aviation_propeller()`) is two curved wings meeting at the
centre; the right wing's own outer edge is a single ~180-degree cubic
bezier around its own local centre (130,100), radius 12. Angles read
as compass bearings (0 deg = up/north, 90 deg = right/east, clockwise -
the same convention `terrain/hillshade_combination.py`'s own light
azimuths already use elsewhere in this plugin) - the arc's own start
point (130,88) is due north of its local centre, its own rightmost
bulge (~145,100) is due east (bearing 90), and its end point (130,112)
is due south (bearing 180), so "60 to 120 degrees" sits astride
due-east, centred exactly on the arc's own rightmost point - reads as
"open on the right", confirmed against a render. Implemented by
splitting the single 180-degree bezier into two 60-degree arcs (0-60,
120-180), each rebuilt with the standard cubic-bezier circular-arc
control-point formula (k = 4/3 * tan(angle/4) * radius, not guessed),
leaving a real gap - two subpaths (a second `M` mid-path), which reads
correctly since the shape is stroke-only (`fill="none"`).
`nonnato_symbol_engine.open_air_force_propeller_arc()`, keyed to
`AIR_FORCE_ENTITY = "nonnato_air_force"`, resolved to the real
`aviation_fixed_wing` key only at SIDC-build time
(`_UNIT_ENTITY_KEY_ALIASES`) - same pattern as Air Defence Artillery
above, so the gap never leaks onto a plain Army Aviation render.

**Land Equipment (58 of 189, five with no APP-6E equivalent - see
below):** *(this is the original 2026-08-31 reviewed list, kept as a
historical record - the nine mine entities named in it moved OUT to
their own "Mines and Obstacles" layer 2026-09-03; see Part D's own
"Mines and Obstacles, a new fourth layer" entry for the current count)*
Air Defence Gun (Light), Air Defence Gun (Medium), Air
Defence Gun (Heavy), Air Defence Missile Launcher (Light), Air Defence
Missile Launcher (Medium), Air Defence Missile Launcher (Heavy),
Antennae, Antipersonnel Fragmentation Mine, Antipersonnel Mine,
Antitank Gun (Light), Antitank Gun (Medium), Antitank Gun (Heavy),
**Antitank Mine Booby Trapped** *(new, no entity key)*, Antitank Mine,
Antitank Missile Launcher (Light), Antitank Missile Launcher (Medium),
Antitank Missile Launcher (Heavy), Antitank Rocket Launcher (Light),
Antitank Rocket Launcher (Medium), Antitank Rocket Launcher (Heavy),
Armoured Protected Vehicle, **Bar Mine** *(new, no entity key)*,
Bridge, Field Gun (Light), Field Gun (Medium), Field Gun (Heavy),
Flame Thrower, Grenade Launcher (Light), Grenade Launcher (Medium),
Grenade Launcher (Heavy), Howitzer (Light), Howitzer (Medium),
Howitzer (Heavy), **Influence Mine (Anti Personnel)** *(new, no entity
key)*, **Influence Mine (Anti Tank)** *(new, no entity key)*,
Improvised Explosives Device, Machine Gun (Light), Machine Gun
(Medium), Machine Gun (Heavy), Missile Launcher (Light), Missile
Launcher (Medium), Missile Launcher (Heavy), Mortar (Light), Mortar
(Medium), Mortar (Heavy), Pack Animals, Radar, Recoilless Gun (Light),
Recoilless Gun (Medium), Recoilless Gun (Heavy), Single Rocket
Launcher (Light), Single Rocket Launcher (Medium), Single Rocket
Launcher (Heavy), Tank (Light), Tank (Medium), Tank (Heavy), **Unknown
Mine** *(new, no entity key - see Icon modifications below)*, ~~Vehicle~~
*(removed 2026-09-05, replaced by the Vehicle family below)*.

**Renamed 2026-08-31** (entity key unchanged, display label only):
- `antipersonnel_land_mine` "Antipersonnel Land Mine" ->
  **Antipersonnel Fragmentation Mine**
- `land_mine` "Land Mine" -> **Antipersonnel Mine** *(a different key
  from the one above, confirmed 2026-08-31 as the intended pairing)*
- `direct_fire_gun` "Direct Fire Gun" -> **Field Gun**

**Weapon light/medium/heavy tiers actually applied, 2026-09-01** - the
general rule (Part D) required checking, per family, which real APP-6E
sibling keys exist and applying the settled shift (base -> Light,
NATO's own Light -> Medium, NATO's own Medium -> Heavy, NATO's own
Heavy dropped) to each. **This surfaced a real blocker first**: this
branch had forked from `main` before `main`'s own APP-6E vocabulary
fix (105 entities losing their parent name/tier siblings to a
forward-fill bug, fixed and shipped in 1.3.1) - so several of these
families' Light/Medium/Heavy siblings were silently missing from this
branch's own `sidc_2525e.py` until that one commit was cherry-picked
in specifically for this. Full test suite re-run clean after
(1588/1588) before continuing.

**13 real weapon families confirmed tiered** in APP-6E (checked every
one of the 25 real Land Equipment entities individually, not assumed -
this caught 2 more than the maintainer's own first pass named): Air
Defence Gun, Air Defence Missile Launcher, Antitank Gun, Antitank
Missile Launcher, Antitank Rocket Launcher, Field Gun, **Grenade
Launcher**, Howitzer, Missile Launcher, Mortar, Recoilless Gun, Single
Rocket Launcher, Tank (the two in bold were not in the maintainer's
own original candidate list, found only by checking every entity
rather than the assumed set). Each becomes three required entities
(its own Light/Medium/Heavy), replacing the single line each held
before - **13 families x 3 = 39 entities, a net +26** over treating
them as single, untiered entities.

**Machine Gun is NOT one of the 13** - checked directly against both
`sidc_2525e.py` and the raw MIL-STD-2525E source table: `automatic_
rifle` has no Light/Medium/Heavy siblings at all. It is one of three
RIFLE FIRE-MODE variants instead (Single Shot/Semiautomatic/Automatic
Rifle, siblings under a generic "Rifle" parent that is itself not
used here) - a genuinely different kind of family, not a weight class.
**An earlier note in this record claiming "confirmed to carry its own
light/medium/heavy tiers" was wrong** - never actually checked against
the vocabulary at the time, corrected here. **Settled instead**: reuse
the rifle fire-mode family creatively for the same three-tier shape
every other weapon gets - `single_shot_rifle` -> **Machine Gun
(Light)**, `semiautomatic_rifle` -> **Machine Gun (Medium)**,
`automatic_rifle` -> **Machine Gun (Heavy)**. `automatic_rifle` no
longer sits alone as bare "Machine Gun" - it is now specifically the
Heavy tier, with two more real entities added to complete the set (a
further +2, on top of the +26 above).

**Collision resolved 2026-08-31 (for context, superseded by the above
2026-09-01 entry)**: the original `machine_gun` entity was dropped -
no longer required - and `automatic_rifle` took over the "Machine Gun"
name. That name now belongs specifically to the Heavy tier per the
rifle-family repurposing above, not to `automatic_rifle` alone as a
single untiered entity.

**The 2026-09-01 "not one of the 13" call was ITSELF wrong - corrected
2026-09-02**, reported live: "in case of machine gun, the light,
medium, heavy designations glyphs are incorrect - light has no
horizontal line in center, medium has one line and heavy two lines -
same as all other; this must have skipped since we changed the names".
Checked again, properly this time: Machine Gun DOES have real
Light/Medium/Heavy siblings in the 2525E table (`110201`/`110202`/
`110203`, right after `machine_gun`'s own `110200`) - the 2026-09-01
check went looking for the pattern every other family uses
(`machine_gun_light` etc., which is exactly how `sidc.py`'s own 2525D
table names the SAME three codes) and never found it, because the
2525E extraction dropped the "machine_gun_" prefix for this one family
only - the siblings sit in `sidc_2525e.py` under bare, unprefixed keys
`"light"`/`"medium"`/`"heavy"` instead. Confirmed by rendering all
four codes directly: `machine_gun` draws the gun body with no tier
line, `"light"` adds one horizontal line, `"medium"` adds two,
`"heavy"` adds three - exactly the same base/Light/Medium/Heavy
line-count progression every other tiered family has (e.g. `howitzer`/
`howitzer_light`/`howitzer_medium` at 0/1/2 lines). **The Rifle-family
repurposing (single_shot/semiautomatic/automatic_rifle) is retired** -
it was a workaround for a family that was never actually missing tiers
in the first place, and it drew the wrong line counts (1/2/3 instead
of 0/1/2) because the rifle fire-mode glyphs don't follow the tier-line
convention at all. Machine Gun now takes the same base -> Light,
real-Light -> Medium, real-Medium -> Heavy shift as the 13 properly-
prefixed families, making it a 14th real tiered family, not a special
case: `machine_gun` -> **Machine Gun (Light)**, `"light"` -> **Machine
Gun (Medium)**, `"medium"` -> **Machine Gun (Heavy)**; the real
`"heavy"` key (3 lines) is dropped, same as every other family's own
real Heavy tier. Entity count is unaffected (still 3 rows for Machine
Gun, just different keys) - only the underlying glyphs change.

**Missile Launcher family's dome gap, 2026-09-03** - Air Defence
Missile Launcher, Antitank Missile Launcher and (plain) Missile
Launcher all share the same real milsymbol glyph shape: a dome-capped
"inverted U" (two vertical legs plus a curved dome bridging their own
tops, drawn as one continuous connected stroke) with a vertical centre
line running up through the middle, touching the dome's own peak
exactly - no gap anywhere. Reported live: "essentially adjust the
length of the dome on top of the glyph so that it does not touch
anything, it should have a gap with the other lines on top, sides and
bottom" plus "reduce the length of the domes sides to match that of
the anti tank missile launcher" (Antitank's own U-legs were already the
shorter of the three, 45 units vs the other two families' own 65).
**First draft corrected live**: "no you misunderstood, the side lines
and dome are one entity like an inverted U" - an initial attempt wrongly
detached the dome from its own legs to open the gap; the U itself stays
one unbroken connected shape. The real fix instead trims the CENTRE
LINE's own top reach short of the dome's peak, by a gap doubled live
from an initial 5 to 10 ("increase the gap between the line and top of
dome by 100%") - `nonnato_symbol_engine._MISSILE_DOME_GAP = 10`. Air
Defence Missile Launcher's and plain Missile Launcher's own U-legs are
additionally shortened from 65 to 45 units to match Antitank
("length adjustment is fine") - opening the same gap versus the base
shape below that Antitank's own legs already had. Applies identically
across all three families' Light/Medium/Heavy tiers (the shared BODY
path is identical within a family; only the appended tier-line differs)
- `separate_antitank_missile_launcher_dome()`, `separate_air_defense_
missile_launcher_dome()`, `separate_missile_launcher_dome()`.

**Missile Launcher tier line inset, same day, immediately after**:
"everything is fine except that the dome legs are touching the
horizontal lines, so introduce a small gap, 50% of that between dome
top and vertical line, on both sides". "The horizontal lines" are the
Light/Medium/Heavy tier-line overlay every tiered weapon family gets
(the exact same shared geometry Machine Gun's own tiers use, fixed at
x=85..115 regardless of family) - unrelated to this family's own body,
but its fixed span happens to land exactly on the missile launcher
dome's own leg x-coordinates, so the two touch. Inset by
`_MISSILE_TIER_LINE_GAP = 5` (half of `_MISSILE_DOME_GAP`) on BOTH
sides, staying centred: 30 units wide (x=85..115) shrinks to 20
(x=90..110). Scoped to only the three missile-launcher fixups
(`_inset_missile_tier_line()`, called from each) - every other tiered
family's own, visually identical tier line is untouched.

**Three synthetic entities built from Armoured Protected Vehicle,
2026-09-03** (Land Equipment's own count moves to 54): three requests
in one batch, all starting from the same real entity's glyph.
`armored_protected_vehicle`'s own real glyph is NOT a true ellipse -
confirmed by rendering it directly - it is a stadium/discorectangle:
straight top/bottom edges from x=75 to 125
(`M125,80 C150,80 150,120 125,120 L75,120 C50,120 50,80 75,80 Z`),
semicircular caps left/right centred at (75,100)/(125,100) radius 20.
Overall bounding box x 50..150 (semi-major axis 50), y 80..120
(semi-minor axis 20 - the axis APV Wheeled's own radius spec refers
to).
- **Bridge Layer Tank**: "start with the Armoured Protected Vehicle
  (APV) glyph - over the oval, add a < on the top left - slightly
  inward say 1/3rd inside". First draft read "top left of the oval" as
  the stadium's own only real corner - (75,80), where the straight top
  edge meets the left semicircular cap - with "1/3rd inside" moving
  that point a third of the way toward the oval's own centre
  (100,100). **Corrected live, same day, twice**: (1) "shift the < to
  the top of the oval not inside it, and increase the < size by
  double" - dropped the inward interpolation, anchored at (75,80)
  itself, arm length doubled (10 -> 20 units); (2) "the bottom of <
  or / should touch the top of the oval" - the whole chevron moved to
  sit entirely ABOVE the oval's own straight top edge (y=80), its own
  lower arm-tip touching that edge exactly rather than the shape
  straddling it. Final vertex/arm-tips: (75,65.9) / (89.1,51.8) /
  (89.1,80) - `nonnato_symbol_engine.bridge_layer_tank_mark()`.
- **Armoured Recce Vehicle**: "start with the APV glyph and add a /
  at the same position as the Bridge Layer Tank <", corrected the same
  two rounds as Bridge Layer Tank above but with its own arm length
  (+50%, 10 -> 15 units, not doubled) - the two marks share the same
  horizontal anchor (x=75) and both now touch the oval's own top edge
  at their own lowest point, but are no longer the same size. Final
  line: (75,80) [touching] to (85.6,58.8) -
  `armoured_recce_vehicle_mark()`.
- **APV Wheeled, later renamed Armoured Protection Vehicle (Wheeled)**:
  "add APV Wheeled - start with APV glyph and add three circles below
  the oval, slightly inside the edges, touching the oval, radii size
  can be 1/3 of semi-minor axis" - radius = 20/3, left/right circles
  inset exactly one radius from the oval's own straight left/right
  edges (x=75/125), middle circle centring the group horizontally -
  **Real bug, caught by an actual smoke test**: "the circles below the
  ellipse are not visible - the full circle is not being drawn, circles
  are being cropped". QGIS's own SVG marker rendering clips to a paint
  rect tied to milsymbol's ORIGINAL declared draw area, regardless of
  what the viewBox attribute itself says afterwards - reproduced with a
  minimal two-shape SVG outside the plugin entirely, and confirmed
  Qt's own bare `QSvgRenderer` does NOT clip to viewBox at all, so this
  is QGIS-marker-layer-specific, not a Qt limitation. Six SVG-side
  workarounds were tried and all failed the same way: growing the
  viewBox (`_expand_viewbox_for_rect()`), leaving width/height
  unchanged while growing only the viewBox, dropping width/height
  entirely, drawing the circles as path arcs instead of `<circle>`
  elements, a second SVG marker layer with its own tight viewBox and
  offset, and circle-shaped text glyphs. **Settled fix**, after the
  maintainer pointed at the plugin's own NATO side ("there are
  instances where we have added additional svg elements to existing
  milsymbols - check the main branch files"): the wheels are not in the
  SVG at all. They are three QGIS simple-marker (circle) symbol layers
  composed alongside the icon's own SVG marker layer - the same
  multi-layer approach `c2_measures.py`'s own crossed runway lines
  already use on `main` - sized, offset and coloured from
  `nonnato_symbol_engine.py`'s own `APV_WHEEL_*` constants against this
  layer's own MARKER_SIZE_MM, scaling with the "scale" field and
  collapsing to size 0 for every other entity. Renders in full, exactly
  as originally specified (top of each wheel touching the oval's own
  bottom edge), with the icon's own SVG left completely untouched.
  See `land_equipment_layer_nonnato._wheel_symbol_layers()`.

  **Two follow-on fixes the multi-layer approach needed**, both
  reported live the same day: (1) "when i add the unique designator in
  APV wheeled, the wheels shift and overlap on the text of unique
  designation instead of staying where they are" - a designation grows
  the SVG's own viewBox downward, which moves the marker's anchor (its
  viewBox centre) down and so shifts the ICON up, while a fixed wheel
  offset stayed put. The wheels' own vertical offset is now computed
  per feature from the icon's own RENDERED height, via a new
  `mct_nonnato_equipment_svg_height()` expression function, so they
  track the hull whatever the designation does. (2) The designation
  itself is placed relative to the SVG's own measured content, which
  now stops at the hull - so it tucked under the hull and straight
  through the wheels. `inject_centered_designation_below()` grew a
  `min_content_bottom` argument for exactly this: an icon whose drawn
  extent is not all inside its own SVG passes the lowest point its
  extra symbol layers actually reach, and the normal gap is measured
  below THAT.

All three keyed to synthetic entities (`BRIDGE_LAYER_TANK_ENTITY`,
`ARMOURED_RECCE_VEHICLE_ENTITY`, `APV_WHEELED_ENTITY`, all
"nonnato_"-prefixed per the standing collision-proof convention),
resolved to the real `armored_protected_vehicle` key only at
SIDC-build time (`_EQUIPMENT_ENTITY_KEY_ALIASES`) - same pattern as
every other synthetic-entity-from-a-real-glyph built on this branch, so
none of the three marks ever leak onto a plain APV render.

**The Vehicle family: 'B' Vehicle, 'C' Vehicle, Light Recce Vehicle,
2026-09-05** (Land Equipment's own count moves to 56): "remove the
existing vehicle glyph, we will replace with 'B' Vehicle and 'C'
Vehicle / draw a rectangle, similar dimensions as land unit, draw two
circles - similar to what we did for the APV wheeled with the center
wheel removed, insert letter 'B' in the center of the rectangle /
Similarly - same construction for 'C' Vehicle except that 'B' is
replaced with 'C' / Finally - Light Recce Vehicle - start with vehicle
'B', remove the alphabet B and put a "/" on top of the rectangle of
same dimensions as the Armoured Recce Vehicle".

APP-6E's own real `vehicle` entity is dropped from this layer
entirely - rendered directly to check what was being replaced, it is a
stadium hull over a ground line with two small wheels
(`m 60,120 80,0 M 120,80 c 25,0.2 25,40 0,40 l -40,0 C 55,120 55,80
80,80 Z` plus two r=7 circles at (80,130)/(120,130)).

Unlike the three APV variants above, these three are **fully
synthetic**: nothing starts from a milsymbol render at all, so they are
built the same way the synthetic mine family is - a complete SVG
authored in `nonnato_symbol_engine.py` and routed through a new
`_SYNTHETIC_VEHICLE_SVG` dict, not as `_EQUIPMENT_ENTITY_FIXUPS`
entries. They therefore have no SIDC and no `_EQUIPMENT_ENTITY_KEY_
ALIASES` entry either, and `is_synthetic_entity()` now covers them.
- **Geometry.** "Similar dimensions as land unit" read literally: the
  same rectangle every Land Unit icon's own frame uses, 150 x 100 at
  x 25..175, y 50..150 (the measurement `enemy_info_unknown_svg()`
  already states). Wheels follow APV Wheeled's own rule exactly, minus
  its middle wheel - radius = 1/3 of the shape's own semi-minor axis
  (here half the rectangle's height, so 100/2/3 = 16.67), centred one
  radius below the bottom edge so each wheel's own top touches it, and
  inset one radius from the left/right edges. The letter sits at
  font-size 56.25, milsymbol's own letter-in-a-shape proportion
  (45 in an 80-unit shape) restated for a 100-unit-tall rectangle.
- **Qt honours no `dominant-baseline`.** The first draft centred the
  letter with `dominant-baseline="middle"` and it rendered a half
  cap-height high on both QGIS versions. The baseline is computed
  instead, using the same 0.7-of-font-size cap-height estimate
  `_text_element_bounds()` already works to. (Land Unit's own side
  designations still carry the attribute; their position was accepted
  live at the time and is not being changed off the back of this.)
- **Light Recce Vehicle's own "/"** is Armoured Recce Vehicle's own
  mark re-anchored to the rectangle's own top-left corner (25,50), its
  own lower end touching the top edge exactly, the same way that mark
  meets the oval. **Corrected live the same day**: "increase the mast
  height of the light recce vehicle by 125%" - 2.25x, read the way
  every other "increase by N%" on this branch has been (a 100%
  increase doubled the missile dome gap), and applied to the arm so
  the whole mark scales uniformly and keeps Armoured Recce Vehicle's
  own angle rather than stretching vertically.
- **Size and line weight, corrected live after a smoke test**:
  "reduce the size of all three by 20% - too big now, also increase the
  line width slightly to match with that of APV probably". Both come
  from the same cause: this family's own viewBox is 166 units wide
  against every milsymbol glyph's 108, and QGIS scales an SVG marker
  so its viewBox WIDTH equals the marker size. So the icon draws
  nearly edge to edge (a 150-unit rectangle in 166) and close to twice
  as tall as its neighbours, while a plain `stroke-width="3"` - correct
  at 108 - renders at 108/166 of everyone else's apparent thickness.
  The 20% reduction goes through Land Equipment's own existing
  per-entity multiplier (`VEHICLE_SIZE_MULTIPLIER = 0.8`, the same
  mechanism Jammer/Radar use in the other direction), and the stroke
  divides BOTH factors back out
  (`3 * (166/108) / 0.8`) so the lines match Armoured Protected
  Vehicle's own weight exactly on the map - the comparison the request
  named. Confirmed against a render at true relative marker sizes.
  The viewBox padding went 4 -> 8 in the same pass: the widened stroke
  put Light Recce Vehicle's own diagonal mast cap outside the viewBox,
  caught by this family's own viewBox-contains-the-ink test rather
  than by eye.

**Real bug found while building the above, 2026-09-05**:
`_expand_viewbox_for_rect()`'s own width/height rescale (which follows
a viewBox expansion, because QGIS sizes a marker by its declared
width) matched the FIRST `width="..." height="..."` pair anywhere in
the document. Every milsymbol render declares that pair on its own root
`<svg>`, so it happened to be right for them - but an SVG hand-built in
this module declares neither, and the first pair is then a `<rect>` the
icon actually draws with. **Bar Mine has been silently deformed by this
since it was built**: type a designation and its own bar stretched from
14.7 units tall to 72.5. Invisible without a designation, which is why
the Bar Mine smoke test passed. The match is now scoped to the root tag
only; both halves are covered by tests
(`TestViewboxExpansionLeavesDrawnRectanglesAlone`).

**Mine icons (2026-08-31)** - checked milsymbol's actual current
render for all three real mine entities against the maintainer's
rules before changing anything:
- **Antipersonnel Mine** (`land_mine`) - already renders as a plain
  hollow circle by default. Matches the rule exactly; no change.
- **Antitank Mine** (`antitank_mine`) - already renders as a solid/
  filled circle by default (one of the hardcoded-fill exceptions,
  same class as Field Artillery's dot). Matches the rule exactly - the
  existing exception is kept as-is here, not overridden.
- **Antipersonnel Fragmentation Mine** (`antipersonnel_land_mine`) -
  currently a filled circle plus two filled triangular "horns", both
  hardcoded fills. **Confirmed 2026-08-31: the circle becomes hollow
  (overriding that exception, to distinguish it from Antitank Mine's
  solid circle), the two horns stay filled** as they already render.
- **Unknown Mine** - **no APP-6E equivalent exists** in Land
  Equipment's vocabulary (checked - only the three real entities above
  exist). Built as a new custom icon per the "Icon source" rule (Part
  D): a hollow circle, same size/style as the other three mines, with
  a plain vertical diameter line through it. No entity key/SIDC yet -
  needs one assigned when this is actually implemented, most likely a
  synthetic key outside APP-6E's own numbering.
- **Influence Mine (Anti Tank)** - **no APP-6E equivalent** (checked
  both Land Equipment and the Control Measure Point vocabulary,
  neither has it). Built on the Antitank Mine's solid circle, with two
  horns reusing the exact same attachment/tip points as the
  Antipersonnel Fragmentation Mine's horns (base near the circle edge,
  tip out and up, mirrored left/right) - but as plain **unfilled
  lines**, not filled triangles, each ending in a small **arrowhead**
  at the tip. Confirmed against a rendered SVG before recording.
- **Antitank Mine Booby Trapped** - **no APP-6E equivalent**. Starts
  from Influence Mine's solid circle and its two top horns, but with
  the arrowheads removed (plain lines) and two more horns added at the
  bottom as a vertical mirror of the top pair - four horns total,
  symmetric top/bottom. **Corrected after the first render**: the
  horns were initially left at the angle inherited from the
  Antipersonnel Fragmentation Mine's horns (~54 degrees from
  horizontal) - confirmed instead to sit at **exactly 45/135/225/315
  degrees** (a clean X of diagonals through the circle) **and 25%
  shorter** than that first draft (length 30.8 -> 23.1 in milsymbol's
  path-space, measured from the circle's own edge outward). Confirmed
  against a rendered SVG comparing both versions before recording.
- **Influence Mine (Anti Personnel)** - **no APP-6E equivalent**.
  Identical to Influence Mine (Anti Tank) - same two arrow-tipped
  horns, unchanged - except the circle is **hollow** instead of solid,
  the same solid/hollow distinction already used to tell Antitank Mine
  and Antipersonnel Mine apart. Confirmed against a rendered SVG.
- **Bar Mine** - **no APP-6E equivalent** (checked Land Equipment and
  Control Measure Point vocabularies - the closest name match is an
  unrelated `barra_sonobuoy`). Antitank Mine's solid circle, with a
  hollow rectangle placed directly below it (top edge touching the
  circle's bottom edge, centred horizontally): height = circle
  diameter / 3, width = **2x** the circle's diameter (revised down
  from an initial 2.5x after review). A dashed horizontal line runs
  through the rectangle's own vertical centre, full width, with a
  dash length **twice** the standard dash unit used elsewhere in this
  scheme (8 vs the usual 4) while the gap stays at the standard 3 -
  only the dash itself was asked to lengthen, not the gap. Confirmed
  against a rendered SVG comparing both draft and final versions.
- **Directional Mine, added 2026-09-03** - **no APP-6E equivalent**
  (the real `antipersonnel_mine_directional` entity is an unrelated
  NATO-side Control Measure, `obstacle_control_measures.py`'s own).
  "we had designed a directional mine yesterday, it is missing from
  the menu" - no trace of it survived anywhere (no commit, function,
  or menu entry checked directly), so this is a fresh build, not a
  recovered one, though it turned out to reuse geometry that DOES
  survive in history - see below. Requested shape: "use booby trap
  symbol to begin with, remove the bottom lines at 315 and 225 deg,
  change the top lines to dashed, add a parallel line each to the two
  top lines also dashed". Built from Control Measure Point's own Booby
  Trap shape (hollow circle + four 45/135/225/315-degree horns): the
  two bottom horns (225/315) dropped, the two top horns (45/135) made
  dashed, each with a second, parallel dashed line of the same length
  alongside it. The horn/offset geometry (5-unit perpendicular offset,
  dash pattern "4,3", new line sitting outward away from the OTHER
  horn) is not a fresh guess - it is recovered unchanged from a
  same-shaped "dashed parallel horns" design originally built
  2026-09-01 for Booby Trap itself (commit `16f9bc1`), later superseded
  there once the maintainer clarified the circle's FILL, not the horn
  count/style, was the actual complaint (see this doc's own "Icon
  replacement 2026-08-31 - `booby_trap`" entry above). That geometry
  was never wrong, just built for the wrong icon at the time.

**Mine colour (2026-08-31)**: all mine icons above default to
**green** rather than affiliation colour - confirmed to match an
existing NATO-side convention already in this codebase:
`obstacle_control_measures.py` already draws obstacles/mines in a
fixed green (`OBSTACLE_GREEN_EXPRESSION`, `rgb(0,155,0)` / `#009b00`)
as an overridable default rather than affiliation-coloured, per that
module's own "obstacles are GREEN, not affiliation-coloured" rule.
Reused the exact same shade here for consistency rather than picking
a new green. Applies to Antipersonnel Mine, Antitank Mine, Influence
Mine (Anti Tank), Influence Mine (Anti Personnel), Antitank Mine
Booby Trapped, Bar Mine, Directional Mine, Antipersonnel Fragmentation
Mine, Unknown Mine, and Booby Trap (the Control Measure Point, see
below) alike.

**SIGINT Land (2 of 2 - unchanged):** Jammer, Radar - matches what was
already the entire in-scope SIGINT list, so no narrowing needed here.

**Control Measure Points (11 of 241):** *(this is the original
2026-08-31 reviewed list, kept as a historical record - Booby Trap
moved OUT to "Mines and Obstacles" 2026-09-03; see Part D's own "Mines
and Obstacles, a new fourth layer" entry for the current count)* Booby
Trap, Decision Point, Fort, Impact Point, Observation Post, Artillery
Observation Post,
Point Of Interest, Pill Box, Shelter Above Ground, Shelter Below
Ground, Target/DF Task.

**Renamed 2026-08-31** (entity key unchanged, display label only):
- `target_reference_point` "Target Reference Point" -> **Target**
  *(renamed again 2026-09-03 - see below)*
- `shelter` "Shelter" -> **Pill Box** *(the "Shelter Above Ground"/
  "Shelter Below Ground" entities are separate keys, left unchanged)*
- `observation_post_forward_observer` "Observation Post Forward
  Observer" -> **Artillery Observation Post**

**Renamed again 2026-09-03**: `target_reference_point` "Target" ->
**Target/DF Task** (entity key/SIDC unchanged, display label only,
same as every other rename in this table).

**Icon replacement 2026-08-31 - `booby_trap`**: fully replaces its
current NATO glyph (an ellipse with a triangular peak over it), rather
than a tweak to the existing icon. **Colour**: green, not
affiliation-based - checked `obstacle_control_measures.py` directly,
and `booby_trap` already defaults to green there too (`colour=GREEN`
is that module's own default for every entry unless overridden, and
this entry has no override), so this is "carrying over unchanged" per
Part C's own settled affiliation rule, not a new deviation from it.

**Shape, first draft**: started from Land Equipment's Antitank Mine
Booby Trapped shape (hollow circle + four 45/135/225/315-degree
horns).

**Shape, revised same day - superseded, see below**: the two bottom
horns (225/315 degrees) are removed. The two top horns (45/135
degrees) become **dashed**, and each gets a **second, parallel dashed
line of the same length** alongside it (offset 5 units, perpendicular
to the horn's own direction) - four short dashed strokes total,
arranged as two parallel pairs rather than four single lines. **Three
judgment calls made without an explicit spec, confirmed against a
render before recording**: the new parallel line is dashed too, not
just the original; the offset is 5 units; the new line sits
outward/above the original rather than the pair straddling the
original's centreline symmetrically. **This description was never
actually implemented in code** - when the layer was finally built
(2026-09-01/02), no surviving implementation of this shape could be
found, so it was re-derived fresh from this prose and shipped, then
immediately corrected below once the maintainer saw it live.

**Shape, corrected 2026-09-02, first pass - superseded, see below**:
reported live, against a rendered screenshot, as simply wrong -
"booby trap is incorrect - it should be same as antitank mine but with
the circle only, no fill". Read (wrongly) as "drop the horns entirely"
- the icon was rebuilt as Antitank Mine's own real circle geometry
(cx=100, cy=100, r=22, stroke-width 3 - Land Equipment's own
`_mine_circle()` helper), hollow rather than that icon's own filled
circle, with no horns at all.

**Shape, corrected 2026-09-02, second pass - this is the actual final
version**: reported live again, against a screenshot of the bare-
circle render - "its supposed to have four lines at the four angles as
described earlier". The horns were never meant to be dropped; only the
circle's own fill was ever the real complaint, both times. Final
shape: the hollow circle above, PLUS all four horns at 45/135/225/315
degrees, plain (no dashing) - the exact same horn coordinates
`antitank_mine_booby_trapped_svg()` uses for its own (filled-circle)
version. This is, in the end, precisely the "first draft" shape this
record originally described ("hollow circle + four 45/135/225/315-
degree horns") - that description was right all along; it was
ANTITANK_MINE_BOOBY_TRAPPED_ENTITY's own filled circle, not the horn
count, that caused both rounds of confusion.

**Echelons and the Combined Arms indicator are unaffected by this
review** - all 11 echelons were checked in the reviewed sheet
(matching the already-settled full list exactly, nothing pruned), and
only 2 of the 4 Combined Arms examples were checked, but that section
was illustrative of the sizing RULE (which applies uniformly to
whichever echelon is present), not a per-echelon feature to
individually enable - so this is read as "these examples were looked
at and confirmed correct," not a scope change to the Combined Arms
rule itself.

**Pill Box (`shelter`) - no fill, added 2026-09-02**: reported live,
against a rendered screenshot - "pillbox is rendering as filled
rectangle, it should be just the outline, no fill". Confirmed live
that milsymbol's own `fill: false` option does nothing for this icon
(a hardcoded fill, same defect class Part A's own "blanket policy"
note already catalogues elsewhere), so this needed a post-render fixup
rather than an options change. A genuine non-NATO-specific deviation
from Part C's own default "no non-NATO-specific treatment" rule for
Control Measure Points - narrow, one entity, not a broadening of that
rule. Affiliation colouring is otherwise untouched (still NATO's own
real colours, still the "friend/neutral/unknown render black, only
hostile renders red" quirk). Also confirmed live: `shelter` defines no
designation slot in milsymbol at all - a typed designation is accepted
without error but never actually appears on the icon, independent of
this fix and not something this fix could address.

**SIGINT designation position, corrected 2026-09-02, first pass -
superseded**: reported live, against a rendered screenshot - "in both
sigint glyphs - the unique designator is too far from the icon - get
it closer similar to other land unit glyphs". Confirmed live that
milsymbol places a designation at a fixed y="160" regardless of how
far down the icon's own artwork actually reaches - fine for a full
Unit frame (drawn to y=150, a 10-unit gap) but far too distant for
SIGINT's own compact bare glyphs (Jammer's "J", Radar's hook - both
drawn no lower than ~y=120). Moved to y="130" for both Jammer and
Radar. **This SIGINT-only fix was replaced days later** by
`inject_centered_designation_below()` - see Part D's own "Designation
position" entry - which centres the designation under EVERY Land
Equipment icon, mines and Jammer/Radar alike, not just these two.

**SIGINT merged into Land Equipment, 2026-09-02**: "merge sigint
glyphs (since there are only two) with land equipment" - the
standalone SIGINT (Non-NATO) layer/module/toolbar action is retired.
Jammer and Radar are now two more entities on the Land Equipment
layer, resolving to symbol_set "sigint_land" under the hood rather
than "land_equipment". Caught a real key collision doing this: Land
Equipment already had its own distinct real "radar" entity (a physical
radar system, one of the originally reviewed 26 base entities) -
SIGINT's own Radar was stored under a separate key
(`nonnato_symbol_engine.SIGINT_RADAR_ENTITY`, "sigint_radar") to avoid
silently breaking it. **That separate Land Equipment "radar" entity
was then removed entirely**, same day: "remove radar and keep only
radar (sigint) since both are same; rename radar (sigint) as radar
only" - the two read as visually the same thing in practice, so only
SIGINT_RADAR_ENTITY remains, now labelled plain "Radar".

**Jammer/Radar size, corrected 2026-09-02**: "Jammer and radar (sigint)
are still smaller than other land equipment, adjust them same as
others" - both are a compact/bare glyph that occupies a much smaller
fraction of its own declared viewBox than a typical Equipment icon's
own path does, even at the identical declared marker width every icon
on the layer shares. Measured real rendered pixel extents before
picking a multiplier (1.8x) rather than guessing.

**Radar's own mast, added 2026-09-02**: "add a small vertical line from
the center of the arc of the radar, length about 1/2 the current
height of the radar glyph", then "increase the mast length by 20%".
The arc's own midpoint (90, 112) is computed directly from milsymbol's
own cubic-bezier path (`nonnato_symbol_engine.add_radar_center_mast()`
has the full derivation), not eyeballed; final mast length 21 units,
drawn straight down.

---

## Part A — General symbol-category rules

Rules that apply across every domain in Part B unless a domain is
later called out as an exception.

- [x] **Units** — one frame shape only (rectangle), for every
      affiliation. No diamond/circle/square/quatrefoil shape-switching
      by affiliation like NATO. Affiliation is coded by the
      rectangle's OUTLINE colour, not by shape. **No fill** — interior
      stays empty, unlike NATO's solid affiliation-colour fill.
      - **Exception, confirmed 2026-08-26**: a handful of entities
        (e.g. Field Artillery's dot, Reconnaissance and Surveillance's
        triangle) have a solid-fill shape hardcoded into milsymbol's
        own icon drawing, not controlled by its `fill` option.
        Deliberate exception, not a bug to fix: these keep their solid
        shape as part of what makes the entity recognisable. "No fill"
        applies to the frame/background, not to every sub-shape of
        every glyph.
      - **Full sweep, 2026-08-26**: rendered all 187 Land Unit and 189
        Land Equipment APP-6E entities under the settled non-NATO
        options (0 render errors). Hardcoded-fill glyphs or text-based
        icons (like Jammer's bare "J", see SIGINT below) turn out to
        be common, not rare: **121 of 187 Land Unit entities (65%)**
        and **59 of 189 Land Equipment entities (31%)** have one or
        the other. **Blanket policy confirmed**: accept every one of
        these as-is, same as Field Artillery/Jammer above - no
        per-entity review pass. Individual entities get sorted out
        only if/when a specific one causes a real problem while
        building, not upfront.
      - **Combined Arms indicator (Land Unit only) - settled
        2026-08-26, geometry fully worked out standalone before any
        plugin code:** a new checkbox in the layer's dialog. When
        checked, draw a rectangle whose bottom edge touches the top of
        the milsymbol Land Unit icon (frame is 150 wide x 100 tall in
        milsymbol's own path-space; frame's top edge = the rectangle's
        bottom). **Styling confirmed**: same affiliation colour and
        line weight as the unit frame, no fill - visually confirmed as
        one cohesive glyph rather than a bolt-on. **Sizing**: no
        echelon selected -> fixed 37.5 wide x 33.3 tall (1/4 x 1/3 of
        the glyph), centered. Echelon selected -> take that echelon's
        own glyph bounding box, add a 5-unit margin on every side for
        breathing room (confirmed visually - without it, e.g.
        Detachment's circle touches the rectangle's edge), then widen
        past the 37.5 x 33.3 floor only on whichever axis the result
        exceeds it - never shrink below the floor. Final size per
        echelon (width x height): Detachment 54x40, Section 37.5x34.5,
        Platoon/Troop 89x34.5, Company 37.5x42, Battalion 37.5x42,
        Brigade 39x42, Division 74x42, Corps 109x42, Command 144x42,
        Army Group 179x42 (wider than the 150-wide frame itself - not
        a problem, just the natural result for the largest tier).
      - **Enemy (Info Unknown) - added 2026-08-31, no APP-6E
        equivalent** (checked - no generic/blank "unit" entity exists
        in the ground_unit vocabulary either). Not tied to a specific
        entity's icon at all - a standalone frame variant: **two
        concentric rectangles** instead of the usual single frame, no
        icon glyph inside. **Judgment calls made without an explicit
        spec, confirmed against a render before recording**: coloured
        hostile red (`#c02020`) per "Enemy" rather than a neutral/
        generic colour; inner rectangle set 15 units in from the outer
        frame on every side (outer stays the standard 150x100, inner
        is 120x70, centred) - an arbitrary but reasonable margin, not
        derived from any other measurement in this scheme.
- [x] **Equipment** — no frame at all (no filled-circle container like
      NATO). Just the bare icon glyph, drawn directly, no fill.
      Affiliation is coded by the colour of the glyph's own
      outline/stroke lines, same mechanism as Units.
- [x] **Installations** — not required. Land Installation symbols are
      out of scope for non-NATO symbology; no non-NATO Installation
      layer will be built for Land. (Subsurface also carries an
      Installation layer - not yet addressed; stated for Land
      specifically, not assumed to generalize.)
- [x] **Civilians** — not required. Land Civilian symbols are out of
      scope for non-NATO symbology; no non-NATO Civilian layer will be
      built for Land. (Other domains that also carry a Civilian layer
      - Air, Sea Surface, Space, Subsurface - not yet addressed; this
      decision was stated for Land specifically, not assumed to
      generalize.)
- [ ] Any other general category not covered by the above

## Part B — Per-domain confirmation

Whether Part A's rules apply as-is, or a domain needs its own
exception. (Land already covers Unit/Civilian/Equipment/Installation
as its own four sub-categories above.)

- [x] **Land** — confirmed via its own four sub-categories in Part A
      (Units and Equipment settled; Installations and Civilians not
      required) plus Land-scoped SIGINT (Jammer/Radar only). No
      separate domain-level exception beyond those.
- [x] **Air** (including Air-Missile) — not required
- [x] **Sea Surface** — not required
- [x] **Subsurface** — not required
- [x] **Space** (including Space-Missile) — not required
- [x] **Cyberspace** — not required
- [x] **SIGINT** — Air, Space, Sea Surface and Subsurface SIGINT: not
      required. Land SIGINT: only Jammer and Radar are required,
      following the same rules as Land Equipment (no frame, bare
      glyph, affiliation by the glyph's own outline colour). Radar's
      APP-6E icon is proper line art and renders cleanly under those
      rules. Jammer's APP-6E icon is a bare letter "J" (a font glyph,
      not a pictogram) — confirmed 2026-08-26 to accept as-is, same
      as milsymbol provides, rather than building a custom icon.
- [x] **Activities** — not required
- [x] **Mine Warfare** — not required *(catalogue section not
      previously in this list — added from the PDF's own structure)*

## Part C — Control measures (Appendix H tactical graphics)

Lines/areas/points for boundaries, objectives, obstacles, fire
support, etc. — structurally different from units/equipment, likely
needs its own rules rather than inheriting Part A.

**Mechanism settled**: affiliation is coded the same way as NATO —
line colour indicates affiliation, carrying over unchanged, no
non-NATO-specific treatment needed for that part. **Scope**: not every
module/icon below is required; only some are, and which ones will be
decided and built incrementally as work proceeds rather than specified
all at once up front — going through each module's own Points, Lines
and Areas in turn, the same sequence the NATO build already follows.
The list below stays as the full NATO inventory for reference, not a
commitment to build all of it.

- [ ] Airspace Control Measures (Lines, Areas, Points)
- [ ] C2 Measures (Lines, Areas, Points)
- [ ] CBRN Defense (Points, Areas, Dose Rate Contours, Safe Distance Zones)
- [ ] Deception Control Measures (Lines)
- [ ] Defensive Control Measures (Areas, Lines, Points)
- [ ] Field Fortification (Points, Lines)
- [ ] Fire Support Coordination Measures (Lines, Areas)
- [ ] Intelligence Control Measures (Lines)
- [ ] Maneuver Control Measures + II (Lines, Areas)
- [ ] Maritime Control Measures (Lines, Points)
- [ ] Mission Task (Lines, Points)
- [ ] Obstacle Control Measures (Minefields, Lines, Points, Areas)
- [ ] Offensive Control Measures (Lines, Areas, Points)
- [ ] Supply/Sustainment (Supply Points, Supply Routes, Sustainment Areas, Sustainment Points)
- [ ] Target Acquisition Control Measures (Areas, Weapon/Sensor Range Fans)
- [ ] Target Control Measures (Lines, Areas, Points)

## Part D — Cross-cutting mechanics

Meta-questions likely to come up regardless of category/domain.

- [x] **Designation position (Land Equipment)** — settled 2026-09-02,
      after three live-reported rounds. Round one: "the unique
      designation is still too far from the glyphs... I want the
      unique designation to be directly under the glyph, with text
      centered" - drawn as its own centred `<text>` element directly
      below the icon (widened downward to fit, never sideways - a long
      designation shrinks its own font size instead, mirroring the
      NATO supply-box convention), not through milsymbol's own
      uniqueDesignation option at all -
      `nonnato_symbol_engine.inject_centered_designation_below()`.
      Round two: "it is a bit far, can we move it as close to the
      glyph as possible with some gap - this should be dynamic as we
      move ahead with the modifications in future" - the gap was
      anchored to the icon's DECLARED viewBox, which is not a tight
      box (confirmed live: Jammer/Radar's own declared viewBox extends
      20-30 units past their real ink, Tank/Antitank Mine within ~2),
      so the fix re-anchors to each icon's own REAL rendered content
      bounds instead - `_content_bounds()`, measured with Qt's
      QSvgRenderer.boundsOnElement() rather than any per-icon constant,
      so a future icon's own real ink is measured automatically rather
      than needing to be hand-tuned. Applies to every entity on the
      layer, mines and the merged-in Jammer/Radar included. Land Unit
      got its OWN, different two-sided replacement the same day - see
      the next entry.
- [x] **Two-sided designation (Land Unit)** — settled 2026-09-02:
      "i want two unique designators - unique designator (left) and
      unique designator (right)... both left and right designators
      should be vertically middle aligned to the left or right of the
      glyph, the present unique designator can be removed or ignored".
      Replaces milsymbol's own single, side-anchored uniqueDesignation
      slot entirely (the older mechanism this same section used to
      describe as still in use there) - two independent fields,
      `unique_designation_left`/`unique_designation_right`, each drawn
      as its own `<text>` element vertically centred on the icon's own
      REAL rendered content bounds (reusing Land Equipment's own
      `_content_bounds()`/`_DESIGNATION_GAP` above), one to either side,
      widening the viewBox sideways rather than downward -
      `nonnato_symbol_engine.inject_side_designations()`. Applied
      before the Combined Arms rectangle, so both designations align
      with the unit glyph/frame, not with Combined Arms' own indicator
      sitting above it. **Font size corrected the same day**: "the
      font size is too small to read, the position is ok, increase
      the size to 8pt or more" - the position stayed as-is; font size
      moved to its own constant, `_SIDE_DESIGNATION_FONT_SIZE = 45`
      (up from 28, the value it started out sharing with Land
      Equipment's own `_DESIGNATION_FONT_SIZE`) - 45 matches
      milsymbol's own established legible-in-icon-text size at this
      same coordinate scale (see symbol_engine.py's own sonobuoy-
      family comment). Kept as a separate constant on purpose, so a
      future font tweak to one layer's designation text can't
      silently move the other's too.
- [x] **Affiliation colour palette**:
      - Blue — Friendly
      - Red — Hostile
      - Brown — Friendly Paramilitary
      - Purple — Non-state actors, hostile
      - Green — Neutral
      - Amber — Unknown
- [x] **Icon source** — maximum reuse of milsymbol.js glyphs as-is;
      for whatever it doesn't already have, build a new icon or modify
      an existing milsymbol one, decided case by case. Which specific
      symbols need building/modifying will be indicated as each module
      is developed, rather than listed all now.
- [x] **Echelon / amplifier conventions** — carried over, drawn on the
      same rectangle frame (no fill, line colour = affiliation), but
      renamed and pruned from the NATO list:
      - Unspecified — included, unchanged.
      - Team/Crew — renamed **Detachment**; glyph changed from NATO's
        circle-with-a-crossed-line to a plain **hollow circle** (no
        crossing line).
      - Squad — renamed **Section**.
      - (NATO's) Section — not required (name reused above, for Squad).
      - Platoon — renamed **Platoon/Troop**.
      - Company — renamed **Company/Battery/Flight/Squadron**.
      - Battalion — renamed **Battalion/Regiment/Avn Squadron**
        *(changed from "Squadron" 2026-08-31, to disambiguate from
        Company's own "...Squadron" rename above)*.
      - (NATO's) Regiment — not required (name reused above, for
        Battalion).
      - Brigade, Division, Corps — retained as-is, unchanged.
      - Army — renamed **Command**.
      - Army Group — retained as-is, unchanged.
      - Theater and Command — not required.
- [x] **Line weight / stroke width** — same as the existing NATO
      symbology, unchanged.
- [x] **Status convention** — changed from NATO's Present/Planned
      labelling to naming the states directly after the line style
      itself: **Solid** and **Dashed**. The underlying visual
      mechanism (solid vs dashed line) is unchanged from NATO.
      - **Scope confirmed 2026-08-26**: applies to Units only.
        milsymbol only dashes the FRAME's own stroke for Planned
        status, and Equipment has no frame (`frame: false`) - tested
        directly, status=planned vs status=present produced
        byte-identical SVG for a Tank. Rather than post-processing the
        glyph's own lines to fake a dash, Equipment simply doesn't
        carry a Solid/Dashed distinction at all - matches the idea
        that "planned" is more naturally a unit-level concept.
- [x] **Symbology standard edition** — APP-6E (MIL-STD-2525E) entity
      vocabulary only; APP-6D/2525D is not used for non-NATO symbology.
- [x] **Spelling convention (2026-08-31, broadened same day)** —
      general rule: wherever the APP-6E vocabulary (or this record's
      own prose) uses an American spelling with a standard British
      equivalent, use the British one. Confirmed examples so far:
      "defense" -> "defence" (e.g. "Air Defence Gun"), "armor" ->
      "armour" and "armored" -> "armoured" (e.g. "Armour Mechanized",
      "Armoured Protected Vehicle"). Swept the whole record for other
      American/British spelling pairs and fixed what applied
      ("recognizable" -> "recognisable", "catalog section" ->
      "catalogue section" - prose only, not literal filenames). Entity
      keys/SIDCs are unchanged - this is display text only. **Excluded
      on purpose, confirmed 2026-08-31**: Part C's control-measures
      list (the 16 NATO Appendix H module names - Airspace Control
      Measures, C2 Measures, CBRN Defense, etc., see the list itself
      further down) and the Echelon list's dropped "Theater" both
      quote the existing NATO/plugin catalog's own names for reference
      - not new non-NATO labels - so both stay in their original
      spelling.
- [x] **Weapon light/medium/heavy tier renaming (2026-08-31)** — for
      weapons that carry a light/medium/heavy size class as a sector
      modifier (drawn as 1/2/3 horizontal lines across the base icon,
      e.g. Air Defence Gun), each tier shifts up one name for
      non-NATO: the plain/unmarked base icon (0 lines) is labelled
      **Light**, NATO's own **Light** (1 line) becomes **Medium**, and
      NATO's own **Medium** (2 lines) becomes **Heavy**. Confirmed to
      apply to every weapon in scope that carries this modifier, not
      just Air Defence Gun - one general rule, not a per-entity
      exception. **NATO's own 3-line Heavy tier is confirmed not
      required** - same pattern as Squad's rename orphaning NATO's own
      Section: its name is now taken by the old Medium tier, and
      there's nothing to shift it up into.
- [x] **Mines and Obstacles, a new fourth layer (2026-09-03)** —
      requested live: "now, let's move all the mines to a different
      layer - say mines and obstacles; shift booby trap also into this
      new layer". Consolidates two groups of entities that used to sit
      on different layers purely because of which real APP-6E
      symbol_set they happened to belong to, even though both already
      shared identical real behaviour (fixed MINE_GREEN, never
      affiliation-coloured, custom non-milsymbol-default icons): the
      nine-entity mine family (moved OUT of Land Equipment - three real
      entities plus six synthetic icons) and Booby Trap (moved OUT of
      Control Measure Points, the one custom-icon exception that layer
      used to carry). See `mines_and_obstacles_layer_nonnato.py` - a
      new module, own toolbar action ("Mines and Obstacles", third
      entry in the "Non-NATO Symbols" group), own icon
      (`nonnato_mines_and_obstacles.svg`, reusing the Booby Trap horn
      glyph Control Measure Points' own icon used to show - that layer
      needed a NEW icon instead, a generic crosshair/target mark, since
      Booby Trap no longer represents it).

      Rendering functions themselves (`booby_trap_control_measure_svg()`,
      the whole mine family in `nonnato_symbol_engine.py`) are
      completely unchanged - always layer-agnostic; only which QGIS
      layer's own renderer calls them changed. Two judgment calls made
      without an explicit spec, both confirmed against a render before
      settling:
      - **No "affiliation" field on the new layer at all** - every
        entity here is fixed-green regardless of affiliation, so a
        field that could never change the render would be dead weight
        on the attribute form. The rendering functions still need SOME
        affiliation value passed through (mine entities only - Booby
        Trap never took one), so a fixed `'friend'` literal is used in
        the expression instead of a live field reference.
      - **MARKER_SIZE_MM reset to the scheme's own plain 8.0mm
        default**, not Land Equipment's own 20%-bigger 9.6mm the mine
        family used to inherit purely by sitting on that layer - that
        multiplier was requested specifically for Land Equipment as a
        whole ("in land equipment, i want all the glyphs to be 20%
        bigger by default"), not for mines in particular, so it does
        not follow them to the new layer. Matches Booby Trap's own
        prior 8.0mm on Control Measure Points too, so neither group
        changes visual size as a side effect of the move.

      Land Equipment's own count dropped from 60 to 51 at the time of
      the move (9 mine entities removed - it is 56 now, after the three
      Armoured Protected Vehicle variants added later the same day and
      the three-entity Vehicle family that replaced the real "vehicle"
      entity on 2026-09-05);
      Control Measure Points' own count drops from 11 to 10 (Booby Trap
      removed); the new layer carries all 10 of them.
- [ ] Designation / label placement conventions — to be specified
      later.
      - **NEXT ITEM WHEN WORK RESUMES (flagged 2026-09-05)**: the
        designation text under the Vehicle family renders noticeably
        SMALLER than under every other Land Equipment entity, for
        exactly the same reason its strokes did before they were
        compensated — `_DESIGNATION_FONT_SIZE = 28` is in icon units,
        and QGIS scales an SVG marker so its viewBox WIDTH equals the
        marker size, so 28 units in this family's own 166-wide viewBox
        at a 0.8 size multiplier draws at roughly 0.44x the apparent
        size it does in a 108-wide one. Raised and deliberately left
        alone in the same pass that fixed the strokes, rather than
        widening scope unasked. The fix is the same shape as the stroke
        one (`* (viewBox width / 108) / size multiplier`), but it wants
        a general answer rather than a Vehicle-family constant: any
        future entity authored in a non-108 viewBox hits it too, and
        Bar Mine (160-wide) already does.
- [ ] Anything else that surfaces while specifying the above
