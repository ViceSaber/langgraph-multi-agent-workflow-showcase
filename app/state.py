"""Workflow state definition for the LangGraph multi-agent workflow."""

import uuid
from typing import List, Literal, Optional, TypedDict

from app.config import MAX_REVISIONS


class WorkflowState(TypedDict, total=False):
    """Core state object for the multi-agent workflow.

    Tracks the full lifecycle of a task from request to finalization,
    including review scores, revision counts, human decisions, and
    execution logs for observability.
    """

    task_id: str
    user_request: str
    plan: str
    draft: str
    review_feedback: str
    review_score: float  # 1-10 quantified score; below threshold triggers revision
    final_output: str
    status: Literal[
        "RECEIVED",
        "PLANNED",
        "DRAFTED",
        "REVIEW_PASSED",
        "REVIEW_FAILED",
        "WAITING_HUMAN",
        "APPROVED",
        "REJECTED",
        "FINALIZED",
        "FAILED",
    ]
    revision_count: int
    max_revisions: int
    human_decision: Optional[Literal["approve", "reject"]]
    human_rejection_reason: Optional[str]  # Used by supervisor for re-planning
    execution_log: List[dict]  # {node, input_summary, output_summary, duration_ms}
    error_info: Optional[str]  # Error details when a node fails


def create_initial_state(
    user_request: str,
    task_id: str = "",
    max_revisions: int = MAX_REVISIONS,
) -> WorkflowState:
    """Create an initial workflow state from a user request."""
    return WorkflowState(
        task_id=task_id or str(uuid.uuid4()),
        user_request=user_request,
        plan="",
        draft="",
        review_feedback="",
        review_score=0.0,
        final_output="",
        status="RECEIVED",
        revision_count=0,
        max_revisions=max_revisions,
        human_decision=None,
        human_rejection_reason=None,
        execution_log=[],
        error_info=None,
    )
