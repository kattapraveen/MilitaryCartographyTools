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

**Land Unit expansion, 2026-09-06** (the layer's own count moves from
23 to 31): six new entities, one new field, and two real bugs found
while wiring them.

**The Enemy family goes from one entity to four** - "enemy (info
unknown) remains as is / enemy (echelon unknown) - add a "?" on top of
the glyph / enemy (designation unknown) - add a "?" to the right center
of the glyph (same place as unique designation right) / enemy (type
unknown) - add a "?" in the center of the glyph". All four share the
same two concentric rectangles and the same fixed hostile red, and none
of them touches a SIDC. The "?" is sized to
`_SIDE_DESIGNATION_FONT_SIZE` deliberately, not a constant of its own,
because "same place as unique designation right" means it has to land
on that anchor at that size - verified by a test comparing it against a
real right designation. It is injected AFTER the side designations, so
a typed right designation keeps its own anchor and the "?" steps
outside it instead of colliding.

**Five more Land Unit entities**, all requested the same day:
- **Motorised Infantry** - "start with the infantry glyph, add the two
  wheels under it (from the B vehicle or C vehicle glyphs in land
  equipment)". Literally those wheels: the Vehicle family's own
  `_VEHICLE_WHEEL_*` constants, reused with no re-derivation, because
  the Land Unit frame and the Vehicle body are the SAME 150 x 100
  rectangle (x 25..175, y 50..150). Synthetic over plain `infantry` -
  APP-6E's own `infantry_motorized` exists but draws milsymbol's own
  motorized modifier, not this scheme's wheels.
- **Mountain Infantry** - "in the lower half of the rectangle add a "^"
  or s small triangle with the bottom ends on the rectangle bottom
  line, the height of the "mountain" is 1/3 of the rectangle height".
  Drawn as an open "^" (the frame's own bottom line closes it), height
  33.3. The BASE was not specified; set to twice the height, putting
  both slopes at 45 degrees so it reads as a mountain rather than a
  spike.
- **Recce & Support (Wheeled)** - "start with mechanised infantry - add
  the wheels of the motorised infantry to it". Mechanised Infantry is
  this layer's own label for the real `armored_mechanized_tracked`, and
  the wheels are the same function again - the wheeled counterpart to
  the existing "Light Armour/Recce & Support (Tracked)".
- **Administration or Logistics Unit** - "Add a simple circle - same
  dimensions as the rectangle of land units, option to add unique
  designation left/right as existing". A circle has only one dimension
  to match against a 150 x 100 rectangle, so it matches the HEIGHT:
  diameter 100 centred at (100,100), sharing the frame's top and bottom
  edges. Affiliation-coloured normally, unlike the Enemy family.
- **Static Formation Headquarters** - "Use a basic rectangle with flag
  mast of headquarters - instead of right line of rectangle - replace
  with a < the resulting rectangle looks like a flag". A standalone
  pennant frame with no glyph inside and no SIDC, carrying its own copy
  of the mast. The notch DEPTH was not specified; set to a fifth of the
  frame's width. Its mast is copied from a real `headquarters=True`
  render (`M25,150 L25,250`) rather than guessed, and a test pins that
  path so a milsymbol update cannot shift it silently.

**Headquarters is now a field on the layer** - "there is a choice for
Headquarters in the NATO symbology wherein a flag mast is added to the
glyph - implement the same in non-nato also - option for headquarters
to be added in the dialog box". A Bool field with a CheckBox widget
defaulting to false, exactly the convention
`_point_symbol_layer.include_headquarters` already uses on the NATO
side, passed straight through to `build_sidc()`'s own `headquarters`
argument (SIDC Field S). **It has no effect on the four Enemy entities,
Administration or Logistics, or Static Formation Headquarters** - none
of them reaches a SIDC for milsymbol to amplify. Documented behaviour,
covered by a test, not an oversight.

**Real bug 1: the side designations were never centred on the frame.**
Reported live - "even in normal headquarters - the unique designations
should be center of the rectangle and not the entire glyph". They were
centred on the icon's own MEASURED ink, and the HQ mast hangs 100 units
below the frame, dragging that centre from 100 down to 150. Measuring
the same way showed **the identical drift had been there all along for
every echelon above "unspecified"** - a battalion's own amplifier sits
above the frame and pulled the centre UP to 82.6, army_group to 82.0 -
so this fixes considerably more than was reported. They now centre on
`_UNIT_FRAME_CENTRE_Y`, which is safe because every Land Unit icon's
frame occupies the same rectangle whatever the entity, echelon or
affiliation (milsymbol's own `M25,50 l150,0 0,100 -150,0 z`, Enemy's
own hand-built rectangle, and Administration or Logistics' circle all
state the same numbers) - pinned by its own test.

**Real bug 2: a NULL boolean field blanked the whole icon.** QGIS
returns NULL from an expression function the moment ANY argument is
NULL, so a feature whose checkbox had never been set rendered NOTHING.
Field defaults only apply to features created through the attribute
form - a pasted feature, a provider-level insert, or a project
predating the field all arrive NULL. `"combined_arms"` had carried this
latent blank-icon bug since it was added; adding `"headquarters"`
beside it is what surfaced it. Both are now wrapped in
`coalesce(..., false)`. Confirmed by direct expression evaluation.

**Land Unit, second batch the same day, 2026-09-06** (23 -> 39
entities across both batches): eight more entities, two corrections to
existing glyphs, and one resize.

- **Self Propelled Artillery** - "Use the Artillery glyph (rectangle
  with a filled dot) - add three wheels (same as APV wheeled)". "Same
  as APV wheeled" is read as that icon's own RULE, not its literal
  radius: three circles at a third of the shape's own semi-minor axis,
  tops touching its bottom edge, outer two inset one radius, middle
  centring the group. On the Land Unit frame that gives radius 16.7,
  not the APV oval's 6.7 - the literal radius would draw three dots
  about a tenth of the frame's width, and would clash with Motorised
  Infantry's own wheels sitting on the same layer at frame scale. So
  these ARE Motorised Infantry's own two wheels with the middle one
  restored, which is what the APV rule yields here anyway; a test pins
  the two entities to the same wheel size.
