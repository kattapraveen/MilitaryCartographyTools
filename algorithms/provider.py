# -*- coding: utf-8 -*-

"""
The plugin's own Processing provider.

Everything else in this plugin is a dialog behind a toolbar button.
Range rings is a Processing algorithm instead, and deliberately: that
gives it a progress bar and a working Cancel for free - which is
precisely the gap task 7 exists to close for the dialog-based tools -
plus Run as Batch over several sets of points, and the ability to sit
inside a model. A toolbar button in the Navigation group opens its
Processing dialog, so it is still reachable the same way as
everything else.

NOTE the package is called `algorithms/`, not `processing/`. A
package named `processing` inside the plugin would shadow QGIS's own
`processing` module on import and break every tool that calls
processing.run().

Military Cartography Tools
"""

from qgis.core import QgsProcessingProvider

from qgis.PyQt.QtGui import QIcon

from .range_rings import RangeRingsAlgorithm


PROVIDER_ID = "militarycartographytools"

PROVIDER_NAME = "Military Cartography Tools"


class MilitaryCartographyProvider(QgsProcessingProvider):

    def __init__(self, icon_path=None):

        super().__init__()

        self._icon_path = icon_path

    def id(self):
        return PROVIDER_ID

    def name(self):
        return PROVIDER_NAME

    def longName(self):
        return PROVIDER_NAME

    def icon(self):

        if self._icon_path:
            return QIcon(self._icon_path)

        return super().icon()

    def loadAlgorithms(self):

        self.addAlgorithm(
            RangeRingsAlgorithm()
        )
