"""Graph builder — assembles the LangGraph StateGraph and compiles it."""

from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from app.graph.nodes.clean import clean_node
from app.graph.nodes.discovery import discovery_node
from app.graph.nodes.evaluation import evaluation_node
from app.graph.nodes.harvest import harvest_node
from app.graph.nodes.reasoning import reasoning_node
from app.graph.nodes.synthesis import synthesis_node
from app.graph.state import OracleState
from app.graph.supervisor import (
    force_synthesis_prep,
    retry_prep_node,
    supervisor,
)

logger = logging.getLogger(__name__)


def build_oracle_graph():
    """
    Build and compile the Engineering Oracle LangGraph.

    Graph topology:
        discovery → harvest → clean → reasoning → evaluation
                                                        ↓
                                                   [supervisor]
                                              ┌────────┼────────┐
                                              ↓        ↓        ↓
                                          synthesis  retry   force_synth
                                              ↓        ↓        ↓
                                             END    discovery  synthesis
                                                                ↓
                                                               END
    """
    graph = StateGraph(OracleState)

    # ── Add nodes ─────────────────────────────────────────────────────
    graph.add_node("discovery", discovery_node)
    graph.add_node("harvest", harvest_node)
    graph.add_node("clean", clean_node)
    graph.add_node("reasoning", reasoning_node)
    graph.add_node("evaluation", evaluation_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("retry_prep", retry_prep_node)
    graph.add_node("force_synthesis_prep", force_synthesis_prep)

    # ── Linear edges ──────────────────────────────────────────────────
    graph.add_edge("discovery", "harvest")
    graph.add_edge("harvest", "clean")
    graph.add_edge("clean", "reasoning")
    graph.add_edge("reasoning", "evaluation")

    # ── Conditional edge from evaluation (supervisor decision) ────────
    graph.add_conditional_edges(
        "evaluation",
        supervisor,
        {
            "synthesis": "synthesis",
            "retry": "retry_prep",
            "force_synthesis": "force_synthesis_prep",
        },
    )

    # ── Retry loops back to discovery ─────────────────────────────────
    graph.add_edge("retry_prep", "discovery")

    # ── Force synthesis → synthesis ───────────────────────────────────
    graph.add_edge("force_synthesis_prep", "synthesis")

    # ── Synthesis → END ───────────────────────────────────────────────
    graph.add_edge("synthesis", END)

    # ── Entry point ───────────────────────────────────────────────────
    graph.set_entry_point("discovery")

    # ── Compile ───────────────────────────────────────────────────────
    compiled = graph.compile()
    logger.info("Oracle graph compiled successfully")

    return compiled
