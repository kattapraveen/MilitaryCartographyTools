# Third Party Notices


## MGRS Conversion Engine

Military Cartography Tools includes the MGRS conversion engine
originally developed by:

Alex Bruy
Boundless
Planet Federal / Planet Inc.

Original source file:
mgrs.py

License:
GNU General Public License v2 or later

The original copyright notice has been retained in the source file.

Military Cartography Tools adds QGIS integration,
expression functions, layout support, and plugin functionality.

One upstream bug was fixed in the vendored copy (`core/mgrs_engine.py`):
a UPS/polar-coordinate validation check used `letters[1] in [invalid]`
(membership against a one-element list containing a list, which can
never be true) instead of `letters[1] in invalid`, silently disabling
that validation. See the comment at the fix site for detail.


--------------------------------------------------


## MGRS Grid Generation Workflow Reference

The grid generation workflow was inspired by QGIS Processing
models published by:

Klas Karlsson

Source:
QGIS Model Repository

License:
Creative Commons Zero (CC0)

Referenced functionality:
- MGRS GZD polygon generation
- 100 km MGRS square generation
- Special UTM zone handling

The original Processing models are not included in this plugin.
The grid management and generation implementation has been
independently developed for Military Cartography Tools.


--------------------------------------------------


## World Magnetic Model (Magnetic Declination)

Military Cartography Tools includes a vendored copy of the World
Magnetic Model calculation code from pyGeoMag, originally
developed by:

Justin Myers

Original source:
https://github.com/boxpet/pygeomag

Original source files:
geomag.py, wmm/wmm_2025.py

License:
MIT License

Copyright (c) 2023 Justin Myers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

The WMM2025 model coefficients themselves (wmm_2025.py) are
public-domain data published by NOAA/NCEI, valid 2025.0-2030.0.

Vendored unmodified apart from a short attribution header comment
in each file. Military Cartography Tools adds the QGIS expression
functions (mct_magnetic_declination, mct_map_magnetic_declination)
and the decimal-year/date-handling wrapper around this code.