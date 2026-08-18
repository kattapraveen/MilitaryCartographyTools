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


--------------------------------------------------


## Milsymbol (MIL-STD-2525 / APP-6 Symbol Rendering)

Military Cartography Tools includes a vendored copy of milsymbol,
a military symbology rendering library originally developed by:

Måns Beckman
www.spatialillusions.com

Original source:
https://github.com/spatialillusions/milsymbol

Version vendored:
3.0.4 (dist/milsymbol.js, minified UMD build)

Vendored file:
military_symbology/vendor/milsymbol.js

License:
MIT License

Copyright (c) 2017 Måns Beckman - www.spatialillusions.com

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

Milsymbol runs entirely offline, in-process, via Qt's own
QJSEngine (no Node.js, no browser, no network access of any kind) -
Military Cartography Tools adds the QJSEngine bridge
(military_symbology/symbol_engine.py), the SIDC data model
(military_symbology/sidc.py), and the QGIS expression function
(mct_sidc_svg) that connects a feature's own attributes to a
rendered symbol at render time.

**Modified, 2026-08-18 - 8 icon assignments swapped, otherwise
unmodified.** Land Unit's own sector-1 modifier table (in the
vendored file, the minified equivalent of upstream's
src/numbersidc/sidc/landunit.js) branches on milsymbol's own
`_STD2525` flag at 8 of its 99 code assignments (codes 01, 47, 56,
58, 71, 72, 73, 74) - drawing one icon when the flag is true (its
default, and this plugin never calls `ms.setStandard()` to change
it) and a different one when false. Verified directly against
`reference/MIL-STD-2525D.pdf` Table D-VI (gitignored, so not in this
repo - see docs/roadmap.md's D-4b entry for the transcription): at
every one of these 8 codes, the printed standard matches milsymbol's
FALSE branch, not the TRUE branch its own default selects - e.g.
code 01 renders as "Tactical Satellite Communications" under the
unmodified default, but MIL-STD-2525D Table D-VI prints "Airmobile/
Air Assault" at that code. Confirmed by checking every one of the 8
icon keys involved is referenced exactly once anywhere in milsymbol's
own numbersidc/sidc tables - i.e., only at this single ternary site
each - so swapping which branch `_STD2525=true` selects, at these 8
assignments only, cannot affect any other symbol this library draws.
The 8 swaps are the only change; every other byte of the vendored
file, including its own icon and geometry definitions, is untouched
(confirmed: the patched file is byte-identical in size to the
original). Applying `ms.setStandard("APP6")` instead was considered
and rejected - that flag is a single global mutable property on the
shared `ms` module instance, so flipping it would change every OTHER
symbol in the library that also branches on it, not just these 8.