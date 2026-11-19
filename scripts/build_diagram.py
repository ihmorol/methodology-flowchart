#!/usr/bin/env python3
"""Build a one-page methodology / workflow flowchart from a JSON spec.

The spec lists groups, rows of boxes and diamonds, frames with cells, arrows and
labels. The builder lays out rows, routes arrows between named anchors, checks
the layout and exports HTML, PDF, SVG and PNG.

The build refuses to write files when a check fails: text wider than its box,
overlapping or cramped shapes, a shape cut by a group border, an arrow through
a shape or tab, a diagonal arrow, a label on a shape or border, or a broken
writing rule. Fix the spec; never weaken the checks.

Usage:
    uv run --no-project --with fonttools --with pymupdf python scripts/build_diagram.py SPEC.json --out DIR
    python scripts/build_diagram.py SPEC.json --check        # validate only, needs fonttools

Spec format: references/spec-format.md. Style: references/style-guide.md.
"""

from pathlib import Path
from html import escape
import argparse
import base64
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile

SKILL = Path(__file__).resolve().parents[1]
FONT_DIR = SKILL / "assets" / "fonts"
FONT_FILES = {
    (False, False): "STIX-Regular.otf",
    (True, False): "STIX-Bold.otf",
    (False, True): "STIX-Italic.otf",
    (True, True): "STIX-BoldItalic.otf",
}
PAGES = {  # CSS-pixel canvas and printed page size
    "a4-landscape": (1200, 848, "297mm", "210mm"),
    "a4-portrait": (848, 1200, "210mm", "297mm"),
    "letter-landscape": (1200, 927, "11in", "8.5in"),
    "letter-portrait": (927, 1200, "8.5in", "11in"),
}

INK = "#1f2328"
ARROW = "#3b4049"
GREEN = "#3d7a58"
TAB_FILL = "#2f5d46"
TONES = {  # fill, stroke, badge
    "peach": ("#fcebe1", "#e3a98a", "#b9532b"),
    "blue": ("#e9effb", "#8ea3dc", "#2f4a9a"),
    "purple": ("#f1ebfa", "#a993d6", "#6b4bb3"),
    "green": ("#e3f3ea", "#82c3a1", "#23735a"),
    "cyan": ("#e4f2f7", "#86bcd0", "#2e6f8e"),
    "gray": ("#f1f2f4", "#a4a9b1", "#4b5361"),
    "orange": ("#fef1e3", "#e2a256", "#c4691b"),
    "red": ("#fbe7e3", "#e2a092", "#b0443a"),
}
DIAMOND = ("#fdf3c7", "#d8b443")
SIZE = dict(title=15, body=12.5, cell_title=12.5, cell_body=11.5, diamond_title=13.5,
            diamond_body=11.5, tab=11.5, label=10.5, badge=11.5)
MIN_GAP = 12        # between any two shapes
GROUP_PAD = 12      # between a shape and the border of the group holding it
PAGE_MARGIN = 12


logging.getLogger("fontTools").setLevel(logging.ERROR)


class SpecError(Exception):
    pass


# ------------------------------------------------------------------ text

class Metrics:
    def __init__(self):
        from fontTools.ttLib import TTFont
        self.fonts = {}
        for key, name in FONT_FILES.items():
            font = TTFont(FONT_DIR / name)
            self.fonts[key] = (font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm)

    def width(self, text, size, bold, italic):
        cmap, hmtx, upem = self.fonts[(bold, italic)]
        total = 0
        for char in text:
            glyph = cmap.get(ord(char))
            if glyph is None:
                raise SpecError(f"the font has no glyph for {char!r} (U+{ord(char):04X}); use another character")
            total += hmtx[glyph][0]
        return total * size / upem


def parse(markup, italic=False, shift=0):
    """*x* italic, _{x} subscript, ^{x} superscript, \\* a literal star."""
    runs, buffer, i = [], "", 0
    while i < len(markup):
        char = markup[i]
        if char == "\\" and i + 1 < len(markup):
            buffer += markup[i + 1]
            i += 2
        elif char == "*":
            if buffer:
                runs.append((buffer, italic, shift))
                buffer = ""
            italic = not italic
            i += 1
        elif char in "_^" and markup[i + 1:i + 2] == "{":
            if buffer:
                runs.append((buffer, italic, shift))
                buffer = ""
            depth, j = 1, i + 2
            while depth:
                if j >= len(markup):
                    raise SpecError(f"unclosed {{ in {markup!r}")
                depth += {"{": 1, "}": -1}.get(markup[j], 0)
                j += 1
            runs += parse(markup[i + 2:j - 1], italic, 1 if char == "_" else -1)
            i = j
        else:
            buffer += char
            i += 1
    if buffer:
        runs.append((buffer, italic, shift))
    return runs


