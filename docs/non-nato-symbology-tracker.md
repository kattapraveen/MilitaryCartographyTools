# Non-NATO Symbology — Rules Record

**Frozen reference, not an active checklist.** This started as a
rule-by-rule tracker (with a companion interactive HTML checklist,
since dropped once its job was done - the rules that mattered are
captured here). From this point on, remaining rules are worked out
directly during implementation rather than specified upfront; this
file stays as the record of what was already settled before that
switch. Lives on the `non-nato-symbology` branch; not part of `main`
until this work is ready to integrate (see `docs/roadmap.md`'s note on
why this is a separate branch).

This is a rules record, not a design doc — capture what the maintainer
says here verbatim/close to verbatim, not an interpretation of it.

**Current scope (as of 2026-08-26): Land, plus a Land-scoped slice of
SIGINT (Jammer/Radar only) and a yet-to-be-picked subset of Control
Measures.** Every other domain (Air, Sea Surface, Subsurface, Space,
Cyberspace, Activities, Mine Warfare, and the rest of SIGINT) has been
reviewed against the catalog and marked not required outright — not
deferred, genuinely out of scope for this work. Rules below are being
worked out against two reference documents the maintainer supplied —
`reference/non-nato/MIL-STD-2525D_Symbol_Catalog.pdf` and
`reference/non-nato/symbol_check_sheets.html` (both gitignored, kept
locally only, same as the rest of `reference/`).

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
        shape as part of what makes the entity recognizable. "No fill"
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
- [x] **Mine Warfare** — not required *(catalog section not
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
      - Battalion — renamed **Battalion/Regiment/Squadron**.
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
- [ ] Designation / label placement conventions — to be specified
      later.
- [ ] Anything else that surfaces while specifying the above
