# -*- coding: utf-8 -*-

"""
Tests for terrain/viewshed_tool.py's ViewshedTool - the single-click
observer placement, exercised via its _handle_point() method directly
(no real mouse event needed) rather than driving canvasReleaseEvent(),
mirroring tests/test_line_of_sight_tool.py's own approach.

Military Cartography Tools
"""

from qgis.core import QgsPointXY

from .qgis_test_case import FakeIface, QgisTestCase, make_canvas

from MilitaryCartographyTools.terrain.viewshed_tool import ViewshedTool


class TestViewshedTool(QgisTestCase):

    def setUp(self):

        super().setUp()

        # Keep the canvas alive as an instance attribute - a bare
        # make_canvas() passed inline with no reference kept gets
        # garbage-collected right after setUp() returns, taking the
        # tool's underlying C++ object down with it (QgsMapTool is
        # parented to its canvas), which only actually surfaces once
        # something calls self.canvas() (e.g. to place a marker).
        self.canvas = make_canvas()
        self.iface = FakeIface(canvas=self.canvas)
        self.tool = ViewshedTool(self.canvas, self.iface)


    def test_first_click_creates_dialog_and_sets_observer(self):

        point = QgsPointXY(37.34, -3.09)

        self.tool._handle_point(point)

        self.assertIsNotNone(self.tool.dialog)
        self.assertEqual(self.tool.dialog.observer_lonlat, point)


    def test_first_click_runs_a_check(self):

        # No DEM layer registered in the project, so the auto-run
        # triggered by set_observer() should warn on the message bar -
        # confirms the click actually drives
        # generate_from_dialog_values() through to completion, not
        # just updating the dialog's own fields.
        self.tool._handle_point(QgsPointXY(37.34, -3.09))

        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_second_click_moves_the_observer(self):

        first = QgsPointXY(37.34, -3.09)
        second = QgsPointXY(37.36, -3.07)

        self.tool._handle_point(first)
        self.tool._handle_point(second)

        self.assertEqual(self.tool.dialog.observer_lonlat, second)


    def test_dialog_is_reused_across_clicks(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))

        dialog_after_first_click = self.tool.dialog

        self.tool._handle_point(QgsPointXY(37.35, -3.08))

        self.assertIs(self.tool.dialog, dialog_after_first_click)


    def test_first_click_places_an_observer_marker(self):

        # Real usability lesson carried over from Line of Sight -
        # nothing on the map itself showed a click had registered
        # without a marker there.
        point = QgsPointXY(37.34, -3.09)

        self.tool._handle_point(point)

        self.assertIsNotNone(self.tool.observer_marker)
        self.assertEqual(self.tool.observer_marker.center(), point)


    def test_second_click_moves_the_marker(self):

        first = QgsPointXY(37.34, -3.09)
        second = QgsPointXY(37.36, -3.07)

        self.tool._handle_point(first)
        self.tool._handle_point(second)

        self.assertEqual(self.tool.observer_marker.center(), second)


    def test_deactivate_clears_the_marker(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))

        self.tool.deactivate()

        self.assertIsNone(self.tool.observer_marker)
