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
    Held in a class-level registry because Python collects the
    object before the layer is loaded otherwise, and the styling
    then silently never happens. The same trap the range-rings
    prototype already guarded against.

    The mechanism, measured on 2026-11-03 rather than assumed, is
    worth stating precisely because it is not the usual weak
    reference. `LayerDetails.setPostProcessor()` TRANSFERS ownership
    of the C++ instance to C++ - `sip.ispyowned()` goes from True to
    False across the call - so the C++ object itself survives and
    `postProcessor()` keeps returning something non-None. What does
    not survive is the PYTHON subclass: drop the last Python
    reference, collect, and what comes back out of the context is a
    bare `QgsProcessingLayerPostProcessorInterface`. Calling
    postProcessLayer() on it dispatches to the C++ base, which does
    nothing. Hence a run that reports success and styles nothing,
    with no error anywhere.

    The registry is pruned in postProcessLayer()'s own `finally`,
    which is the one moment the object is certainly no longer needed
    - see _forget().
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

        """
        Nothing may escape this method, and that is not defensive
        habit - it is the shape of the code that calls it.
        `processing/gui/Postprocessing.py:handleAlgorithmResults`
        does:

            iface.layerTreeView().setUpdatesEnabled(False)
            QgsProcessingGuiUtils.addResultLayers(...)
            for layer, details in layers_to_post_process:
                details.postProcessor().postProcessLayer(...)
            iface.layerTreeView().setUpdatesEnabled(True)

        Only the earlier layer-resolution loop is wrapped in
        try/except; this one is not. So an exception leaving here
        skips both the remaining post-processors and
        `setUpdatesEnabled(True)`, and the Layers panel then stops
        repainting for the REST OF THE SESSION. Every later algorithm
        would look as though it did nothing - indistinguishable from
        the bug fixed on 2026-11-02, and far harder to trace back.

        The risk is real rather than theoretical: `style()` is
        supplied by the caller and reads the written raster.
        `_apply_raster_style()` asks the provider for band statistics,
        which fails on a full or disconnected volume, and
        `_build_labeling()` assumes a field that a hand-edited model
        could leave absent.

        A failure is reported through `feedback` instead, where it
        lands in the algorithm dialog's own log. With no feedback to
        report to - a direct call, as the tests make - it is re-raised
        rather than swallowed: there is nobody to tell, and a silent
        pass would hide exactly the kind of bug these tests exist to
        catch.
        """

        try:
            self._place(layer, context)

        except Exception as failure:

            if feedback is None:
                raise

            feedback.reportError(
                f"The \"{self.layer_name}\" layer was created, but "
                "could not be styled or moved to its place in the "
                f"Layers panel: {failure}. The layer itself is "
                "usable - restyle it by hand, or run the tool again.",
                fatalError=False
            )

        finally:
            self._forget()

    def _forget(self):

        """
        Drop this instance from the registry, once it has done the
        one job it was kept alive for.

        Without this the list grows for the lifetime of the QGIS
        session - one post-processor plus its captured style closure
        per run - and these tools are used by re-running them, since
        that is the whole point of replace-in-place.

        Safe to do from inside postProcessLayer(): the executing
        frame holds `self`, so the object cannot go before the method
        returns, and the C++ instance belongs to C++ (see the class
        docstring), so dropping the last Python reference afterwards
        frees only the wrapper. Identity, not ==, so no __eq__ of a
        sip object is involved.
        """

        cls = type(self)

        cls._instances = [
            held for held in cls._instances if held is not self
        ]

    def _place(self, layer, context):

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
