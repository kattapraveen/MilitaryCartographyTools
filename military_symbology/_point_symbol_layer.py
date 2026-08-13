# -*- coding: utf-8 -*-

"""
Shared builder for a single-symbol-set "<Domain>"
point layer: one entity vocabulary, one fixed SIDC symbol_set, a plain
affiliation/entity/echelon/status/headquarters/unique_designation
attribute form, and a renderer that computes each feature's own
MIL-STD-2525/APP-6 symbol live via mct_build_sidc()/mct_sidc_svg().

Factored out of military_symbology/unit_layer.py (2026-08-08) once the
appendix-by-appendix completion plan called for each MIL-STD-2525D
appendix to get its OWN dedicated layer + icon, rather than everything
funneling into the single shared "Units" layer
(ground_unit/air/sea_surface/subsurface together via a cascading
symbol_set/entity dropdown). unit_layer.py itself is untouched for now -
it will be retired domain-by-domain as Appendices C/D/E/F's own
mini-phases split their entities out into layers built with this module,
not all at once, to keep the appendix-by-appendix sequence strict.

Each single-domain layer built here has exactly one symbol_set, baked
into the renderer expression as a literal string rather than stored as
a per-feature field - there's nothing to cascade when a layer only ever
represents one domain, so the ValueRelation lookup-layer machinery
unit_layer.py needs for its multi-domain case simply doesn't exist here.
The one exception (added 2026-08-08 for Appendix J, SIGINT): a small,
fixed "Dimension" field (dimension_labels/dimension_symbol_sets below,
never more than 5 known values, no lookup layer) for the rare appendix
whose SAME entity vocabulary is genuinely spread across several symbol
sets - see _symbol_set_expression()'s own docstring for the distinction
from entity_symbol_set_overrides.

Deliberately NOT a generate_*()/replace_named_layer() feature, same
reasoning as unit_layer.py: this layer's content is hand-placed
operational data a user digitizes with QGIS's own native point-editing
tools, not something safe to silently regenerate - add_single_domain_
point_layer() only ever builds a fresh layer, warning instead of
replacing if one already exists under the same name.

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

from ..core._layer_utils import add_layer_at_default_position


DEFAULT_MARKER_SIZE_MM = 8.0

# Shared across every single-domain layer this module builds. Table VII
# (Ch 5) shows echelon (Field B) and headquarters (Field S) aren't
# applicable to every domain - e.g. Appendix B's own Table B-II (Space
# symbol amplifiers) lists neither field at all - so both are now
# per-layer opt-in (include_echelon/include_headquarters below), unlike
# unit_layer.py's own older pattern of always including both regardless
# of domain.
_AFFILIATION_LABELS = {
    "friend": "Friend",
    "hostile": "Hostile",
    "neutral": "Neutral",
    "unknown": "Unknown",
}

_ECHELON_LABELS = {
    "unspecified": "Unspecified",
    "team_crew": "Team/Crew",
    "squad": "Squad",
    "section": "Section",
    "platoon": "Platoon",
    "company": "Company",
    "battalion": "Battalion",
    "regiment": "Regiment",
    "brigade": "Brigade",
    "division": "Division",
    "corps": "Corps",
    "army": "Army",
    # Table D-III's own three highest echelons - added 2026-08-09
    # alongside sidc.py's own ECHELONS extension (see that dict's own
    # comment); every layer built with this module gains these three
    # values automatically since they all share this one label dict.
    "army_group": "Army Group",
    "theater": "Theater",
    "command": "Command",
}

_STATUS_LABELS = {
    "present": "Present",
    "planned": "Planned",
}


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _value_map_with_none(labels, none_label="(None)"):

    """
    Same as _value_map(), plus a leading `none_label` -> "" entry - used
    for the sector 1/2 modifier dropdowns, where "no modifier" (SIDC
    code "00") is the common case and must be explicitly selectable
    (empty string, not a missing/invalid value) rather than only
    reachable by clearing the field some other way.
    """

    result = {none_label: ""}

    result.update(_value_map(labels))

    return result


def _configure_attribute_form(
    layer,
    entity_labels,
    default_entity,
    include_echelon,
    include_headquarters,
    sector1_labels,
    sector2_labels,
    dimension_labels=None,
    default_dimension=None,
):

    fields = layer.fields()

    affiliation_idx = fields.indexOf("affiliation")
    entity_idx = fields.indexOf("entity")
    status_idx = fields.indexOf("status")

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_AFFILIATION_LABELS)}
        )
    )

    if dimension_labels:

        dimension_idx = fields.indexOf("dimension")

        layer.setEditorWidgetSetup(
            dimension_idx,
            QgsEditorWidgetSetup(
                "ValueMap",
                {"map": _value_map(dimension_labels)}
            )
        )

        layer.setDefaultValueDefinition(dimension_idx, QgsDefaultValue(f"'{default_dimension}'"))

    layer.setEditorWidgetSetup(
        entity_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(entity_labels)}
        )
    )

    layer.setEditorWidgetSetup(
        status_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_STATUS_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(affiliation_idx, QgsDefaultValue("'friend'"))
    layer.setDefaultValueDefinition(entity_idx, QgsDefaultValue(f"'{default_entity}'"))
    layer.setDefaultValueDefinition(status_idx, QgsDefaultValue("'present'"))

    if include_echelon:

        echelon_idx = fields.indexOf("echelon")

        layer.setEditorWidgetSetup(
            echelon_idx,
            QgsEditorWidgetSetup(
                "ValueMap",
                {"map": _value_map(_ECHELON_LABELS)}
            )
        )

        layer.setDefaultValueDefinition(echelon_idx, QgsDefaultValue("'unspecified'"))

    if include_headquarters:

        headquarters_idx = fields.indexOf("headquarters")

        layer.setEditorWidgetSetup(
            headquarters_idx,
            QgsEditorWidgetSetup("CheckBox", {})
        )

        layer.setDefaultValueDefinition(headquarters_idx, QgsDefaultValue("false"))

    if sector1_labels:

        sector1_idx = fields.indexOf("sector1_modifier")

        layer.setEditorWidgetSetup(
            sector1_idx,
            QgsEditorWidgetSetup(
                "ValueMap",
                {"map": _value_map_with_none(sector1_labels)}
            )
        )

        layer.setDefaultValueDefinition(sector1_idx, QgsDefaultValue("''"))

    if sector2_labels:

        sector2_idx = fields.indexOf("sector2_modifier")

        layer.setEditorWidgetSetup(
            sector2_idx,
            QgsEditorWidgetSetup(
                "ValueMap",
                {"map": _value_map_with_none(sector2_labels)}
            )
        )

        layer.setDefaultValueDefinition(sector2_idx, QgsDefaultValue("''"))


def _symbol_set_expression(default_symbol_set, entity_symbol_set_overrides, dimension_symbol_sets=None):

    """
    The SIDC expression's own "symbol_set" argument - normally just the
    layer's one literal symbol_set, quoted. `entity_symbol_set_overrides`
    (an optional {entity_key: symbol_set} dict) lets a small number of
    entities that are technically a DIFFERENT SIDC symbol set live in
    this same layer's entity dropdown anyway, via a CASE expression keyed
    on the feature's own "entity" value - e.g. space_layer.py folding
    Space Missile's single entity (symbol set "06") into the "Space"
    layer (symbol set "05") rather than giving it a whole second layer
    for one entity. Not meant for large-scale mixing of domains - if a
    layer's overrides dict starts covering more than a handful of
    entities, it should probably be its own layer instead.

    `dimension_symbol_sets` (an optional {dimension_key: symbol_set}
    dict) is the other, genuinely different case that needs: a single
    entity vocabulary that is IDENTICAL across several symbol sets, with
    a separate "dimension" field (not the entity itself) choosing which
    one applies - e.g. sigint_layer.py's "Communications"/"Jammer"/
    "Radar" entities, which mean the same thing whether the SIGINT
    platform is in space, air, land, sea surface, or subsurface (Table
    J-II's own SymbolSetCode column literally lists all five symbol sets
    against the same four entity codes) - entity_symbol_set_overrides
    would need one entry per (entity, dimension) combination to express
    that, well past "a handful". Takes priority over
    entity_symbol_set_overrides when both are given (no layer needs
    both at once yet).
    """

    if dimension_symbol_sets:

        clauses = " ".join(
            f'WHEN "dimension" = \'{dimension}\' THEN \'{symbol_set}\''
            for dimension, symbol_set in dimension_symbol_sets.items()
        )

        return f"CASE {clauses} ELSE '{default_symbol_set}' END"

    if not entity_symbol_set_overrides:
        return f"'{default_symbol_set}'"

    clauses = " ".join(
        f'WHEN "entity" = \'{entity}\' THEN \'{symbol_set}\''
        for entity, symbol_set in entity_symbol_set_overrides.items()
    )

    return f"CASE {clauses} ELSE '{default_symbol_set}' END"


def _build_renderer(
    symbol_set,
    marker_size_mm,
    entity_symbol_set_overrides=None,
    include_echelon=True,
    include_headquarters=True,
    sector1_labels=None,
    sector2_labels=None,
    dimension_symbol_sets=None,
    entity_marker_size_scales=None,
):

    """
    Same mct_build_sidc()/mct_sidc_svg() data-defined-SVG-path pattern
    as unit_layer.py's own _build_renderer(), except symbol_set is a
    literal string (or a small CASE expression, see
    _symbol_set_expression()) baked into the expression rather than a
    field reference - this layer represents one domain (with, at most,
    a couple of documented exceptions), not a user-chosen field.
    mct_build_sidc() always needs all 6 positional arguments (plus,
    optionally, the two modifier ones), so when a domain excludes
    echelon/headquarters/either modifier (no field on the layer - see
    include_echelon/include_headquarters/sector1_labels/sector2_labels),
    the expression passes the "no amplifier" literal for that argument
    instead of a field reference: "unspecified" for echelon, false for
    headquarters, empty string for either modifier.
    """

    symbol_set_expr = _symbol_set_expression(
        symbol_set,
        entity_symbol_set_overrides,
        dimension_symbol_sets
    )

    echelon_expr = '"echelon"' if include_echelon else "'unspecified'"
    headquarters_expr = '"headquarters"' if include_headquarters else "false"
    sector1_expr = '"sector1_modifier"' if sector1_labels else "''"
    sector2_expr = '"sector2_modifier"' if sector2_labels else "''"

    # The layer's own "unique_designation" (Field T) goes through
    # mct_sidc_svg's SEPARATE text channel, not through the SIDC - the
    # SIDC string encodes structured attributes only and has no room
    # for free text.
    #
    # **This was missing until 2026-08-13**, so every layer built
    # through this helper collected a designation in its attribute
    # table and then drew nothing with it. That is the exact defect
    # the maintainer found on 2026-08-10 in c2_measures.py,
    # defensive_control_measures.py and control_measure_points.py -
    # each of which carries its own SIDC expression and was fixed
    # there - and this shared builder simply never got the same
    # treatment. Found again on Table H-XXI's own decontamination
    # points, whose Field T the standard puts to the right of the box.
    #
    # upper(...) per H.5.4's own all-caps rule; coalesce(..., '')
    # because QGIS short-circuits the whole call to NULL on any NULL
    # argument, which would blank the icon rather than just its text.
    # An empty string is treated as "no designation" inside
    # mct_sidc_svg, so an untouched field costs nothing.
    expression = (
        'mct_sidc_svg(mct_build_sidc('
        f'"affiliation","entity",{symbol_set_expr},'
        f'{echelon_expr},"status",{headquarters_expr},'
        f'{sector1_expr},{sector2_expr}'
        '),'
        'upper(coalesce("unique_designation", \'\')),'
        "'uniqueDesignation'"
        ')'
    )

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(marker_size_mm)

    # Some icons are drawn at a visibly different scale from their own
    # siblings because milsymbol's declared bounding box for them is a
    # different shape - QGIS sizes an SVG marker by its WIDTH, so a
    # wide-and-short icon comes out small next to a narrow-and-tall
    # one. Where that is worth correcting, the caller passes a per-
    # entity multiplier; see cbrn_defense.py, the first to need it.
    if entity_marker_size_scales:

        clauses = " ".join(
            f"WHEN \"entity\" = '{entity}' THEN {marker_size_mm * scale:g}"
            for entity, scale in entity_marker_size_scales.items()
        )

        svg_layer.setDataDefinedProperty(
            QgsSymbolLayer.Property.Size,
            QgsProperty.fromExpression(
                f"CASE {clauses} ELSE {marker_size_mm:g} END"
            )
        )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(expression)
    )

    symbol.changeSymbolLayer(0, svg_layer)

    return QgsSingleSymbolRenderer(symbol)


def build_single_domain_point_layer(
    name,
    symbol_set,
    entity_labels,
    default_entity,
    marker_size_mm=DEFAULT_MARKER_SIZE_MM,
    entity_symbol_set_overrides=None,
    include_echelon=True,
    include_headquarters=True,
    sector1_labels=None,
    sector2_labels=None,
    dimension_labels=None,
    dimension_symbol_sets=None,
    default_dimension=None,
    entity_marker_size_scales=None,
):

    """
    A fresh, empty, single-symbol-set point layer named `name` - see
    this module's own docstring. `symbol_set` is baked into the
    renderer as a literal (never a per-feature field); `entity_labels`
    is this layer's own {entity_key: display_label} vocabulary (see
    e.g. military_symbology/sidc.py's ENTITIES["space"]).
    `entity_symbol_set_overrides` (optional) lets a handful of entities
    resolve to a different symbol_set than the layer's default - see
    _symbol_set_expression()'s own docstring. `include_echelon`/
    `include_headquarters` control whether this domain gets those two
    fields at all - not every domain's own amplifier table (Ch 5 Table
    VII / each appendix's own domain-specific table) includes them; see
    this module's own docstring. `sector1_labels`/`sector2_labels`
    (optional {modifier_key: display_label} dicts, mirroring
    entity_labels - see e.g. sidc.py's MODIFIERS["space"]["sector1"])
    add the corresponding "Sector 1/2 Modifier" field, each with an
    explicit "(None)" option (see _value_map_with_none()) for "no
    modifier" - omit either to leave that field off entirely, the same
    opt-in pattern as include_echelon/include_headquarters. If this
    layer's entity_symbol_set_overrides spans more than one symbol_set
    (e.g. space_layer.py's "missile"), pass the UNION of every relevant
    symbol_set's own sector1/sector2 vocabulary here - the field stores
    a plain modifier key, and mct_build_sidc() looks it up against
    whichever symbol_set the feature's own entity actually resolves to.
    build_sidc() itself does raise KeyError for a key that's invalid for
    the resolved symbol_set (see sidc.py's own tests) - but
    mct_build_sidc() catches that and returns the error text as a plain
    string, which mct_sidc_svg()/milsymbol.js then may still render as
    SOME symbol (its own fallback for an unparseable SIDC, not
    necessarily an obviously-broken one) rather than visibly failing -
    so this is NOT a guaranteed clean, visible error at the rendered-map
    level. Callers should keep merged vocabularies free of keys that
    mean genuinely different things across the merged symbol_sets, and
    lean on sidc.py's own build_sidc() tests (not a rendered-symbol
    check) to guard the real contract here. Never added to
    the project itself - callers use add_single_domain_point_layer() (or
    their own project.addMapLayer()) exactly once.

    `dimension_labels`/`dimension_symbol_sets`/`default_dimension` are
    the other multi-symbol-set case - see _symbol_set_expression()'s own
    docstring for when to reach for this instead of
    entity_symbol_set_overrides. `dimension_labels` (optional
    {dimension_key: display_label}) adds a "Dimension" field (placed
    right after Affiliation, before Entity, matching the standard's own
    symbol-building order of choosing dimension/standard-identity before
    the icon); `dimension_symbol_sets` (optional {dimension_key:
    symbol_set}) is the CASE mapping actually used by the renderer;
    `default_dimension` sets the field's default value. All three must
    be given together or not at all - dimension_labels' keys and
    dimension_symbol_sets' keys should match exactly.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        name,
        "memory"
    )

    attributes = [
        QgsField("affiliation", QMetaType.Type.QString),
    ]

    if dimension_labels:
        attributes.append(QgsField("dimension", QMetaType.Type.QString))

    attributes.append(QgsField("entity", QMetaType.Type.QString))

    if include_echelon:
        attributes.append(QgsField("echelon", QMetaType.Type.QString))

    attributes.append(QgsField("status", QMetaType.Type.QString))

    if include_headquarters:
        attributes.append(QgsField("headquarters", QMetaType.Type.Bool))

    if sector1_labels:
        attributes.append(QgsField("sector1_modifier", QMetaType.Type.QString))

    if sector2_labels:
        attributes.append(QgsField("sector2_modifier", QMetaType.Type.QString))

    attributes.append(QgsField("unique_designation", QMetaType.Type.QString))

    layer.dataProvider().addAttributes(attributes)

    layer.updateFields()

    _configure_attribute_form(
        layer,
        entity_labels,
        default_entity,
        include_echelon,
        include_headquarters,
        sector1_labels,
        sector2_labels,
        dimension_labels,
        default_dimension,
    )

    layer.setRenderer(
        _build_renderer(
            symbol_set,
            marker_size_mm,
            entity_symbol_set_overrides,
            include_echelon,
            include_headquarters,
            sector1_labels,
            sector2_labels,
            dimension_symbol_sets,
            entity_marker_size_scales,
        )
    )

    return layer


def default_insert_position(project, layer):

    """Top of the layer tree - matches unit_layer.py's own convention."""

    root = project.layerTreeRoot()

    root.insertLayer(
        0,
        layer
    )


def add_single_domain_point_layer(
    iface,
    name,
    symbol_set,
    entity_labels,
    default_entity,
    marker_size_mm=DEFAULT_MARKER_SIZE_MM,
    entity_symbol_set_overrides=None,
    include_echelon=True,
    include_headquarters=True,
    sector1_labels=None,
    sector2_labels=None,
    dimension_labels=None,
    dimension_symbol_sets=None,
    default_dimension=None,
    entity_marker_size_scales=None,
):

    """
    Guard-and-insert helper shared by every single-domain appendix
    layer's own add_*_layer(iface) - if a layer named `name` already
    exists, warns and does nothing (see this module's own docstring for
    why silently replacing it would be a data-loss bug); otherwise
    builds and inserts a fresh one. Returns the new layer, or None if
    one already existed.
    """

    project = QgsProject.instance()

    if project.mapLayersByName(name):

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            f'A "{name}" layer already exists - use the Layers panel '
            "to work with it, or rename it first if you want a second "
            "one."
        )

        return None

    layer = build_single_domain_point_layer(
        name,
        symbol_set,
        entity_labels,
        default_entity,
        marker_size_mm,
        entity_symbol_set_overrides,
        include_echelon,
        include_headquarters,
        sector1_labels,
        sector2_labels,
        dimension_labels,
        dimension_symbol_sets,
        default_dimension,
        entity_marker_size_scales,
    )

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )
