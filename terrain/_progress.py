# -*- coding: utf-8 -*-

"""
Passing Processing's feedback down into the work the terrain
generators actually spend their time in.

Why this exists. The four terrain tools became Processing algorithms
on 2026-10-26 for one stated reason: "a progress bar and a working
Cancel, which was the whole complaint". Neither worked. Every
generator calls processing.run() for its heavy steps -
gdal:warpreproject, gdal:contour, native:splitlinesbylength,
gdal:hillshade, gdal:rastercalculator, gdal:translate - and none of
those calls was given the parent's feedback, so a child algorithm
never learned it had been cancelled and never reported progress. The
algorithms tested feedback.isCanceled() only BETWEEN stages, and the
stages are where all the time goes. Pressing Cancel on a large DEM
did nothing at all until the run finished of its own accord, and the
bar sat at 10% throughout.

So each generator now takes an optional `feedback` and hands the
SAME object on to every child algorithm it runs.

**Not a QgsProcessingMultiStepFeedback, which is what this module
was written to hold.** That class exists for exactly this job: it
maps each child's own 0-100 into its own slice of the parent's bar,
so the bar moves forward once, evenly, instead of sweeping from 0 to
100 again per child. It also segfaults here. A multi-step feedback
holds a bare pointer to the parent feedback and nothing owns it but
the Python local it was assigned to, so when Python collects it
after the parent has gone, Qt is left delivering queued events to
freed memory. The whole suite died at the first
QCoreApplication.processEvents() in the process - inside the
`_settle()` call added the same day to catch the layer-tree bug -
with the same crash on three consecutive runs, and went green on
2083 tests the moment the wrapper was dropped. It survived every
smaller grouping of the tests that run these algorithms, which is
the ordinary signature of a use-after-free: whether it crashes
depends on what has since been written over the freed block.

Giving the parent to each child instead costs proportional progress:
the bar now sweeps once per heavy step rather than once per run.
Cancel - which was the complaint - works either way, and a bar that
sweeps is worth more than a crash.

Two rules for callers:

  - `feedback` stays OPTIONAL and defaults to None. Line of Sight,
    Viewshed and Sensor Coverage still call these generators from
    plain dialogs on the main thread, where there is no feedback to
    pass, and they must keep working unchanged.
  - a generator returns None when it was cancelled. It is not an
    error and must not raise: the generators use ValueError for
    considered refusals the user needs to read, and a cancellation
    is neither a refusal nor a failure. Every caller therefore has
    to treat None as "stop quietly".

Military Cartography Tools
"""


def cancelled(feedback):

    """
    True if the user has asked to stop. Safe with feedback=None, so
    callers do not each need their own None check.
    """

    return feedback is not None and feedback.isCanceled()
