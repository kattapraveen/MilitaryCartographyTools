# -*- coding: utf-8 -*-

"""
Builds the "Mines and Obstacles (Non-NATO)" point layer.

New 2026-09-03, at the maintainer's own request ("let's move all the
mines to a different layer - say mines and obstacles; shift booby trap
also into this new layer") - consolidates two groups of entities that
were previously split across two other non-NATO layers purely because
of where their REAL APP-6E vocabulary happened to sit, even though both
groups already shared the same real behaviour: fixed green, never
affiliation-coloured, custom (non-milsymbol-default) icons.

- The nine-entity mine family (three real APP-6E `land_equipment`
  entities plus six synthetic icons with no SIDC at all) - moved out of
  Land Equipment (Non-NATO), where they used to live purely because
  their real APP-6E entity, where they have one, happens to sit in that
  symbol_set. See nonnato_symbol_engine.py's own "Mine family (Land
  Equipment)" section comment - still accurate about the RENDERING
  logic (unchanged, layer-agnostic), just no longer accurate about
  which QGIS layer calls it.
- Booby Trap (`booby_trap`) - moved out of Control Measure Points
  (Non-NATO), where it was the one custom-icon exception on an
  otherwise plain-milsymbol layer. See nonnato_symbol_engine.
  booby_trap_control_measure_svg()'s own docstring for the icon itself
  (unchanged) - only which layer offers it has changed.

No "affiliation" field at all - a deliberate simplification, not an
oversight: every entity on this layer is fixed MINE_GREEN regardless of
affiliation (confirmed already true for all nine mine entities before
this layer existed, and Booby Trap never took an affiliation argument
in the first place), so a field that could never change what gets
drawn would be dead weight on the attribute form. The rendering
functions still need SOME affiliation value passed through (Booby Trap
aside), so a fixed `'friend'` literal is used in the expression instead
of a live field reference - purely a plumbing detail, invisible to a
user of this layer.

MARKER_SIZE_MM reset to the scheme's own plain 8.0mm default, NOT Land
Equipment's own 20%-bigger 9.6mm the mine family used to inherit purely
by virtue of sitting on that layer - that multiplier was requested
"in land equipment, i want all the glyphs to be 20% bigger by default"
specifically for Land Equipment as a whole, not for mines in
particular, so it does not follow them here. Matches Booby Trap's own
prior 8.0mm on Control Measure Points too, so neither group changes
visual size as a side effect of this move.

Reachable via its own "Mines and Obstacles" entry in the toolbar's
"Non-NATO Symbols" group (see plugin.py), or directly via
add_mines_and_obstacles_layer_nonnato(iface).

Military Cartography Tools
"""

