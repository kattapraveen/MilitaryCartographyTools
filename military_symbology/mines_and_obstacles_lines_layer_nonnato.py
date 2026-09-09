# -*- coding: utf-8 -*-

"""
Builds the "Mines and Obstacles Lines (Non-NATO)" line layer.

New 2026-09-09: "Minefield (General) - this will be a line feature -
type of mines will be required input, draw two parallel lines, populate
the mines as per selection".

Its own layer rather than a row on mines_and_obstacles_layer_nonnato.py
because a QGIS vector layer carries ONE geometry type, and that one is
points. Everything else about it matches its point sibling - the same
mine-type vocabulary, the same fixed MINE_GREEN, the same toolbar group.

Unlike every other non-NATO layer, this one draws no SVG at all. The
symbol is built from QGIS's own line primitives, so it follows whatever
line the user digitises instead of being a fixed icon dropped on a
point:

- two QgsSimpleLineSymbolLayer, offset either side of the digitised
  line, which are the "two parallel lines";
- one QgsMarkerLineSymbolLayer per mine type, placed at a fixed
  interval along the line, which is how the mines "populate".

Alternation falls out of that: the antitank run is offset half an
interval along the line from the antipersonnel one, so with both types
selected they interleave. Each run is sized to zero when its own type
is not selected - the same "every slot is always present, an unused one
gets size 0" pattern obstacle_control_measures._mine_glyph_marker_
layers() already uses, and for the same reason: a symbol's layers are
fixed when it is built, while mine_type varies per feature.

Reachable via the "Mines and Obstacles (Lines)" entry in the toolbar's
"Non-NATO Symbols" group (see plugin.py), or directly via
add_mines_and_obstacles_lines_layer_nonnato(iface).

Military Cartography Tools
"""

from qgis.core import (
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSingleSymbolRenderer,
    QgsSymbolLayer,
    QgsTemplatedLineSymbolLayerBase,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import add_layer_if_absent
from .nonnato_symbol_engine import (
    MINE_GREEN,
    MINE_TYPE_ANTIPERSONNEL,
    MINE_TYPE_ANTITANK,
    MINE_TYPE_BOTH,
    MINE_TYPE_LABELS,
    MINEFIELD_GENERAL_ENTITY,
)


LAYER_NAME = "Mines and Obstacles Lines (Non-NATO)"

DEFAULT_ENTITY = MINEFIELD_GENERAL_ENTITY

ENTITY_LABELS = {
    MINEFIELD_GENERAL_ENTITY: "Minefield (General)",
}

# Millimetres, like every other size on these layers.
_LINE_WIDTH_MM = 0.5

# Half the distance between the two parallel lines, so they sit either
# side of the line the user actually drew.
_LINE_OFFSET_MM = 1.6

_MINE_DIAMETER_MM = 1.8

# Far enough apart that the mines read individually at map scale, close
# enough that a short line still gets several. Set for the WORST case -
# "both", where the two runs interleave and the effective spacing is
# half this - so that case is not cramped.
_MINE_INTERVAL_MM = 7.0

_MINE_TYPE_EXPRESSION = 'coalesce("mine_type", \'\')'


def _mine_run_is_drawn(mine_type):

    """
    True when this run's own type is selected - either on its own or as
    half of "both".
    """

    return (
        f"CASE WHEN {_MINE_TYPE_EXPRESSION} IN "
        f"('{mine_type}', '{MINE_TYPE_BOTH}') THEN 1 ELSE 0 END"
    )


def _parallel_line_layers():

    layers = []

    for offset in (-_LINE_OFFSET_MM, _LINE_OFFSET_MM):

        line = QgsSimpleLineSymbolLayer(QColor(MINE_GREEN))

        line.setWidth(_LINE_WIDTH_MM)
        line.setOffset(offset)

        layers.append(line)

    return layers


def _mine_run_layers():

    """One marker line per mine type - see this module's own docstring."""

    layers = []

    runs = (
        (MINE_TYPE_ANTIPERSONNEL, False, 0.0),
        # Half an interval along, so the two interleave when both are
        # selected rather than landing on top of each other.
        (MINE_TYPE_ANTITANK, True, _MINE_INTERVAL_MM / 2),
    )

    for mine_type, filled, along in runs:

        mine = QgsSimpleMarkerSymbolLayer(
            QgsSimpleMarkerSymbolLayerBase.Shape.Circle
        )

        mine.setSize(_MINE_DIAMETER_MM)
        mine.setStrokeColor(QColor(MINE_GREEN))
        mine.setStrokeWidth(_LINE_WIDTH_MM)
        mine.setFillColor(
            QColor(MINE_GREEN) if filled else QColor(0, 0, 0, 0)
        )

        mine.setDataDefinedProperty(
            QgsSymbolLayer.Property.Size,
            QgsProperty.fromExpression(
                f"({_mine_run_is_drawn(mine_type)}) * {_MINE_DIAMETER_MM:g}"
            )
        )

        marker_line = QgsMarkerLineSymbolLayer()

        marker_line.setPlacements(
            QgsTemplatedLineSymbolLayerBase.Placement.Interval
        )
        marker_line.setInterval(_MINE_INTERVAL_MM)
        marker_line.setOffsetAlongLine(along)

        marker_line.setSubSymbol(QgsMarkerSymbol([mine]))

        layers.append(marker_line)

    return layers


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

    layer.setEditorWidgetSetup(
        fields.indexOf("mine_type"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(MINE_TYPE_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("mine_type"), QgsDefaultValue("''")
    )


def _build_renderer():

    symbol = QgsLineSymbol()

    parallels = _parallel_line_layers()

    symbol.changeSymbolLayer(0, parallels[0])

    for layer in parallels[1:] + _mine_run_layers():
        symbol.appendSymbolLayer(layer)

    return QgsSingleSymbolRenderer(symbol)


def build_mines_and_obstacles_lines_layer_nonnato():

    """A fresh, empty line layer - never added to the project itself, see add_mines_and_obstacles_lines_layer_nonnato()."""

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"LineString?crs={crs.authid()}", LAYER_NAME, "memory"
    )

    layer.dataProvider().addAttributes([
        QgsField("entity", QMetaType.Type.QString),
        QgsField("mine_type", QMetaType.Type.QString),
    ])

    layer.updateFields()

    _configure_attribute_form(layer)

    layer.setRenderer(_build_renderer())

    return layer


def add_mines_and_obstacles_lines_layer_nonnato(iface):

    """Adds the layer to the project, unless one of the same name is already there - same helper its point sibling uses."""

    return add_layer_if_absent(
        iface,
        LAYER_NAME,
        build_mines_and_obstacles_lines_layer_nonnato,
    )
