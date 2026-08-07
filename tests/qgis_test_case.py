# -*- coding: utf-8 -*-

"""
Shared test scaffolding for the headless PyQGIS test suite.

QGIS's own bundled Python is required to run these tests (the
`qgis` package isn't pip-installable) - see run_tests.sh at the
repo root, or docs/developer-guide.md for how to run them by hand.
Only one QgsApplication may exist per process, so it's started
once here (from tests/__init__.py, guaranteeing it happens before
any test module runs) rather than per test case.

Military Cartography Tools
"""

import atexit
import tempfile
import unittest

from qgis.core import QgsApplication, QgsProject, QgsCoordinateReferenceSystem
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QToolBar


_qgs_app = None


def start_app():

    """
    Start the single QgsApplication this whole test process shares
    - idempotent, so every test module can safely call this itself
    without caring whether another module already did. Also
    initializes QGIS's Processing framework, needed the moment
    anything imports MilitaryCartographyTools at all (terrain/
    imports the `processing` package eagerly at module load time,
    not just when a Tanaka contour is actually generated) - not
    auto-available like it is inside a normally-launched QGIS GUI
    session, which loads Processing as a core plugin on startup.
    """

    global _qgs_app

    if _qgs_app is None:

        _qgs_app = QgsApplication(
            [],
            False
        )

        _qgs_app.initQgis()

        from processing.core.Processing import Processing

        Processing.initialize()

        # An orderly QGIS/GDAL provider shutdown via atexit, run
        # before Python's own uncontrolled interpreter teardown
        # begins, rather than leaving it to whatever destruction
        # order happens naturally at process exit - confirmed
        # necessary after the terrain/ tests (the first in this
        # suite to use Processing/GDAL raster I/O directly) segfaulted
        # at process exit, strictly after every test had already
        # passed, only when run through the real unittest runner.
        atexit.register(_qgs_app.exitQgis)

    return _qgs_app


class FakeMessageBar:

    """
    Records every pushInfo()/pushMessage() call instead of actually
    showing anything - lets a test assert on what the plugin tried
    to tell the user.
    """

    def __init__(self):

        self.calls = []
        self.clear_count = 0


    def clearWidgets(self):

        self.clear_count += 1


    def pushInfo(self, title, text):

        self.calls.append(
            (title, text)
        )


    def pushMessage(self, *args, **kwargs):

        self.calls.append(
            (args, kwargs)
        )


    def pushWarning(self, title, text):

        self.calls.append(
            (title, text)
        )


class FakeIface(QObject):

    """
    Minimal QgisInterface stand-in covering every method/signal
    this plugin actually calls on iface, gathered from plugin.py
    and the layout/grid modules - built as one canonical fake so
    individual tests don't each hand-roll a partial version (which
    is exactly how this session's own ad hoc scripts once hit a
    "FakeIface has no attribute removePluginMenu" gap, and
    separately a real crash from a signal-owning QObject being
    garbage-collected because it wasn't kept as an instance
    attribute - subclassing QObject directly here, with the
    signals as class attributes, avoids that class of bug
    entirely).
    """

    layoutDesignerOpened = pyqtSignal(object)
    layoutDesignerWillBeClosed = pyqtSignal(object)

    def __init__(self, window=None, canvas=None):

        super().__init__()

        self._window = window
        self._canvas = canvas
        self._message_bar = FakeMessageBar()

        self.menu_actions = []
        self.opened_layouts = []


    def mainWindow(self):

        return self._window


    def addToolBar(self, name):

        toolbar = QToolBar(
            name,
            self._window
        )

        if self._window is not None:

            self._window.addToolBar(
                toolbar
            )

        return toolbar


    def addPluginToMenu(self, name, action):

        self.menu_actions.append(
            action
        )


    def removePluginMenu(self, name, action):

        if action in self.menu_actions:

            self.menu_actions.remove(
                action
            )


    def removeToolBarIcon(self, action):

        pass


    def mapCanvas(self):

        return self._canvas


    def messageBar(self):

        return self._message_bar


    def openLayoutDesigner(self, layout):

        self.opened_layouts.append(
            layout
        )


def make_canvas(crs="EPSG:4326"):

    """
    A real QgsMapCanvas with the given CRS - needed by anything
    that constructs a genuine QgsMapTool (a lightweight fake
    widget isn't an acceptable substitute; QgsMapTool's own
    constructor requires a real QgsMapCanvas).
    """

    canvas = QgsMapCanvas()

    canvas.setDestinationCrs(
        QgsCoordinateReferenceSystem(crs)
    )

    return canvas


