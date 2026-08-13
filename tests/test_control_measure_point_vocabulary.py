# -*- coding: utf-8 -*-

"""
Cross-module guard on Appendix H's own point-symbol vocabulary.

Every H.5.x group now owns its own Points layer, and the shared
"Tactical Graphics - Control Measure Points" layer that used to hold
whichever entities had no home yet is gone - emptied and retired by
Mini-Phases H19/H20/H21, which moved its last 21 entries out to
sustainment_control_measures.py, supply_points.py and
mission_task_control_measures.py.

That retirement takes two invariants with it, and they move here rather
than disappearing:

- **Every control-measure entity is offered by exactly ONE layer.**
  While the shared layer existed, each table's own tests asserted "my
  family left the shared points layer" - eleven separate near-copies of
  the same check, each of which could only see two layers at a time.
  One pairwise sweep says it properly.
- **Every control-measure entity is offered SOMEWHERE.** An entity
  added to sidc.py and then forgotten renders perfectly well in
  isolation and is simply unreachable in the UI. Only a union check
  catches that.

Military Cartography Tools
"""

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.military_symbology.airspace_control_measures import (
    POINT_ENTITY_LABELS as AIRSPACE,
)
from MilitaryCartographyTools.military_symbology.c2_measures import (
    POINT_ENTITY_LABELS as C2,
)
from MilitaryCartographyTools.military_symbology.cbrn_defense import (
    POINT_ENTITY_LABELS as CBRN,
)
from MilitaryCartographyTools.military_symbology.defensive_control_measures import (
    POINT_ENTITY_LABELS as DEFENSIVE,
)
from MilitaryCartographyTools.military_symbology.field_fortification import (
    POINT_ENTITY_LABELS as FIELD_FORTIFICATION,
)
from MilitaryCartographyTools.military_symbology.maritime_control_measures import (
    POINT_ENTITY_LABELS as MARITIME,
)
from MilitaryCartographyTools.military_symbology.mission_task_control_measures import (
    POINT_ENTITY_LABELS as MISSION_TASK,
)
from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
    POINT_ENTITY_LABELS as OBSTACLE,
)
from MilitaryCartographyTools.military_symbology.offensive_control_measures import (
    POINT_ENTITY_LABELS as OFFENSIVE,
)
from MilitaryCartographyTools.military_symbology.supply_points import (
    POINT_ENTITY_LABELS as SUPPLY,
)
from MilitaryCartographyTools.military_symbology.sustainment_control_measures import (
    POINT_ENTITY_LABELS as SUSTAINMENT,
)
from MilitaryCartographyTools.military_symbology.target_control_measures import (
    POINT_ENTITY_LABELS as TARGET,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES


# Table -> that table's own Points vocabulary. Add a row when a new
# H.5.x group gets its own Points layer; that is the point of the file.
_POINT_VOCABULARIES = {
    "H-V/H-VI (C2)": C2,
    "H-VIII/H-IX (defensive)": DEFENSIVE,
    "H-XI (offensive)": OFFENSIVE,
    "H-XIII (airspace)": AIRSPACE,
    "H-XIV (maritime)": MARITIME,
    "H-XVII (targets)": TARGET,
    "H-XIX (obstacles)": OBSTACLE,
    "H-XX (field fortification)": FIELD_FORTIFICATION,
    "H-XXI (CBRN defense)": CBRN,
    "H-XXII (sustainment)": SUSTAINMENT,
    "H-XXIII (supply points)": SUPPLY,
    "H-XXIV (mission tasks)": MISSION_TASK,
}

# In sidc.py's control_measure vocabulary but NOT a point symbol, so no
# Points dropdown should offer it.
#
# Abatis is the only one: it is a LINE (Table H-XIX, 280100), built in
# batch B4 and offered on the Obstacle Control Measures (Lines) layer
# as a measure_type instead.
_NOT_POINT_ENTITIES = frozenset({"abatis"})


class TestControlMeasurePointVocabulary(QgisTestCase):

    def test_no_entity_is_offered_by_two_layers(self):

        # Offering one entity on two layers is not a cosmetic problem:
        # the two would drift, and a user editing "the" checkpoint
        # would have no way to tell which layer they were on.
        tables = list(_POINT_VOCABULARIES.items())

        for index, (name, vocabulary) in enumerate(tables):

            for other_name, other in tables[index + 1:]:

                overlap = set(vocabulary) & set(other)

                self.assertEqual(
                    overlap,
                    set(),
                    f"{name} and {other_name} both offer {sorted(overlap)}"
                )


    def test_every_control_measure_entity_is_offered_somewhere(self):

        offered = set()

        for vocabulary in _POINT_VOCABULARIES.values():
            offered |= set(vocabulary)

        self.assertEqual(
            offered,
            set(ENTITIES["control_measure"]) - _NOT_POINT_ENTITIES
        )


    def test_every_offered_entity_is_real_sidc_vocabulary(self):

        # The other direction, and the one a typo in a new module's own
        # label dict trips: an entity key that no longer resolves in
        # sidc.py renders as milsymbol's unknown icon rather than
        # failing.
        for name, vocabulary in _POINT_VOCABULARIES.items():

            for entity in vocabulary:

                self.assertIn(entity, ENTITIES["control_measure"], name)


    def test_the_shared_points_layer_is_really_gone(self):

        # It was always a holding pen for entities whose own table had
        # not been built yet, and H19/H20/H21 emptied it. Leaving the
        # module behind would leave a layer nothing can populate.
        with self.assertRaises(ImportError):

            from MilitaryCartographyTools.military_symbology import (  # noqa: F401
                control_measure_points,
            )
