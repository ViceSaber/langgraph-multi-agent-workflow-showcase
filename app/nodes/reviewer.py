"""Reviewer node: evaluates the draft with structured scoring."""

import time
import logging

from app.config import REVIEW_PASS_THRESHOLD
from app.models import call_llm_json
from app.prompts import reviewer_prompt
from app.utils import log_execution, truncate

logger = logging.getLogger(__name__)


def reviewer_node(state: dict) -> dict:
    """Review the draft and return a structured assessment.

    Scores the draft on completeness, format, and actionability.
    Pass if score >= threshold, fail otherwise.

    Returns:
        State update with review_score, review_feedback, and status.
    """
    start = time.time()

    user_request = state["user_request"]
    plan = state["plan"]
    draft = state["draft"]

    system, user = reviewer_prompt(user_request, plan, draft)

    logger.info("Reviewer evaluating draft for task %s", state.get("task_id", "unknown"))
    try:
        result = call_llm_json(user, system=system)
    except Exception as exc:
        from app.utils import error_update

        logger.exception("Reviewer failed")
        return error_update(state, "reviewer", exc, start)

    # Extract structured review result
    score = max(1.0, min(10.0, float(result.get("score", 0))))
    decision = result.get("decision", "fail")
    issues = result.get("issues", [])
    summary = result.get("summary", "")

    # Enforce threshold-based decision
    if score >= REVIEW_PASS_THRESHOLD:
        decision = "pass"
    else:
        decision = "fail"

    # Build human-readable feedback
    if issues:
        feedback = f"Score: {score}/10 | Issues: {'; '.join(issues)} | {summary}"
    else:
        feedback = f"Score: {score}/10 | {summary}"

    status = "REVIEW_PASSED" if decision == "pass" else "REVIEW_FAILED"
    revision_count = state.get("revision_count", 0)
    if status == "REVIEW_FAILED":
        revision_count += 1

    log_update = log_execution(
        state,
        node="reviewer",
        input_summary=truncate(draft, 150),
        output_summary=f"{decision} (score={score}/10): {truncate(summary, 100)}",
        start_time=start,
    )

    logger.info("Review result: %s, score=%.1f (threshold=%.1f)", decision, score, REVIEW_PASS_THRESHOLD)

    return {
        "review_score": score,
        "review_feedback": feedback,
        "status": status,
        "revision_count": revision_count,
        "error_info": None,
        "execution_log": log_update["execution_log"],
    }