from qgis.core import (
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType

from ._control_measure_shared import (
    add_layer_if_absent,
    configure_rotation_and_scale_fields,
)
from .nonnato_symbol_engine import (
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY,
    BAR_MINE_ENTITY,
    DIRECTIONAL_MINE_ENTITY,
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY,
    INFLUENCE_MINE_ANTI_TANK_ENTITY,
    UNKNOWN_MINE_ENTITY,
    nonnato_entity_size_multiplier_expression,
    stabilised_nonnato_size_expression,
)


LAYER_NAME = "Mines and Obstacles (Non-NATO)"

MARKER_SIZE_MM = 8.0

BOOBY_TRAP_ENTITY = "booby_trap"

DEFAULT_ENTITY = "land_mine"

# The ten required entities - nine real/synthetic mines plus Booby
# Trap, moved in from Land Equipment (Non-NATO) and Control Measure
# Points (Non-NATO) respectively - see this module's own docstring.
# Real entity keys are unchanged (render_nonnato_equipment_svg()'s own
# build_sidc() call still resolves the three real ones directly);
# synthetic keys are nonnato_symbol_engine.py's own, also unchanged.
ENTITY_LABELS = {
    BOOBY_TRAP_ENTITY: "Booby Trap",
    "land_mine": "Antipersonnel Mine",
    "antitank_mine": "Antitank Mine",
    "antipersonnel_land_mine": "Antipersonnel Fragmentation Mine",
    UNKNOWN_MINE_ENTITY: "Unknown Mine",
    INFLUENCE_MINE_ANTI_TANK_ENTITY: "Influence Mine (Anti Tank)",
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY: "Influence Mine (Anti Personnel)",
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY: "Antitank Mine Booby Trapped",
    BAR_MINE_ENTITY: "Bar Mine",
    DIRECTIONAL_MINE_ENTITY: "Directional Mine",
}

# Every mine entity shares one designation field; Booby Trap never
# takes a designation at all (mct_nonnato_booby_trap_svg() takes no
# arguments) - its own branch below simply never references this.
_DESIGNATION_EXPRESSION = 'upper(coalesce("unique_designation", \'\'))'

# The affiliation argument every mct_nonnato_equipment_svg() call still
# needs is a fixed literal, not a field reference - see this module's
# own docstring for why there is no live "affiliation" field to read
# from at all.
_NAME_EXPRESSION = (
    "CASE"
    f" WHEN \"entity\" = '{BOOBY_TRAP_ENTITY}' THEN mct_nonnato_booby_trap_svg()"
    " ELSE mct_nonnato_equipment_svg("
    f"'friend',\"entity\",{_DESIGNATION_EXPRESSION})"
    " END"
)

_SCALED_SIZE_EXPRESSION = f'{MARKER_SIZE_MM:g} * coalesce("scale", 100) / 100.0'

# Bar Mine's own 160-unit viewBox (wider than every other mine's 108,
# to make room for the rectangle below the circle) made the SAME
# 22-unit circle read smaller on screen, since QGIS sizes an SVG marker
# off its declared width - reported live 2026-09-03: "bar mine - the
# size of the circle is too small... and therefore, the bar below the
# circle is also increased in size". A per-entity multiplier of exactly
# the viewBox-width ratio fixes it and grows the rectangle right along
# with the circle. That multiplier now lives in nonnato_symbol_engine's
# own shared table (2026-09-05) rather than here, because the engine
# has to divide it back out again when sizing designation text - see
# NONNATO_ENTITY_SIZE_MULTIPLIERS.
_MINE_SIZE_MULTIPLIER_EXPRESSION = nonnato_entity_size_multiplier_expression(
    ENTITY_LABELS
)

_MINE_SCALED_SIZE_EXPRESSION = (
    f"({_SCALED_SIZE_EXPRESSION}) * ({_MINE_SIZE_MULTIPLIER_EXPRESSION})"
)

# Booby Trap never carries a designation, so its size needs no
# stabilisation ratio - the plain scaled size is already correct, same
# as it was on Control Measure Points. Every mine entity keeps the
# existing mct_nonnato_equipment_svg_width()-based ratio, same as it
# was on Land Equipment.
_SIZE_EXPRESSION = (
    "CASE"
    f" WHEN \"entity\" = '{BOOBY_TRAP_ENTITY}' THEN ({_SCALED_SIZE_EXPRESSION})"
    " ELSE ("
    + stabilised_nonnato_size_expression(
        _MINE_SCALED_SIZE_EXPRESSION,
        'mct_nonnato_equipment_svg_width('
        f'\'friend\',"entity",{_DESIGNATION_EXPRESSION})',
        'mct_nonnato_equipment_svg_width(\'friend\',"entity",\'\')',
    )
    + ")"
    " END"
)


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

    configure_rotation_and_scale_fields(layer)


def _build_renderer():

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(MARKER_SIZE_MM)

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        QgsProperty.fromExpression(_SIZE_EXPRESSION)
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(_NAME_EXPRESSION)
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Angle,
        QgsProperty.fromExpression('coalesce("rotation", 0)')
    )

    symbol.changeSymbolLayer(0, svg_layer)

    return QgsSingleSymbolRenderer(symbol)


def build_mines_and_obstacles_layer_nonnato():

    """A fresh, empty "Mines and Obstacles (Non-NATO)" layer - never added to the project itself, see add_mines_and_obstacles_layer_nonnato()."""

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        LAYER_NAME,
        "memory"
    )

    attributes = [
        QgsField("entity", QMetaType.Type.QString),
        QgsField("unique_designation", QMetaType.Type.QString),
        QgsField("rotation", QMetaType.Type.Double),
        QgsField("scale", QMetaType.Type.Double),
    ]

    layer.dataProvider().addAttributes(attributes)

    layer.updateFields()

    _configure_attribute_form(layer)

    layer.setRenderer(_build_renderer())

    return layer


def add_mines_and_obstacles_layer_nonnato(iface):

    return add_layer_if_absent(
        iface,
        LAYER_NAME,
        build_mines_and_obstacles_layer_nonnato,
    )
