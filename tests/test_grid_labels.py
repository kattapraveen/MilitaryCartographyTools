# -*- coding: utf-8 -*-

"""
Tests for GridLabelManager.apply_square_label() (grid/grid_labels.py)
- the scale-gated centred/corner rule split that fixes the two
zoomed-out label bugs (labels drifting into a neighbouring square's
box, and labels piling up too large once many squares are on
screen), the corner-label y_sign fix (confirmed live that PAL's
yOffset is positive-down, not positive-up as an earlier version of
CORNERS assumed - see grid_labels.py's own comment), and making
corner/centred labels mutually exclusive by zoom scale rather than
both showing at once for the same square.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRectangle,
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


    def test_rule_set_has_one_centred_rule_and_four_corner_rules(self):

        # Corner and centred labels are mutually exclusive by zoom
        # scale (see grid_labels.py's 2026-08-03 note) - only one
        # centred rule now, not a near/far pair.
        self.manager.apply_square_label(self.layer, "100K")

        root = self.layer.labeling().rootRule()

        self.assertEqual(len(root.children()), 5)


    def test_far_centred_rule_has_no_offset(self):

        self.manager.apply_square_label(self.layer, "100K")

        rules = _rules_by_description(self.layer)

        far = rules["Centered, no offset (zoomed out)"]

        self.assertEqual(
            far.settings().yOffset,
            0
        )


    def test_centred_and_corner_rules_partition_on_corner_scale_threshold(self):

        # Exactly one style is ever active at a given scale: corner
        # labels below the threshold, the centred label at or above
        # it - never both, never neither.
        threshold = 250000

        self.manager.apply_square_label(
            self.layer,
            "100K",
            corner_scale_threshold=threshold
        )

        rules = _rules_by_description(self.layer)

        far = rules["Centered, no offset (zoomed out)"]

        self.assertIn(
            f"@map_scale >= {threshold}",
            far.filterExpression()
        )

        root = self.layer.labeling().rootRule()

        corner_rules = [
            rule
            for rule in root.children()
            if rule.description().startswith("Corner")
        ]

        for rule in corner_rules:

            self.assertEqual(
                rule.filterExpression(),
                f"@map_scale < {threshold}"
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


    def test_far_centred_rule_anchors_to_the_true_centroid(self):

        # Real reported bug: without a geometry-generator-derived
        # fixed point, PAL doesn't anchor a centred polygon label to
        # its true, full centroid - for a polygon that's only
        # partially on screen, it drifts toward whatever portion is
        # currently visible instead, sliding the label toward (and
        # past) the polygon's own edge as more of it leaves the
        # screen. Confirmed live by panning a fresh grid across zone
        # boundaries. centroid($geometry) is immune to this, since
        # it's computed from the full geometry regardless of what's
        # currently on screen.
        self.manager.apply_square_label(self.layer, "100K")

        far = _rules_by_description(self.layer)["Centered, no offset (zoomed out)"]

        settings = far.settings()

        self.assertTrue(settings.geometryGeneratorEnabled)
        self.assertEqual(settings.geometryGenerator, "centroid($geometry)")


    def test_far_rule_uses_same_default_font_size_as_corner_labels(self):

        # Matched 2026-08-03: corner and centred labels use the same
        # default size (SQUARE_LABEL_SIZE) so a square's label reads
        # consistently across the corner_scale_threshold cutover.
        self.manager.apply_square_label(self.layer, "100K")

        root = self.layer.labeling().rootRule()

        corner_rule = next(
            rule
            for rule in root.children()
            if rule.description().startswith("Corner")
        )

        far = _rules_by_description(self.layer)["Centered, no offset (zoomed out)"]

        corner_size = corner_rule.settings().format().size()
        far_size = far.settings().format().size()

        self.assertEqual(far_size, corner_size)
        self.assertEqual(far_size, self.manager.SQUARE_LABEL_SIZE)


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


    def test_square_labels_outrank_utm_label_but_not_sub_grid(self):

        # 2026-08-05: raising the 100km square's own label priority
        # above the UTM/GZD label's (1) - combined with
        # GZD_LABEL_OFFSET_MM nudging the GZD label away from the
        # centroid it would otherwise share with a 100km square's
        # centred label - is the user-confirmed fix for the two
        # still occasionally competing for the same screen space,
        # even after the layer z-order fix. Kept below the sub-grid
        # tick labels' priority (9) so the intended fine-to-coarse
        # hierarchy (sub-grid > 100km > UTM GZD) still holds.
        self.manager.apply_square_label(self.layer, "100K")

        root = self.layer.labeling().rootRule()

        for rule in root.children():

            self.assertEqual(
                rule.settings().priority,
                self.manager.SQUARE_LABEL_PRIORITY
            )

        self.assertGreater(
            self.manager.SQUARE_LABEL_PRIORITY,
            1
        )

        self.assertLess(
            self.manager.SQUARE_LABEL_PRIORITY,
            9
        )


class TestApplyLabelOffset(QgisTestCase):

    """
    GridLabelManager.apply_label() - used for the UTM/GZD grid label.

    Covers two fixes: (1) 2026-08-05, nudging this label away from
    its polygon's centroid (rather than sitting exactly on it, where
    a 100km square's own centred label is also anchored at matching
    zoom levels) reduces how often the two even compete for the same
    screen space; (2) 2026-08-06, a real reported bug - that fixed
    offset is only safe while the GZD polygon is still large on
    screen. Zoomed out far enough, it pushed the label past its own
    polygon's edge into the neighbouring GZD zone, the same failure
    mode already fixed for the 100km square label's own corner/
    centred switch (see apply_square_label). apply_label() now uses
    the same scale-gated rule-based approach: offset while zoomed in,
    centred (no offset) once zoomed out past the room that
    particular cell has for the offset.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

        self.layer = UTMGridGenerator().generate(EXTENT)

        self.manager = GridLabelManager()


    def test_rule_set_has_one_offset_rule_and_one_centered_rule(self):

        # Two rules for three bands - the third, "too small to label
        # at all", is the absence of any rule matching rather than a
        # rule of its own.
        self.manager.apply_label(self.layer, "GZD")

        root = self.layer.labeling().rootRule()

        self.assertEqual(len(root.children()), 2)

        descriptions = {rule.description() for rule in root.children()}

        self.assertIn("Offset up-left (zoomed in)", descriptions)
        self.assertIn("Centered, no offset (zoomed out)", descriptions)


    def test_offset_rule_is_offset_up_and_left_of_its_anchor(self):

        self.manager.apply_label(self.layer, "GZD")

        rules = _rules_by_description(self.layer)

        offset = rules["Offset up-left (zoomed in)"].settings()

        # Negative x/y - confirmed live elsewhere in this module that
        # PAL offsets are positive-right/positive-down, so negative
        # is up-left.
        self.assertLess(offset.xOffset, 0)
        self.assertLess(offset.yOffset, 0)

        self.assertEqual(
            offset.offsetUnits,
            Qgis.RenderUnit.Millimeters
        )


    def test_centered_rule_has_no_offset(self):

        self.manager.apply_label(self.layer, "GZD")

        rules = _rules_by_description(self.layer)

        centered = rules["Centered, no offset (zoomed out)"].settings()

        self.assertEqual(centered.xOffset, 0)
        self.assertEqual(centered.yOffset, 0)


    def test_both_rules_anchor_to_the_true_centroid(self):

        # Real reported bug, 2026-08-06: without a geometry-generator-
        # derived fixed point, PAL doesn't anchor a polygon label to
        # its true, full centroid - for a GZD zone, which routinely
        # spans well beyond what's on screen at once, it drifts
        # toward whatever portion is currently visible instead,
        # sliding the label toward (and past) the zone's own edge
        # into a neighbouring zone as more of it pans off screen.
        # Confirmed live by panning a fresh grid across zone
        # boundaries in every direction. centroid($geometry) is immune
        # to this - it's computed from the full geometry regardless
        # of what's currently on screen. Applies to both scale
        # variants (offset and centred both anchor from this same
        # fixed point, the offset rule just nudges from it).
        # Since 2026-08-17 the anchor is the centroid of the VISIBLE
        # portion, not of the whole cell - which reduces to the true
        # centroid whenever the cell is entirely on screen, and keeps
        # a label on screen when it is not. See
        # _anchor_to_visible_centroid().
        self.manager.apply_label(self.layer, "GZD")

        root = self.layer.labeling().rootRule()

        for rule in root.children():

            settings = rule.settings()

            self.assertTrue(settings.geometryGeneratorEnabled)

            self.assertEqual(
                settings.geometryGenerator,
                "centroid(intersection($geometry, @map_extent))"
            )


    def test_rules_partition_on_offset_max_scale(self):

        # Exactly one style is ever active. The offset applies only
        # while the cell is BOTH large enough and wholly on screen;
        # the centred rule is its exact negation, further bounded
        # above by the scale at which labelling stops entirely.
        self.manager.apply_label(self.layer, "GZD")

        rules = _rules_by_description(self.layer)

        offset_max = self.manager._offset_max_scale_expression(self.layer)
        hide_min = self.manager._scale_for_on_screen_mm(
            self.manager.GZD_LABEL_MIN_ON_SCREEN_MM
        )
        whole = "contains(@map_extent, $geometry)"

        self.assertEqual(
            rules["Offset up-left (zoomed in)"].filterExpression(),
            f"@map_scale < {offset_max} AND {whole}"
        )

        self.assertEqual(
            rules["Centered, no offset (zoomed out)"].filterExpression(),
            f"NOT (@map_scale < {offset_max} AND {whole})"
            f" AND @map_scale < {hide_min}"
        )

        # The threshold is per cell, not one number for the whole
        # grid - it has to read the feature's own half-extent.
        self.assertIn(
            self.manager.HALF_EXTENT_FIELD,
            offset_max
        )


    def test_both_rules_keep_gzd_priority(self):

        # Both scale variants must stay at the same low priority (1) -
        # this label is background context that should still yield to
        # the 100km square label (SQUARE_LABEL_PRIORITY) and the
        # sub-grid regardless of which scale rule is currently active.
        self.manager.apply_label(self.layer, "GZD")

        root = self.layer.labeling().rootRule()

        for rule in root.children():

            self.assertEqual(
                rule.settings().priority,
                1
            )


