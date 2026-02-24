"""Tests for search tools."""

import pytest
from unittest.mock import patch, MagicMock

from app.graph.models import SearchResult
from app.tools.search import filter_quality_results


class TestFilterQualityResults:
    def test_filters_short_snippets(self):
        results = [
            SearchResult(url="https://a.com", snippet="short"),
            SearchResult(url="https://b.com", snippet="x" * 150),
            SearchResult(url="https://c.com", snippet="x" * 50),
        ]
        filtered = filter_quality_results(results, min_snippet_length=100)
        assert len(filtered) == 1
        assert filtered[0].url == "https://b.com"

    def test_empty_list(self):
        assert filter_quality_results([]) == []

    def test_all_pass(self):
        results = [
            SearchResult(url="https://a.com", snippet="x" * 200),
            SearchResult(url="https://b.com", snippet="x" * 300),
        ]
        filtered = filter_quality_results(results)
        assert len(filtered) == 2
