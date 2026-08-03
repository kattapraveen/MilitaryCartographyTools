# -*- coding: utf-8 -*-

"""
Tests for terrain/line_of_sight_tool.py's LineOfSightTool - the
observer/target click state machine, exercised via its
_handle_point() method directly (no real mouse event needed) rather
than driving canvasReleaseEvent(), since there's no existing
precedent in this repo for constructing a real QgsMapMouseEvent in
tests.

Military Cartography Tools
"""

from qgis.core import QgsPointXY

from .qgis_test_case import FakeIface, QgisTestCase, make_canvas

from MilitaryCartographyTools.terrain.line_of_sight_tool import LineOfSightTool


class TestLineOfSightTool(QgisTestCase):

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
        self.tool = LineOfSightTool(self.canvas, self.iface)


    def test_first_click_creates_dialog_and_sets_observer(self):

        point = QgsPointXY(37.34, -3.09)

        self.tool._handle_point(point)

        self.assertIsNotNone(self.tool.dialog)
        self.assertEqual(self.tool.dialog.observer_lonlat, point)
        self.assertIsNone(self.tool.dialog.target_lonlat)


    def test_second_click_sets_target_without_disturbing_observer(self):

        observer = QgsPointXY(37.34, -3.09)
        target = QgsPointXY(37.35, -3.08)

        self.tool._handle_point(observer)
        self.tool._handle_point(target)

        self.assertEqual(self.tool.dialog.observer_lonlat, observer)
        self.assertEqual(self.tool.dialog.target_lonlat, target)


    def test_second_click_runs_a_check(self):

        # No DEM layer registered in the project, so the auto-run
        # triggered by completing the pair should warn on the
        # message bar - confirms the second click actually drives
        # generate_from_dialog_values() through to completion, not
        # just updating the dialog's own fields.
        self.tool._handle_point(QgsPointXY(37.34, -3.09))
        self.tool._handle_point(QgsPointXY(37.35, -3.08))

        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_third_click_starts_a_new_pair(self):

        observer = QgsPointXY(37.34, -3.09)
        target = QgsPointXY(37.35, -3.08)
        new_observer = QgsPointXY(37.36, -3.07)

        self.tool._handle_point(observer)
        self.tool._handle_point(target)
        self.tool._handle_point(new_observer)

        self.assertEqual(self.tool.dialog.observer_lonlat, new_observer)
        self.assertIsNone(self.tool.dialog.target_lonlat)


    def test_dialog_is_reused_across_clicks(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))

        dialog_after_first_click = self.tool.dialog

        self.tool._handle_point(QgsPointXY(37.35, -3.08))

        self.assertIs(self.tool.dialog, dialog_after_first_click)


    def test_first_click_places_an_observer_marker(self):

        # Real usability complaint: nothing on the map itself showed
        # a click had registered, especially the first one, so
        # multiple clicks happened by accident. A marker at the
        # clicked point is the fix.
        point = QgsPointXY(37.34, -3.09)

        self.tool._handle_point(point)

        self.assertIsNotNone(self.tool.observer_marker)
        self.assertEqual(self.tool.observer_marker.center(), point)
        self.assertIsNone(self.tool.target_marker)


    def test_second_click_places_a_target_marker_and_keeps_observer(self):

        observer = QgsPointXY(37.34, -3.09)
        target = QgsPointXY(37.35, -3.08)

        self.tool._handle_point(observer)
        self.tool._handle_point(target)

        self.assertEqual(self.tool.observer_marker.center(), observer)
        self.assertIsNotNone(self.tool.target_marker)
        self.assertEqual(self.tool.target_marker.center(), target)


    def test_third_click_moves_observer_marker_and_clears_target_marker(self):

        observer = QgsPointXY(37.34, -3.09)
        target = QgsPointXY(37.35, -3.08)
        new_observer = QgsPointXY(37.36, -3.07)

        self.tool._handle_point(observer)
        self.tool._handle_point(target)
        self.tool._handle_point(new_observer)

        self.assertEqual(self.tool.observer_marker.center(), new_observer)
        self.assertIsNone(self.tool.target_marker)


    def test_deactivate_clears_both_markers(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))
        self.tool._handle_point(QgsPointXY(37.35, -3.08))

        self.tool.deactivate()

        self.assertIsNone(self.tool.observer_marker)
        self.assertIsNone(self.tool.target_marker)
