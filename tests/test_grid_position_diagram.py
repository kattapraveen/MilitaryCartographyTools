# -*- coding: utf-8 -*-

"""
Tests for layout/grid_position_diagram.py's
add_grid_position_diagram()/remove_grid_position_diagram() - the
inset mosaic diagram drawn from grid_position.compute_grid_position()
for a real QgsLayoutItemMap, rather than the pure math (see
tests/test_grid_position.py for that level).

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsLayoutItemMap,
    QgsPrintLayout,
    QgsProject,
    QgsRectangle,
)

from qgis.PyQt.QtCore import QRectF

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.layout.grid_position_diagram import (
    add_grid_position_diagram,
    remove_grid_position_diagram,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


def _make_layout_with_map_item(extent):

    project = QgsProject.instance()

    project.setCrs(WGS84)

    layout = QgsPrintLayout(project)

    layout.initializeDefaults()

    map_item = QgsLayoutItemMap(layout)

    map_item.attemptSetSceneRect(
        QRectF(10.0, 10.0, 200.0, 150.0)
    )

    map_item.setCrs(WGS84)

    layout.addLayoutItem(
        map_item
    )

    map_item.setExtent(
        extent
    )

    return layout, map_item


def _diagram_items(layout):

    return [
        item for item in layout.items()
        if hasattr(item, "id")
        and item.id()
        and item.id().startswith("mct_grid_position")
    ]


class TestAddGridPositionDiagram(QgisTestCase):

    def test_a_single_square_extent_adds_one_cell_and_a_footprint(self):

        layout, map_item = _make_layout_with_map_item(
            QgsRectangle(39.2080, -6.7926, 39.2090, -6.7916)
        )

        add_grid_position_diagram(
            layout,
            map_item
        )

        self.assertIsNotNone(
            layout.itemById("mct_grid_position_cell_bg_0_0")
        )

        self.assertIsNotNone(
            layout.itemById("mct_grid_position_cell_label_0_0")
        )

        self.assertEqual(
            layout.itemById("mct_grid_position_cell_label_0_0").text(),
            "EN"
        )

        self.assertIsNotNone(
            layout.itemById("mct_grid_position_footprint")
        )


    def test_a_wider_extent_adds_a_mosaic_of_multiple_cells(self):

        layout, map_item = _make_layout_with_map_item(
            QgsRectangle(38.0, -8.0, 40.5, -5.5)
        )

        add_grid_position_diagram(
            layout,
            map_item
        )

        cell_labels = [
            item for item in _diagram_items(layout)
            if item.id().startswith("mct_grid_position_cell_label_")
        ]

        self.assertGreater(len(cell_labels), 1)


    def test_calling_it_twice_does_not_duplicate_items(self):

        layout, map_item = _make_layout_with_map_item(
            QgsRectangle(39.2080, -6.7926, 39.2090, -6.7916)
        )

        add_grid_position_diagram(layout, map_item)
        first_count = len(_diagram_items(layout))

        add_grid_position_diagram(layout, map_item)
        second_count = len(_diagram_items(layout))

        self.assertEqual(first_count, second_count)


class TestRemoveGridPositionDiagram(QgisTestCase):

    def test_removes_every_diagram_item(self):

        layout, map_item = _make_layout_with_map_item(
            QgsRectangle(39.2080, -6.7926, 39.2090, -6.7916)
        )

        add_grid_position_diagram(
            layout,
            map_item
        )

        remove_grid_position_diagram(
            layout
        )

        self.assertEqual(
            len(_diagram_items(layout)),
            0
        )


    def test_a_layout_with_no_diagram_does_not_error(self):

        layout, _map_item = _make_layout_with_map_item(
            QgsRectangle(39.2080, -6.7926, 39.2090, -6.7916)
        )

        remove_grid_position_diagram(
            layout
        )