- **Parachute Field Artillery** - "Use the Artillery glyph - add the
  parachute symbol (from the Parachute unit - inserted below the
  diagonals)". The same path as the Parachute unit's own canopy, not a
  redrawing. **Resized on sight the same day**: "reduce the size of the
  parachute canopy just enough that it is clear of the dot and clear
  from the rectangle". The scale is DERIVED, not picked - fit the
  glyph's own ink (geometry plus a stroke that scales with it) into the
  clear band between the dot's own bottom edge and the frame's, leaving
  `_PARACHUTE_CLEARANCE` = 3 at each end. That works out to exactly
  0.6, against the Parachute unit's own 0.8. The first pass reused 0.8
  unchanged and left the canopy's crown ~3.5 units behind the dot,
  because Artillery's dot is filled and 30 across where Infantry's
  diagonal crossing - what that placement was designed around - is a
  thin X. The test asserts the CLEARANCE at both ends rather than the
  number, so the fit survives a future change to either shape.
- **Signal's own jagged line is mirrored** - "horizontally invert the
  jagged line - it should touch the other two vertices of the
  rectangle". milsymbol draws `M25,50 100,110 100,90 175,150`,
  top-left to bottom-right; it now runs top-right to bottom-left. Only
  the endpoints move: the two middle vertices sit on x=100 and are
  their own mirror image. A test asserts it is a true reflection of
  milsymbol's own path rather than a hand-typed one. This CHANGES an
  existing entity rather than adding one.