class TestCornerOffsetSigns(QgisTestCase):

    """
    Regression test for a real bug: CORNERS' y_sign values were
    written assuming PAL's yOffset is positive-up (map/mathematical
    convention), but it's actually positive-down (screen/render
    convention) - confirmed live by rendering a single offset label
    and inspecting the pixels. Getting this backwards nudges every
    corner label OUTWARD into the neighbouring square instead of
    INWARD into its own - confirmed live too, by rendering a small
    2x2 test grid and seeing each square's corner labels land on the
    wrong side of a shared boundary.

    Expected signs, given confirmed +x = right, +y = down:
    - SW (bottom-left corner) needs right+up to go inward: (+1, -1)
    - SE (bottom-right corner) needs left+up to go inward: (-1, -1)
    - NW (top-left corner) needs right+down to go inward: (+1, +1)
    - NE (top-right corner) needs left+down to go inward: (-1, +1)
    """

    EXPECTED_SIGNS = {
        "SW": (1, -1),
        "SE": (-1, -1),
        "NW": (1, 1),
        "NE": (-1, 1),
    }

    def test_corner_signs_nudge_inward_not_outward(self):

        actual = {
            name: (x_sign, y_sign)
            for name, _anchor_expr, x_sign, y_sign in GridLabelManager.CORNERS
        }

        self.assertEqual(actual, self.EXPECTED_SIGNS)
