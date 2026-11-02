# -*- coding: utf-8 -*-

"""
Shared post-processing for the terrain algorithms: style the layer
the way its own module does, replace any earlier layer of the same
name rather than piling another one up beside it, and put the result
where the old one was sitting.

**Why this has to survive the move to Processing.** A Processing
algorithm always emits a NEW output and drops it at the top of the
Layers panel, but these tools came from dialogs that deliberately
corrected the existing layer in place instead. Both halves of that
exist because of real usability complaints, and both had regression
coverage before the move:

  - "every run of the dialog was creating a brand new layer, so
    tweaking settings and re-running left a pile of stale layers
    behind instead of correcting the existing one";
  - and a layer the user had dragged somewhere in the Layers panel
    came back at the default position on every regenerate, "which
    reads as the plugin ignoring their own organisation of the
    project" (core/_layer_utils.py, which the dialogs used for this).

Converting without either would hand those complaints straight back.
core/_layer_utils.py itself cannot be reused as-is: it both builds
and inserts the layer, whereas by the time a post-processor runs
Processing has already added this one to the project and to the tree.
The node is therefore MOVED here rather than inserted - and the order
that move is done in is load-bearing, for the reason set out on
_reposition() below.

`context.project()` is available inside postProcessLayer(), which
runs on the main thread after the layer is loaded, so all of this is
safe to do there - confirmed before any of it was written.

Military Cartography Tools
"""

from qgis.core import QgsProcessingLayerPostProcessorInterface


class StyleAndReplacePostProcessor(QgsProcessingLayerPostProcessorInterface):

    """
    Held in a class-level registry because Processing keeps only a
    weak reference to a post-processor: without it Python collects
    the object before the layer is loaded and the styling silently
    never happens. The same trap the range-rings prototype already
    guarded against.
    """

    _instances = []

    def __init__(self, layer_name, style, replace_existing, default_position):

        super().__init__()

        self.layer_name = layer_name
        self.style = style
        self.replace_existing = replace_existing
        self.default_position = default_position

    @classmethod
    def create(
        cls,
        layer_name,
        style,
        replace_existing,
        default_position=None
    ):

        instance = cls(layer_name, style, replace_existing, default_position)

        cls._instances.append(instance)

        return instance

    def postProcessLayer(self, layer, context, feedback):

        if layer is None or not layer.isValid():
            return

        layer.setName(self.layer_name)

        if self.style is not None:
            self.style(layer)

        project = context.project()

        if project is None:
            return

        stale = [
            existing
            for existing in project.mapLayersByName(self.layer_name)
            if existing.id() != layer.id()
        ]

        if not self.replace_existing:

            # A brand new layer alongside the old one, so there is no
            # previous position to inherit - this feature's own
            # default placement applies instead. Without it a raster
            # fill lands on top of everything and hides the map.
            if not stale:
                self._reposition(project, layer, self.default_position)

            return

        remembered = (
            _layer_tree_position(project, stale[0]) if stale else None
        )

        if remembered is None:
            self._reposition(project, layer, self.default_position)

        else:
            parent, index = remembered

            # The index is read with BOTH the old layer's node and
            # the one Processing dropped at the top still in place,
            # and the insert happens while they are still there too.
            # Dropping Processing's node afterwards shifts this one
            # up by exactly the row that node occupied, which is what
            # lands it where the old layer actually sat.
            def place(_project, moving):
                parent.insertLayer(
                    min(index, len(parent.children())),
                    moving
                )

            self._reposition(project, layer, place)

        for existing in stale:
            project.removeMapLayer(existing.id())

    def _reposition(self, project, layer, place):

        """
        Give the layer its new node FIRST, and only then drop the one
        Processing created at the top of the tree.

        That order is the whole point of this method, and reversing
        it loses the layer completely. Removing a layer's LAST tree
        node makes QgsLayerTreeRegistryBridge drop the layer from the
        project altogether - and it does that on the next turn of the
        event loop, not there and then. Synchronously the layer still
        reads as present, and re-inserting it in the same breath does
        not save it: the bridge has already decided.

        That is exactly how this shipped broken. Detaching first and
        re-inserting after passed all 25 algorithm tests, because a
        unittest asserts before the event loop ever runs, and then
        lost every terrain layer in the real QGIS - the run would
        report success, write its output, and add nothing. Inserting
        first means the layer always holds at least one node, so the
        bridge never has anything to clean up.

        `core/_layer_utils.py`, which the dialogs used, never had
        this problem and its docstring says why: it adds the layer
        with `addMapLayer(layer, False)` and inserts it exactly once
        at an explicit position, so the layer never holds a node it
        can then lose. That docstring already warned, from a bug
        confirmed live, about "the extra remove-then-reinsert churn
        on the very layer generate() just added". A post-processor
        cannot borrow the fix - Processing has already added this
        layer and given it a node - but it has to respect the same
        rule: never leave the layer without one.

        Reproduced and fixed against QGIS 4.2.2 on 2026-11-02.
        """

        if place is None:
            return

        original = project.layerTreeRoot().findLayer(layer.id())

        place(project, layer)

        if original is not None and original.parent() is not None:
            original.parent().removeChildNode(original)


def _layer_tree_position(project, layer):

    """
    (parent_group, index_within_parent) for layer's own node in the
    project's layer tree, or None if it has no node.
    """

    node = project.layerTreeRoot().findLayer(layer.id())

    if node is None:
        return None

    parent = node.parent()

    return parent, parent.children().index(node)
