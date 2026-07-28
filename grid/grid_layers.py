# -*- coding: utf-8 -*-

"""
Grid layer manager.

Military Cartography Tools
"""

from qgis.core import QgsProject


class GridLayerManager:
    """
    Creates and manages military grid groups.
    """


    GROUP_NAME = "Military Grids"


    SUB_GROUP = "MGRS Sub Grid"



    def __init__(self):

        self.project = QgsProject.instance()



    def get_group(self):

        root = self.project.layerTreeRoot()

        group = root.findGroup(
            self.GROUP_NAME
        )


        if group is None:

            group = root.addGroup(
                self.GROUP_NAME
            )


        self.create_groups(
            group
        )


        return group



    def create_groups(self, group):

        """
        Create only required subgroups.

        Generated layers are added directly
        to Military Grids.
        """

        existing = {
            child.name()
            for child in group.children()
            if child.nodeType() == 0
        }


        if self.SUB_GROUP not in existing:

            group.addGroup(
                self.SUB_GROUP
            )



    def get_layer_group(self, name):

        """
        Return a subgroup.
        """

        parent = self.get_group()

        return parent.findGroup(
            name
        )



    def clear_group(self, group):

        """
        Remove every layer currently in a layer tree group
        (but leave the group itself and any subgroups).
        """

        for layer_node in list(group.findLayers()):

            self.project.removeMapLayer(
                layer_node.layerId()
            )



    def set_layer_visible(self, name, visible):

        """
        Show/hide (without removing) every layer with this
        name.
        """

        root = self.project.layerTreeRoot()

        for layer in self.project.mapLayersByName(name):

            node = root.findLayer(
                layer.id()
            )

            if node is not None:

                node.setItemVisibilityChecked(
                    visible
                )



    def hide_group(self, group):

        """
        Hide (without removing) every layer currently in a
        layer tree group.
        """

        for layer_node in group.findLayers():

            layer_node.setItemVisibilityChecked(
                False
            )