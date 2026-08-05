# -*- coding: utf-8 -*-

"""
Shared "replace this layer in place" helper, originally built for the
terrain/ dialogs (Tanaka Contours, Hypsometric Tint, Combined
Hillshade, Line of Sight, Viewshed) - re-running one of those with
tweaked settings should correct the existing layer rather than piling
up a new one, AND leave the corrected layer wherever the user has
since dragged it in the Layers panel, rather than resetting it to
whatever position a fresh generate would place a brand new layer at
by default. Later reused as-is by waypoints/gpx_kml_dialog.py, since
nothing about it is actually terrain-specific - moved here from
terrain/_layer_utils.py once a second, unrelated feature family
needed it.

generate_*()/import_*() functions build and style a layer but
deliberately don't add it to the project/tree themselves - this
module owns ALL project/tree insertion, in exactly one explicit place
per call. Earlier, generate_*() self-inserted (via
QgsProject.addMapLayer()) and this module then removed-and-reinserted
that same layer to reposition it - confirmed live as a real bug: a
plain addMapLayer() call in a live QGIS session is influenced by
QgsLayerTreeRegistryBridge's "current insertion point" (tied to
whatever's selected in the Layers panel), something no headless test
can reproduce (there's no Layers panel widget), and the extra
remove-then-reinsert churn on the very layer `generate()` just added
was a second, independent source of fragility. Building the layer
without inserting it, then inserting it exactly once at an explicit
position, sidesteps both.

Military Cartography Tools
"""

from qgis.core import QgsProject


def _layer_tree_position(layer):

    """
    (parent_group, index_within_parent) for layer's own node in the
    current project's layer tree, or None if it has no node (e.g.
    never added to the legend).
    """

    root = QgsProject.instance().layerTreeRoot()

    node = root.findLayer(
        layer.id()
    )

    if node is None:
        return None

    parent = node.parent()

    return parent, parent.children().index(node)


def add_layer_at_default_position(project, layer, default_insert_position):

    """
    Add layer to project (not yet in the legend) and position it via
    default_insert_position(project, layer) - used for the "Add as
    new layer" path, where there's no previous layer's position to
    inherit, so the feature's own default placement (e.g. top of the
    tree for a vector overlay, bottom for a raster fill) applies.
    """

    project.addMapLayer(
        layer,
        False
    )

    default_insert_position(
        project,
        layer
    )

    return layer


def replace_named_layer(name, generate, default_insert_position):

    """
    Call generate() (a zero-arg callable that builds and styles a
    fresh replacement layer - generate_tanaka_contours()/
    generate_hypsometric_tint()/generate_hillshade_combination()/
    generate_line_of_sight(), already bound to their own arguments via
    a lambda/closure at the call site - WITHOUT adding it to the
    project); if it succeeds, remove every existing layer named `name`
    and insert the new layer exactly once - at the old layer's own
    tree position if one existed, or via default_insert_position(
    project, layer) otherwise (a small per-feature callback that knows
    that feature's own sensible default placement).

    Without the position-preservation, a user who has manually
    dragged the layer to a different spot in the Layers panel finds
    it reset to the default position on every regenerate, which reads
    as the plugin ignoring their own organisation of the project.

    generate() can genuinely return None - not every caller is
    guaranteed to succeed (generate_line_of_sight() does, when the
    observer/target point falls outside the DEM). Old layers are only
    removed once generate() has actually produced a replacement, so a
    failed regenerate leaves any existing layer alone instead of
    deleting it for nothing; returns None in that case.
    """

    project = QgsProject.instance()

    existing = project.mapLayersByName(name)

    remembered_position = None

    if existing:
        remembered_position = _layer_tree_position(existing[0])

    new_layer = generate()

    if new_layer is None:
        return None

    for layer in existing:

        project.removeMapLayer(
            layer.id()
        )

    project.addMapLayer(
        new_layer,
        False
    )

    if remembered_position is not None:

        parent, index = remembered_position

        # The remembered index came from the OLD layer, which has
        # since been removed - the parent's current child count may
        # be smaller now, so clamp defensively rather than risk an
        # out-of-range insert.
        index = min(
            index,
            len(parent.children())
        )

        parent.insertLayer(
            index,
            new_layer
        )

    else:

        default_insert_position(
            project,
            new_layer
        )

    return new_layer
