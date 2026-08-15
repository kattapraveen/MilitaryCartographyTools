# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.23 (Table H-XXI, "CBRN defense control
measure symbols") - Mini-Phase H18. Printed pages 606-614, 27 code
rows.

**This module currently builds the table's POINTS only - 18 of the 27.**
The remaining nine are areas and lines and are audited but deliberately
NOT built yet; see TABLE_H_XXI_REMAINING below for what they are and
what has to be settled before they can be.

**Why the split is a clean one, not an arbitrary stopping place.**
Every one of the 18 point codes (281300-281809) is backed by a real
milsymbol icon - checked directly against milsymbol's own
src/numbersidc/sidc/control-measure.js, entry by entry, not inferred
from the code prefix. None of the nine area/line codes
(271700-272200) is, which is expected: milsymbol has no line or
polygon support at all, so every line and area in this appendix has
always been hand-built. So the points are mechanical and the areas
are new drawing work, and they divide exactly there.

**Colour: affiliation, not green.** As with Table H-XX, the green is
H.5.21.1's own explicit exception for obstacles and H.5.23 claims
nothing like it. For milsymbol-rendered points the affiliation hue
comes free (see control_measure_points.py's own docstring).

**Four of the 18 are RELOCATED, not new**: Chemical/Biological/Nuclear/
Radiological Event already existed in sidc.py and were offered on the
shared control_measure_points.py layer. They move here with the rest
of their table, exactly as Tables H-VI, H-IX, H-XIII, H-XIX and H-XX's
own points did before them. The other 14 are new vocabulary.

**Field T (unique designation).** Every row in the table carries it -
to the right of the box on the decontamination points, at the lower
left of the triangle on the events - and it reaches the symbol through
mct_sidc_svg's own text channel, wired in the shared point-layer
builder (see _point_symbol_layer.py, where it was missing until
2026-08-13). milsymbol's `uniqueDesignation` slot is the right one
here: probed directly, it places the text to the RIGHT of the box,
where the template puts T, while `uniqueDesignation1` places it INSIDE
the box, which is the template's own T1. One icon,
Biological - Toxic Industrial Material (281401), defines no
designation slot at all in milsymbol even though the table draws a T
on it; passing one is a harmless no-op, so that row simply shows no
designation.

**One quirk worth knowing before anyone reports it as a bug**: Nuclear
Event (281500) and Nuclear Fallout Producing Event (281600) are two
distinct codes that milsymbol draws with the SAME icon
(TP.NUCLEAR EVENT). That is the standard's own doing - the two rows
have different names and different codes but no drawn difference -
and it is pinned by a test so it reads as a known fact rather than a
duplication defect.
"""

from ._control_measure_shared import (
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_status_field,
    _value_map,
    add_layer_if_absent,
)

from ._point_symbol_layer import build_single_domain_point_layer

import base64

from qgis.core import (
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFillSymbol,
    QgsGeometryGeneratorSymbolLayer,
    QgsLinePatternFillSymbolLayer,
    QgsMarkerSymbol,
    QgsMaskMarkerSymbolLayer,
    QgsProject,
    QgsProperty,
    QgsSimpleLineSymbolLayer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbol,
    QgsSymbolLayer,
    QgsSymbolLayerReference,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType

from qgis.PyQt.QtGui import QColor


POINTS_LAYER_NAME = "CBRN Defense Points"

# Table H-XXI's own 18 point entries, in the standard's own order.
# Names follow the standard's own CONTROL MEASURE column, cross-checked
# against milsymbol's own icon names.
POINT_ENTITY_LABELS = {
    "chemical_event": "Chemical Event",
    "chemical_toxic_industrial_material":
        "Chemical - Toxic Industrial Material",
    "biological_event": "Biological Event",
    "biological_toxic_industrial_material":
        "Biological - Toxic Industrial Material",
    "nuclear_event": "Nuclear Event",
    "nuclear_fallout_producing_event": "Nuclear Fallout Producing Event",
    "radiological_event": "Radiological Event",
    "radiological_toxic_industrial_material":
        "Radiological - Toxic Industrial Material",
    "decontamination_point": "Decontamination Point/Site",
    "decontamination_point_alternate":
        "Decontamination Point/Site - Alternate",
    "decontamination_point_equipment":
        "Decontamination Point/Site - Equipment",
    "decontamination_point_troops": "Decontamination Point/Site - Troops",
    "decontamination_point_equipment_troops":
        "Decontamination Point/Site - Equipment and Troops",
    "decontamination_point_operational":
        "Decontamination Point/Site - Operational",
    "decontamination_point_thorough":
        "Decontamination Point/Site - Thorough",
    "decontamination_point_main_equipment":
        "Main Equipment Decontamination Point/Site",
    "decontamination_point_forward_troop":
        "Forward Troop Decontamination Point/Site",
    "decontamination_point_wounded_personnel":
        "Wounded Personnel Decontamination Site",
}

POINT_ENTITY_CODES = {
    "chemical_event": "281300",
    "chemical_toxic_industrial_material": "281301",
    "biological_event": "281400",
    "biological_toxic_industrial_material": "281401",
    "nuclear_event": "281500",
    "nuclear_fallout_producing_event": "281600",
    "radiological_event": "281700",
    "radiological_toxic_industrial_material": "281701",
    "decontamination_point": "281800",
    "decontamination_point_alternate": "281801",
    "decontamination_point_equipment": "281802",
    "decontamination_point_troops": "281803",
    "decontamination_point_equipment_troops": "281804",
    "decontamination_point_operational": "281805",
    "decontamination_point_thorough": "281806",
    "decontamination_point_main_equipment": "281807",
    "decontamination_point_forward_troop": "281808",
    "decontamination_point_wounded_personnel": "281809",
}

# The two codes the standard distinguishes but does not draw
# differently - see the module docstring.
SHARED_GLYPH_CODES = ("281500", "281600")

# **The eight events are drawn smaller than the ten decontamination
# points, and that is milsymbol's bounding boxes, not this layer.**
#
# Every event icon (281300-281701) is a wide, low inverted triangle
# whose declared box is 158x118; every decontamination point
# (281800-281809) is a narrow, tall box-and-spike at 88x168. QGIS
# sizes an SVG marker by its WIDTH, so at one marker size the events
# render at 8/158 mm per icon unit against the decon points' 8/88 -
# barely more than half the scale, and unreadable next to them, which
# is what the maintainer's smoke test reported.
#
# Their number: 30%, asked for directly. Note that matching the decon
# points' drawn scale exactly would be 158/88, about 80% - so this is
# a legibility call rather than a normalisation, and is theirs to
# revisit.
_EVENT_MARKER_SIZE_SCALE = 1.30

_EVENT_ENTITIES = (
    "chemical_event",
    "chemical_toxic_industrial_material",
    "biological_event",
    "biological_toxic_industrial_material",
    "nuclear_event",
    "nuclear_fallout_producing_event",
    "radiological_event",
    "radiological_toxic_industrial_material",
)

POINT_MARKER_SIZE_SCALES = {
    entity: _EVENT_MARKER_SIZE_SCALE for entity in _EVENT_ENTITIES
}

# **Field T1, not Field T, on the ten decontamination points** - where
# their own templates put the designation.
#
# Every 2818xx template draws it INSIDE the lower part of the box, in
# the box marked "T1", and the standard's own examples fill it -
# "1/2COY" under Forward Troop Decontamination Point/Site's own "DCN
# (F) T", "4CBRN" under Wounded Personnel Decontamination Site's "DCN
# W". Field T is a separate box outside the symbol, to its upper right.
# Until 2026-08-14 all ten put it in T.
#
# Found while fixing the identical defect on Tables H-XXII and H-XXIII,
# whose supply/sustainment boxes are the same shape with the same T1
# box; applied here at the maintainer's own instruction after being
# raised, since this table had already been signed off. milsymbol
# exposes the position as `uniqueDesignation1` at (100, 30), against
# Field T's (150, -30) - probed per icon, not assumed.
#
# **The eight EVENTS are deliberately not here.** They are a different
# icon family - a wide inverted triangle, not the box - and milsymbol
# gives them one text position only, at (40, 90). Nothing to move.
POINT_DESIGNATION_SLOTS = {
    entity: "uniqueDesignation1"
    for entity in POINT_ENTITY_CODES
    if entity not in _EVENT_ENTITIES
}

# --- Audited, NOT built. ---
#
# The last two rows of Table H-XXI, neither backed by a milsymbol
# icon. Recorded here so the gap is explicit rather than looking like
# an oversight, and so whoever builds them starts from the audit
# rather than re-reading the table.
#
# Minimum Safe Distance Zone (272100) is a circle - its own draw rules
# DO number it (a centre point plus a radius point), so it could be
# built without asking anything.
#
# Radiation Dose Rate Contour Line (272200) is a plain line carrying a
# dose-rate label at each end, in the same shape as Table H-III's own
# Boundary labelling.
TABLE_H_XXI_REMAINING = {
    "272100": "Minimum Safe Distance Zone",
    "272200": "Radiation Dose Rate Contour Line",
}


def create_cbrn_defense_points_layer(name=POINTS_LAYER_NAME):

    """
    Table H-XXI's own 18 point symbols, milsymbol-rendered.

    No echelon and no headquarters flag, the same call every other
    control-measure point layer in this project makes - Appendix H's
    own amplifier table gives them neither.
    """

    return build_single_domain_point_layer(
        name,
        "control_measure",
        POINT_ENTITY_LABELS,
        "chemical_event",
        include_echelon=False,
        include_headquarters=False,
        entity_marker_size_scales=POINT_MARKER_SIZE_SCALES,
        entity_designation_slots=POINT_DESIGNATION_SLOTS,
    )


def add_cbrn_defense_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_cbrn_defense_points_layer,
    )


# ============================================================
# Table H-XXI's seven contaminated areas
# ============================================================
#
# One construction, seven rows: a freeform outline of at least three
# anchor points, a yellow hatched fill, and one glyph centred inside
# it - an inverted triangle carrying B/C/N/R, with a "T" beneath the
# letter on the Toxic Industrial Material variants.
#
# **The glyph was the blocker, and it was a false one.** Until
# 2026-08-15 this module recorded that the triangle "does not exist in
# milsymbol, so it has to be drawn", with proportions the standard
# never gives - which is why the seven sat unbuilt while every other
# row of the table shipped. The maintainer's answer was simply "the
# appropriate milsymbol inside", and they were right: the triangle in
# each area's own template picture is pixel-for-pixel the icon
# milsymbol already draws for the matching EVENT point in this same
# table. Nothing had to be drawn at all. Confirmed by probe render of
# all seven event codes - identical viewBox, identical triangle path -
# and the areas simply borrow them, which is also why a Toxic
# Industrial Material area gets its "T" for free.
#
# The area codes themselves (2717xx-2720xx) render NOTHING through
# milsymbol - probed, all seven return its empty placeholder - so the
# glyph is addressed by the event's own entity, not by the area's.
AREAS_LAYER_NAME = "CBRN Contaminated Areas"

# The standard's own CONTROL MEASURE column, verbatim. Note 272001:
# it is "Radiological Contaminated Area - Toxic Industrial Material",
# matching its six siblings - this module's own audit list previously
# abbreviated it to "Radiological Contaminated Material", which is not
# what the table says.
AREA_MEASURE_TYPE_LABELS = {
    "biological": "Biological Contaminated Area",
    "biological_tim":
        "Biological Contaminated Area - Toxic Industrial Material",
    "chemical": "Chemical Contaminated Area",
    "chemical_tim":
        "Chemical Contaminated Area - Toxic Industrial Material",
    "nuclear": "Nuclear Contaminated Area",
    "radiological": "Radiological Contaminated Area",
    "radiological_tim":
        "Radiological Contaminated Area - Toxic Industrial Material",
}

AREA_MEASURE_TYPE_CODES = {
    "biological": "271700",
    "biological_tim": "271701",
    "chemical": "271800",
    "chemical_tim": "271801",
    "nuclear": "271900",
    "radiological": "272000",
    "radiological_tim": "272001",
}

# Which of this table's own EVENT points supplies each area's glyph.
# Every pairing is the standard's own: the area row and the event row
# draw the same triangle with the same letter, and the Toxic
# Industrial Material rows pair with the Toxic Industrial Material
# events, which is where the extra "T" comes from.
AREA_GLYPH_ENTITIES = {
    "biological": "biological_event",
    "biological_tim": "biological_toxic_industrial_material",
    "chemical": "chemical_event",
    "chemical_tim": "chemical_toxic_industrial_material",
    "nuclear": "nuclear_event",
    "radiological": "radiological_event",
    "radiological_tim": "radiological_toxic_industrial_material",
}

_AREA_HATCH_LAYER_ID = "cbrn_contaminated_area_hatch"

# Yellow is the standard's own, not an affiliation colour: every one
# of the seven template pictures fills with the same yellow hatch
# whatever the symbol's identity, exactly as Table H-XIX's obstacles
# are green whatever theirs. The OUTLINE still follows affiliation
# per H.5.3, which nothing here overrides.
_AREA_HATCH_COLOR = QColor(255, 255, 0)

# Thick, at the maintainer's own instruction - and matching the
# template, where the yellow bars are about as wide as the white gaps
# between them.
_AREA_HATCH_WIDTH_MM = 1.0
_AREA_HATCH_DISTANCE_MM = 2.4
_AREA_HATCH_ANGLE_DEG = 45

_AREA_OUTLINE_WIDTH_MM = 0.4

# --- the glyph's own geometry, read off milsymbol's own output ---
#
# Every one of the seven event icons renders into the same box - a
# viewBox of "21 -14 158 118" with the triangle at (40,-10),
# (160,-10), (100,100) and a stroke width of 3. Probed for all seven,
# not assumed from one.
_GLYPH_VIEWBOX_WIDTH = 158.0

# The centre of that viewBox is (100, 45), which is also the centre of
# the triangle's own bounding box - so the marker's anchor point sits
# exactly on the middle of the drawn triangle, and no offset is needed.
# The two TOP corners are the furthest points from it: hypot(60, 55),
# plus half the stroke so the outline itself is inside the clearance
# too.
_GLYPH_CORNER_RATIO = (
    ((60.0 ** 2 + 55.0 ** 2) ** 0.5) + 1.5
) / _GLYPH_VIEWBOX_WIDTH

# The gap the maintainer asked for between the glyph and the outline.
_GLYPH_CLEARANCE_MM = 3.0

# A floor, so the glyph never disappears completely. It is reached
# only when the area itself is a few millimetres across on the page,
# where nothing can both fit inside and be legible - at that zoom the
# glyph deliberately overflows its own area rather than vanishing.
_GLYPH_MIN_SIZE_MM = 3.0

# The shape the hatch is cut away behind: the triangle alone, filled,
# in the icon's own coordinate system, so that at the same marker size
# it lands exactly on the drawn triangle. The template shows the hatch
# stopping at the triangle's outline and the interior clean - not a
# white box around the glyph - so masking the triangle is the whole
# job. Stroked as well as filled, at milsymbol's own stroke width, so
# the cut covers the drawn outline rather than stopping inside it.
_GLYPH_MASK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="158" height="118"'
    ' viewBox="21 -14 158 118">'
    '<path d="M 100,100 40,-10 160,-10 z" fill="black" stroke="black"'
    ' stroke-width="3"/></svg>'
)

_GLYPH_MASK_PATH = "base64:" + base64.b64encode(
    _GLYPH_MASK_SVG.encode("utf-8")
).decode("ascii")


def _area_glyph_sidc_expression():

    """
    The SIDC of the EVENT point whose icon this area borrows - see the
    section comment above for why an area's own code cannot be used
    (milsymbol draws nothing at all for 2717xx-2720xx).
    """

    cases = " ".join(
        f"WHEN \"measure_type\" = '{measure_type}' THEN '{entity}'"
        for measure_type, entity in AREA_GLYPH_ENTITIES.items()
    )

    entity_expression = f"CASE {cases} ELSE 'chemical_event' END"

    return (
        "mct_sidc_svg(mct_build_sidc("
        f"\"affiliation\",{entity_expression},'control_measure',"
        "'unspecified',\"status\",false))"
    )


def _area_glyph_size_expression():

    """
    The marker size, in millimetres, that makes the glyph as large as
    it can be while keeping _GLYPH_CLEARANCE_MM between its own
    furthest corner and the area's outline.

    The glyph is inscribed in the largest circle that fits inside the
    polygon, shrunk by the clearance: a corner at exactly
    (inscribed radius - clearance) from the circle's own centre is, by
    definition of that circle, at least `clearance` from every edge.
    That is deliberately conservative for a long thin area - only the
    two top corners ever reach that far - and it is what makes the
    guarantee hold for ANY shape the user digitizes, including a
    crescent, rather than only for the blobs the template draws.

    `geometry(@feature)`, NOT `$geometry`: inside the sub-symbol of a
    geometry generator (or a centroid fill) `$geometry` is the POINT
    being drawn, not the feature's own polygon, and this function
    returns 0 for a point - which silently collapsed the glyph to its
    floor until it was rendered and measured.
    """

    radius = (
        "coalesce(mct_inscribed_radius_mm("
        "geometry(@feature), @map_extent, @map_scale), 0)"
    )

    return (
        f"max({_GLYPH_MIN_SIZE_MM},"
        f" ({radius} - {_GLYPH_CLEARANCE_MM}) / {_GLYPH_CORNER_RATIO:.6f})"
    )


def _area_hatch_layer():

    hatch_layer = QgsLinePatternFillSymbolLayer()

    # The id the glyph's own mask cuts into - see _area_glyph_layer().
    hatch_layer.setId(_AREA_HATCH_LAYER_ID)

    hatch_layer.setLineAngle(_AREA_HATCH_ANGLE_DEG)
    hatch_layer.setDistance(_AREA_HATCH_DISTANCE_MM)

    # The colour and width MUST go on the sub-symbol's own line layer,
    # not on the pattern-fill layer itself, where QGIS silently ignores
    # them - a bug this project has shipped twice before (Weapons Free
    # Zone, then No Fire Area).
    hatch_line = hatch_layer.subSymbol().symbolLayer(0)

    hatch_line.setWidth(_AREA_HATCH_WIDTH_MM)
    hatch_line.setColor(_AREA_HATCH_COLOR)

    return hatch_layer


def _area_outline_layer():

    outline_layer = QgsSimpleLineSymbolLayer()

    outline_layer.setColor(QColor(0, 0, 0))
    outline_layer.setWidth(_AREA_OUTLINE_WIDTH_MM)

    _apply_affiliation_color(
        outline_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    outline_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    return outline_layer


def _area_glyph_layer(layer):

    """
    The centred glyph, plus the mask that clears the hatch out from
    behind it - both drawn at the area's own pole of inaccessibility.

    **The pole, not point_on_surface().** The size is computed for a
    circle centred on the pole, so drawing anywhere else breaks the
    clearance the size was chosen for: built first on a centroid fill
    (which offers point-on-surface and nothing better), the glyph's own
    corners crossed the outline in the render.

    A QgsMaskMarkerSymbolLayer nested inside a geometry generator DOES
    reach a sibling fill layer of the same symbol - verified by render,
    and worth stating because the reverse is not true: a masked layer
    nested inside a geometry generator cannot be reached at all, which
    this project has hit twice.
    """

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Marker)

    generator.setGeometryExpression("mct_inscribed_centre($geometry)")

    size = QgsProperty.fromExpression(_area_glyph_size_expression())

    mask_shape = QgsSvgMarkerSymbolLayer(_GLYPH_MASK_PATH)

    mask_shape.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        size
    )

    mask_layer = QgsMaskMarkerSymbolLayer()

    mask_layer.setSubSymbol(QgsMarkerSymbol([mask_shape]))

    mask_layer.setMasks(
        [QgsSymbolLayerReference(layer.id(), _AREA_HATCH_LAYER_ID)]
    )

    glyph_layer = QgsSvgMarkerSymbolLayer("")

    glyph_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(_area_glyph_sidc_expression())
    )

    glyph_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        size
    )

    generator.setSubSymbol(
        QgsMarkerSymbol([mask_layer, glyph_layer])
    )

    return generator


def _contaminated_area_symbol(layer):

    """
    All seven rows draw identically apart from the letter inside the
    triangle, so there is one symbol builder rather than seven - the
    per-row difference is entirely inside
    _area_glyph_sidc_expression()'s own CASE.
    """

    symbol = QgsFillSymbol.createSimple({"style": "no"})

    symbol.changeSymbolLayer(0, _area_hatch_layer())
    symbol.appendSymbolLayer(_area_outline_layer())
    symbol.appendSymbolLayer(_area_glyph_layer(layer))

    return symbol


def create_cbrn_contaminated_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Table H-XXI's own seven
    contaminated areas.

    No unique_designation field: unlike almost every other area in this
    appendix, not one of the seven template pictures carries a text
    amplifier at all - the glyph is the whole symbol.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Polygon?crs={crs.authid()}",
        name,
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("area_km2", QMetaType.Type.Double),
            QgsField("perimeter_km", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    measure_type_idx = layer.fields().indexOf("measure_type")

    layer.setEditorWidgetSetup(
        measure_type_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(AREA_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        measure_type_idx,
        QgsDefaultValue("'chemical'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("area_km2"),
        QgsDefaultValue("mct_area_km2($geometry)", True)
    )

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("perimeter_km"),
        QgsDefaultValue("mct_perimeter_km($geometry)", True)
    )

    # One builder for every row - _build_rule_based_renderer still gets
    # a rule per measure_type so the layer's own legend names all seven,
    # which a single-symbol renderer could not.
    layer.setRenderer(
        _build_rule_based_renderer(
            layer,
            {
                measure_type: (lambda: _contaminated_area_symbol(layer))
                for measure_type in AREA_MEASURE_TYPE_LABELS
            }
        )
    )

    return layer


def add_cbrn_contaminated_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_cbrn_contaminated_areas_layer,
    )
