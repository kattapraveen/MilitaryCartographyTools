# -*- coding: utf-8 -*-

"""
Grid Label Manager

Handles labelling of military grid layers.

Military Cartography Tools
"""


from qgis.core import (
    QgsPalLayerSettings,
    QgsRuleBasedLabeling,
    QgsWkbTypes,
    Qgis
)

from ..core.text_format import build_text_format



class GridLabelManager:
    """
    Controls grid labels.
    """


    def __init__(self):

        pass



    # How far, top-left of its anchor point, to nudge the UTM/GZD
    # label - reduces the odds of it landing exactly on top of a
    # 100km square's own corner/center label in the first place,
    # rather than relying solely on priority (below) and layer
    # z-order to sort out a collision after the fact. Confirmed live
    # (2026-08-05): combined with SQUARE_LABEL_PRIORITY, this leaves
    # every case checked overlap-free - AT SCALES WHERE THE GZD
    # POLYGON ITSELF IS STILL LARGE ON SCREEN. See GZD_OFFSET_MAX_SCALE
    # below for the zoomed-out case, where this stops being true.
    GZD_LABEL_OFFSET_MM = 12


    # Beyond this map-scale denominator, the UTM/GZD label switches
    # from the up-left nudge above to sitting exactly on its polygon's
    # centroid instead - same "fixed offset stops being safe once the
    # polygon is small on screen" fix already applied to the 100km
    # square label's own corner/centered switch (see
    # apply_square_label's corner_scale_threshold), just for a much
    # larger polygon: a GZD zone is roughly 6deg x 8deg (very roughly
    # 600-900km per side), so the crossover happens at a far more
    # zoomed-out scale than a 100km square's own 250,000. Loosely
    # derived (a 12mm offset should stay comfortably inside even the
    # narrower ~half-width of a GZD zone up to a few million scale)
    # rather than measured live - worth tuning once seen live, same
    # as CENTER_LABEL_MAX_SCALE below. Fixes a real reported bug: at
    # sufficiently zoomed-out scales, the fixed offset pushed this
    # label out of its own GZD polygon and into the neighbouring one.
    GZD_OFFSET_MAX_SCALE = 3000000


    def _anchor_to_true_centroid(self, settings):

        """
        Force the label onto a point generated from centroid($geometry)
        rather than letting PAL derive a position from the polygon
        geometry directly. Real bug, confirmed live: with placement =
        OverPoint applied straight to a polygon (no geometry
        generator), PAL doesn't anchor to the feature's true, full
        centroid - for a large polygon that's only partially on
        screen (routine for a GZD zone, which regularly spans well
        beyond a single view, unlike a 100km square), it instead
        drifts toward whatever portion of the polygon is currently
        visible, sliding the label toward whichever edge is cut off -
        confirmed by panning a fresh grid across zone boundaries and
        watching each zone's label creep toward, and past, its own
        edge into the neighbour as more of it left the screen.
        `_corner_settings()` already avoids this (it generates an
        explicit corner point via make_point(...) before placing), so
        this mirrors that same fix for the centroid case - centroid()
        computes the true, full-geometry centroid regardless of what
        portion of the polygon happens to be on screen.
        """

        settings.geometryGeneratorEnabled = True

        settings.geometryGeneratorType = (
            QgsWkbTypes.GeometryType.PointGeometry
        )

        settings.geometryGenerator = "centroid($geometry)"


    def _gzd_offset_settings(self, field, size):

        """
        The UTM/GZD label nudged up-left from its polygon's true
        centroid - safe once the polygon is large enough on screen
        that the fixed mm offset can't reach past its edge. See
        GZD_LABEL_OFFSET_MM.
        """

        settings = QgsPalLayerSettings()

        settings.fieldName = field

        settings.placement = (
            Qgis.LabelPlacement.OverPoint
        )

        self._anchor_to_true_centroid(settings)

        # Nudged up and left from its anchor point (negative x/y -
        # confirmed live that PAL's offsets are positive-right/
        # positive-down, so negative is up-left) rather than sitting
        # exactly on the polygon's own centroid, which is where a
        # 100km square's centred label is also anchored at matching
        # zoom levels - reduces how often the two even compete for
        # the same screen space.
        settings.xOffset = -self.GZD_LABEL_OFFSET_MM
        settings.yOffset = -self.GZD_LABEL_OFFSET_MM

        settings.offsetUnits = (
            Qgis.RenderUnit.Millimeters
        )

        self._apply_gzd_common_settings(settings, size)

        return settings


    def _gzd_centered_settings(self, field, size):

        """
        The UTM/GZD label sitting exactly on its polygon's true
        centroid, no offset - used once the polygon is small enough
        on screen (see GZD_OFFSET_MAX_SCALE) that any fixed offset
        risks landing outside it, in the neighbouring GZD zone
        instead.
        """

        settings = QgsPalLayerSettings()

        settings.fieldName = field

        settings.placement = (
            Qgis.LabelPlacement.OverPoint
        )

        self._anchor_to_true_centroid(settings)

        self._apply_gzd_common_settings(settings, size)

        return settings


    def _apply_gzd_common_settings(self, settings, size):

        # Low priority: this is background context (the whole
        # GZD), so it should yield to the sub-grid's tick labels
        # AND the 100km square labels (SQUARE_LABEL_PRIORITY)
        # rather than fight either for the same screen space.
        settings.priority = 1

        # displayAll bypasses PAL's collision suppression, so
        # this still renders (faded, via opacity below) even
        # when it loses that priority fight, rather than
        # disappearing outright - a watermark, not a competitor.
        settings.displayAll = True

        settings.setFormat(
            build_text_format(
                size,
                opacity=0.4
            )
        )


    def apply_label(
        self,
        layer,
        field,
        size=10
    ):

        """
        Apply labels to the UTM/GZD grid layer - offset up-left of
        each polygon's centroid while it's still large enough on
        screen for that to stay safely inside it, falling back to
        sitting exactly on the centroid once zoomed out past
        GZD_OFFSET_MAX_SCALE (mirrors apply_square_label's own
        corner/centered switch, for the same reason).
        """

        root_rule = QgsRuleBasedLabeling.Rule(
            QgsPalLayerSettings()
        )

        offset_rule = QgsRuleBasedLabeling.Rule(
            self._gzd_offset_settings(field, size)
        )

        offset_rule.setFilterExpression(
            f"@map_scale < {self.GZD_OFFSET_MAX_SCALE}"
        )

        offset_rule.setDescription(
            "Offset up-left (zoomed in)"
        )

        root_rule.appendChild(
            offset_rule
        )

        centered_rule = QgsRuleBasedLabeling.Rule(
            self._gzd_centered_settings(field, size)
        )

        centered_rule.setFilterExpression(
            f"@map_scale >= {self.GZD_OFFSET_MAX_SCALE}"
        )

        centered_rule.setDescription(
            "Centered, no offset (zoomed out)"
        )

        root_rule.appendChild(
            centered_rule
        )

        labeling = QgsRuleBasedLabeling(
            root_rule
        )


        layer.setLabeling(
            labeling
        )


        layer.setLabelsEnabled(
            True
        )


        layer.triggerRepaint()



    # Faded like a watermark rather than a fully opaque label,
    # since this sits underneath the (much crisper) sub-grid
    # tick labels once those are enabled.
    WATERMARK_OPACITY = 0.4


    # Beyond this map-scale denominator, a 100km square's own
    # label stops rendering entirely (falling back to the UTM
    # GZD label for context) - mirrors
    # MGRSSubGridGenerator.LABEL_MAX_SCALE. Zoomed out this far,
    # a 100km square's on-screen footprint is only a few
    # millimetres, so with displayAll forcing every one of them
    # to render regardless of collisions, a full-size label per
    # square is clutter rather than information. Loosely chosen
    # as roughly an order of magnitude past corner_scale_threshold;
    # worth adjusting once you've seen it live.
    CENTER_LABEL_MAX_SCALE = 3000000


    # Shared by both the zoomed-in corner labels and the zoomed-out
    # centred label (see apply_square_label) - matched 2026-08-03 so
    # a square's label reads the same size whether it's showing at
    # its corners or centred, rather than shrinking on the far side
    # of the corner_scale_threshold cutover.
    SQUARE_LABEL_SIZE = 14


    # Above the UTM/GZD label's priority (1) so a 100km square's own
    # label wins whenever the two still end up competing for the same
    # screen space (belt-and-suspenders alongside GZD_LABEL_OFFSET_MM
    # above) - but below the sub-grid tick labels' priority (9, see
    # mgrs_sub_grid.py), preserving the intended fine-to-coarse
    # hierarchy: sub-grid > 100km square > UTM GZD.
    SQUARE_LABEL_PRIORITY = 5


    def _centered_settings(self, field, size):

        """
        One label per square, centred, no offset - used when
        zoomed out far enough that a corner position would look
        cluttered or misleading, and a square's on-screen footprint
        may be too small for any fixed screen-space nudge to stay
        safely inside it.
        """

        settings = QgsPalLayerSettings()

        settings.fieldName = field

        settings.placement = (
            Qgis.LabelPlacement.OverPoint
        )

        # Same fix as the GZD label's own centred/offset settings
        # (see _anchor_to_true_centroid) - without this, PAL derives
        # the anchor from whatever portion of the square happens to
        # be on screen rather than its true centroid. Less likely to
        # be visible for a 100km square (usually small enough to be
        # fully on screen at once) than for a GZD zone, but the same
        # underlying bug either way.
        self._anchor_to_true_centroid(settings)

        # Above the UTM GZD label's priority, below the sub-grid's -
        # see SQUARE_LABEL_PRIORITY. displayAll still keeps this a
        # watermark against the sub-grid's own labels rather than
        # disappearing outright when it loses that fight.
        settings.priority = self.SQUARE_LABEL_PRIORITY

        settings.displayAll = True

        settings.setFormat(
            build_text_format(size, opacity=self.WATERMARK_OPACITY)
        )

        return settings



    #
    # One entry per corner of a square's own bounding box:
    # (label, anchor expression, x offset sign, y offset sign).
    # The offset sign always points back INTO the square (e.g.
    # the south-west anchor nudges up/right, the north-east
    # anchor nudges down/left), so each square unambiguously
    # shows its own label at each of its own four corners -
    # matching the USGS/military convention where a 100km
    # square's identifier appears at every corner it touches,
    # so there's never doubt which square a label belongs to.
    #
    # y_sign follows QgsPalLayerSettings.yOffset's own convention -
    # confirmed live (rendered a single offset label and inspected
    # the pixels) that positive yOffset moves a label DOWN the
    # screen, not up. A square's SW/SE corners sit at its bottom
    # edge, so nudging "inward" (up) needs a NEGATIVE y_sign; its
    # NW/NE corners sit at the top edge, so nudging inward (down)
    # needs POSITIVE. Getting this backwards (as an earlier version
    # of this list did, assuming +y meant up) pushes every corner
    # label outward into the neighbouring square instead of inward
    # into its own - confirmed live by rendering a small 2x2 test
    # grid: each square's labels landed on the wrong side of a
    # shared boundary from its neighbour.
    CORNERS = [
        (
            "SW",
            "make_point(x_min($geometry), y_min($geometry))",
            1,
            -1
        ),
        (
            "SE",
            "make_point(x_max($geometry), y_min($geometry))",
            -1,
            -1
        ),
        (
            "NW",
            "make_point(x_min($geometry), y_max($geometry))",
            1,
            1
        ),
        (
            "NE",
            "make_point(x_max($geometry), y_max($geometry))",
            -1,
            1
        ),
    ]



    def _corner_settings(self, field, size, gap_mm, anchor_expr, x_sign, y_sign):

        """
        One label per square, anchored to one of its own
        corners and nudged inward (toward the square's own
        centre) by a fixed screen distance.
        """

        settings = QgsPalLayerSettings()

        settings.fieldName = field

        settings.placement = (
            Qgis.LabelPlacement.OverPoint
        )

        settings.geometryGeneratorEnabled = True

        settings.geometryGeneratorType = (
            QgsWkbTypes.GeometryType.PointGeometry
        )

        settings.geometryGenerator = anchor_expr

        settings.xOffset = x_sign * gap_mm

        settings.yOffset = y_sign * gap_mm

        settings.offsetUnits = (
            Qgis.RenderUnit.Millimeters
        )

        # Above the UTM GZD label's priority, below the sub-grid's -
        # see SQUARE_LABEL_PRIORITY.
        settings.priority = self.SQUARE_LABEL_PRIORITY

        settings.displayAll = True

        settings.setFormat(
            build_text_format(size, opacity=self.WATERMARK_OPACITY)
        )

        return settings



    def apply_square_label(
        self,
        layer,
        field,
        corner_size=None,
        corner_gap_mm=12,
        corner_scale_threshold=250000,
        center_far_size=None,
        center_max_scale=None
    ):

        """
        Label a 100km-square-style grid layer, switching
        placement by zoom level - exactly one style active at any
        given scale, never both at once:

        - Zoomed in past corner_scale_threshold (e.g. only a
          handful of squares visible): each square shows its
          label at all four of its own corners, nudged inward -
          so every corner on screen unambiguously shows which
          square it belongs to.
        - Zoomed out at or beyond corner_scale_threshold (no
          more corner labels): one centred label per square, same
          size as the corner labels, with no offset - a square may
          now be only a few millimetres across, so a fixed offset
          that's safe zoomed in would push the label past its own
          edge and into a neighbouring square instead.
        - Zoomed out beyond center_max_scale: no per-square label
          at all, since that many squares' worth of labels piling
          up (displayAll bypasses PAL's own collision suppression)
          is clutter rather than information; the UTM GZD label
          is left to carry context at that scale.

        An earlier version also kept a centred label active
        alongside the corner labels while zoomed in (to guarantee
        something shows even if panned to a square's interior with
        none of its corners on screen) - removed 2026-08-03 after
        live testing showed it read as two conflicting labels for
        the same square rather than a helpful fallback. The
        traded-away edge case (deep zoom, no corner in view) now
        shows no label for that square until you pan enough to see
        one of its corners or zoom out past corner_scale_threshold -
        confirmed as an accepted limitation (not a bug) rather than
        something worth the added rule-engine complexity to fix; see
        the roadmap's 100km-label entry.
        """

        if corner_size is None:

            corner_size = self.SQUARE_LABEL_SIZE

        if center_far_size is None:

            center_far_size = self.SQUARE_LABEL_SIZE

        if center_max_scale is None:

            center_max_scale = self.CENTER_LABEL_MAX_SCALE


        root_rule = QgsRuleBasedLabeling.Rule(
            QgsPalLayerSettings()
        )


        centered_far_rule = QgsRuleBasedLabeling.Rule(
            self._centered_settings(
                field,
                center_far_size
            )
        )

        centered_far_rule.setFilterExpression(
            f"@map_scale >= {corner_scale_threshold} "
            f"AND @map_scale <= {center_max_scale}"
        )

        centered_far_rule.setDescription(
            "Centered, no offset (zoomed out)"
        )

        root_rule.appendChild(
            centered_far_rule
        )


        for name, anchor_expr, x_sign, y_sign in self.CORNERS:

            corner_rule = QgsRuleBasedLabeling.Rule(
                self._corner_settings(
                    field,
                    corner_size,
                    corner_gap_mm,
                    anchor_expr,
                    x_sign,
                    y_sign
                )
            )

            corner_rule.setFilterExpression(
                f"@map_scale < {corner_scale_threshold}"
            )

            corner_rule.setDescription(
                f"Corner {name} (zoomed in)"
            )

            root_rule.appendChild(
                corner_rule
            )


        labeling = QgsRuleBasedLabeling(
            root_rule
        )


        layer.setLabeling(
            labeling
        )


        layer.setLabelsEnabled(
            True
        )


        layer.triggerRepaint()