- **Six entities on Military Police's own framed glyph** - "Information
  Warfare, Postal Unit and Intelligence - use the Military Police
  Glyph, replace MP with IW, PO and I respectively", plus "Supplies and
  Transport unit - standard rectangle, insert a circle in the middle
  and add a X (two diagonals) inside the circle only", "Ordnance unit -
  standard rectangle with the [booby trap] glyph inside it" and
  "Remount and Veterinary corps unit - standard rectangle with \/ -
  starting at the top corners and meeting at the center of the bottom
  line of the rectangle".

  **Built on a real milsymbol render, NOT as standalone SVGs** - unlike
  Administration or Logistics and Static Formation Headquarters, which
  are hand-built and therefore carry no echelon, status or headquarters
  support. Military Police is the donor because its own interior is a
  single `<text>` element, the cleanest thing in the vocabulary to
  remove; the first three swap its letters, the last three delete it
  and inject a shape. This is safe because all six non-NATO
  affiliations map to SIDC "friend" (`SIDC_AFFILIATION_FOR`), so the
  frame shape never varies. A test asserts all six still respond to
  echelon, status and headquarters.

  Supplies and Transport's circle radius (35) was NOT specified -
  chosen to leave a clear margin inside the frame's own 100-unit height
  while staying big enough for the X to read at map size. Its diagonals
  end ON the circle, per "inside the circle only", which a test pins by
  measuring each endpoint's distance from the centre.

  **Ordnance was corrected live**: the first pass read "the decoy
  glyph" literally and used milsymbol's own Decoy (three filled
  triangles, from the `air` symbol_set) - "its booby trap not decoy -
  and the colour affiliation remains standard as per land units and not
  green". It now draws Mines and Obstacles' own Booby Trap shape, and
  the shape itself was factored out of
  `booby_trap_control_measure_svg()` into a shared `booby_trap_marks()`
  so the two layers cannot drift apart. MINE_GREEN turns out to be that
  LAYER's own rule rather than a property of the shape - `colour` was
  already an argument - so Land Unit just passes its own affiliation
  colour. Tests cover both directions: Ordnance never renders green,
  and the mines layer's own Booby Trap still does.

**A FIFTH layer: Aviation (Non-NATO), 2026-09-06** - "Insert in land
equipment - or better make a separate layer called aviation / move army
aviation and airforce into that, same rules as land unit i.e. same
dialog box replicated".

"Same dialog box replicated" is taken literally: the layer SHARES Land
Unit's own `build_unit_style_layer()`, `configure_unit_attribute_form()`
and `build_unit_renderer()` rather than copying them, so every field,
widget, default and expression is identical by construction and cannot
drift. Land Unit's own count drops 39 -> 37 as Army Aviation and Air
Force move across; Aviation carries eight.

- **Army Aviation** (`aviation_fixed_wing`) - "let's start with the army
  aviation glyph - use only the figure of 8 inside the rectangle", which
  is what it already drew (the hollow-propeller fixup had settled that
  on 2026-09-01). No change beyond the move.
- **Air Force** - the same figure-of-8 with its right arc opened, moved
  unchanged.
- **Six new mast-carrying entities**, all the figure-of-8 with a mast
  hanging from it: Rotary Wing (plain inverted T), Attack / Utility /
  Light Helicopter (the same T flanked by "AH" / "UH" / "LH"), Fixed
  Wing (the bar trimmed to the right of the mast, so an L rather than a
  T) and UAV/RPV/Drone (the whole mast flipped upward - which works
  because the figure-of-8 is symmetric about the crossing point, so
  nothing else needs mirroring).

**Rotary Wing took four live corrections**, and each one generalised to
the whole family:
1. "the mast should touch the figure of 8" - the first draft anchored it
   at y=112, the lobes' own lowest point. But the lobes only reach 112
   at their WIDEST; along the centre line the shape passes through
   exactly one point, the crossing at (100,100) where the two lobes
   meet. That is why it looked detached despite 112 being a real edge of
   the glyph.
2. "increase the length of the mast by 50%" - 28 -> 42.
3. "increase the mast length by another 30%" - 42 -> 54.6.
4. "i dont want the rectangle" - the frame is removed, making these the
   only Land Unit-style icons on the branch with no frame at all.