def plain(markup):
    return "".join(run[0] for run in parse(markup))


def text_svg(markup, x, y, size, bold=False, anchor="middle", fill=INK, extra=""):
    parts, offset = [], 0.0
    for text, italic, shift in parse(markup):
        target = {0: 0.0, 1: size * 0.28, -1: -size * 0.38}[shift]
        attrs = []
        if target != offset:
            attrs.append(f'dy="{target - offset:.2f}"')
            offset = target
        if italic:
            attrs.append('font-style="italic"')
        if shift:
            attrs.append(f'font-size="{size * 0.72:.2f}"')
        parts.append(f'<tspan {" ".join(attrs)}>{escape(text)}</tspan>' if attrs else escape(text))
    weight = ' font-weight="bold"' if bold else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{fill}"{weight}{extra}>{"".join(parts)}</text>')


# ------------------------------------------------------------------ scene

class Scene:
    def __init__(self, spec, metrics):
        self.spec, self.m = spec, metrics
        page = spec.get("page", "a4-landscape")
        if page not in PAGES:
            raise SpecError(f"page must be one of {sorted(PAGES)}")
        self.W, self.H, self.page_w, self.page_h = PAGES[page]
        self.layers = {"groups": [], "arrows": [], "nodes": [], "labels": []}
        self.nodes = {}          # id -> shape dict
        self.groups = []
        self.tabs = []
        self.paths = []          # (points, inner, name)
        self.label_boxes = []
        self.strings = []
        self.errors, self.warnings = [], []
        self.auto_id = 0

    # -- helpers ---------------------------------------------------------
    def measure(self, markup, size, bold=False):
        return sum(self.m.width(text, size * (0.72 if shift else 1), bold, italic)
                   for text, italic, shift in parse(markup))

    def fit(self, markup, size, bold, room, where):
        self.strings.append(plain(markup))
        width = self.measure(markup, size, bold)
        if width > room:
            self.errors.append(f"{where}: '{plain(markup)}' is {width:.0f}px wide, room is {room:.0f}px. "
                               f"Shorten the text or widen the shape.")

    def new_id(self, prefix):
        self.auto_id += 1
        return f"{prefix}-{self.auto_id}"

    def register(self, el, kind, x, y, w, h, inner=False):
        key = el.get("id") or self.new_id(kind)
        if key in self.nodes:
            raise SpecError(f"duplicate id '{key}'")
        if w <= 0 or h <= 0:
            raise SpecError(f"'{key}' has no size (w={w}, h={h})")
        self.nodes[key] = dict(key=key, kind=kind, x=x, y=y, w=w, h=h, inner=inner)
        return key

    # -- shapes ----------------------------------------------------------
    def group(self, el):
        x, y, w, h, tab = el["x"], el["y"], el["w"], el["h"], el.get("tab", "").upper()
        self.layers["groups"].append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="none" stroke="{GREEN}" '
            f'stroke-width="1.6" stroke-dasharray="7 5"/>')
        self.groups.append(dict(key=el.get("id", tab or "group"), x=x, y=y, w=w, h=h))
        if tab:
            tw = self.measure(tab, SIZE["tab"], True) + 0.8 * len(tab) + 30
            self.strings.append(tab)
            self.layers["groups"].append(
                f'<rect x="{x + 16}" y="{y - 12}" width="{tw:.1f}" height="24" rx="12" fill="{TAB_FILL}"/>'
                + text_svg(tab, x + 16 + tw / 2, y + 4.2, SIZE["tab"], True, fill="#ffffff",
                           extra=' letter-spacing="0.8"'))
            self.tabs.append(dict(key=f"tab '{tab}'", kind="rect", x=x + 16, y=y - 12, w=tw, h=24))

    def badge(self, x, y, number, color):
        self.strings.append(str(number))
        return (f'<circle cx="{x + 20}" cy="{y + 20}" r="10.5" fill="{color}"/>'
                + text_svg(str(number), x + 20, y + 24.2, SIZE["badge"], True, fill="#ffffff"))

    def box(self, el):
        x, y, w, h = el["x"], el["y"], el["w"], el["h"]
        tone = el.get("tone", "blue")
        if tone not in TONES:
            raise SpecError(f"tone '{tone}' unknown; use one of {sorted(TONES)}")
        fill, stroke, badge = TONES[tone]
        key = self.register(el, "box", x, y, w, h)
        number = el.get("number")
        size = el.get("size", SIZE["body"])
        lines = list(el.get("lines", []))
        width = 2 if el.get("thick") else 1.3
        out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>']
        if number is not None:
            out.append(self.badge(x, y, number, badge))
        block = 14 + (21 + (len(lines) - 1) * 17 + 4 if lines else 4)
        top = y + (h - block) / 2 + 13
        if number is not None:
            top = max(top, y + 23)
        title = el.get("title", "")
        self.fit(title, SIZE["title"], True, w - 80 if number is not None else w - 28, f"{key} title")
        out.append(text_svg(title, x + w / 2, top, SIZE["title"], True))
        for i, line in enumerate(lines):
            self.fit(line, size, False, w - 28, f"{key} line {i + 1}")
            out.append(text_svg(line, x + w / 2, top + 21 + i * 17, size))
        bottom = top + (21 + (len(lines) - 1) * 17 if lines else 0) + 4
        if bottom > y + h - 4:
            self.errors.append(f"{key}: {len(lines)} line(s) do not fit in height {h}. Use h >= "
                               f"{int(h + bottom - (y + h - 4)) + 1} or fewer lines.")
        self.layers["nodes"].append("".join(out))

    def frame(self, el):
        x, y, w, h = el["x"], el["y"], el["w"], el["h"]
        tone = el.get("tone", "blue")
        fill, stroke, badge = TONES[tone]
        key = self.register(el, "box", x, y, w, h)
        number = el.get("number")
        title = el.get("title", "")
        self.fit(title, SIZE["title"], True, w - 80 if number is not None else w - 28, f"{key} title")
        out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>']
        if number is not None:
            out.append(self.badge(x, y, number, badge))
        out.append(text_svg(title, x + w / 2, y + 26, SIZE["title"], True))
        self.layers["nodes"].append("".join(out))
        cells = el.get("cells", [])
        if cells:
            gap = el.get("cell_gap", 22 if el.get("cell_arrows") else 14)
            pad = 10
            cw = (w - 2 * pad - gap * (len(cells) - 1)) / len(cells)
            cy, ch = y + 36, h - 36 - 10
            if ch < 40:
                self.errors.append(f"{key}: cells need frame height >= 86 (got {h})")
            cell_stroke = TONES[tone][1] if tone != "gray" else "#a4a9b1"
            for i, cell in enumerate(cells):
                cx = x + pad + i * (cw + gap)
                self.cell(f"{key}/cell{i + 1}", cx, cy, cw, ch, cell.get("title", ""), cell.get("line", ""), cell_stroke)
                if i and el.get("cell_arrows"):
                    self.add_path([(cx - gap, cy + ch / 2), (cx, cy + ch / 2)], inner=True)

    def cell(self, key, x, y, w, h, title, line, stroke):
        self.register({"id": key}, "box", x, y, w, h, inner=True)
        self.fit(title, SIZE["cell_title"], True, w - 16, f"{key} title")
        if line:
            self.fit(line, SIZE["cell_body"], False, w - 16, f"{key} line")
        title_y = y + h / 2 - 3 if line else y + h / 2 + 4
        self.layers["nodes"].append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="#ffffff" stroke="{stroke}" stroke-width="1.1"/>'
            + text_svg(title, x + w / 2, title_y, SIZE["cell_title"], True)
            + (text_svg(line, x + w / 2, y + h / 2 + 13, SIZE["cell_body"]) if line else ""))

    def diamond(self, el):
        cx, cy, w, h = el["cx"], el["cy"], el.get("w", 200), el.get("h", 76)
        key = self.register(el, "diamond", cx - w / 2, cy - h / 2, w, h)
        fill, stroke = DIAMOND
        points = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
        out = [f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>']
        rows = [(el.get("title", ""), SIZE["diamond_title"], True)] + \
               [(line, SIZE["diamond_body"], False) for line in el.get("lines", [])]
        heights = [16] + [14] * (len(rows) - 1)
        ty = cy - sum(heights) / 2 + 12
        for (markup, size, bold), step in zip(rows, heights):
            far = max(abs(ty - size * 0.75 - cy), abs(ty + size * 0.2 - cy))
            room = w * (1 - far / (h / 2)) - 14
            self.fit(markup, size, bold, room, f"{key} '{plain(markup)}'")
            out.append(text_svg(markup, cx, ty, size, bold))
            ty += step
        self.layers["nodes"].append("".join(out))

    def row(self, el):
        """Place items left to right between x0 and x1, vertically centred on the row."""
        items, gap = el["items"], el.get("gap", 24)
        x0, x1, y, h = el["x0"], el["x1"], el["y"], el["h"]
        fixed = sum(it.get("w", 200 if it["type"] == "diamond" else 0) for it in items
                    if "w" in it or it["type"] == "diamond")
        grow = sum(it.get("grow", 1) for it in items if "w" not in it and it["type"] != "diamond")
        free = x1 - x0 - gap * (len(items) - 1) - fixed
        if grow and free <= 0:
            raise SpecError(f"row at y={y}: no width left for the growing boxes; reduce fixed widths or gap")
        if not grow and abs(free) > 0.5:
            self.warnings.append(f"row at y={y}: items fill {x1 - x0 - free:.0f}px of {x1 - x0}px; add a growing item or adjust widths")
        x, previous = x0, None
        for it in items:
            if it["type"] == "diamond":
                w = it.get("w", 200)
            else:
                w = it.get("w", free * it.get("grow", 1) / grow if grow else 0)
            ih = it.get("h", h)
            iy = y + (h - ih) / 2
            spec = dict(it)
            if it["type"] == "diamond":
                spec.update(cx=x + w / 2, cy=y + h / 2, w=w, h=ih)
            else:
                spec.update(x=round(x, 1), y=iy, w=round(w, 1), h=ih)
            spec.setdefault("id", self.new_id(it["type"]))
            {"box": self.box, "frame": self.frame, "diamond": self.diamond}[it["type"]](spec)
            if previous and el.get("connect", True) and not it.get("no_arrow_in"):
                self.pending_arrows.append({"from": f"{previous}.right", "to": f"{spec['id']}.left"})
            previous = spec["id"]
            x += w + gap

    # -- arrows ----------------------------------------------------------
    def anchor(self, ref):
        if isinstance(ref, list):
            return tuple(map(float, ref)), None
        match = re.fullmatch(r"([^.@]+(?:/[^.@]+)?)\.(top|bottom|left|right)(?:@([0-9.]+))?", ref)
        if not match:
            raise SpecError(f"bad anchor '{ref}'; use 'id.side' or 'id.side@0.3' or [x, y]")
        key, side, frac = match.group(1), match.group(2), match.group(3)
        if key not in self.nodes:
            raise SpecError(f"anchor '{ref}': no shape with id '{key}'")
        n = self.nodes[key]
        f = float(frac) if frac else 0.5
        if n["kind"] == "diamond" and frac:
            raise SpecError(f"anchor '{ref}': diamonds only have the four corner anchors")
        x, y, w, h = n["x"], n["y"], n["w"], n["h"]
        point = {"top": (x + w * f, y), "bottom": (x + w * f, y + h),
                 "left": (x, y + h * f), "right": (x + w, y + h * f)}[side]
        return point, side

    def arrow(self, el):
        a, sa = self.anchor(el["from"])
        b, sb = self.anchor(el["to"])
        vertical = {"top", "bottom"}
        facing = {("bottom", "top"), ("top", "bottom"), ("right", "left"), ("left", "right")}
        straight_v = abs(a[0] - b[0]) < 0.5 and ((sa, sb) in facing or None in (sa, sb)) and sa not in ("left", "right") and sb not in ("left", "right")
        straight_h = abs(a[1] - b[1]) < 0.5 and ((sa, sb) in facing or None in (sa, sb)) and sa not in vertical and sb not in vertical
        if "via" in el:
            via = [list(map(float, p)) for p in el["via"]]
            # snap hand-given corners onto the anchors so small rounding never makes a diagonal
            for end, corner in ((a, via[0]), (b, via[-1])):
                for k in (0, 1):
                    if abs(corner[k] - end[k]) < 4:
                        corner[k] = end[k]
            points = [a] + [tuple(p) for p in via] + [b]
        elif straight_v or straight_h:
            points = [a, b]
        elif sa in vertical and sb in vertical:
            vy = el.get("via_y")
            if vy is None:
                vy = (max(a[1], b[1]) + 20 if sa == sb == "bottom" else
                      min(a[1], b[1]) - 20 if sa == sb == "top" else (a[1] + b[1]) / 2)
            points = [a, (a[0], vy), (b[0], vy), b]
        elif sa not in vertical and sb not in vertical and sa and sb:
            vx = el.get("via_x")
            if vx is None:
                vx = (max(a[0], b[0]) + 20 if sa == sb == "right" else
                      min(a[0], b[0]) - 20 if sa == sb == "left" else (a[0] + b[0]) / 2)
            points = [a, (vx, a[1]), (vx, b[1]), b]
        elif sa in vertical:
            points = [a, (a[0], b[1]), b]
        else:
            points = [a, (b[0], a[1]), b]
        points = [p for i, p in enumerate(points) if i == 0 or p != points[i - 1]]
        style = el.get("style", "solid")
        color = GREEN if style == "loop" else ARROW
        self.add_path(points, dashed=style in ("loop", "dashed"), color=color, name=f"{el['from']} -> {el['to']}")
        if "label" in el:
            self.arrow_label(el, points, color if style == "loop" else ARROW)

    def add_path(self, points, dashed=False, inner=False, color=ARROW, name="arrow"):
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if abs(x0 - x1) > 0.5 and abs(y0 - y1) > 0.5:
                self.errors.append(f"{name}: diagonal segment ({x0:.0f},{y0:.0f})->({x1:.0f},{y1:.0f}); "
                                   f"arrows must run horizontally or vertically")
        (x0, y0), (x1, y1) = points[-2], points[-1]
        length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        if length < 12:
            self.errors.append(f"{name}: last segment is {length:.0f}px; needs >= 12px for the arrowhead")
            length = max(length, 1)
        trimmed = points[:-1] + [(x1 - (x1 - x0) / length * 4, y1 - (y1 - y0) / length * 4)]
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in trimmed)
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        marker = "head-green" if color == GREEN else "head"
        self.layers["arrows"].append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6"{dash} marker-end="url(#{marker})"/>')
        self.paths.append((points, inner, name))

    def arrow_label(self, el, points, color):
        text = el["label"]
        bold = el.get("label_bold", text.upper() in ("YES", "NO") or text.upper().startswith(("YES", "NO:")))
        where = el.get("label_at", "start")
        if isinstance(where, list):
            self.label({"text": text, "x": where[0], "y": where[1], "bold": bold,
                        "anchor": el.get("label_anchor", "middle"), "color": "green" if color == GREEN else "ink"})
            return
        segments = list(zip(points, points[1:]))
        seg = {"start": segments[0], "end": segments[-1]}.get(
            where, max(segments, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1])))
        (x0, y0), (x1, y1) = seg
        width = self.measure(text, SIZE["label"], bold)
        side = el.get("label_side")
        if abs(y0 - y1) < 0.5:  # horizontal segment
            direction = 1 if x1 >= x0 else -1
            half = abs(x1 - x0) / 2
            if where == "start":
                x = x0 + direction * min(width / 2 + 8, half)
            elif where == "end":
                x = x1 - direction * min(width / 2 + 14, half)
            else:
                x = (x0 + x1) / 2
            y = y0 + 14 if side == "below" else y0 - 6
            anchor = "middle"
        else:
            direction = 1 if y1 >= y0 else -1
            if where == "start":
                y = y0 + direction * 14 + 4
            elif where == "end":
                y = y1 - direction * 14 + 4
            else:
                y = (y0 + y1) / 2 + 4
            if side == "left":
                x, anchor = x0 - 7, "end"
            else:
                x, anchor = x0 + 7, "start"
        self.label({"text": text, "x": x, "y": y, "bold": bold, "anchor": anchor,
                    "color": "green" if color == GREEN else "ink"})

    def label(self, el):
        text, x, y = el["text"], el["x"], el["y"]
        size = el.get("size", SIZE["label"])
        bold = el.get("bold", False)
        anchor = el.get("anchor", "middle")
        color = GREEN if el.get("color") == "green" else ARROW
        self.strings.append(plain(text))
        width = self.measure(text, size, bold)
        extra = f' transform="rotate(-90 {x} {y})"' if el.get("rotate") else ""
        self.layers["labels"].append(text_svg(text, x, y, size, bold, anchor, color, extra))
        if el.get("rotate"):
            box = (x - size * 0.8, y - width / 2, size, width)
        else:
            left = {"middle": x - width / 2, "start": x, "end": x - width}[anchor]
            box = (left, y - size * 0.75, width, size)
        self.label_boxes.append((plain(text),) + box)

    # -- validation ------------------------------------------------------
    @staticmethod
    def inside(n, px, py, pad=1.5):
        if n["kind"] == "diamond":
            cx, cy = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
            return abs(px - cx) / (n["w"] / 2) + abs(py - cy) / (n["h"] / 2) < 1 - 2 * pad / min(n["w"], n["h"])
        return n["x"] + pad < px < n["x"] + n["w"] - pad and n["y"] + pad < py < n["y"] + n["h"] - pad

    @staticmethod
    def rect_gap(a, b):
        dx = max(b["x"] - (a["x"] + a["w"]), a["x"] - (b["x"] + b["w"]), 0)
        dy = max(b["y"] - (a["y"] + a["h"]), a["y"] - (b["y"] + b["h"]), 0)
        overlap = (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
                   and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"])
        return -1 if overlap else max(dx, dy) if (dx == 0 or dy == 0) else (dx ** 2 + dy ** 2) ** 0.5

    def validate(self):
        W, H = self.W, self.H
        outer = [n for n in self.nodes.values() if not n["inner"]]
        for n in outer + self.groups:
            if n["x"] < PAGE_MARGIN or n["y"] < PAGE_MARGIN or n["x"] + n["w"] > W - PAGE_MARGIN or n["y"] + n["h"] > H - PAGE_MARGIN:
                self.errors.append(f"{n['key']}: outside the page or within {PAGE_MARGIN}px of its edge ({W}x{H})")
        for i, a in enumerate(outer):
            for b in outer[i + 1:]:
                gap = self.rect_gap(a, b)
                if gap < 0:
                    self.errors.append(f"{a['key']} overlaps {b['key']}")
                elif gap < MIN_GAP:
                    self.errors.append(f"{a['key']} and {b['key']} are {gap:.0f}px apart; keep >= {MIN_GAP}px")
        for g in self.groups:
            for n in outer:
                inside = (g["x"] <= n["x"] and n["x"] + n["w"] <= g["x"] + g["w"]
                          and g["y"] <= n["y"] and n["y"] + n["h"] <= g["y"] + g["h"])
                apart = self.rect_gap(g, n) >= 0 and not (
                    g["x"] < n["x"] + n["w"] and n["x"] < g["x"] + g["w"] and g["y"] < n["y"] + n["h"] and n["y"] < g["y"] + g["h"])
                if inside:
                    pad = min(n["x"] - g["x"], g["x"] + g["w"] - n["x"] - n["w"], n["y"] - g["y"], g["y"] + g["h"] - n["y"] - n["h"])
                    if pad < GROUP_PAD:
                        self.errors.append(f"{n['key']} is {pad:.0f}px from the border of group {g['key']}; keep >= {GROUP_PAD}px")
                elif not apart:
                    self.errors.append(f"{n['key']} is cut by the border of group {g['key']}; put it fully inside or outside")
        for t in self.tabs:
            for n in outer:
                if self.rect_gap(t, n) < 0:
                    self.errors.append(f"{n['key']} overlaps {t['key']}")
        for i, a in enumerate(self.groups):
            for b in self.groups[i + 1:]:
                gap = self.rect_gap(a, b)
                if 0 <= gap < 16:
                    self.errors.append(f"groups {a['key']} and {b['key']} are {gap:.0f}px apart; keep >= 16px side by side, 36px stacked")
                elif gap < 0:
                    self.errors.append(f"groups {a['key']} and {b['key']} overlap")
        for points, inner, name in self.paths:
            if inner:
                continue
            samples = []
            for (x0, y0), (x1, y1) in zip(points, points[1:]):
                steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / 2))
                samples += [(x0 + (x1 - x0) * k / steps, y0 + (y1 - y0) * k / steps) for k in range(steps + 1)]
            hit = next((n["key"] for px, py in samples[2:-2] for n in outer + self.tabs if self.inside(n, px, py)), None)
            if hit:
                self.errors.append(f"arrow {name} runs through {hit}; reroute it with via, via_x, via_y or another anchor")
            for px, py in (points[0], points[-1]):
                on_edge = any(self.on_border(n, px, py) for n in self.nodes.values())
                on_group = any(self.on_border(g, px, py) for g in self.groups)
                on_arrow = any(min(x0, x1) - 2 <= px <= max(x0, x1) + 2 and min(y0, y1) - 2 <= py <= max(y0, y1) + 2
                               for other, _, other_name in self.paths if other_name != name
                               for (x0, y0), (x1, y1) in zip(other, other[1:]))
                if not (on_edge or on_group or on_arrow):
                    self.warnings.append(f"arrow {name}: end ({px:.0f},{py:.0f}) is not on a shape or group border")
        for name, x, y, w, h in self.label_boxes:
            for n in outer + self.tabs:
                if n["kind"] == "diamond":
                    probes = [(x + w * i / 4, y + h * j / 2) for i in range(5) for j in range(3)]
                    hit = any(self.inside(n, px, py, pad=0) for px, py in probes)
                else:
                    hit = x < n["x"] + n["w"] and n["x"] < x + w and y < n["y"] + n["h"] and n["y"] < y + h
                if hit:
                    self.errors.append(f"label '{name}' overlaps {n['key']}; move it with label_at [x, y] or label_side")
            for g in self.groups:
                cut_x = any(x < edge < x + w for edge in (g["x"], g["x"] + g["w"])) and y < g["y"] + g["h"] and g["y"] < y + h
                cut_y = any(y < edge < y + h for edge in (g["y"], g["y"] + g["h"])) and x < g["x"] + g["w"] and g["x"] < x + w
                if cut_x or cut_y:
                    self.errors.append(f"label '{name}' sits on the border of group {g['key']}")
            if x < PAGE_MARGIN or x + w > W - PAGE_MARGIN:
                self.errors.append(f"label '{name}' runs off the page")
            for points, inner, path_name in self.paths:
                for (x0, y0), (x1, y1) in zip(points, points[1:]):
                    if (min(x0, x1) < x + w - 1 and x + 1 < max(x0, x1) + 0.01
                            and min(y0, y1) < y + h - 1 and y + 1 < max(y0, y1) + 0.01):
                        self.errors.append(f"label '{name}' lies on the arrow {path_name}")
                        break
        for i, a in enumerate(self.label_boxes):
            for b in self.label_boxes[i + 1:]:
                if a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]:
                    self.errors.append(f"labels '{a[0]}' and '{b[0]}' overlap")
        # page use
        everything = outer + self.groups
        if everything:
            left = min(n["x"] for n in everything); right = max(n["x"] + n["w"] for n in everything)
            top = min(n["y"] for n in everything); bottom = max(n["y"] + n["h"] for n in everything)
            if (right - left) < 0.85 * W or (bottom - top) < 0.80 * H:
                self.warnings.append(f"content covers {100 * (right - left) / W:.0f}% of the width and "
                                     f"{100 * (bottom - top) / H:.0f}% of the height; spread the layout to fill the page")
        # writing rules
        rules = self.spec.get("writing", {})
        text = " ".join(self.strings + [self.spec.get("title", ""), self.spec.get("caption", "")])
        for word in rules.get("banned_words", []):
            if re.search(rf"\b{re.escape(word)}", text, re.I):
                self.errors.append(f"banned word in the text: {word}")
        if rules.get("forbid_dashes", True) and re.search("[\u2013\u2014]", text):
            self.errors.append("en or em dash in the text; use a colon, comma or 'to'")
        max_words = rules.get("max_title_words", 5)
        for n in self.spec_titles:
            if len(plain(n).split()) > max_words:
                self.errors.append(f"box title '{plain(n)}' has more than {max_words} words")

    @staticmethod
    def on_border(n, px, py, tol=1.5):
        if n.get("kind") == "diamond":
            cx, cy = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
            return abs(abs(px - cx) / (n["w"] / 2) + abs(py - cy) / (n["h"] / 2) - 1) < 0.03
        x, y, w, h = n["x"], n["y"], n["w"], n["h"]
        near_v = (abs(px - x) < tol or abs(px - x - w) < tol) and y - tol <= py <= y + h + tol
        near_h = (abs(py - y) < tol or abs(py - y - h) < tol) and x - tol <= px <= x + w + tol
        return near_v or near_h

    # -- build -----------------------------------------------------------
    def build(self):
        self.pending_arrows, self.spec_titles = [], []
        later = []
        for el in self.spec["elements"]:
            kind = el.get("type")
            if kind in ("box", "frame", "diamond", "row"):
                self.spec_titles += [el.get("title", "")] if kind != "row" else \
                    [it.get("title", "") for it in el["items"] if it["type"] != "diamond"]
            if kind == "group":
                self.group(el)
            elif kind == "box":
                self.box(el)
            elif kind == "frame":
                self.frame(el)
            elif kind == "diamond":
                self.diamond(el)
            elif kind == "row":
                self.row(el)
            elif kind in ("arrow", "label"):
                later.append(el)
            else:
                raise SpecError(f"unknown element type '{kind}'")
        for el in self.pending_arrows:
            self.arrow(el)
        for el in later:
            (self.arrow if el["type"] == "arrow" else self.label)(el)
        self.validate()

    def svg(self, fonts_css=""):
        defs = ''.join(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="5.6" refY="5" markerWidth="9" markerHeight="9" '
            f'markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            for mid, color in (("head", ARROW), ("head-green", GREEN)))
        style = f"<style>{fonts_css}</style>" if fonts_css else ""
        body = "".join(self.layers["groups"] + self.layers["arrows"] + self.layers["nodes"] + self.layers["labels"])
        caption = escape(self.spec.get("caption", self.spec.get("title", "")))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" role="img" '
                f'aria-label="{caption}" font-family="Diagram Serif, STIX, serif">{style}'
                f'<rect width="{self.W}" height="{self.H}" fill="#ffffff"/><defs>{defs}</defs>{body}</svg>')


