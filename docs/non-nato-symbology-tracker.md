# Non-NATO Symbology — Rules Tracker

Working tracker for the maintainer to lay out non-NATO symbology rules
rule-by-rule, and check off as each is specified. Lives on the
`non-nato-symbology` branch; not part of `main` until this work is
ready to integrate (see `docs/roadmap.md`'s note on why this is a
separate branch).

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
      glyph, affiliation by the glyph's own outline colour).
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
- [x] **Symbology standard edition** — APP-6E (MIL-STD-2525E) entity
      vocabulary only; APP-6D/2525D is not used for non-NATO symbology.
- [ ] Designation / label placement conventions — to be specified
      later.
- [ ] Anything else that surfaces while specifying the above
