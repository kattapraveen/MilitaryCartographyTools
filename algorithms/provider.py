# -*- coding: utf-8 -*-

"""
The plugin's own Processing provider.

Range rings was the first algorithm here, and deliberately: being
one gives a tool a progress bar and a working Cancel for free, plus
Run as Batch and the ability to sit inside a model. That was exactly
the gap task 7 existed to close, so on 2026-10-26 the four terrain
tools - Contours, Tanaka Contours, Hypsometric Tint and Hillshade
Combinations - moved here too, from the modal dialogs they used to
be. Each still has its toolbar button; the button now opens the
algorithm's own dialog.

Sensor Coverage stays a dialog. It is not one generator behind a
form - it runs a viewshed per sensor through its own manager, and
converting it is separate work.

NOTE the package is called `algorithms/`, not `processing/`. A
package named `processing` inside the plugin would shadow QGIS's own
`processing` module on import and break every tool that calls
processing.run().

Military Cartography Tools
"""

from qgis.core import QgsProcessingProvider

from qgis.PyQt.QtGui import QIcon

from .contours import ContoursAlgorithm
from .hillshade_combination import HillshadeCombinationAlgorithm
from .hypsometric_tint import HypsometricTintAlgorithm
from .range_rings import RangeRingsAlgorithm
from .tanaka_contours import TanakaContoursAlgorithm


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
            ContoursAlgorithm()
        )

        self.addAlgorithm(
            TanakaContoursAlgorithm()
        )

        self.addAlgorithm(
            HypsometricTintAlgorithm()
        )

        self.addAlgorithm(
            HillshadeCombinationAlgorithm()
        )

        self.addAlgorithm(
            RangeRingsAlgorithm()
        )
