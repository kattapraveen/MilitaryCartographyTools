# Non-NATO Symbology — Rules Tracker

Working tracker for the maintainer to lay out non-NATO symbology rules
rule-by-rule, and check off as each is specified. Lives on the
`non-nato-symbology` branch; not part of `main` until this work is
ready to integrate (see `docs/roadmap.md`'s note on why this is a
separate branch).

This is a rules record, not a design doc — capture what the maintainer
says here verbatim/close to verbatim, not an interpretation of it.

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
- [ ] **Installations**
- [ ] **Civilians**
- [ ] Any other general category not covered by the above

## Part B — Per-domain confirmation

Whether Part A's rules apply as-is, or a domain needs its own
exception. (Land already covers Unit/Civilian/Equipment/Installation
as its own four sub-categories above.)

- [ ] Land
- [ ] Air
- [ ] Sea Surface
- [ ] Subsurface
- [ ] Space
- [ ] Cyberspace
- [ ] SIGINT
- [ ] Activities

## Part C — Control measures (Appendix H tactical graphics)

Lines/areas/points for boundaries, objectives, obstacles, fire
support, etc. — structurally different from units/equipment, likely
needs its own rules rather than inheriting Part A.

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

- [ ] Affiliation colour palette — exact colours per affiliation
      (friend/hostile/neutral/unknown/...), and whether it matches or
      diverges from the NATO palette already in use
- [ ] Icon source — reuse milsymbol.js glyphs as-is, a modified subset,
      or an entirely separate icon set for non-NATO
- [ ] Echelon / amplifier conventions (if any carry over)
- [ ] Line weight / stroke width conventions
- [ ] Status (present/planned/etc.) convention — still dashed vs solid?
- [ ] Designation / label placement conventions
- [ ] Anything else that surfaces while specifying the above
