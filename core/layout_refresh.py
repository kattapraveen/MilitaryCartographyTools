from qgis.core import QgsProject


# Every (item, slot) pair currently connected by connect_layout_
# refresh() below, so disconnect_layout_refresh() can undo exactly
# these connections (each slot is a distinct per-layout lambda, not
# a single reusable function, so they have to be tracked
# individually rather than disconnected by function identity alone).
_connections = []


def _connect_layout_items(layout):

    for item in layout.items():

        # only connect map items
        if hasattr(item, "extentsChanged"):

            slot = lambda layout=layout: layout.refresh()

            item.extentsChanged.connect(slot)

            _connections.append((item, slot))


def _on_layout_added(name):

    layout = QgsProject.instance().layoutManager().layoutByName(name)

    if layout is not None:

        _connect_layout_items(layout)


def connect_layout_refresh():

    """
    Connect every existing print layout's map item(s) so panning/
    resizing/rescaling one refreshes that layout - keeps its
    expression-driven labels (scale, centre coordinate, etc.) up
    to date without the user needing to manually force a redraw.

    Also listens for QgsLayoutManager.layoutAdded, so a layout
    created later (e.g. via New Military Layout, after this ran)
    gets the same wiring - not just whatever layouts already
    existed at plugin-load time.
    """

    manager = QgsProject.instance().layoutManager()

    for layout in manager.printLayouts():

        _connect_layout_items(layout)

    manager.layoutAdded.connect(
        _on_layout_added
    )


def disconnect_layout_refresh():

    """
    Undo connect_layout_refresh() - both the per-item
    extentsChanged connections and the layoutAdded listener.
    Called from plugin.py's unload() so a Plugin Reloader cycle
    doesn't stack a fresh, un-removed set of connections onto the
    same map items every time the plugin reloads.
    """

    manager = QgsProject.instance().layoutManager()

    try:

        manager.layoutAdded.disconnect(
            _on_layout_added
        )

    except (TypeError, RuntimeError):

        # Already disconnected, or the manager's own C++ object is
        # gone (e.g. project closing) - nothing left to undo.
        pass

    for item, slot in _connections:

        try:

            item.extentsChanged.disconnect(
                slot
            )

        except (TypeError, RuntimeError):

            # Already disconnected, or the item's own C++ object
            # is gone (e.g. its layout was since deleted) - safe
            # to skip.
            pass

    _connections.clear()
