# -*- coding: utf-8 -*-

"""
Builds the "Areas (Non-NATO)" polygon layer.

New 2026-09-23, dictated as one list: "make a new layer called Areas /
Key Terrain Feature - Area with slanted lines like \\ / Boggy Terrain -
Area with dashes fill like - - - / Restricted Terrain - Area with
horizontal lines fill / Severely Restricted Terrain - Area with
horizontal and verticals lines fill".

Four terrain descriptions, and terrain is terrain whoever holds it:
**there is no affiliation field and no status field**. Every area is
drawn in black with a solid boundary - "yes, always solid", then
"correction - make the colour default black" (both 2026-09-23). The
entity is the only thing the user picks.

Its own layer rather than a row on an existing one because a QGIS
vector layer carries ONE geometry type, and no other non-NATO layer is
polygons.

Like the minefield line layer, this one draws no SVG at all - the
symbols are QGIS's own fill primitives, so they follow whatever area
the user digitises instead of being a fixed icon. Each entity is one
rule on a QgsRuleBasedRenderer keyed on `entity`, the same shape of
thing every Appendix H area layer uses, because the four differ by
whole symbol rather than by one property.

**These four are NOT for the Office companion** - "These are not to be
incorporated into Office fork - so no required to be included there"
(2026-09-23), which is why there is no "For the Office companion"
section on this one's roadmap entry. That is a deliberate exception to
the standing rule, not an omission.

Reachable via the "Areas" entry in the toolbar's "Non-NATO Symbols"
group (see plugin.py), or directly via add_areas_layer_nonnato(iface).

Military Cartography Tools
"""

