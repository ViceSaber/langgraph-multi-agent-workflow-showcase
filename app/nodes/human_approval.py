"""Human approval node: interrupts for human decision."""

import logging
import time
from typing import Any

from app.utils import log_execution, truncate

logger = logging.getLogger(__name__)


def human_approval_node(state: dict) -> dict:
    """Pause execution and wait for human approval or rejection.

    Uses LangGraph's interrupt() to pause the graph. On resume,
    the human's decision (approve/reject) and optional rejection
    reason are provided via the resume payload.

    The interrupt payload includes context for the human:
    - The draft
    - Review score and feedback
    - Revision count

    Resume payload format:
        {"decision": "approve"} or
        {"decision": "reject", "reason": "..."}
    """
    start = time.time()

    draft = state.get("draft", "")
    review_feedback = state.get("review_feedback", "")
    review_score = state.get("review_score", 0)
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 3)

    # Build context for the human reviewer
    context = {
        "message": "Human approval required. Please review the draft and decide.",
        "draft_preview": truncate(draft, 500),
        "review_score": review_score,
        "review_feedback": review_feedback,
        "revision_count": revision_count,
        "max_revisions": max_revisions,
    }

    if revision_count >= max_revisions:
        context["message"] = (
            "Revision limit reached. Please review the current draft "
            "and decide whether to accept it or terminate."
        )

    logger.info(
        "Human approval interrupt for task %s (score=%.1f, revision=%d/%d)",
        state.get("task_id", "unknown"), review_score, revision_count, max_revisions,
    )

    human_response: Any
    if state.get("human_decision") in {"approve", "reject"}:
        human_response = {
            "decision": state.get("human_decision"),
            "reason": state.get("human_rejection_reason") or "",
        }
    else:
        try:
            from langgraph.types import interrupt
        except ImportError as exc:
            raise RuntimeError(
                "Human approval interrupts require langgraph. "
                "Install dependencies with `pip install -r requirements.txt`."
            ) from exc

        human_response = interrupt(context)

    # Process human response
    if isinstance(human_response, str):
        human_response = {"decision": human_response}

    decision = str(human_response.get("decision", "reject")).lower()
    rejection_reason = human_response.get("reason", "") or ""

    if decision == "approve":
        new_status = "APPROVED"
        rejection_reason = None
        new_revision_count = revision_count
    else:
        decision = "reject"
        new_status = "REJECTED"
        if not rejection_reason:
            rejection_reason = "No reason provided by human reviewer."
        new_revision_count = revision_count + 1
        if new_revision_count >= max_revisions:
            new_status = "FAILED"

    log_update = log_execution(
        state,
        node="human_approval",
        input_summary=f"Score: {review_score}/10, Revision: {revision_count}/{max_revisions}",
        output_summary=f"Decision: {decision}"
        + (f" | Reason: {truncate(rejection_reason or '', 100)}" if rejection_reason else ""),
        start_time=start,
    )

    return {
        "status": new_status,
        "human_decision": decision,
        "human_rejection_reason": rejection_reason,
        "revision_count": new_revision_count,
        "error_info": (
            "Human rejected the draft after revision guardrail was reached."
            if new_status == "FAILED"
            else state.get("error_info")
        ),
        "execution_log": log_update["execution_log"],
    }
