"""``c2gui`` — Tk interface. :class:`cyclone2.gui.app.App` is assembled from small mixins:

* :mod:`.pages`       — layout helpers, the section pages and navigation
* :mod:`.controller`  — the controller drawing, its animation and the mapping highlight
* :mod:`.editor`      — profile/lighting dicts <-> widget values, the lighting editor, LED preview colours
* :mod:`.sync`        — device I/O on a worker thread: read, profile switching, auto-save, polling, backups
* :mod:`.live_input`  — live input from the state reports, heartbeat and the LED frame preview

Shared building blocks live in :mod:`.theme`, :mod:`.catalog`, :mod:`.geometry`, :mod:`.drawing` and
:mod:`.widgets` (the last two are shared with the 8BitDo Ultimate 2 configurator).
"""