from qgis.core import (
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFillSymbol,
    QgsLinePatternFillSymbolLayer,
    QgsProject,
    QgsRuleBasedRenderer,
    QgsSimpleLineSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import add_layer_if_absent


LAYER_NAME = "Areas (Non-NATO)"

# Plain black, like every hand-drawn area the plugin already has when
# no affiliation colours it. This layer has no affiliation to colour it
# with.
AREA_COLOUR = "#000000"

KEY_TERRAIN_FEATURE_ENTITY = "nonnato_key_terrain_feature"
BOGGY_TERRAIN_ENTITY = "nonnato_boggy_terrain"
RESTRICTED_TERRAIN_ENTITY = "nonnato_restricted_terrain"
SEVERELY_RESTRICTED_TERRAIN_ENTITY = "nonnato_severely_restricted_terrain"

# The entity keys live here rather than in nonnato_symbol_engine.py
# with the rest of the scheme's: that module is the SVG post-processing
# engine, and nothing on this layer reaches it.
ENTITY_LABELS = {
    KEY_TERRAIN_FEATURE_ENTITY: "Key Terrain Feature",
    BOGGY_TERRAIN_ENTITY: "Boggy Terrain",
    RESTRICTED_TERRAIN_ENTITY: "Restricted Terrain",
    SEVERELY_RESTRICTED_TERRAIN_ENTITY: "Severely Restricted Terrain",
}

DEFAULT_ENTITY = KEY_TERRAIN_FEATURE_ENTITY

# Millimetres, like every other size on these layers.
_BOUNDARY_WIDTH_MM = 0.4

_HATCH_WIDTH_MM = 0.3

# Far enough apart that the individual lines read at map scale, close
# enough that a small area still gets several of them.
_HATCH_SPACING_MM = 2.5

# A line pattern fill's angle is measured CLOCKWISE from horizontal, in
# screen terms - so 45 leans the way a backslash does and 135 the other
# way, which is the opposite of what the anticlockwise convention would
# give. Worth stating: the two are mirror images, a symbol dialogue's
# own thumbnail is too small to tell them apart, and 135 was the first
# guess here. It only shows on a real render.
_BACKSLASH_ANGLE = 45
_HORIZONTAL_ANGLE = 0
_VERTICAL_ANGLE = 90

# Dash, gap - in millimetres, as QgsSimpleLineSymbolLayer's own custom
# dash vector wants them. A long dash and a short gap, so the fill
# reads as a row of dashes rather than as a broken line.
_BOGGY_DASH_PATTERN = [2.0, 1.5]


def _boundary_layer():

    """The solid boundary every one of the four carries."""

    boundary = QgsSimpleLineSymbolLayer()

    boundary.setColor(QColor(AREA_COLOUR))
    boundary.setWidth(_BOUNDARY_WIDTH_MM)

    return boundary


def _hatch_layer(angle, dashes=None):

    """
    One run of parallel lines across the area, at `angle`, optionally
    dashed.

    A QgsLinePatternFillSymbolLayer paints through a SUB-SYMBOL, so the
    colour, the width and the dashes all have to be set on THAT line's
    own symbol layer - setting them on the fill layer itself is
    silently ignored. The same trap left every Weapons Free Zone
    hatched black in 2026-08-12 while its outline was correctly
    coloured; see airspace_control_measures._weapons_free_zone_symbol().
    """

    hatch = QgsLinePatternFillSymbolLayer()

    hatch.setLineAngle(angle)
    hatch.setDistance(_HATCH_SPACING_MM)
    hatch.setLineWidth(_HATCH_WIDTH_MM)
    hatch.setColor(QColor(AREA_COLOUR))

    line = hatch.subSymbol().symbolLayer(0)

    line.setColor(QColor(AREA_COLOUR))
    line.setWidth(_HATCH_WIDTH_MM)

    if dashes:
        line.setUseCustomDashPattern(True)
        line.setCustomDashVector(dashes)

    return hatch


def _area_symbol(*hatches):

    """The boundary, with each hatch run painted inside it."""

    symbol = QgsFillSymbol.createSimple({"style": "no"})

    symbol.changeSymbolLayer(0, _boundary_layer())

    for hatch in hatches:
        symbol.appendSymbolLayer(hatch)

    return symbol


def _key_terrain_feature_symbol():

    """"Area with slanted lines like \\"."""

    return _area_symbol(_hatch_layer(_BACKSLASH_ANGLE))


def _boggy_terrain_symbol():

    """"Area with dashes fill like - - -" - horizontal, and broken."""

    return _area_symbol(
        _hatch_layer(_HORIZONTAL_ANGLE, dashes=_BOGGY_DASH_PATTERN)
    )


def _restricted_terrain_symbol():

    """"Area with horizontal lines fill"."""

    return _area_symbol(_hatch_layer(_HORIZONTAL_ANGLE))


def _severely_restricted_terrain_symbol():

    """
    "Area with horizontal and verticals lines fill" - Restricted
    Terrain's own hatch with a second run crossing it, which is what
    makes the pair read as a progression rather than as two unrelated
    fills.
    """

    return _area_symbol(
        _hatch_layer(_HORIZONTAL_ANGLE),
        _hatch_layer(_VERTICAL_ANGLE),
    )


_SYMBOL_BUILDERS = {
    KEY_TERRAIN_FEATURE_ENTITY: _key_terrain_feature_symbol,
    BOGGY_TERRAIN_ENTITY: _boggy_terrain_symbol,
    RESTRICTED_TERRAIN_ENTITY: _restricted_terrain_symbol,
    SEVERELY_RESTRICTED_TERRAIN_ENTITY: _severely_restricted_terrain_symbol,
}


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _configure_attribute_form(layer):

    fields = layer.fields()

    layer.setEditorWidgetSetup(
        fields.indexOf("entity"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(ENTITY_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("entity"), QgsDefaultValue(f"'{DEFAULT_ENTITY}'")
    )


def _build_renderer():

    """
    One rule per entity, keyed on `entity` - the four differ by whole
    symbol, not by one property, so there is nothing to data-define.

    _control_measure_shared._build_rule_based_renderer() does the same
    job for Appendix H but filters on `measure_type`, which this layer
    does not have.
    """

    root_rule = QgsRuleBasedRenderer.Rule(None)

    for entity, build_symbol in _SYMBOL_BUILDERS.items():

        rule = QgsRuleBasedRenderer.Rule(build_symbol())

        rule.setFilterExpression(f'"entity" = \'{entity}\'')
        rule.setLabel(ENTITY_LABELS[entity])

        root_rule.appendChild(rule)

    return QgsRuleBasedRenderer(root_rule)


def build_areas_layer_nonnato():

    """A fresh, empty polygon layer - never added to the project itself, see add_areas_layer_nonnato()."""

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Polygon?crs={crs.authid()}", LAYER_NAME, "memory"
    )

    layer.dataProvider().addAttributes([
        QgsField("entity", QMetaType.Type.QString),
    ])

    layer.updateFields()

    _configure_attribute_form(layer)

    layer.setRenderer(_build_renderer())

    return layer


def add_areas_layer_nonnato(iface):

    """Adds the layer to the project, unless one of the same name is already there - the same helper every other non-NATO layer uses."""

    return add_layer_if_absent(iface, LAYER_NAME, build_areas_layer_nonnato)