**The frame's removal orphaned milsymbol's own amplifiers**, which then
drew in empty space - the echelon bars well above the glyph, the
Headquarters mast as a detached line down at the left. Re-anchoring both
to the figure-of-8 was built and rendered first; the maintainer settled
it the other way on sight - "this glyph - other than the unique
identifiers, nothing else is needed - so no need to check headquarters
etc" - so they are REMOVED. The side designations are the only amplifier
these six keep, and they already centre on `_UNIT_FRAME_CENTRE_Y` (100),
which is exactly the figure-of-8's own centre, so they needed nothing.

The layer's own echelon/status/headquarters fields still exist, because
the dialog is replicated wholesale - they simply have no effect on those
six entities. Army Aviation and Air Force keep their frames and honour
all of them.

**Stripping the amplifiers left milsymbol's own viewBox oversized** - it
had grown to fit bars that are no longer drawn, which would shift the
glyph off the marker's own anchor. So these six declare their own
viewBox, sized to exactly what they draw, and the root width/height are
restated to match (QGIS scales a marker by the declared WIDTH, and a
mismatched pair leaves the two disagreeing about the icon's aspect).

**Bridges, minefields, and a SIXTH layer, 2026-09-09.** One request
covering three layers, plus one Land Unit addition.

**Land Unit: Surveillance and Target Acquisition** - "start with a
rectangle, make a triangle with the three vertices as center of the
rectangle and the two bottom edges, add a dot in the center of the
triangle (size half of the artillery unit dot); add a flag pennant on
top without a mast". The dot sits at the triangle's own CENTROID, which
is what "center of the triangle" means for a triangle - not the centre
of its bounding box. The pennant's hoist stands on the triangle's apex,
on the centre line where a mast would be, and points right. Trimmed 15%
on sight, both dimensions, scaled about the hoist's foot so it stays
attached. Land Unit's own count goes to 38.

**The bridge family moves to Mines and Obstacles** - "shift all bridges
to mines and obstacles - but they retain the original colour affiliation
not defaulting to green". The real `bridge` entity moves across (Land
Equipment 56 -> 55) and three synthetic variants join it:
- **Preliminary Demolition** - two dashed parallel lines cut across the
  bridge, "left bottom to right top", the pair straddling its centre so
  the line BETWEEN them passes through (100,100). Dashes lengthened to
  the branch's own established 8,3 - the pattern Bar Mine already uses -
  and the gap between the pair cut 20%, both on sight.
- **Reserve Demolition** - the same cuts, solid.
- **Demolished** - Reserve plus the mirrored pair, making an X.

**This reversed a deliberate decision.** The layer had NO "affiliation"
field, recorded as dead weight because everything on it was fixed
MINE_GREEN. The bridges are the first thing there whose colour is not
fixed, so the field arrives; every other entity still overrides it
internally (the mine family to MINE_GREEN, Booby Trap to its own), so
one expression serves the layer and the field is simply inert for them.
The test that asserted the field's ABSENCE is replaced by one proving
only the bridges respond to it.

**Gap/Safe Lane** - and a lesson about reading a spec. The words were
"start with a bridge in land equipment, add two X inside the parallel
lines of the bridge, now draw a rectangle across the bridge... two mines
on each side; the bridge with cross is over the rectangle". Built from
those words with the bridge left horizontal, which put the strip
vertical and the mines above and below - and a clarifying question was
asked in that same wrong frame, so the answer confirmed the error. The
maintainer's own sketch settled it: the BRIDGE is vertical (milsymbol's
glyph a quarter turn round), the STRIP is horizontal, and the mines sit
two to the LEFT of the bridge and two to the RIGHT. **When a geometric
spec has a chosen orientation, ask for the sketch before building.**

Three further things the sketch and its follow-ups settled:
- **The strip is drawn as two three-sided halves**, each open toward the
  bridge, NOT as one rectangle behind it. The bridge is two thin lines,
  so its channel is transparent and a rectangle behind it showed
  straight through; SVG has no opaque mask that would work over an
  unknown map background. The sketch shows the strip's edges simply
  stopping at the bridge, so they stop.
- **The bridge is widened for this entity only** - milsymbol's own 10
  unit gap leaves ~5 clear once both strokes are counted, and an X
  inside that is a sliver. Opened to 30.
