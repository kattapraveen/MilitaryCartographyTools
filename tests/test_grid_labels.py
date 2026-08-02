# -*- coding: utf-8 -*-

"""
Tests for GridLabelManager.apply_square_label() (grid/grid_labels.py)
- specifically the scale-gated centred/corner rule split that fixes
the two zoomed-out label bugs (labels drifting into a neighbouring
square's box, and labels piling up too large once many squares are
on screen).

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRectangle,
    QgsRuleBasedLabeling,
)

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.grid.grid_labels import GridLabelManager
from MilitaryCartographyTools.grid.mgrs_100k import MGRS100KGenerator
from MilitaryCartographyTools.grid.utm_grid import UTMGridGenerator


EXTENT = QgsRectangle(39.0, -7.0, 39.5, -6.5)


def _rules_by_description(layer):

    root = layer.labeling().rootRule()

    return {
        rule.description(): rule
        for rule in root.children()
    }


class TestApplySquareLabel(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

        utm_layer = UTMGridGenerator().generate(EXTENT)

        self.layer = MGRS100KGenerator().generate(utm_layer)

        self.manager = GridLabelManager()


    def test_rule_set_has_two_centred_rules_and_four_corner_rules(self):

        self.manager.apply_square_label(self.layer, "100K")

        root = self.layer.labeling().rootRule()

        self.assertEqual(len(root.children()), 6)


    def test_near_centred_rule_offsets_and_far_one_does_not(self):

        self.manager.apply_square_label(self.layer, "100K")

        rules = _rules_by_description(self.layer)

        near = rules["Centered, offset clear of the GZD label (zoomed in)"]
        far = rules["Centered, no offset (zoomed out)"]

        self.assertEqual(
            near.settings().yOffset,
            GridLabelManager.CENTER_LABEL_Y_OFFSET_MM
        )

        self.assertEqual(
            far.settings().yOffset,
            0
        )


    def test_near_and_far_rules_partition_on_corner_scale_threshold(self):

        threshold = 250000

        self.manager.apply_square_label(
            self.layer,
            "100K",
            corner_scale_threshold=threshold
        )

        rules = _rules_by_description(self.layer)

        near = rules["Centered, offset clear of the GZD label (zoomed in)"]
        far = rules["Centered, no offset (zoomed out)"]

        self.assertEqual(
            near.filterExpression(),
            f"@map_scale < {threshold}"
        )

        self.assertIn(
            f"@map_scale >= {threshold}",
            far.filterExpression()
        )


    def test_far_rule_stops_at_center_max_scale(self):

        self.manager.apply_square_label(
            self.layer,
            "100K",
            center_max_scale=1234567
        )

        rules = _rules_by_description(self.layer)

        far = rules["Centered, no offset (zoomed out)"]

        self.assertIn(
            "@map_scale <= 1234567",
            far.filterExpression()
        )


    def test_far_rule_uses_smaller_default_font_than_near_rule(self):

        self.manager.apply_square_label(self.layer, "100K")

        rules = _rules_by_description(self.layer)

        near = rules["Centered, offset clear of the GZD label (zoomed in)"]
        far = rules["Centered, no offset (zoomed out)"]

        near_size = near.settings().format().size()
        far_size = far.settings().format().size()

        self.assertLess(far_size, near_size)


    def test_corner_rules_still_gated_to_zoomed_in_only(self):

        threshold = 250000

        self.manager.apply_square_label(
            self.layer,
            "100K",
            corner_scale_threshold=threshold
        )

        root = self.layer.labeling().rootRule()

        corner_rules = [
            rule
            for rule in root.children()
            if rule.description().startswith("Corner")
        ]

        self.assertEqual(len(corner_rules), 4)

        for rule in corner_rules:

            self.assertEqual(
                rule.filterExpression(),
                f"@map_scale < {threshold}"
            )