def build_synthetic_sloped_dem(
    width=30,
    height=30,
    pixel_size=0.0001,
    origin_lon=37.34,
    origin_lat=-3.09
):

    """
    A small synthetic GeoTIFF DEM whose elevation rises steadily
    eastward (elevation == column * 10.0) - a single, clean gradient
    direction, so tests that need real DEM raster I/O (Tanaka
    contours, hypsometric tint) can check an expected uphill side/
    illumination sign or elevation range exactly rather than just
    "something came out". Returns the file path; the caller owns
    deleting it (e.g. in tearDown()).
    """

    import numpy
    from osgeo import gdal, osr

    path = tempfile.mktemp(suffix=".tif")

    driver = gdal.GetDriverByName("GTiff")

    dataset = driver.Create(
        path, width, height, 1, gdal.GDT_Float32
    )

    dataset.SetGeoTransform(
        [origin_lon, pixel_size, 0, origin_lat, 0, -pixel_size]
    )

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dataset.SetProjection(srs.ExportToWkt())

    band = numpy.fromfunction(
        lambda row, col: col * 10.0,
        (height, width),
        dtype="float32"
    )

    dataset.GetRasterBand(1).WriteArray(band)
    dataset.FlushCache()
    dataset = None

    return path


def build_synthetic_ridge_dem(
    width=30,
    height=30,
    pixel_size=0.0001,
    origin_lon=37.34,
    origin_lat=-3.09,
    base_elevation=0.0,
    ridge_height=200.0,
    ridge_start_column=13,
    ridge_end_column=17
):

    """
    A small synthetic GeoTIFF DEM: flat base_elevation everywhere,
    except a raised block of ridge_height across columns
    [ridge_start_column, ridge_end_column) - a single obstruction
    between two low points on either side of it, for line-of-sight
    tests that need something concrete to block (or, with
    ridge_height=0, a plain flat DEM for curvature-only cases where
    there should be nothing in the way at all). Returns the file path;
    the caller owns deleting it (e.g. in tearDown()).
    """

    import numpy
    from osgeo import gdal, osr

    path = tempfile.mktemp(suffix=".tif")

    driver = gdal.GetDriverByName("GTiff")

    dataset = driver.Create(
        path, width, height, 1, gdal.GDT_Float32
    )

    dataset.SetGeoTransform(
        [origin_lon, pixel_size, 0, origin_lat, 0, -pixel_size]
    )

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dataset.SetProjection(srs.ExportToWkt())

    def elevation(row, col):

        on_ridge = (col >= ridge_start_column) & (col < ridge_end_column)

        return numpy.where(
            on_ridge,
            base_elevation + ridge_height,
            base_elevation
        )

    band = numpy.fromfunction(
        elevation,
        (height, width),
        dtype="float32"
    )

    dataset.GetRasterBand(1).WriteArray(band)
    dataset.FlushCache()
    dataset = None

    return path


def build_synthetic_cone_dem(
    width=80,
    height=80,
    pixel_size=0.0001,
    origin_lon=37.34,
    origin_lat=-3.09,
    peak_elevation=1000.0,
    slope_per_pixel=10.0
):

    """
    A small synthetic GeoTIFF DEM shaped like a radially symmetric
    cone (elevation falls off from a single peak at the raster's own
    centre, in every direction, at a constant rate per pixel of
    distance from it) - unlike build_synthetic_sloped_dem()'s single,
    constant gradient direction, a cone's own contour rings genuinely
    curve, so a segment's tangent (and therefore its perpendicular
    sampling direction) keeps rotating all the way around each ring.
    Needed to reproduce a real regression: a fixed, too-small
    perpendicular sampling offset in Tanaka Contours' own
    _segment_illumination() produced a dense, near-uniform alternating
    light/dark "barcode" pattern specifically on curving rings like
    these, even with zero injected noise - a straight-line DEM like
    build_synthetic_sloped_dem()'s can't expose that, since its
    tangent direction never rotates. Returns the file path; the caller
    owns deleting it (e.g. in tearDown()).
    """

    import numpy
    from osgeo import gdal, osr

    path = tempfile.mktemp(suffix=".tif")

    driver = gdal.GetDriverByName("GTiff")

    dataset = driver.Create(
        path, width, height, 1, gdal.GDT_Float32
    )

    dataset.SetGeoTransform(
        [origin_lon, pixel_size, 0, origin_lat, 0, -pixel_size]
    )

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dataset.SetProjection(srs.ExportToWkt())

    center_row, center_col = height / 2.0, width / 2.0

    def elevation(row, col):

        distance = numpy.hypot(row - center_row, col - center_col)

        return peak_elevation - distance * slope_per_pixel

    band = numpy.fromfunction(
        elevation,
        (height, width),
        dtype="float32"
    )

    dataset.GetRasterBand(1).WriteArray(band)
    dataset.FlushCache()
    dataset = None

    return path


class QgisTestCase(unittest.TestCase):

    """
    Base class for tests that need the shared QgsApplication
    running and a clean QgsProject - most test cases can just
    subclass this instead of repeating the same setUp() boilerplate.
    """

    @classmethod
    def setUpClass(cls):

        start_app()


    def setUp(self):

        QgsProject.instance().clear()
