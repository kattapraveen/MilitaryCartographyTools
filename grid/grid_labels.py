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
    # POLYGON ITSELF IS STILL LARGE ON SCREEN. See
    # _offset_max_scale_expression() below for the zoomed-out case,
    # where this stops being true.
    GZD_LABEL_OFFSET_MM = 12


    # Past the point where the up-left nudge above would push the
    # label out of its own polygon, the UTM/GZD label sits exactly on
    # the centroid instead - same "a fixed page offset stops being safe
    # once the polygon is small on screen" fix already applied to the
    # 100km square label's own corner/centered switch. Fixes a real
    # reported bug: at zoomed-out scales the offset pushed this label
    # into the NEIGHBOURING zone.
    #
    # Where that point falls is decided PER CELL, from the cell's own
    # HALF_MIN_M (see grid/utm_grid.py) rather than one global scale
    # for all of them. A single threshold cannot be right here: GZD
    # cells range from 3 degrees wide (31V) to 12 (33X and 35X), and a
    # 6-degree cell's ground width falls by a factor of ten between the
    # equator and band X. Any global value is simultaneously far too
    # cautious near the equator and marginal near the pole. This was
    # carried as a known-loose constant from 2026-08-06 until
    # 2026-08-17.
    #
    # The offset stays inside the cell while
    #
    #     (GZD_LABEL_OFFSET_MM / 1000) * @map_scale
    #         <= HALF_MIN_M * GZD_OFFSET_SAFE_FRACTION
    #
    # which rearranges to a maximum scale per cell. The fraction is the
    # deliberate margin: the offset may spend at most half the room the
    # cell actually has, leaving the rest for the label's own drawn
    # width, which this comparison does not attempt to model.
    GZD_OFFSET_SAFE_FRACTION = 0.5

    # Below this on-screen width, a GZD cell stops carrying a label at
    # all. `displayAll` (see _apply_gzd_common_settings) deliberately
    # switches OFF PAL's collision suppression so the GZD watermark
    # still shows when it loses a priority fight to the 100km or
    # sub-grid labels - which means nothing else will ever hide these,
    # and an upper cutoff has to be supplied here instead. Without one,
    # a world view drew 1,197 labels on top of each other and the grid
    # lines vanished underneath them entirely (reported and reproduced
    # 2026-08-17). apply_square_label already had exactly this pairing
    # right for the 100km squares - see CENTER_LABEL_MAX_SCALE - and
    # this is the same lesson applied to the GZD label.
    #
    # 16mm is calibrated, not guessed: the maintainer reported a world
    # view first becoming marginally readable at 1:40,372,844, which
    # for a 6-degree equatorial cell is 16mm across.
    GZD_LABEL_MIN_ON_SCREEN_MM = 16.0

    # Used only when HALF_MIN_M is absent or null - a "UTM Grid" layer
    # from a project saved before that field existed. The old global
    # constant, kept as the fallback precisely because it is the
    # behaviour those layers already had.
    GZD_OFFSET_FALLBACK_SCALE = 3000000

    HALF_EXTENT_FIELD = "HALF_MIN_M"


    def _scale_for_on_screen_mm(self, millimetres):

        """
        The map scale at which a cell of HALF_MIN_M metres measures
        `millimetres` across on screen, as an expression.

        A cell's full width is twice its half-extent, and a metre is
        1000mm, so on-screen mm = 2 * HALF_MIN_M * 1000 / @map_scale;
        solving for the scale gives the constant below. Returns None
        for a layer with no HALF_MIN_M field - see
        _offset_max_scale_expression() for why that case is decided
        here rather than inside the expression.
        """

        per_metre = 2000.0 / millimetres

        return f'("{self.HALF_EXTENT_FIELD}" * {per_metre})'


    def _has_half_extent(self, layer):

        return layer is not None and layer.fields().indexOf(
            self.HALF_EXTENT_FIELD
        ) >= 0


    def _offset_max_scale_expression(self, layer=None):

        """
        The largest map scale at which a cell can still carry the
        up-left nudge - an expression, since the answer differs per
        feature.

        Takes the layer so the decision is made HERE rather than in
        the expression. A layer saved before HALF_MIN_M existed has no
        such column, and referencing a missing column is an evaluation
        ERROR, not a null - so `coalesce("HALF_MIN_M" * k, fallback)`
        does not rescue it, it yields null, and `@map_scale < null` is
        false for BOTH rules. That would leave such a layer with no
        GZD label at all. Checking the field up front and emitting the
        plain old constant instead keeps those layers behaving exactly
        as they already did.
        """

        if not self._has_half_extent(layer):

            return str(self.GZD_OFFSET_FALLBACK_SCALE)

        per_metre = (
            self.GZD_OFFSET_SAFE_FRACTION
            * 1000.0
            / self.GZD_LABEL_OFFSET_MM
        )

        return (
            f'coalesce("{self.HALF_EXTENT_FIELD}" * {per_metre}, '
            f'{self.GZD_OFFSET_FALLBACK_SCALE})'
        )


    def _anchor_to_true_centroid(self, settings):

        """
        Anchor to the polygon's own full centroid, regardless of what
        portion is on screen. Used by the 100km square labels, whose
        squares are small enough that the whole square is essentially
        always in view when its label matters - so the visible-portion
        refinement _anchor_to_visible_centroid() makes for GZD cells
        buys them nothing, and changing their smoke-tested placement
        for no gain would be the wrong trade.
        """

        settings.geometryGeneratorEnabled = True

        settings.geometryGeneratorType = (
            QgsWkbTypes.GeometryType.PointGeometry
        )

        settings.geometryGenerator = "centroid($geometry)"


    def _anchor_to_visible_centroid(self, settings):

        """
        Force the label onto the centroid of the part of the polygon
        that is actually on screen, via
        `centroid(intersection($geometry, @map_extent))`.

        Two separate bugs meet here, and the intersection is what
        satisfies both at once.

        The first: with placement = OverPoint applied straight to a
        polygon, PAL does not anchor to the feature's true centroid -
        for a large polygon only partly on screen (routine for a GZD
        zone) it drifts toward the visible portion and slides the
        label past the zone's own edge into the neighbour. Confirmed
        live by panning across zone boundaries.

        The second, found 2026-08-17: anchoring to `centroid($geometry)`
        fixed that, but left the label with exactly ONE anchor point.
        Zoom in until a zone is larger than the viewport, pan away from
        its centre, and there is no label anywhere on screen. Corner
        labels - the answer apply_square_label reached for 100km
        squares - do not fix this case either: pan into the deep
        interior of a cell this large and no corner is on screen
        either. apply_square_label's own docstring records the same
        limitation being hit and worked around in 2026-08-03.

        Intersecting with @map_extent answers both. The result is
        always on screen when any part of the cell is, so the label
        cannot vanish; and both the cell and the map extent are
        rectangles, so the intersection is a rectangle and its
        centroid is strictly inside it - and therefore inside the
        cell - so the label cannot escape into the neighbour. When
        the whole cell is visible the intersection IS the cell, and
        this reduces exactly to the true centroid it replaces.
        """

        settings.geometryGeneratorEnabled = True

        settings.geometryGeneratorType = (
            QgsWkbTypes.GeometryType.PointGeometry
        )

        settings.geometryGenerator = (
            "centroid(intersection($geometry, @map_extent))"
        )


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

        self._anchor_to_visible_centroid(settings)

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
        on screen (see _offset_max_scale_expression()) that any fixed offset
        risks landing outside it, in the neighbouring GZD zone
        instead.
        """

        settings = QgsPalLayerSettings()

        settings.fieldName = field

        settings.placement = (
            Qgis.LabelPlacement.OverPoint
        )

        self._anchor_to_visible_centroid(settings)

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
        Apply labels to the UTM/GZD grid layer, in four scale bands
        decided per cell from its own HALF_MIN_M - exactly one active
        at any scale, no overlap and no gap:

        Every label anchors to the centroid of the part of its cell
        that is actually on screen - see _anchor_to_visible_centroid()
        for the two bugs that answers. Three bands, exactly one active
        at any scale:

        - Whole cell on screen and comfortably large: offset up-left
          of the centroid, to stay clear of the 100km square labels.
        - Cell clipped by the view, or small enough that the offset
          would cross its own edge: the same label, centred, no
          offset.
        - Cell only a few millimetres across: no label at all.
          displayAll means nothing else will ever suppress these, so
          without this a world view drew 1,197 of them on top of each
          other and buried the grid lines underneath.

        apply_square_label reached the same "and an upper cutoff, or
        displayAll buries everything" conclusion for 100km squares
        first - see CENTER_LABEL_MAX_SCALE.
        """

        root_rule = QgsRuleBasedLabeling.Rule(
            QgsPalLayerSettings()
        )

        offset_max = self._offset_max_scale_expression(layer)

        if self._has_half_extent(layer):

            hide_min = self._scale_for_on_screen_mm(
                self.GZD_LABEL_MIN_ON_SCREEN_MM
            )

        else:
            # A layer saved before HALF_MIN_M existed keeps exactly the
            # two-band behaviour it already had. Its cells carry no
            # size to reason from, and silently changing what an
            # existing project draws is worse than leaving it be.
            hide_min = None

        # The offset only applies while the WHOLE cell is on screen.
        # Once it is clipped, the anchor moves to the centre of the
        # visible portion (see _anchor_to_visible_centroid), and a
        # fixed 12mm nudge from there could push the label off a
        # narrow sliver and into the neighbouring cell - the very
        # thing the offset threshold exists to prevent, reappearing
        # by a different route.
        whole_cell_visible = "contains(@map_extent, $geometry)"

        offset_rule = QgsRuleBasedLabeling.Rule(
            self._gzd_offset_settings(field, size)
        )

        offset_rule.setFilterExpression(
            f"@map_scale < {offset_max} AND {whole_cell_visible}"
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
            f"NOT (@map_scale < {offset_max} AND {whole_cell_visible})"
            + (f" AND @map_scale < {hide_min}" if hide_min else "")
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