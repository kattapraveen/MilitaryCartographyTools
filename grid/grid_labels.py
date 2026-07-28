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
    CENTER_LABEL_Y_OFFSET_MM = -20


    def _centered_settings(self, field, size):

        """
        One label per square, centred - used when zoomed out
        far enough that a corner position would look cluttered
        or misleading.
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
            QgsWkbTypes.PointGeometry
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
        corner_scale_threshold=250000
    ):

        """
        Label a 100km-square-style grid layer, switching
        placement by zoom level:

        - Zoomed out (map scale denominator >=
          corner_scale_threshold): one bigger, centred label
          per square.
        - Zoomed in past that point (e.g. only a handful of
          squares visible): each square ALSO shows its label at
          all four of its own corners, nudged inward - so every
          corner on screen unambiguously shows which square it
          belongs to, and squares sharing an intersection show
          their labels clustered around it.

        The centred rule stays active at every zoom level (not
        just zoomed out) rather than being replaced by the
        corner rules - a square that's zoomed in far enough to
        have NONE of its four corners on screen (you're panned
        to somewhere in the middle of it) would otherwise show
        no label at all. Since it's a low-priority, low-opacity
        watermark like the corner labels, having both active at
        once when a corner happens to also be in view just means
        the two coexist rather than fighting.
        """


        root_rule = QgsRuleBasedLabeling.Rule(
            QgsPalLayerSettings()
        )


        centered_rule = QgsRuleBasedLabeling.Rule(
            self._centered_settings(
                field,
                center_size
            )
        )

        centered_rule.setDescription(
            "Centered (always available as a fallback)"
        )

        root_rule.appendChild(
            centered_rule
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