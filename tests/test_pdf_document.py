import os
import sys

import pytest

from app.pdf_document import PdfDocument


@pytest.fixture
def doc(text_pdf):
    d = PdfDocument(str(text_pdf))
    yield d
    d.close()


def test_page_count_and_size(doc):
    assert doc.page_count == 8
    assert doc.page_size(0) == (595, 842)


def test_render_page_scales_with_zoom(doc):
    img = doc.render_page(0, 2.0)
    assert (img.width(), img.height()) == (1190, 1684)
    assert not img.isNull()


def test_toc(doc):
    toc = doc.get_toc()
    assert [entry[1] for entry in toc] == ["Chapter 1", "Section 1.1", "Chapter 2"]
    assert [entry[0] for entry in toc] == [1, 2, 1]
    assert toc[2][2] == 4  # 1-based page number


def test_search_page(doc):
    assert len(doc.search_page(0, "Findme")) == 1
    assert doc.search_page(0, "not in the document") == []
    assert doc.search_page(0, "") == []


def test_text_layout_chars_and_lines_are_consistent(doc):
    chars, lines = doc.get_text_layout(0)
    assert "Sample document - Page 1" in "".join(c[4] for c in chars)
    assert lines[0][4] == 0 and lines[-1][5] == len(chars)
    for n, (_, _, _, _, start, end) in enumerate(lines):
        assert start < end
        assert all(chars[i][5] == n for i in range(start, end))


def test_text_layout_is_cached(doc):
    assert doc.get_text_layout(1) is doc.get_text_layout(1)


def test_links(links_pdf):
    d = PdfDocument(str(links_pdf))
    try:
        links = d.get_links(0)
        assert [kind for _, kind, _ in links] == ["page", "uri", "uri"]
        assert links[0][2] == (3, 300.0)
        assert links[1][2] == "https://example.com/"
        assert links[2][2] == "file:///C:/Windows/notepad.exe"
        assert d.get_links(1) == []
    finally:
        d.close()


@pytest.mark.skipif(sys.platform != "win32", reason="drive-letter paths")
@pytest.mark.parametrize("spec, expected", [
    ("/C:/Windows/notepad.exe", r"C:\Windows\notepad.exe"),
    ("/C/Windows/notepad.exe", r"C:\Windows\notepad.exe"),
])
def test_resolve_absolute_file_spec(doc, spec, expected):
    assert doc._resolve_file_spec(spec) == expected


def test_resolve_relative_file_spec(doc, text_pdf):
    expected = os.path.join(os.path.dirname(text_pdf), "sub", "other.pdf")
    assert doc._resolve_file_spec("sub/other.pdf") == os.path.normpath(expected)
