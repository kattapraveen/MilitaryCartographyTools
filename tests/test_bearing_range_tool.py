# -*- coding: utf-8 -*-

"""
Tests for core/bearing_range_tool.py's BearingRangeTool - the
from/to click state machine, exercised via its _handle_point() method
directly (no real mouse event needed), mirroring
tests/test_line_of_sight_tool.py's own approach.

Military Cartography Tools
"""

from qgis.core import QgsPointXY

from .qgis_test_case import FakeIface, QgisTestCase, make_canvas

from MilitaryCartographyTools.core.bearing_range_tool import BearingRangeTool


class TestBearingRangeTool(QgisTestCase):

    def setUp(self):

        super().setUp()

        # Keep the canvas alive as an instance attribute - see
        # test_line_of_sight_tool.py's own setUp() for why a bare
        # make_canvas() passed inline would get garbage-collected
        # too early.
        self.canvas = make_canvas()
        self.iface = FakeIface(canvas=self.canvas)
        self.tool = BearingRangeTool(self.canvas, self.iface)


    def test_first_click_creates_dialog_and_sets_from_point(self):

        point = QgsPointXY(37.34, -3.09)

        self.tool._handle_point(point)

        self.assertIsNotNone(self.tool.dialog)
        self.assertEqual(self.tool.dialog.from_lonlat, point)
        self.assertIsNone(self.tool.dialog.to_lonlat)


    def test_second_click_sets_to_point_without_disturbing_from_point(self):

        from_point = QgsPointXY(37.34, -3.09)
        to_point = QgsPointXY(37.35, -3.08)

        self.tool._handle_point(from_point)
        self.tool._handle_point(to_point)

        self.assertEqual(self.tool.dialog.from_lonlat, from_point)
        self.assertEqual(self.tool.dialog.to_lonlat, to_point)


    def test_second_click_logs_a_reading(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))
        self.tool._handle_point(QgsPointXY(37.35, -3.08))

        self.assertEqual(self.tool.dialog.table.rowCount(), 1)


    def test_third_click_starts_a_new_pair(self):

        from_point = QgsPointXY(37.34, -3.09)
        to_point = QgsPointXY(37.35, -3.08)
        new_from_point = QgsPointXY(37.36, -3.07)

        self.tool._handle_point(from_point)
        self.tool._handle_point(to_point)
        self.tool._handle_point(new_from_point)

        self.assertEqual(self.tool.dialog.from_lonlat, new_from_point)
        self.assertIsNone(self.tool.dialog.to_lonlat)

        # Still just the one row from the completed first pair - a
        # fresh "from" click alone shouldn't log anything.
        self.assertEqual(self.tool.dialog.table.rowCount(), 1)


    def test_a_second_completed_pair_adds_a_second_row(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))
        self.tool._handle_point(QgsPointXY(37.35, -3.08))
        self.tool._handle_point(QgsPointXY(37.36, -3.07))
        self.tool._handle_point(QgsPointXY(37.37, -3.06))

        self.assertEqual(self.tool.dialog.table.rowCount(), 2)


    def test_dialog_is_reused_across_clicks(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))

        dialog_after_first_click = self.tool.dialog

        self.tool._handle_point(QgsPointXY(37.35, -3.08))

        self.assertIs(self.tool.dialog, dialog_after_first_click)


    def test_first_click_places_a_from_marker(self):

        # Real usability complaint already fixed for Line of Sight:
        # nothing on the map itself showed a click had registered,
        # especially the first one. A marker at the clicked point is
        # the fix, applied here from the start.
        point = QgsPointXY(37.34, -3.09)

        self.tool._handle_point(point)

        self.assertIsNotNone(self.tool.from_marker)
        self.assertEqual(self.tool.from_marker.center(), point)
        self.assertIsNone(self.tool.to_marker)


    def test_second_click_places_a_to_marker_and_keeps_from_marker(self):

        from_point = QgsPointXY(37.34, -3.09)
        to_point = QgsPointXY(37.35, -3.08)

        self.tool._handle_point(from_point)
        self.tool._handle_point(to_point)

        self.assertEqual(self.tool.from_marker.center(), from_point)
        self.assertIsNotNone(self.tool.to_marker)
        self.assertEqual(self.tool.to_marker.center(), to_point)


    def test_third_click_moves_from_marker_and_clears_to_marker(self):

        from_point = QgsPointXY(37.34, -3.09)
        to_point = QgsPointXY(37.35, -3.08)
        new_from_point = QgsPointXY(37.36, -3.07)

        self.tool._handle_point(from_point)
        self.tool._handle_point(to_point)
        self.tool._handle_point(new_from_point)

        self.assertEqual(self.tool.from_marker.center(), new_from_point)
        self.assertIsNone(self.tool.to_marker)


    def test_deactivate_clears_both_markers(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))
        self.tool._handle_point(QgsPointXY(37.35, -3.08))

        self.tool.deactivate()

        self.assertIsNone(self.tool.from_marker)
        self.assertIsNone(self.tool.to_marker)


    def test_second_click_draws_a_line_and_arrowhead(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))

        self.assertIsNone(self.tool.line_rubber_band)
        self.assertIsNone(self.tool.arrow_rubber_band)

        self.tool._handle_point(QgsPointXY(37.35, -3.08))

        self.assertIsNotNone(self.tool.line_rubber_band)
        self.assertIsNotNone(self.tool.arrow_rubber_band)

        # Both ends of the line rubber band match the clicked points.
        self.assertEqual(
            self.tool.line_rubber_band.asGeometry().asPolyline(),
            [QgsPointXY(37.34, -3.09), QgsPointXY(37.35, -3.08)]
        )


    def test_third_click_clears_the_line(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))
        self.tool._handle_point(QgsPointXY(37.35, -3.08))
        self.tool._handle_point(QgsPointXY(37.36, -3.07))

        self.assertIsNone(self.tool.line_rubber_band)
        self.assertIsNone(self.tool.arrow_rubber_band)


    def test_deactivate_clears_the_line(self):

        self.tool._handle_point(QgsPointXY(37.34, -3.09))
        self.tool._handle_point(QgsPointXY(37.35, -3.08))

        self.tool.deactivate()

        self.assertIsNone(self.tool.line_rubber_band)
        self.assertIsNone(self.tool.arrow_rubber_band)


    def test_identical_from_and_to_points_do_not_error(self):

        # _arrowhead_geometry() has no direction to point in when the
        # two points coincide - shouldn't raise (division by zero on
        # the zero-length line), just skip drawing the arrowhead.
        point = QgsPointXY(37.34, -3.09)

        self.tool._handle_point(point)
        self.tool._handle_point(point)

        self.assertIsNotNone(self.tool.line_rubber_band)
