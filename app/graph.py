"""Graph assembly for the LangGraph multi-agent workflow."""

import logging

from app.checkpoint import get_checkpointer
from app.nodes.supervisor import supervisor_node
from app.nodes.worker import worker_node
from app.nodes.reviewer import reviewer_node
from app.nodes.human_approval import human_approval_node
from app.nodes.error_handler import error_handler_node
from app.nodes.finalize import finalize_node
from app.routing import (
    route_after_supervisor,
    route_after_worker,
    route_after_reviewer,
    route_after_human_approval,
    route_after_error_handler,
)
from app.state import WorkflowState

logger = logging.getLogger(__name__)

_compiled_graph = None


def build_graph():
    """Build the multi-agent workflow graph.

    Graph structure:
        START -> supervisor -> worker -> reviewer -> human_approval -> finalize -> END
                                  |          |            |
                                  v          v            v
                          error_handler   worker      supervisor
                          (loop back or    (revision   (re-plan on
                           FAIL)          loop)       rejection)
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "Graph execution requires langgraph. "
            "Install dependencies with `pip install -r requirements.txt`."
        ) from exc

    graph = StateGraph(WorkflowState)

    # Add all nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("worker", worker_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("error_handler", error_handler_node)
    graph.add_node("finalize", finalize_node)

    # Set entry point
    graph.set_entry_point("supervisor")

    # supervisor -> worker or error_handler
    graph.add_conditional_edges("supervisor", route_after_supervisor, {
        "worker": "worker",
        "error_handler": "error_handler",
    })

    # worker -> reviewer (success) or error_handler (failure)
    graph.add_conditional_edges("worker", route_after_worker, {
        "reviewer": "reviewer",
        "error_handler": "error_handler",
    })

    # reviewer -> human_approval (pass) or worker (revision) or human_approval (limit reached)
    graph.add_conditional_edges("reviewer", route_after_reviewer, {
        "human_approval": "human_approval",
        "worker": "worker",
    })

    # human_approval -> finalize (approve) or supervisor (reject, re-plan)
    graph.add_conditional_edges("human_approval", route_after_human_approval, {
        "finalize": "finalize",
        "supervisor": "supervisor",
        "END": END,
    })

    # error_handler -> supervisor (recoverable) or END (non-recoverable)
    graph.add_conditional_edges("error_handler", route_after_error_handler, {
        "supervisor": "supervisor",
        "END": END,
    })

    # finalize -> END
    graph.add_edge("finalize", END)

    return graph


def compile_graph(checkpointer=None):
    """Build and compile the graph with optional checkpointing.

    Args:
        checkpointer: Optional LangGraph checkpointer for persistence.

    Returns:
        Compiled graph ready for execution.
    """
    graph = build_graph()
    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Graph compiled with checkpointer=%s", type(checkpointer).__name__ if checkpointer else "None")
    return compiled


def get_graph(use_checkpoint: bool = True):
    """Return a compiled graph, cached when checkpointing is enabled."""
    global _compiled_graph
    if not use_checkpoint:
        return compile_graph(checkpointer=None)

    if _compiled_graph is None:
        _compiled_graph = compile_graph(checkpointer=get_checkpointer())
    return _compiled_graph


def thread_config(thread_id: str) -> dict:
    """Build the LangGraph config for a checkpoint thread."""
    return {"configurable": {"thread_id": thread_id}}
