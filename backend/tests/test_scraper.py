"""Tests for scraper URL classification."""

import pytest

from app.graph.models import UrlCategory
from app.tools.scraper import classify_url


class TestClassifyUrl:
    def test_pdf(self):
        assert classify_url("https://arxiv.org/pdf/2312.00001.pdf") == UrlCategory.PDF

    def test_github(self):
        assert classify_url("https://github.com/user/repo") == UrlCategory.GITHUB

    def test_docs(self):
        assert classify_url("https://docs.python.org/3/library") == UrlCategory.DOC

    def test_arxiv(self):
        assert classify_url("https://arxiv.org/abs/2312.00001") == UrlCategory.DOC

    def test_regular(self):
        assert classify_url("https://example.com/page") == UrlCategory.OTHER
