"""Tests for the graph builder — ensures the graph compiles without errors."""

import pytest


class TestGraphBuilder:
    def test_graph_compiles(self):
        from app.graph.builder import build_oracle_graph

        graph = build_oracle_graph()
        assert graph is not None

    def test_graph_has_correct_nodes(self):
        from app.graph.builder import build_oracle_graph

        graph = build_oracle_graph()
        # The compiled graph should have our nodes
        node_names = set(graph.get_graph().nodes.keys())
        expected = {
            "discovery",
            "harvest",
            "clean",
            "reasoning",
            "evaluation",
            "synthesis",
            "retry_prep",
            "force_synthesis_prep",
            "__start__",
            "__end__",
        }
        assert expected.issubset(node_names)
