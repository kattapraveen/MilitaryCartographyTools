# -*- coding: utf-8 -*-

"""
Shared "replace this layer in place" helper for the terrain/ dialogs
(Tanaka Contours, Hypsometric Tint) - both want re-running their
dialog with tweaked settings to correct the existing layer rather
than piling up a new one, AND to leave the corrected layer wherever
the user has since dragged it in the Layers panel, rather than
resetting it to whatever position a fresh generate_*() call would
place a brand new layer at by default (top of the tree for Tanaka
Contours, bottom for Hypsometric Tint).

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


def replace_named_layer(name, generate):

    """
    Call generate() (a zero-arg callable that builds and adds a fresh
    replacement layer - generate_tanaka_contours()/
    generate_hypsometric_tint()/generate_line_of_sight(), already
    bound to their own arguments via a lambda/partial at the call
    site); if it succeeds, remove every existing layer named `name`
    and - if a prior layer existed - move the new layer to the same
    layer tree position the old one occupied.

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

    if remembered_position is not None:

        parent, index = remembered_position

        root = project.layerTreeRoot()

        node = root.findLayer(
            new_layer.id()
        )

        if node is not None:

            # No direct "move" API on QgsLayerTreeGroup - undo
            # whichever default placement generate() just used and
            # insert fresh at the remembered position instead.
            node.parent().removeChildNode(
                node
            )

            parent.insertLayer(
                index,
                new_layer
            )

    return new_layer