- **The X's centre ON the strip's own edges** - "align the center of Xs
  with the top and bottom lines of the rectangle". An earlier "X, gap of
  half of X width, then X" was read as a measurement ACROSS the bridge
  and declared impossible; it was ALONG it. Read the axis before
  declaring a constraint unsatisfiable.
- **It is the one icon on the branch that mixes two colours** - "the
  mine field along with the rectangle will remain green, the bridge with
  X will only retain the affiliation colours". The obstacle is an
  obstacle whoever laid it; the bridge belongs to somebody.

**Minefield (with number of mines)** - a frame with the count in it and
a chevron band below, mines running along the band. Drawn as a complete
standalone SVG: the Military Police donor trick used elsewhere does not
work here, because Land Equipment renders carry no frame at all and the
framed ground_unit entities are the wrong symbol_set for this layer's
render path. Specified as a chevron "1.5 times rectangle", but the
sketch draws it nearer 1.1 and it was settled there - at 1.5 the arms
reach well past the rectangle and it stops reading as one symbol. Five
mines, one at the apex and two down each arm, inset from the tips.
Fixed MINE_GREEN, per "default colour is green", by joining
MINE_ENTITIES rather than getting a colour rule of its own.

**The count comes from `unique_designation`** - "the number field can be
pulled from the unique designation, we dont need to create a new field
for it" - which removed a whole argument from the plumbing. That entity
therefore skips the usual centred-below designation, or the value would
be drawn twice. It also means arbitrary text can land in it, so the
number shrinks to fit the frame like every other designation here.

**Real bug, found 2026-09-09 while building the Office companion**: the
mine type never reached either of the two entities that read it, so Gap
/ Safe Lane and Minefield both rendered as EMPTY CARRIERS - a bridge or
a frame with no mines in it - whatever the dropdown said.

The Mines and Obstacles expression passes five arguments to
`mct_nonnato_equipment_svg()`; `_render_equipment()` only ever read
four, so `mine_type` was dropped between the layer and the renderer.
The field, the dropdown and the engine were all correct in isolation.

**Why the test suite missed it**: every test stopped on one side of the
gap or the other. There were tests that the field exists, that the
dropdown offers the right four values, that the LINE layer's mine runs
respond to it, and that the engine draws mines when called directly -
but none that followed a mine type from a feature attribute through the
layer's own expression to the drawn symbol. That path was the only one
that failed. Two regression tests now cover it, and both were confirmed
to fail with the fix reverted.

It surfaced because the Office companion exports every symbol by calling
the engine directly, then diffs each file against what the layer's own
expression renders - so the two paths disagreeing became visible
immediately. That check lives in that project as `tools/verify.sh`.

**A sixth layer: Mines and Obstacles Lines (Non-NATO)** - "Minefield
(General) - this will be a line feature". Its own layer because a QGIS
vector layer carries ONE geometry type and its sibling is points.

**It is the branch's first symbol with no SVG at all.** Two
QgsSimpleLineSymbolLayer offset either side of the digitised line are
the "two parallel lines"; one QgsMarkerLineSymbolLayer per mine type
populates it. Alternation falls out of offsetting the antitank run half
an interval along the line. Each run is sized to zero when its type is
not selected - the same "every slot is always present, an unused one
gets size 0" pattern obstacle_control_measures.py already uses, and for
the same reason: a symbol's layers are fixed at build time while
mine_type varies per feature. The interval is set for the WORST case
("both", where the effective spacing halves) rather than tuned for a
single type.

**Mine types are two, not the NATO six** - "use only antipersonnel and
anti-tank" - with four dropdown options: None, Antitank, Antipersonnel,
Both (alternating). None is the default, the same convention the
mobility field uses for "no mark".

