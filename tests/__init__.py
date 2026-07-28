# -*- coding: utf-8 -*-

"""
Headless PyQGIS test suite for Military Cartography Tools.

Run via run_tests.sh at the repo root (needs QGIS's own bundled
Python - see docs/developer-guide.md).

Starting the shared QgsApplication here, at package import time,
guarantees it's running before any test module executes, no
matter what order unittest discovery imports them in - only one
QgsApplication may exist per process.
"""

from .qgis_test_case import start_app

start_app()
