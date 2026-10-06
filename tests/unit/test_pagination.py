"""Pagination helper tests."""

from app.core.pagination import PageMeta, PageParams


def test_page_params_offset_first_page():
    p = PageParams(page=1, size=25)
    assert p.offset == 0
    assert p.limit == 25


def test_page_params_offset_later_page():
    p = PageParams(page=3, size=10)
    assert p.offset == 20
    assert p.limit == 10


def test_page_meta_calculations():
    m = PageMeta(page=1, size=25, total=100, pages=4, has_next=True, has_prev=False)
    assert m.pages == 4
    assert m.has_next is True
    assert m.has_prev is False


def test_page_meta_last_page():
    m = PageMeta(page=4, size=25, total=100, pages=4, has_next=False, has_prev=True)
    assert m.has_next is False
    assert m.has_prev is True