**Four viewBox defects, all caught by the render sweep and none by
eye**: the Gap bridge is drawn at milsymbol's 3.75 stroke rather than
the 3 most injected marks use; the minefield chevron's arms end ON A
SLANT, so a butt cap reaches sideways as well as along and half a
stroke of margin is not enough; the frame is drawn at 4; and a long
designation put the minefield's number at x = -318. **A stroke's
allowance must come from the width THAT shape is drawn at, not a shared
constant.**

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
  offset stayed put. The wheels' own vertical offset was then computed
  per feature from the icon's own RENDERED height, via a
  `mct_nonnato_equipment_svg_height()` expression function. (2) The
  designation itself is placed relative to the SVG's own measured
  content, which stopped at the hull - so it tucked under the hull and
  straight through the wheels. `inject_centered_designation_below()`
  grew a `min_content_bottom` argument for exactly this.

  **ALL OF THE ABOVE WAS REVERTED 2026-09-06** - "simplify the apv
  wheeled wheels back to plain injection". The clipping conclusion the
  whole multi-layer approach rested on was wrong (see the Mobility
  indicators entry below for the measurement that disproved it), and
  both follow-on fixes existed ONLY to compensate for the wheels not
  being in the SVG. The wheels are now three `<circle>` elements
  injected by an ordinary `_EQUIPMENT_ENTITY_FIXUPS` entry
  (`apv_wheeled_marks()`), exactly like Bridge Layer Tank's and
  Armoured Recce Vehicle's own marks, and the designation clears them
  by the same content-bounds measurement every other icon uses. Deleted
  with them: `land_equipment_layer_nonnato._wheel_symbol_layers()` and
  its seven supporting constants, the `mct_nonnato_equipment_svg_
  height()` expression function and its `_viewbox_height()` helper, and
  the `min_content_bottom` argument on BOTH
  `inject_centered_designation_below()` and
  `inject_mobility_indicator()` - about 190 lines net. The layer's
  symbol is a single SVG marker layer again. Verified through a real
  map render of the real layer, not just the SVG: wheels drawn in full,
  with and without a designation and with a mobility mark.

  **One migration note**: a QGIS project saved BEFORE this change
  stores the old renderer - three simple-marker wheel layers plus
  expressions calling `mct_nonnato_equipment_svg_height()`, which no
  longer exists. Such a project will show doubled wheels and a broken
  size expression. Re-add the layer. This is acceptable because the
  branch is unmerged and under active development; it would not be if
  it had shipped.

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
  `_text_element_bounds()` already works to.

  **Measured properly during the 2026-09-05 housekeeping sweep**, since
  the first pass only inferred it from one icon looking wrong: rendering
  a single letter at y=100 with and without the attribute and comparing
  the painted rows gives 71..99 both times — Qt's SVG module ignores the
  attribute outright, on both versions, and `y` is always the BASELINE.
  That measurement is now a test, so it fails loudly if a future Qt
  starts honouring it.

  `_text_element_bounds()` had been modelling the attribute as honoured
  (per the SVG spec) and so measured any such element's bottom half a
  cap height too low. Corrected. Blast radius checked before changing
  it — two icons, Improvised Explosives Device and Jammer, whose
  designations move ~10 and ~5 units closer to their glyph, where they
  were always meant to sit. The five Land Unit letter glyphs that also
  carry the attribute are unaffected: their frame is the outer bound,
  not the letter.
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

**Mobility indicators: Tracked and Self-Propelled, 2026-09-06**: "we
need to design two add-ons to land equipment / tracked and self
propelled / both are added to the existing glyph at the bottom, so the
unique designation text needs to shift if selected / they need to
appear as choice - maybe from a dropdown in the dialog box / for
tracked - we use the same glyph as in APV i.e. the ellipse but it is
1/3 the size of the actual glyph / for self-propelled - we need to add
a diamond or rhombus - size 1/3 of the standard rectangle view box".

Not entities: ANY Land Equipment entity can carry one, so this is a new
`mobility` field with its own three-value dropdown (None / Tracked /
Self-Propelled) rather than more rows in the entity list. Stored as
`""`/`"tracked"`/`"self_propelled"`; a NULL or empty value renders
exactly as before, so features predating the field are unaffected.
- **Tracked** is Armoured Protected Vehicle's own stadium at a third of
  its size - 33.3 x 13.3, from its real 100 x 40 bounding box - drawn
  with the same two cubic caps rather than approximated as an ellipse
  or a rounded rectangle.
