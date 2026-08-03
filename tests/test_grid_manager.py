# -*- coding: utf-8 -*-

"""
Tests for GridManager's layer-tree stacking order (grid/grid_manager.py).

Regression coverage for a real bug: generate_mgrs100k() always runs
after generate_utm() (the 100km grid needs the UTM layer to already
exist), and a plain group.addLayer() append put the MGRS 100km Grid
layer BELOW the UTM Grid layer in the layer tree. QGIS renders the
topmost layer in the tree last (on top), so the UTM Grid's own
polygon fill and GZD label were painting over the MGRS 100km label
wherever the two visually coincided - reported live as "the mgrs
label is rendered but behind the utm grid icon". Confirmed the
top-of-list = on-top convention live, by rendering two overlapping
memory layers in a known order and inspecting the resulting pixel
colour, before writing this fix.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRectangle,
)

from .qgis_test_case import FakeIface, QgisTestCase, make_canvas

from MilitaryCartographyTools.grid.grid_manager import GridManager


EXTENT = QgsRectangle(39.0, -7.0, 39.5, -6.5)


def _direct_child_names(group):

    return [
        child.name()
        for child in group.children()
    ]


class TestGridManagerLayerOrder(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

        canvas = make_canvas()

        canvas.setExtent(EXTENT)

        self.iface = FakeIface(canvas=canvas)

        self.manager = GridManager(self.iface)


    def test_mgrs100k_layer_stacks_above_utm_grid_layer(self):

        self.manager.generate_utm()

        self.manager.generate_mgrs100k()

        group = self.manager.layers.get_group()

        names = _direct_child_names(group)

        self.assertLess(
            names.index("MGRS 100km Grid"),
            names.index("UTM Grid")
        )


    def test_order_still_correct_after_regenerating_utm(self):

        # Regenerating the UTM grid (e.g. after panning) must not
        # bump it back above the already-existing MGRS 100km layer.
        self.manager.generate_utm()

        self.manager.generate_mgrs100k()

        self.manager.generate_utm()

        group = self.manager.layers.get_group()

        names = _direct_child_names(group)

        self.assertLess(
            names.index("MGRS 100km Grid"),
            names.index("UTM Grid")
        )


    def test_sub_grid_group_stays_above_both_layers(self):

        self.manager.generate_utm()

        self.manager.generate_mgrs100k()

        group = self.manager.layers.get_group()

        names = _direct_child_names(group)

        self.assertLess(
            names.index("MGRS Sub Grid"),
            names.index("MGRS 100km Grid")
        )
