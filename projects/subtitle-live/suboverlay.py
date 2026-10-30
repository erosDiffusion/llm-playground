#!/usr/bin/env python3
"""Banner-free subtitle overlay: a transparent, click-through, always-on-top
window on the X11 desktop. Reads one JSON line {"de": "...", "tr": "..."} per
subtitle from stdin. Run with the SYSTEM python3 (needs python3-gi)."""
from __future__ import annotations

import argparse
import json
import sys
import threading

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

CSS = b"""
window { background: transparent; }
box.tr  { background: rgba(0,0,0,0.55); border-radius: 12px; padding: 10px 20px; }
label.tr { color: #ffffff; font-weight: bold; }
label.de { color: #c9c9c9; }
"""


class SubWindow(Gtk.Window):
    def __init__(self, tr_pt: int, de_pt: int, bottom_frac: float,
                 x_frac: float = 0.5, width_frac: float = 0.66):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._timer = 0
        self.rect = None
        self.bottom_frac = bottom_frac
        self.x_frac = x_frac
        self.width_frac = width_frac
        self.set_title("sublive")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        try:
            self.set_type_hint(Gdk.WindowTypeHint.TOOLTIP)
        except Exception:
            pass
        scr = self.get_screen()
        if scr.is_composited():
            self.set_visual(scr.get_rgba_visual())
            self.set_app_paintable(True)
        self.connect("draw", self._clear_bg)

        self.de = Gtk.Label(justify=Gtk.Justification.CENTER)
        self.de.set_line_wrap(True)
        self.de.set_max_width_chars(60)
        self.de.get_style_context().add_class("de")
        self.de.override_font(Pango.FontDescription(f"Sans {de_pt}"))
        self.tr = Gtk.Label(justify=Gtk.Justification.CENTER)
        self.tr.set_line_wrap(True)
        self.tr.set_max_width_chars(60)
        self.tr.get_style_context().add_class("tr")
        self.tr.override_font(Pango.FontDescription(f"Sans Bold {tr_pt}"))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        wrap = Gtk.Box()
        wrap.get_style_context().add_class("tr")
        wrap.pack_start(self.tr, True, True, 0)
        box.pack_start(self.de, False, False, 0)
        box.pack_start(wrap, False, False, 0)
        self.add(box)

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            scr, prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    @staticmethod
    def _clear_bg(_w, cr):
        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)
        return False

    def set_line(self, tr: str, de: str, hold_ms: int, rect=None):
        if rect:
            self.rect = rect
        self.tr.set_text(tr or "")
        self.de.set_text(de or "")
        self.de.set_visible(bool(de))
        self.show()
        self.place()
        if self._timer:
            GLib.source_remove(self._timer)
        self._timer = GLib.timeout_add(max(2500, hold_ms), self._fade)
        return False

    def recenter(self, rect):
        """Follow the browser window without touching the text."""
        if rect:
            self.rect = rect
            self.place()
        return False

    def set_style(self, tr_pt=None, de_pt=None, bottom_frac=None,
                  width_frac=None):
        """Live restyle: font sizes independently, vertical position, width."""
        if tr_pt:
            self.tr.override_font(Pango.FontDescription(f"Sans Bold {int(tr_pt)}"))
        if de_pt is not None:
            self.de.set_visible(bool(de_pt) and bool(self.de.get_text()))
            if de_pt:
                self.de.override_font(Pango.FontDescription(f"Sans {int(de_pt)}"))
        if bottom_frac is not None:
            self.bottom_frac = float(bottom_frac)
        if width_frac is not None:
            self.width_frac = float(width_frac)
        self.place()
        return False

    def _fade(self):
        self.hide()
        self._timer = 0
        return False

    def place(self):
        disp = Gdk.Display.get_default()
        mon = disp.get_primary_monitor() or disp.get_monitor(0)
        g = mon.get_geometry()
        if self.rect and self.rect.get("w", 0) > 100:
            # center on the browser video element, anchored to its bottom
            r = self.rect
            w = min(int(r["w"] * self.width_frac / 0.66), int(r["w"]) - 40,
                    int(g.width * self.width_frac))
            h = None
            _, h_nat = self.get_preferred_height()
            h = h_nat or 140
            left = int(r["x"] + (r["w"] - w) / 2)
            top = int(r["y"] + r["h"] * (1 - self.bottom_frac)) - h
        else:
            w = int(g.width * self.width_frac)
            self.set_size_request(w, -1)
            _, h_nat = self.get_preferred_height()
            h = h_nat or 140
            left = g.x + int(g.width * self.x_frac) - w // 2
            top = g.y + g.height - int(g.height * self.bottom_frac) - h
        self.set_size_request(w, -1)
        self.move(max(0, left), max(0, top))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--de-pt", type=int, default=13)
    ap.add_argument("--tr-pt", type=int, default=30)
    ap.add_argument("--bottom-frac", type=float, default=0.10)
    ap.add_argument("--x-frac", type=float, default=0.5,
                    help="center of the box, fraction of screen width")
    ap.add_argument("--width-frac", type=float, default=0.66)
    args = ap.parse_args()

    win = SubWindow(args.tr_pt, args.de_pt, args.bottom_frac,
                    args.x_frac, args.width_frac)

    def on_realize(_w):
        # click-through: empty input shape -> mouse events pass to the video
        win.get_window().input_shape_combine_region(cairo.Region(), 0, 0)

    win.connect("realize", on_realize)
    win.show_all()
    win.place()
    win.hide()

    def stdin_loop():
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "place" in d:
                GLib.idle_add(win.recenter, d["place"])
                continue
            if "style" in d:
                s = d["style"] or {}
                GLib.idle_add(win.set_style, s.get("tr_pt"), s.get("de_pt"),
                              s.get("bottom_frac"), s.get("width_frac"))
                continue
            GLib.idle_add(win.set_line, d.get("tr", ""), d.get("de", ""),
                          int(d.get("hold_ms", 4000)), d.get("rect"))
        GLib.idle_add(Gtk.main_quit)

    threading.Thread(target=stdin_loop, daemon=True).start()
    Gtk.main()


if __name__ == "__main__":
    main()
