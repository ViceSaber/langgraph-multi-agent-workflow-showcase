"""Utility functions for the workflow."""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def truncate(text: Any, max_len: int = 100) -> str:
    """Truncate text for display in execution logs."""
    text = "" if text is None else str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def error_update(state: dict, node: str, exc: Exception, start_time: float) -> dict:
    """Build a standard node error update for the error handler path."""
    error_info = f"{node}: {type(exc).__name__}: {exc}"
    log_update = log_execution(
        state,
        node=node,
        input_summary="node execution",
        output_summary=f"error: {truncate(error_info, 180)}",
        start_time=start_time,
    )
    return {
        "status": "FAILED",
        "error_info": error_info,
        "execution_log": log_update["execution_log"],
    }


def log_execution(state: dict, node: str, input_summary: str, output_summary: str, start_time: float) -> dict:
    """Record an execution log entry into the workflow state.

    Returns an update dict with the appended execution_log.
    """
    duration_ms = int((time.time() - start_time) * 1000)
    entry = {
        "node": node,
        "input_summary": truncate(input_summary, 200),
        "output_summary": truncate(output_summary, 200),
        "duration_ms": duration_ms,
    }

    log = list(state.get("execution_log", []))
    log.append(entry)

    logger.info(
        "[%s] completed in %dms | input: %s | output: %s",
        node, duration_ms, truncate(input_summary, 60), truncate(output_summary, 60),
    )

    return {"execution_log": log}


def format_execution_log(log: list[dict]) -> str:
    """Format the execution log for display."""
    if not log:
        return "No execution log entries."

    lines = []
    total_ms = 0
    for i, entry in enumerate(log, 1):
        lines.append(
            f"  {i}. [{entry['node']}] {entry['duration_ms']}ms\n"
            f"     Input:  {entry['input_summary']}\n"
            f"     Output: {entry['output_summary']}"
        )
        total_ms += entry.get("duration_ms", 0)

    lines.append(f"\n  Total: {total_ms}ms ({len(log)} steps)")
    return "\n".join(lines)


def print_state_summary(state: dict) -> None:
    """Print a human-readable summary of the current workflow state."""
    print(f"\n{'='*60}")
    print(f"  Task: {state.get('task_id', 'N/A')}")
    print(f"  Status: {state.get('status', 'N/A')}")
    print(f"  Revision: {state.get('revision_count', 0)}/{state.get('max_revisions', 3)}")

    if state.get("plan"):
        print(f"\n  Plan:\n  {truncate(state['plan'], 200)}")

    if state.get("draft"):
        print(f"\n  Draft:\n  {truncate(state['draft'], 200)}")

    if state.get("review_score", 0) > 0:
        print(f"\n  Review Score: {state['review_score']}/10")
        if state.get("review_feedback"):
            print(f"  Review: {truncate(state['review_feedback'], 150)}")

    if state.get("final_output"):
        print(f"\n  Final Output:\n  {truncate(state['final_output'], 300)}")

    if state.get("error_info"):
        print(f"\n  Error: {state['error_info']}")

    if state.get("human_rejection_reason"):
        print(f"\n  Rejection Reason: {state['human_rejection_reason']}")

    print(f"{'='*60}\n")
