"""Tests for the supervisor routing logic."""

import pytest

from app.graph.supervisor import supervisor


class TestSupervisor:
    def test_high_score_routes_to_synthesis(self):
        state = {"evaluation_score": 0.85, "retry_count": 0}
        assert supervisor(state) == "synthesis"

    def test_low_score_with_retries_routes_to_retry(self):
        state = {"evaluation_score": 0.5, "retry_count": 0}
        assert supervisor(state) == "retry"

    def test_low_score_retries_exhausted_routes_to_force(self):
        state = {"evaluation_score": 0.5, "retry_count": 2}
        assert supervisor(state) == "force_synthesis"

    def test_exact_threshold_routes_to_synthesis(self):
        state = {"evaluation_score": 0.8, "retry_count": 0}
        assert supervisor(state) == "synthesis"

    def test_second_retry(self):
        state = {"evaluation_score": 0.6, "retry_count": 1}
        assert supervisor(state) == "retry"
