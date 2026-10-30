import os
import re

import pymupdf as fitz
from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage


class PdfDocument:
    def __init__(self, path):
        self.path = path
        self._doc = fitz.open(path)
        self._layouts = {}
        self._links = {}

    def get_links(self, index):
        """Links as (rect, kind, target): kind "uri" -> url, kind "page" -> (page, y)."""
        links = self._links.get(index)
        if links is None:
            links = []
            for ln in self._doc[index].get_links():
                r = ln["from"]
                rect = (r.x0, r.y0, r.x1, r.y1)
                if ln.get("uri"):
                    links.append((rect, "uri", ln["uri"]))
                elif ln.get("page", -1) >= 0 and ln["kind"] != fitz.LINK_GOTOR:
                    to = ln.get("to")
                    links.append((rect, "page", (ln["page"], to.y if to else 0)))
                elif ln.get("file"):
                    # Launch / other-document links point at a file, relative to this PDF.
                    path = self._resolve_file_spec(ln["file"])
                    links.append((rect, "uri", QUrl.fromLocalFile(path).toString()))
            self._links[index] = links
        return links

    def get_text_layout(self, index):
        """(chars, lines) for a page in reading order.

        chars: (x0, y0, x1, y1, char, line_no)
        lines: (x0, y0, x1, y1, first_char, end_char) with end_char exclusive
        """
        layout = self._layouts.get(index)
        if layout is None:
            chars, lines = [], []
            raw = self._doc[index].get_text("rawdict", sort=True)
            for block in raw["blocks"]:
                for line in block.get("lines", []):
                    start = len(chars)
                    for span in line["spans"]:
                        for ch in span["chars"]:
                            x0, y0, x1, y1 = ch["bbox"]
                            chars.append((x0, y0, x1, y1, ch["c"], len(lines)))
                    if len(chars) > start:
                        x0, y0, x1, y1 = line["bbox"]
                        lines.append((x0, y0, x1, y1, start, len(chars)))
            layout = (chars, lines)
            self._layouts[index] = layout
        return layout

    def _resolve_file_spec(self, spec):
        # PDF file specs write drives as "/C:/dir/f" or "/C/dir/f".
        if re.match(r"^/[A-Za-z]:", spec):
            spec = spec[1:]
        elif re.match(r"^/[A-Za-z]/", spec):
            spec = f"{spec[1]}:{spec[2:]}"
        base = os.path.dirname(os.path.abspath(self.path))
        return os.path.normpath(os.path.join(base, spec))

    @property
    def page_count(self):
        return self._doc.page_count

    def page_size(self, index):
        rect = self._doc[index].rect
        return rect.width, rect.height

    def render_page(self, index, zoom) -> QImage:
        page = self._doc[index]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        return img.copy()

    def get_toc(self):
        return self._doc.get_toc(simple=True)

    def search_page(self, index, text):
        if not text:
            return []
        return self._doc[index].search_for(text, quads=False)

    def close(self):
        self._doc.close()