# ------------------------------------------------------------------ export

def font_css(strings):
    from fontTools import subset
    text = "".join(set("".join(strings))) + "0123456789 "
    rules = []
    for (bold, italic), name in FONT_FILES.items():
        options = subset.Options()
        options.flavor = "woff"
        options.layout_features = ["*"]
        options.ignore_missing_unicodes = True
        font = subset.load_font(str(FONT_DIR / name), options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(text=text)
        subsetter.subset(font)
        buffer = io.BytesIO()
        subset.save_font(font, buffer, options)
        data = base64.b64encode(buffer.getvalue()).decode()
        rules.append(f"@font-face{{font-family:'Diagram Serif';src:url(data:font/woff;base64,{data}) format('woff');"
                     f"font-weight:{700 if bold else 400};font-style:{'italic' if italic else 'normal'}}}")
    return "\n".join(rules)


def html_page(scene, css):
    spec = scene.spec
    title = escape(spec.get("title", "Diagram"))
    caption = escape(spec.get("caption", ""))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<!-- Generated by build_diagram.py from a JSON spec. Edit the spec, then rebuild. -->
<style>
{css}
@page {{ size: {scene.page_w} {scene.page_h}; margin: 0 }}
:root {{ color-scheme: light }}
html, body {{ margin: 0; background: #ffffff; color: {INK}; font-family: 'Diagram Serif', STIX, serif }}
figure {{ margin: 0 auto; padding: 16px; max-width: 1400px; box-sizing: border-box }}
figure svg {{ display: block; width: 100%; height: auto }}
figcaption {{ font-size: 15px; line-height: 1.45; margin: 10px 4px 0; color: #3b4049 }}
@media print {{
  figure {{ padding: 0; max-width: none }}
  figure svg {{ width: {scene.page_w}; height: {scene.page_h} }}
  figcaption {{ display: none }}
}}
</style>
</head>
<body>
<figure>
{scene.svg()}
<figcaption>{caption}</figcaption>
</figure>
</body>
</html>
"""


def find_browser():
    env = os.environ.get("DIAGRAM_BROWSER")
    if env:
        return env
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge"):
        path = shutil.which(name)
        if path:
            return path
    for path in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                 "/Applications/Chromium.app/Contents/MacOS/Chromium",
                 r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if Path(path).exists():
            return path
    return None


def export(scene, html_path, css):
    stem = html_path.with_suffix("")
    browser = find_browser()
    if not browser:
        svg_path = stem.with_suffix(".svg")
        svg_path.write_text(scene.svg(css))
        return [f"no Chrome, Chromium or Edge found (set DIAGRAM_BROWSER); wrote {svg_path.name} with embedded fonts, skipped PDF and PNG"]
    import pymupdf
    pdf_path = stem.with_suffix(".pdf")
    with tempfile.TemporaryDirectory(dir=html_path.parent) as profile:
        run = subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                              f"--user-data-dir={profile}", "--virtual-time-budget=5000",
                              f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
                             capture_output=True, text=True)
    if run.returncode != 0 or not pdf_path.exists():
        raise SpecError(f"browser export failed: {run.stderr[-800:]}")
    document = pymupdf.open(pdf_path)
    if document.page_count != 1:
        raise SpecError(f"{pdf_path.name} has {document.page_count} pages; expected 1")
    document.set_metadata({"title": scene.spec.get("title", ""), "subject": scene.spec.get("caption", ""),
                           "creator": "methodology-flowchart skill"})
    document.saveIncr()
    page = document[0]
    missing = [f[3] for f in page.get_fonts() if f[2] != "Type3" and "STIX" not in f[3]]  # Chrome embeds STIX as Type3
    notes = [f"unexpected fonts in the PDF: {missing}"] if missing else []
    stem.with_suffix(".svg").write_text(page.get_svg_image(text_as_path=True))
    zoom = 2400 / page.rect.width
    page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).save(str(stem) + "-preview.png")
    return notes


def main():
    parser = argparse.ArgumentParser(description="Build a one-page flowchart from a JSON spec.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, help="output folder (default: next to the spec)")
    parser.add_argument("--check", action="store_true", help="validate only; write nothing")
    args = parser.parse_args()
    try:
        spec = json.loads(args.spec.read_text())
    except json.JSONDecodeError as error:
        sys.exit(f"spec is not valid JSON: {error}")
    try:
        scene = Scene(spec, Metrics())
        scene.build()
    except SpecError as error:
        sys.exit(f"SPEC ERROR: {error}")
    except KeyError as error:
        sys.exit(f"SPEC ERROR: missing field {error}")
    for warning in scene.warnings:
        print(f"warning: {warning}")
    if scene.errors:
        print(f"LAYOUT CHECK FAILED ({len(scene.errors)} problems):")
        for error in scene.errors:
            print(f"  - {error}")
        sys.exit(1)
    shapes = sum(1 for n in scene.nodes.values() if not n["inner"])
    if args.check:
        print(f"LAYOUT CHECK PASSED: {shapes} shapes, {len(scene.paths)} arrows, {len(scene.groups)} groups")
        return
    out = args.out or args.spec.parent
    out.mkdir(parents=True, exist_ok=True)
    name = spec.get("name") or args.spec.stem
    css = font_css(scene.strings + [spec.get("title", ""), spec.get("caption", "")])
    html_path = out / f"{name}.html"
    html_path.write_text(html_page(scene, css))
    try:
        notes = export(scene, html_path, css)
    except SpecError as error:
        sys.exit(f"EXPORT ERROR: {error}")
    for note in notes:
        print(f"note: {note}")
    print(f"BUILT {name}: {shapes} shapes, {len(scene.paths)} arrows, {len(scene.groups)} groups -> {out}")
    print(f"Now open {name}-preview.png and review it against the visual checklist.")


if __name__ == "__main__":
    main()
