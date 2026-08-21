# -*- coding: utf-8 -*-

"""
Keeps each level's "Sensor Coverage" perimeter in step with its own
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

from qgis.core import Qgis, QgsProject

from ..core._layer_utils import replace_named_layer
from .sensor_coverage import (
    coverage_layer_name,
    default_insert_position,
    dem_layer_for,
    generate_sensor_coverage,
    points_layer_name,
    SENSOR_LEVELS,
)


# Long enough to read a two-line sentence without hunting for it, short
# enough not to sit over the map for a whole editing session.
EDIT_HINT_DURATION_SECONDS = 8


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

        points_layer.editingStarted.connect(
            lambda: self._remind_to_save(points_layer)
        )

        self._wired_layer_ids.add(
            points_layer.id()
        )


    def _remind_to_save(self, points_layer):

        """
        Say, at the moment it matters, that coverage only redraws on
        SAVE. Regenerating on commit rather than continuously is a
        deliberate decision (see this module's own docstring), but it
        is not a discoverable one: the maintainer's own smoke test
        2026-08-20 placed sensors, saw no coverage, and reasonably read
        that as the feature being broken - "since there is no generate
        or re-generate button as such, it was not showing up". The
        setup dialog does say it, but it is read once at setup and not
        again when a sensor is actually being placed.

        Fired on editingStarted rather than on every feature added, so
        it appears once per edit session rather than once per sensor,
        and it expires on its own.
        """

        self.iface.messageBar().pushMessage(
            "Military Cartography Tools",
            f'Coverage for "{points_layer.name()}" redraws when you SAVE '
            "this layer's edits - placing or moving a sensor on its own "
            "does not update it.",
            level=Qgis.MessageLevel.Info,
            duration=EDIT_HINT_DURATION_SECONDS
        )


    def install(self):

        """
        Listen for layers arriving, so a laydown is live without the
        user having to open the setup dialog first.

        Signal connections do not survive a project load - they belong
        to the layer objects, and reading a project builds new ones -
        so until 2026-08-21 a reopened project looked complete (points
        and coverage both there) but was inert: moving a sensor and
        saving did nothing, and the only way to revive it was to open
        the Sensor Coverage dialog, which called attach_existing() on
        the way past. The maintainer found that during smoke testing
        and asked for it bound rather than explained - "we are already
        throwing a lot of messages to the user for this use case".

        `layersAdded` covers both cases at once: layers restored by a
        project read, and a points layer added at any other time.
        attach_existing() is idempotent, so the extra calls cost
        nothing.
        """

        project = QgsProject.instance()

        project.layersAdded.connect(self._on_layers_added)

        # Layer ids are new after a project read, so anything remembered
        # from the previous project would keep a dead id alive and stop
        # its replacement being wired.
        project.readProject.connect(self._on_project_read)


    def uninstall(self):

        project = QgsProject.instance()

        for signal, slot in (
            (project.layersAdded, self._on_layers_added),
            (project.readProject, self._on_project_read),
        ):

            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                # Never connected, or the project object is already
                # gone during shutdown - neither is worth failing over.
                pass


    def _on_layers_added(self, layers):

        self.attach_existing()


    def _on_project_read(self, *args):

        self._wired_layer_ids.clear()

        self.attach_existing()


    def regenerate_all(self):

        """
        Rebuild every level this project has a points layer for, and
        return the levels actually regenerated.

        This is what the Regenerate action calls. The maintainer asked
        for it 2026-08-21 after finding that a reopened project would
        not redraw coverage until a sensor was nudged far enough to
        re-enable Save: "I think we need to delink saving the point and
        generating coverage but rather give a generate sensor coverage
        button".
        """

        self.attach_existing()

        regenerated = []

        for level in SENSOR_LEVELS:

            if self._points_layer(level) is None:
                continue

            if self.regenerate(level) is not None:
                regenerated.append(level)

        return regenerated


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


    def _remove_named(self, name):

        project = QgsProject.instance()

        for layer in project.mapLayersByName(name):

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
            self._remove_named(coverage_layer_name(level))

        return coverage
