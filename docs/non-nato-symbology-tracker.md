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
Military Intelligence, Military Police, Parachute Rigger, Signal,
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
- **Parachute Rigger** (`parachute_rigger`): composite icon. Add the
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

**Land Equipment (58 of 189, five with no APP-6E equivalent - see
below):** Air Defence Gun (Light), Air Defence Gun (Medium), Air
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
Mine** *(new, no entity key - see Icon modifications below)*, Vehicle.

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
Booby Trapped, Bar Mine, Antipersonnel Fragmentation Mine, Unknown
Mine, and Booby Trap (the Control Measure Point, see below) alike.

**SIGINT Land (2 of 2 - unchanged):** Jammer, Radar - matches what was
already the entire in-scope SIGINT list, so no narrowing needed here.

**Control Measure Points (11 of 241):** Booby Trap, Decision Point,
Fort, Impact Point, Observation Post, Artillery Observation Post,
Point Of Interest, Pill Box, Shelter Above Ground, Shelter Below
Ground, Target.

**Renamed 2026-08-31** (entity key unchanged, display label only):
- `target_reference_point` "Target Reference Point" -> **Target**
- `shelter` "Shelter" -> **Pill Box** *(the "Shelter Above Ground"/
  "Shelter Below Ground" entities are separate keys, left unchanged)*
- `observation_post_forward_observer` "Observation Post Forward
  Observer" -> **Artillery Observation Post**

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

**SIGINT designation position, corrected 2026-09-02**: reported live,
against a rendered screenshot - "in both sigint glyphs - the unique
designator is too far from the icon - get it closer similar to other
land unit glyphs". Confirmed live that milsymbol places a designation
at a fixed y="160" regardless of how far down the icon's own artwork
actually reaches - fine for a full Unit frame (drawn to y=150, a
10-unit gap) but far too distant for SIGINT's own compact bare glyphs
(Jammer's "J", Radar's hook - both drawn no lower than ~y=120). Moved
to y="130" for both Jammer and Radar.

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
- [ ] Designation / label placement conventions — to be specified
      later.
- [ ] Anything else that surfaces while specifying the above
