# -*- coding: utf-8 -*-

"""
Grid Manager

Controls military grid generation,
display and visibility.

Military Cartography Tools
"""

from qgis.core import QgsProject

from .grid_layers import GridLayerManager
from .grid_settings import GridSettings
from .utm_grid import UTMGridGenerator
from .mgrs_100k import MGRS100KGenerator
from .mgrs_sub_grid import MGRSSubGridGenerator
from .grid_labels import GridLabelManager


class GridManager:
    """
    Main controller for military grids.

    Generates against the interactive map canvas. Print layouts
    show whatever's currently visible on the canvas automatically
    (a layout's map item mirrors the project's layer tree unless
    explicitly locked to its own layer set), so there's no
    separate layout-specific generation path - build the grid
    here, and any layout that includes this area picks it up.
    """


    def __init__(self, iface):

        self.iface = iface

        self.layers = GridLayerManager()

        self.utm = UTMGridGenerator()
        self.mgrs100k = MGRS100KGenerator()
        self.mgrs_sub = MGRSSubGridGenerator()

        self.labels = GridLabelManager()




    def remove_existing_layer(self, name):

        layers = QgsProject.instance().mapLayersByName(
            name
        )

        for layer in layers:

            QgsProject.instance().removeMapLayer(
                layer.id()
            )

        #
        # Reset generator references
        #

        if name == "UTM Grid":
            self.utm.layer = None

        elif name == "MGRS 100km Grid":
            self.mgrs100k.layer = None

    def add_layer_to_group(self, layer, group):

        QgsProject.instance().addMapLayer(
            layer,
            False
        )

        group.addLayer(
            layer
        )



    def generate_utm(self):

        self.remove_existing_layer(
            "UTM Grid"
        )


        # IMPORTANT:
        # Use the existing generator instance
        # so the layer remains available
        # for MGRS 100km generation

        layer = self.utm.generate(
            self.iface.mapCanvas().extent()
        )

        self.labels.apply_label(
            layer,
            "GZD",
            30
        )

        group = self.layers.get_group()


        self.add_layer_to_group(
            layer,
            group
        )


        self.iface.messageBar().pushInfo(
            "Military Cartography Tools",
            "UTM Grid generated."
        )



    def generate_mgrs100k(self):

        self.remove_existing_layer(
            "MGRS 100km Grid"
        )


        layer = self.mgrs100k.generate(
            self.utm.layer
        )

        self.labels.apply_square_label(
            layer,
            "100K"
        )


        group = self.layers.get_group()


        self.add_layer_to_group(
            layer,
            group
        )


        self.iface.messageBar().pushInfo(
            "Military Cartography Tools",
            "MGRS 100km Grid generated."
        )

    def generate_mgrs_sub(self):

        spacing = GridSettings.mgrs_sub_spacing()


        name = f"MGRS {spacing//1000}km Grid"


        self.remove_existing_layer(
            name
        )

        self.mgrs_sub.layer = None


        layer = self.mgrs_sub.generate(
            self.iface.mapCanvas().extent(),
            self.utm.layer,
            spacing
        )


        group = self.layers.get_layer_group(
            "MGRS Sub Grid"
        )


        self.add_layer_to_group(
            layer,
            group
        )


        self.iface.messageBar().pushInfo(
            "Military Cartography Tools",
            f"{name} generated."
        )


    def clear(self):
        """
        Remove every grid layer (all sub-grid spacings
        included) - a clean slate before picking grids again
        for a new area.
        """

        self.remove_existing_layer(
            "UTM Grid"
        )

        self.remove_existing_layer(
            "MGRS 100km Grid"
        )

        sub_group = self.layers.get_layer_group(
            "MGRS Sub Grid"
        )

        if sub_group is not None:

            self.layers.clear_group(
                sub_group
            )

        self.mgrs_sub.layer = None


    # ------------------------------------------------------------
    # Show/hide existing layers without regenerating them.
    #
    # generate_*() above always rebuilds from scratch (used for
    # first-time creation, after Clear Grid, or after panning to
    # a new area). These show_*/hide_*() methods are for
    # toggling a grid on/off after it already exists - they only
    # touch layer-tree visibility, so re-checking a box doesn't
    # silently rebuild the layer.
    # ------------------------------------------------------------

    def show_utm(self):

        if QgsProject.instance().mapLayersByName("UTM Grid"):

            self.layers.set_layer_visible(
                "UTM Grid",
                True
            )

        else:

            self.generate_utm()


    def hide_utm(self):

        self.layers.set_layer_visible(
            "UTM Grid",
            False
        )


    def show_mgrs100k(self):

        if QgsProject.instance().mapLayersByName("MGRS 100km Grid"):

            self.layers.set_layer_visible(
                "MGRS 100km Grid",
                True
            )

        else:

            self.generate_mgrs100k()


    def hide_mgrs100k(self):

        self.layers.set_layer_visible(
            "MGRS 100km Grid",
            False
        )


    def show_sub_grid(self):

        """
        Show the sub-grid layer matching the current
        GridSettings spacing, hiding every other spacing's
        layer. Generates it first if it doesn't exist yet.

        Ensures the target layer exists and is shown BEFORE
        hiding the others, rather than hiding first - so a
        freshly-created layer is never touched by the hide
        step for a group it wasn't part of yet.
        """

        spacing = GridSettings.mgrs_sub_spacing()

        name = f"MGRS {spacing//1000}km Grid"

        if QgsProject.instance().mapLayersByName(name):

            self.layers.set_layer_visible(
                name,
                True
            )

        else:

            self.generate_mgrs_sub()

        group = self.layers.get_layer_group(
            "MGRS Sub Grid"
        )

        for layer_node in group.findLayers():

            if layer_node.layer().name() != name:

                layer_node.setItemVisibilityChecked(
                    False
                )


    def hide_sub_grid(self):

        group = self.layers.get_layer_group(
            "MGRS Sub Grid"
        )

        self.layers.hide_group(
            group
        )
