# -*- coding: utf-8 -*-

"""
MGRS Sub Grid generator.

Creates MGRS 10km / 5km / 1km
sub-grid lines for the current
map extent.

Military Cartography Tools
"""

from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsPointXY,
    QgsRectangle,
    QgsCoordinateTransform,
    QgsProject,
    QgsLineSymbol,
    QgsRuleBasedRenderer,
    QgsPalLayerSettings,
    QgsRuleBasedLabeling,
    QgsLabelLineSettings,
    Qgis
)

from qgis.PyQt.QtCore import QVariant

from ..core.coordinate_utils import WGS84, get_utm_crs_from_zone_band
from ..core.text_format import build_text_format


class MGRSSubGridGenerator:
    """
    Generates MGRS sub-grid lines.

    Unlike the MGRS 100km grid (filled squares), the tactical
    sub-grid is rendered as actual grid LINES rather than
    filled cells: each line is a single feature spanning the
    full generated extent, tagged with which "order" it
    belongs to (10km/5km/1km, based on its own coordinate's
    alignment). This avoids the double-outline "boxes" artefact
    you get from drawing a fishnet of individual cell polygons,
    gives correct per-line width without a whole-cell
    approximation, and lets QGIS's line labelling keep each
    line's label floating within whatever part of it is
    currently on screen as you pan/zoom.

    Lines are generated per UTM Grid Zone Designator feature
    (like the 100km grid does), each using ITS OWN zone's UTM
    CRS - rather than picking one single zone from the map
    extent's centre and applying it across the whole visible
    area. A view spanning more than one zone/band would
    otherwise get some of its lines drawn in the wrong zone's
    projection, which shows up as a systematic tilt relative
    to the (correctly per-zone) 100km grid.
    """

    ORDER_MAJOR = 10000
    ORDER_MEDIUM = 5000
    ORDER_MINOR = 1000

    def __init__(self):

        self.layer = None



    def create_layer(self, spacing):

        name = f"MGRS {spacing//1000}km Grid"


        # MultiLineString, not LineString - matches the reference
        # workflow's own layer type (confirmed by inspecting its
        # GeoPackage schema directly: "geom" MULTILINESTRING).
        # Every export of our OWN labeling settings kept
        # serializing as layerType="UnknownGeometry" even after
        # explicitly setting settings.layerType in Python (a
        # silent no-op, matching an earlier QgsLabelLineSettings
        # gotcha this session) - a style saved from a genuinely
        # MultiLineString-typed layer correctly serialized as
        # layerType="LineGeometry" instead.
        self.layer = QgsVectorLayer(
            "MultiLineString?crs=" +
            QgsProject.instance().crs().authid(),
            name,
            "memory"
        )


        provider = self.layer.dataProvider()


        provider.addAttributes(
            [
                QgsField(
                    "GZD",
                    QVariant.String
                ),

                QgsField(
                    "ZONE",
                    QVariant.Int
                ),

                QgsField(
                    "AXIS",
                    QVariant.String
                ),

                QgsField(
                    "COORD",
                    QVariant.Int
                ),

                QgsField(
                    "ORDER",
                    QVariant.Int
                )
            ]
        )


        self.layer.updateFields()


        return self.layer



    #
    # Line widths so a coarser grid stays visually discernible
    # within a finer one. Each LINE's own tier is unambiguous
    # (based on its own coordinate), so - unlike a per-cell
    # approximation - only genuinely-aligned lines get the
    # thicker treatment.
    #
    # WIDTH_MAJOR reduced ~30% from 0.7 per user request (too
    # thick/dark at the original size).
    WIDTH_MAJOR = "0.5"
    WIDTH_MEDIUM = "0.35"
    WIDTH_MINOR = "0.2"

    # Gray rather than black - all three tiers were reading as
    # too dark/heavy against the basemap.
    LINE_COLOR = "100,100,100"


    def _line_symbol(self, width):

        return QgsLineSymbol.createSimple(
            {
                "color": self.LINE_COLOR,
                "line_width": width
            }
        )


    def apply_style(self, spacing):

        root_rule = QgsRuleBasedRenderer.Rule(None)

        major = QgsRuleBasedRenderer.Rule(
            self._line_symbol(self.WIDTH_MAJOR)
        )

        major.setFilterExpression(
            f'"ORDER" = {self.ORDER_MAJOR}'
        )

        root_rule.appendChild(major)

        if spacing <= self.ORDER_MEDIUM:

            medium = QgsRuleBasedRenderer.Rule(
                self._line_symbol(self.WIDTH_MEDIUM)
            )

            medium.setFilterExpression(
                f'"ORDER" = {self.ORDER_MEDIUM}'
            )

            root_rule.appendChild(medium)

        if spacing <= self.ORDER_MINOR:

            minor = QgsRuleBasedRenderer.Rule(
                self._line_symbol(self.WIDTH_MINOR)
            )

            minor.setFilterExpression(
                f'"ORDER" = {self.ORDER_MINOR}'
            )

            root_rule.appendChild(minor)

        self.layer.setRenderer(
            QgsRuleBasedRenderer(root_rule)
        )

        self.layer.triggerRepaint()



    # Same size across all three tiers, matching the (now
    # enlarged) MGRS 100km label - keeps the whole label
    # hierarchy visually consistent rather than each tier
    # picking its own size. Reduced ~60% from 18pt - confirmed
    # via a real printed export (canvas grid shown in a layout,
    # no grid frame) that 18pt rendered far too large relative to
    # the grid spacing.
    LABEL_SIZE = {
        ORDER_MAJOR: 12,
        ORDER_MEDIUM: 12,
        ORDER_MINOR: 12,
    }


    LABEL_EXPRESSION = (
        "lpad(to_string(to_int((\"COORD\" % 100000) / 1000)), 2, '0')"
    )


    def _line_anchor_settings(self, size, anchor_percent):

        """
        Settings for a tick label anchored a fixed percentage
        along its own line, via QGIS's native line-label anchor
        settings - not a custom geometryGenerator/@map_extent
        construction.

        This is the same mechanism (and the same lineAnchorType/
        lineAnchorPercent values) found in the reference
        workflow's own saved layer style (both the exported
        1kmgridlabel.qml and the styles embedded in
        QGIS_Military_grids.gpkg) - Horizontal placement plus a
        small lineAnchorPercent, rather than anything geometry-
        generator-based. That custom approach kept breaking in
        ways that were hard to pin down; this is the proven,
        native technique instead.
        """

        settings = QgsPalLayerSettings()

        settings.fieldName = self.LABEL_EXPRESSION

        settings.isExpression = True

        settings.placement = Qgis.LabelPlacement.Horizontal

        # Win out over the (much lower-priority) UTM GZD label
        # when the two would otherwise overlap.
        settings.priority = 9

        # Tested removing this (to match the reference's
        # overlapHandling="PreventOverlap"/allowDegraded="0"): in
        # the layout specifically, the easting labels vanished
        # entirely rather than landing in the right place - PAL
        # can't confidently resolve "Horizontal placement + line
        # anchor" for a near-vertical line in the layout's
        # single-pass static render at all, and without
        # displayAll it just drops the label instead of falling
        # back to a degraded (centred) placement. Centred-but-
        # visible beats invisible, so this stays True. This
        # on-map PAL limitation is accepted as a known constraint
        # rather than fixed at the PAL level - anyone who needs
        # exact print-layout border labels should use the
        # separate print-layout grid frame feature instead (see
        # grid/layout_grid_frame.py), which sidesteps PAL entirely
        # by using QGIS's own native map-grid frame annotations.
        settings.displayAll = True

        line_settings = settings.lineSettings()

        # Plain attribute assignment on this object silently
        # no-ops (confirmed by exporting the actual saved style
        # and finding pure defaults despite these being "set").
        # The real setter methods are, confirmed via dir(): a
        # mix of setAnchorX (no "Line") for type/textPoint/
        # clipping, but setLineAnchorPercent (keeps "Line") for
        # percent specifically - an inconsistency in the API
        # itself, not a mistake here.
        line_settings.setAnchorType(
            QgsLabelLineSettings.AnchorType(1)
        )

        line_settings.setAnchorTextPoint(
            QgsLabelLineSettings.AnchorTextPoint.CenterOfText
        )

        line_settings.setLineAnchorPercent(
            anchor_percent
        )

        # Without this, the percent above is computed against
        # the ENTIRE (buffered) line - which we deliberately
        # extend well beyond the viewport for pan headroom - so
        # a "near one end" anchor stays fixed at that geographic
        # point rather than tracking the pan (confirmed live:
        # AnchorClipping(1) produced exactly that "fixed" symptom,
        # so 1 = use the whole line, 0 = visible portion only -
        # the opposite of what the enum's ordinal suggested).
        #
        # NOTE: switching easting rules to AnchorClipping(1) to
        # try to fix the layout-eastings-at-centre issue was
        # tested and made things WORSE on both canvas (eastings
        # centred even right after generation, then vanish on
        # pan) and the layout (eastings vanish on pan) - so this
        # stays at 0 for both axes. The layout eastings-at-centre
        # bug is real but its mechanism is still unclear; it does
        # NOT appear to be about this clipping setting.
        line_settings.setAnchorClipping(
            QgsLabelLineSettings.AnchorClipping(0)
        )

        settings.setLineSettings(
            line_settings
        )

        settings.setFormat(
            build_text_format(size)
        )

        return settings


    def visible_orders(self, spacing):

        """
        Every tier actually drawn for this spacing selection -
        mirrors apply_style()'s rule set, since the coarser
        reference lines that come along for free (e.g. the
        10km/5km lines still shown when 1km is selected) should
        be labelled too, not just the exact tier the user picked.
        """

        orders = [self.ORDER_MAJOR]

        if spacing <= self.ORDER_MEDIUM:

            orders.append(self.ORDER_MEDIUM)

        if spacing <= self.ORDER_MINOR:

            orders.append(self.ORDER_MINOR)

        return orders


    # How far along its own line a tick label anchors, as a
    # fraction from that line's first vertex (0.0) to its last
    # (1.0) - matches the reference workflow's lineAnchorPercent
    # (0.02, i.e. very close to the START), used identically for
    # BOTH axes rather than a different value per axis. Vertical
    # (easting) lines are built top-to-bottom (ymax then ymin)
    # and horizontal (northing) lines left-to-right (xmin then
    # xmax) - both confirmed by inspecting the reference
    # workflow's own GeoPackage geometry directly - so "near the
    # START" already lands at the TOP for eastings and the LEFT
    # for northings, with no need for a separate "near the END"
    # value on either axis.
    LINE_ANCHOR_PERCENT = 0.02

    # Beyond these map-scale denominators, a tier's label stops
    # showing (even though the line itself may still be drawn) -
    # coarser tiers tolerate being zoomed out further before
    # their ticks would start cluttering the screen. Starting
    # points loosely modelled on the reference workflow's own
    # scale bands (250000/500000/1500000 for line visibility);
    # worth adjusting once you've seen them live.
    LABEL_MAX_SCALE = {
        ORDER_MAJOR: 1000000,
        ORDER_MEDIUM: 250000,
        ORDER_MINOR: 100000,
    }


    def apply_label(self, spacing):

        """
        Label every tier actually visible at this spacing
        selection, anchored near one end of each line via QGIS's
        native line-label anchoring (see _line_anchor_settings).
        Each tier's label additionally stops showing beyond its
        own LABEL_MAX_SCALE, so zooming out doesn't fill the
        screen with (e.g.) every 1km tick's label.
        """

        size = self.LABEL_SIZE.get(spacing, 8)


        root_rule = QgsRuleBasedLabeling.Rule(
            QgsPalLayerSettings()
        )


        for order in self.visible_orders(spacing):

            max_scale = self.LABEL_MAX_SCALE.get(order)

            scale_condition = f"AND @map_scale <= {max_scale}"

            easting_rule = QgsRuleBasedLabeling.Rule(
                self._line_anchor_settings(
                    size,
                    self.LINE_ANCHOR_PERCENT
                )
            )

            easting_rule.setFilterExpression(
                f"\"AXIS\" = 'E' AND \"ORDER\" = {order} "
                f"{scale_condition}"
            )

            root_rule.appendChild(
                easting_rule
            )


            northing_rule = QgsRuleBasedLabeling.Rule(
                self._line_anchor_settings(
                    size,
                    self.LINE_ANCHOR_PERCENT
                )
            )

            northing_rule.setFilterExpression(
                f"\"AXIS\" = 'N' AND \"ORDER\" = {order} "
                f"{scale_condition}"
            )

            root_rule.appendChild(
                northing_rule
            )


        labeling = QgsRuleBasedLabeling(
            root_rule
        )

        self.layer.setLabeling(
            labeling
        )

        self.layer.setLabelsEnabled(
            True
        )

        self.layer.triggerRepaint()



    # A straight line in UTM isn't straight once reprojected
    # (e.g. to a geographic CRS) - it's a gentle curve. Only
    # transforming the two endpoints draws a straight chord
    # instead, and the gap between chord and true curve grows
    # with the line's length. Densify with intermediate points
    # so the polyline actually follows the curve, the same way
    # the 100km grid's multi-vertex polygons do.
    DENSIFY_SEGMENTS = 16

    # How far beyond the current viewport to generate lines,
    # as a multiple of the viewport's own width/height on each
    # side - gives room to pan before running out of generated
    # grid (see the note in generate() below).
    EXTENT_BUFFER_FACTOR = 1.0


    def generate(self, extent, utm_layer, spacing=1000, buffer_factor=None):
        """
        Generate MGRS sub-grid lines.

        spacing:
            10000 = 10km (finest tier shown: just major lines)
             5000 = 5km  (major + medium lines)
             1000 = 1km  (major + medium + minor lines)

        utm_layer:
            The generated UTM Grid Zone Designator layer -
            iterated per feature so each portion of the visible
            extent is generated using ITS OWN zone's UTM CRS
            (matching MGRS100KGenerator), instead of picking a
            single zone from the extent's centre.

        buffer_factor:
            Overrides EXTENT_BUFFER_FACTOR. A print layout map
            never pans, so it has no use for the canvas's pan
            headroom - worse, that extra buffered line length
            changes where the line-anchor label lands, since the
            anchor percent is computed against whatever portion
            of the line is "visible". Layout callers should pass
            0 here so the generated line matches the displayed
            extent exactly.
        """

        if buffer_factor is None:

            buffer_factor = self.EXTENT_BUFFER_FACTOR


        self.layer = None


        self.create_layer(
            spacing
        )


        provider = self.layer.dataProvider()


        features = []


        if utm_layer is None:

            return self.layer


        project = QgsProject.instance()

        project_crs = project.crs()

        to_wgs84 = QgsCoordinateTransform(
            project_crs,
            WGS84,
            project
        )

        # Lines are only ever generated for this one extent (the
        # grid isn't regenerated just from panning) - buffer it
        # well beyond the current viewport so a label anchored to
        # the visible top/left edge keeps tracking the pan for a
        # while, instead of immediately hitting the end of a line
        # that stops exactly at the original viewport's border.
        buffer_x = extent.width() * buffer_factor

        buffer_y = extent.height() * buffer_factor

        buffered_extent = QgsRectangle(
            extent.xMinimum() - buffer_x,
            extent.yMinimum() - buffer_y,
            extent.xMaximum() + buffer_x,
            extent.yMaximum() + buffer_y
        )

        extent_geom = QgsGeometry.fromRect(
            to_wgs84.transformBoundingBox(buffered_extent)
        )


        def order_of(coord):

            if coord % self.ORDER_MAJOR == 0:
                return self.ORDER_MAJOR

            if coord % self.ORDER_MEDIUM == 0:
                return self.ORDER_MEDIUM

            return self.ORDER_MINOR


        #
        # Process every visible GZD, each in its own UTM CRS
        #

        for gzd in utm_layer.getFeatures():

            gzd_name = gzd["GZD"]

            zone = int(
                gzd["ZONE"]
            )

            band = gzd["BAND"]

            utm_crs = get_utm_crs_from_zone_band(
                zone,
                band
            )

            to_utm = QgsCoordinateTransform(
                WGS84,
                utm_crs,
                project
            )

            from_utm = QgsCoordinateTransform(
                utm_crs,
                project_crs,
                project
            )


            #
            # Only the part of this GZD actually on screen
            #

            gzd_geom = QgsGeometry(
                gzd.geometry()
            )

            visible_geom = gzd_geom.intersection(
                extent_geom
            )

            if visible_geom.isEmpty():

                continue


            visible_geom.transform(
                to_utm
            )

            bbox = visible_geom.boundingBox()


            xmin = int(
                bbox.xMinimum() // spacing
            ) * spacing

            ymin = int(
                bbox.yMinimum() // spacing
            ) * spacing

            xmax = int(
                bbox.xMaximum() // spacing
            ) * spacing

            ymax = int(
                bbox.yMaximum() // spacing
            ) * spacing


            def densified_line(ux1, uy1, ux2, uy2, from_utm=from_utm):

                points = []

                for i in range(self.DENSIFY_SEGMENTS + 1):

                    t = i / self.DENSIFY_SEGMENTS

                    ux = ux1 + (ux2 - ux1) * t
                    uy = uy1 + (uy2 - uy1) * t

                    points.append(
                        from_utm.transform(
                            QgsPointXY(ux, uy)
                        )
                    )

                return QgsGeometry.fromMultiPolylineXY([points])


            #
            # Vertical lines (constant easting)
            #

            x = xmin

            while x <= xmax:

                # Built top-to-bottom (ymax -> ymin), matching
                # the reference workflow's own line construction
                # (confirmed by inspecting its GeoPackage
                # geometry directly) - so the SAME small "near
                # the line's start" anchor percent used for
                # northings also lands eastings near the top,
                # rather than needing a separate "near the end"
                # percent the way our bottom-to-top construction
                # did.
                geom = densified_line(
                    x, ymax, x, ymin
                )

                feature = QgsFeature(
                    self.layer.fields()
                )

                feature.setGeometry(geom)

                feature.setAttributes(
                    [
                        gzd_name,
                        zone,
                        "E",
                        int(x),
                        order_of(x)
                    ]
                )

                features.append(feature)

                x += spacing


            #
            # Horizontal lines (constant northing)
            #

            y = ymin

            while y <= ymax:

                geom = densified_line(
                    xmin, y, xmax, y
                )

                feature = QgsFeature(
                    self.layer.fields()
                )

                feature.setGeometry(geom)

                feature.setAttributes(
                    [
                        gzd_name,
                        zone,
                        "N",
                        int(y),
                        order_of(y)
                    ]
                )

                features.append(feature)

                y += spacing


        provider.addFeatures(
            features
        )


        self.layer.updateExtents()


        self.apply_style(spacing)

        self.apply_label(spacing)


        return self.layer
