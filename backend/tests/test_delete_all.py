"""Clearing out your uploads, and only yours."""
from __future__ import annotations

import io

from docx import Document

from app.docos.service import DocOSService


def a_document() -> bytes:
    doc = Document()
    doc.add_paragraph("Something to keep or not.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_deleting_everything_leaves_nothing():
    service = DocOSService()
    data = a_document()
    for name in ("one", "two", "three"):
        service.import_docx(data, title=name, user="zainab", owner_id="zainab")

    assert service.delete_all_documents(owner_id="zainab") == 3
    assert service.list_documents("zainab") == []


def test_it_takes_only_the_callers_own():
    service = DocOSService()
    data = a_document()
    service.import_docx(data, title="mine", user="zainab", owner_id="zainab")
    service.import_docx(data, title="theirs", user="someone", owner_id="someone")

    assert service.delete_all_documents(owner_id="zainab") == 1
    assert [d["title"] for d in service.list_documents("someone")] == ["theirs"]


def test_nothing_to_delete_is_not_an_error():
    assert DocOSService().delete_all_documents(owner_id="nobody-at-all") == 0
