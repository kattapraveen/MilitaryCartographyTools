# -*- coding: utf-8 -*-

"""
Keeps each level's "Sensor Coverage" polygon in step with its own
"Sensor Points" layer, so a laydown is edited rather than re-run: drop
a sensor, drag one to better ground, correct a range in the attribute
form, and that level's coverage redraws itself.

**Why afterCommitChanges and not geometryChanged.** The maintainer
asked for automatic regeneration - "the user will deploy the sensors
when required" - not a Generate button. But a single regeneration is a
full gdal:viewshed run PER SENSOR, seconds of work on a real DEM, and
QGIS fires geometryChanged continuously while a vertex is being
dragged. Hanging that off every intermediate position would make the
drag itself unusable. Committing an edit session is the moment the
user has decided what they meant, which is exactly the moment worth
recomputing - and it keeps "automatic" honest without a Generate
button.

Only the edited level regenerates, never all three, also per the
maintainer's own request - each layer's own signal carries its own
level, so the other two bands are left exactly as they were.

Military Cartography Tools
"""

from qgis.core import QgsProject

from ..core._layer_utils import replace_named_layer
from .sensor_coverage import (
    coverage_layer_name,
    default_insert_position,
    dem_layer_for,
    generate_sensor_coverage,
    points_layer_name,
    SENSOR_LEVELS,
)


class SensorCoverageManager:

    """
    Owns the points-layer-to-coverage-layer connections for the life of
    the plugin. One instance, created by plugin.py.
    """

    def __init__(self, iface):

        self.iface = iface

        # Layer ids already connected, so re-attaching (on project read,
        # or when a layer is added) cannot wire the same layer twice and
        # regenerate it once per duplicate connection.
        self._wired_layer_ids = set()


    def wire(self, points_layer, level):

        if points_layer.id() in self._wired_layer_ids:
            return

        points_layer.afterCommitChanges.connect(
            lambda: self.regenerate(level)
        )

        self._wired_layer_ids.add(
            points_layer.id()
        )


    def attach_existing(self):

        """
        Wire up any sensor points layer already in the project - a
        project reopened from disk, or one where the user added the
        layers in an earlier session. Matched by layer NAME, the same
        way every replace_named_layer() feature in this plugin
        identifies its own layers.
        """

        project = QgsProject.instance()

        for level in SENSOR_LEVELS:

            for layer in project.mapLayersByName(points_layer_name(level)):

                self.wire(layer, level)


    def _points_layer(self, level):

        existing = QgsProject.instance().mapLayersByName(
            points_layer_name(level)
        )

        return existing[0] if existing else None


    def _remove_coverage(self, level):

        project = QgsProject.instance()

        for layer in project.mapLayersByName(coverage_layer_name(level)):

            project.removeMapLayer(
                layer.id()
            )


    def regenerate(self, level):

        """
        Rebuild one level's coverage from its own points layer, in
        place - preserving wherever the user has dragged the coverage
        layer in the Layers panel (see replace_named_layer()).

        Returns the new coverage layer, or None if there was nothing to
        draw or nothing to draw it against.
        """

        points_layer = self._points_layer(level)

        if points_layer is None:
            return None

        dem_layer = dem_layer_for(points_layer)

        if dem_layer is None:

            # The DEM was never chosen, or has since been removed from
            # the project. Whatever coverage is already drawn was
            # computed against a real DEM and is still the best picture
            # available, so it is left alone rather than deleted over a
            # recoverable setup problem.
            self.iface.messageBar().pushWarning(
                "Military Cartography Tools",
                f'"{points_layer.name()}" has no DEM set - reopen Sensor '
                "Coverage to choose one before its coverage can be updated."
            )

            return None

        def generate():

            return generate_sensor_coverage(
                dem_layer,
                points_layer,
                level
            )

        coverage = replace_named_layer(
            coverage_layer_name(level),
            generate,
            default_insert_position
        )

        if coverage is None:

            # Nothing is visible from anywhere on this level any more -
            # every sensor deleted, or all of them off the DEM. Leaving
            # the previous coverage drawn would show ground that is no
            # longer covered by anything.
            self._remove_coverage(level)

        return coverage