- **Self-Propelled** is a hollow diamond with equal diagonals of 28.8 -
  a third of milsymbol's own 108-wide standard viewBox (36), less a
  20% trim asked for on sight ("reduce the size of rhombus by 20%"):
  at the full 36 it stood nearly three times taller than the Tracked
  mark beside it, which the two separate size rules had not made
  obvious on paper.
- Both touch the glyph's own bottom edge with no gap ("the oval and
  rhombus should touch the glyph bottom", corrected live) - they are
  part of the symbol, not a label hanging off it, whereas a designation
  still stands clear of the whole thing.
- **The designation shift came free.** It is placed from the SVG's own
  measured ink, and the mark is part of that ink, so it drops below by
  itself - which is what "the unique designation text needs to shift if
  selected" asks for. For Armoured Protection Vehicle (Wheeled) the
  mark takes the same `min_content_bottom` floor the designation
  already had, since that icon's wheels are outside the SVG.

**Real bug, reported live with a screenshot the same day**: "the very
bottom extremity is getting clipped, however when we add the unique
designation, it is ok". The first version grew the viewBox to the
mark's own GEOMETRY, but a stroked path's ink reaches half a stroke
width past that, and every stroke here is widened once more at the end
by `scale_svg_stroke_width()` - so the mark's bottom edge hung ~1.95
units outside the viewBox. A designation hid it by growing the box
further down, which is exactly why it only showed up on unlabelled
features. The viewBox now clears the mark by half its own final stroke
width. The render sweep's viewBox-contains-the-ink invariant caught the
same thing independently, and the regression test deliberately covers
the NO-designation case, since that distinction is the whole bug.

