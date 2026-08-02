# -*- coding: utf-8 -*-

"""
Grid Label Manager

Handles labelling of military grid layers.

Military Cartography Tools
"""


from qgis.core import (
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
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



    def apply_label(
        self,
        layer,
        field,
        size=10
    ):

        """
        Apply labels to a polygon grid layer.
        """


        settings = QgsPalLayerSettings()


        settings.fieldName = field


        #
        # QGIS 4.x polygon label placement
        #
        settings.placement = (
            Qgis.LabelPlacement.OverPoint
        )

        # Low priority: this is background context (the whole
        # GZD), so it should yield to the sub-grid's tick labels
        # rather than fight them for the same screen space.
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


        labeling = QgsVectorLayerSimpleLabeling(
            settings
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


    # Both this label and the UTM GZD label use OverPoint
    # placement on a polygon much bigger than the viewport, so
    # PAL tends to plant both of them near the middle of
    # whatever's currently on screen regardless of their true
    # geographic centroids - nudging this one down keeps them
    # from sitting directly on top of each other.
    #
    # This is a FIXED screen-space distance, so it's only safe
    # to apply while a square's own on-screen footprint is
    # comfortably bigger than 20mm (true while zoomed in, past
    # corner_scale_threshold - the same regime the corner labels
    # below are already known to render correctly in). Applied
    # unconditionally at every zoom level, it used to push the
    # label straight past a shrunken square's own edge and into
    # whichever square sits next to it (always the one to the
    # south, since the offset is always downward) - see
    # apply_square_label() for the scale gate that now prevents
    # this.
    CENTER_LABEL_Y_OFFSET_MM = -20


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


    # Smaller than the zoomed-in centered/corner size (24) - used
    # once corner labels have already dropped out (see
    # apply_square_label), where many more squares tend to be on
    # screen at once and a large font makes the pile-up worse.
    CENTER_LABEL_FAR_SIZE = 14


    def _centered_settings(self, field, size, apply_offset):

        """
        One label per square, centred - used when zoomed out
        far enough that a corner position would look cluttered
        or misleading.

        apply_offset: nudge the label down by
        CENTER_LABEL_Y_OFFSET_MM to keep it clear of the UTM GZD
        label. Only pass True when the caller has already
        confirmed (via a scale filter) that the offset is safely
        smaller than the square's own on-screen size - otherwise
        it can land in a neighbouring square instead of this one.
        """

        settings = QgsPalLayerSettings()

        settings.fieldName = field

        settings.placement = (
            Qgis.LabelPlacement.OverPoint
        )

        # Background context, like the UTM GZD label - low
        # priority plus displayAll so it fades into a watermark
        # under the sub-grid's labels instead of disappearing.
        settings.priority = 1

        settings.displayAll = True

        if apply_offset:

            settings.yOffset = self.CENTER_LABEL_Y_OFFSET_MM

            settings.offsetUnits = (
                Qgis.RenderUnit.Millimeters
            )

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
    CORNERS = [
        (
            "SW",
            "make_point(x_min($geometry), y_min($geometry))",
            1,
            1
        ),
        (
            "SE",
            "make_point(x_max($geometry), y_min($geometry))",
            -1,
            1
        ),
        (
            "NW",
            "make_point(x_min($geometry), y_max($geometry))",
            1,
            -1
        ),
        (
            "NE",
            "make_point(x_max($geometry), y_max($geometry))",
            -1,
            -1
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

        settings.priority = 1

        settings.displayAll = True

        settings.setFormat(
            build_text_format(size, opacity=self.WATERMARK_OPACITY)
        )

        return settings



    def apply_square_label(
        self,
        layer,
        field,
        center_size=24,
        corner_size=24,
        corner_gap_mm=12,
        corner_scale_threshold=250000,
        center_far_size=None,
        center_max_scale=None
    ):

        """
        Label a 100km-square-style grid layer, switching
        placement by zoom level:

        - Zoomed in past corner_scale_threshold (e.g. only a
          handful of squares visible): each square shows its
          label at all four of its own corners, nudged inward -
          so every corner on screen unambiguously shows which
          square it belongs to - PLUS a centred label nudged
          clear of the UTM GZD label's own anchor point. The
          offset is safe here because a square's on-screen size
          is comfortably bigger than the fixed nudge distance.
        - Zoomed out at or beyond corner_scale_threshold (no
          more corner labels): one centred label per square,
          smaller and with NO offset - a square may now be only
          a few millimetres across, so a fixed offset that used
          to be safe would push the label past its own edge and
          into a neighbouring square instead.
        - Zoomed out beyond center_max_scale: no per-square
          label at all, since that many squares' worth of labels
          piling up (displayAll bypasses PAL's own collision
          suppression) is clutter rather than information; the
          UTM GZD label is left to carry context at that scale.

        Between them, the two centred rules stay active at every
        zoom level up to center_max_scale (not just zoomed out)
        rather than being replaced by the corner rules - a square
        that's zoomed in far enough to have NONE of its four
        corners on screen (you're panned to somewhere in the
        middle of it) would otherwise show no label at all. Since
        they're low-priority, low-opacity watermarks like the
        corner labels, having both active at once when a corner
        happens to also be in view just means they coexist rather
        than fighting.
        """

        if center_far_size is None:

            center_far_size = self.CENTER_LABEL_FAR_SIZE

        if center_max_scale is None:

            center_max_scale = self.CENTER_LABEL_MAX_SCALE


        root_rule = QgsRuleBasedLabeling.Rule(
            QgsPalLayerSettings()
        )


        centered_near_rule = QgsRuleBasedLabeling.Rule(
            self._centered_settings(
                field,
                center_size,
                apply_offset=True
            )
        )

        centered_near_rule.setFilterExpression(
            f"@map_scale < {corner_scale_threshold}"
        )

        centered_near_rule.setDescription(
            "Centered, offset clear of the GZD label (zoomed in)"
        )

        root_rule.appendChild(
            centered_near_rule
        )


        centered_far_rule = QgsRuleBasedLabeling.Rule(
            self._centered_settings(
                field,
                center_far_size,
                apply_offset=False
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