**Correction: there is no QGIS clipping trap, and there never was.**
The Armoured Protection Vehicle (Wheeled) entry above records a
conclusion that QGIS's own marker rendering clips to milsymbol's
original declared draw area, which is why those wheels became separate
QGIS symbol layers. That conclusion is **wrong**. Re-measured
2026-09-06 before designing these marks, by injecting exactly those
wheels into exactly that APV glyph and rendering the marker through a
real map render at 4 / 6 / 8 / 9.6 / 12 / 20 / 40 mm on BOTH QGIS
versions: the wheels draw in full every time, and the rendered ink
grows with the viewBox exactly as it should. Declaring width/height on
the root or omitting them makes no difference either. The maintainer
confirmed independently ("the clipped wheels was an incorrect approach
- it has been fixed since then"). So these marks are injected straight
into the SVG, which is simpler and gets the designation shift for free.
The wheels' own symbol-layer implementation is left as it is because it
works and is tested - not because it is needed; simplifying it back to
plain injection would remove `mct_nonnato_equipment_svg_height()` and
both `min_content_bottom` arguments, and is worth doing if that code is
ever touched again for another reason.

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
- [x] **Designation text size is now uniform on the map (2026-09-05)**
      — flagged when the Vehicle family's own strokes were compensated,
      deliberately deferred that pass rather than widening scope, and
      settled straight after.

      `_DESIGNATION_FONT_SIZE = 28` is in ICON units, and QGIS scales an
      SVG marker so its declared viewBox WIDTH equals the marker size.
      So a length written in icon units draws at
      `length * (marker size * entity multiplier / viewBox width)`, and
      an icon that departs from milsymbol's own 108-wide viewBox, or
      carries a per-entity multiplier, draws its designation at the
      wrong size. Measured before the fix, within Land Equipment: 51
      entities at 1.0, the Vehicle family at **0.52**, Jammer/Radar at
      **1.8**.

      One helper now restates the constant per icon —
      `designation_font_size_in_icon_units(viewbox_width,
      size_multiplier)`, dividing BOTH factors back out — and the
      shrink-to-fit for a long designation works off that compensated
      base rather than the bare constant. Every Land Equipment entity
      now renders its designation at exactly 2.4889 mm, every mine at
      2.0741 mm (the two layers differ only by their own
      MARKER_SIZE_MM, 9.6 vs 8.0, which is intentional).

      **Correction to what was written when this was flagged**: that
      note said Bar Mine "already does" have the problem. It does not.
      Bar Mine has BOTH factors — a 160-wide viewBox AND a 160/108
      multiplier — and they cancel exactly, so its designation was
      already correct and comes out of this untouched. That is the
      entity that proves the fix has to be one formula over both
      factors rather than either one alone, and it is now a test.

      **Jammer/Radar changed as a side effect and this was deliberate**:
      their designations were rendering 1.8x oversized because the
      multiplier that fixes their small GLYPH was scaling their text
      too. Nobody had complained, but the point of the item was
      uniformity, so they were brought into line with everything else
      rather than special-cased.

      **The per-entity multiplier table moved into
      `nonnato_symbol_engine.py`** (`NONNATO_ENTITY_SIZE_MULTIPLIERS`,
      plus `nonnato_entity_size_multiplier_expression()` which each
      layer calls with its OWN entity keys so no layer carries a branch
      for an entity it does not offer). It had been split across
      `land_equipment_layer_nonnato.py` and
      `mines_and_obstacles_layer_nonnato.py`, while the engine needed
      the same numbers to size both the Vehicle family's strokes and
      every icon's designation — that split is exactly how the
      designation came to be wrong for that family. `108` is likewise
      now one named constant near the designation code
      (`_STANDARD_EQUIPMENT_VIEWBOX_WIDTH`) rather than a Vehicle-family
      detail.
- [x] **Land Unit's side designators are now actually middle-aligned**
      — surfaced by the same measurement during the 2026-09-05
      housekeeping sweep, flagged rather than changed unasked, then
      fixed on the maintainer's own go-ahead ("fix the land unit side
      designators too").

      The request was explicit: "both left and right designators should
      be vertically middle aligned to the left or right of the glyph".
      `inject_side_designations()` implements that with
      `dominant-baseline="middle"`, which Qt ignores — so the text is
      painted with its BASELINE on the glyph's centre line instead of
      its middle.

      **The plugin already solves this everywhere else**, which is what
      makes it a defect rather than a limitation: `symbol_engine.
      _apply_dominant_baseline()` bakes the shift into an explicit `y`
      for every label milsymbol emits (it was written for exactly this
      Qt behaviour, after letters collided with centre dots on
      Appendix H's Reference Points). But it runs INSIDE
      `render_symbol_svg()`, and this module's own hand-written `<text>`
      elements are injected afterwards, so they never pass through it.
      The Vehicle family's letter sidesteps it by computing its own
      baseline; the side designations do not. Measured on a plain Infantry frame (frame y 50..150,
      centre 100, designation font size 45): the text paints from y 67.6
      to y 100, visual centre 83.8, so it sits **16.2 units high** —
      about a third of the frame's half-height.

      **Fixed** the same way the Vehicle family's letter already did
      it: drop the attribute, place the baseline at
      `centre + cap height / 2`, so the cap box's own middle lands on
      the content's midpoint. Re-measured on the same Infantry frame,
      the visual centre moves 83.8 → 99.5 against a frame centre of
      100; the residual half-unit is the difference between the 0.7
      cap-height estimate and Arial's real ratio, and is not worth
      chasing.

      It had NOT been applied on the first pass because the position was
      reviewed live and accepted ("the font size is too small to read,
      the position is ok") — but that review was of the same already-off
      rendering, so the acceptance was not evidence the offset was
      wanted. Confirmed live instead of assumed either way.

      The 0.7 cap-height ratio is now one shared constant
      (`_CAP_HEIGHT_RATIO`) covering the bounds estimate, the Vehicle
      family's letter and these designators, rather than three separate
      literals. It is deliberately NOT
      `symbol_engine._apply_dominant_baseline()`'s own ratio: that
      helper reproduces what `dominant-baseline="middle"` is *defined*
      to do (half the font's X-height, 0.2595 em for Arial) because its
      job is honouring an attribute milsymbol emits; here there is no
      attribute to honour, only a request to centre visible uppercase
      ink, which is half the CAP height.
- [ ] Anything else that surfaces while specifying the above
