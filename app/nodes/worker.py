"""Worker node: generates or revises a draft based on the plan."""

import time
import logging

from app.models import call_llm
from app.prompts import worker_prompt
from app.utils import log_execution, truncate

logger = logging.getLogger(__name__)


def worker_node(state: dict) -> dict:
    """Generate a draft based on the plan, or revise if feedback exists.

    Supports two modes:
    1. Initial generation (no review_feedback)
    2. Revision based on reviewer feedback (review_feedback present)
    """
    start = time.time()

    user_request = state["user_request"]
    plan = state["plan"]
    review_feedback = state.get("review_feedback", "")
    revision_count = state.get("revision_count", 0)

    system, user = worker_prompt(
        user_request=user_request,
        plan=plan,
        review_feedback=review_feedback,
        revision_number=revision_count,
    )

    mode = "revision" if review_feedback and revision_count > 0 else "initial"
    logger.info(
        "Worker generating draft (%s mode) for task %s",
        mode, state.get("task_id", "unknown"),
    )
    try:
        if "SIMULATE_WORKER_TIMEOUT" in user_request and revision_count == 0:
            raise TimeoutError("simulated worker timeout for error recovery demo")
        draft = call_llm(user, system=system)
    except Exception as exc:
        from app.utils import error_update

        logger.exception("Worker failed")
        return error_update(state, "worker", exc, start)

    log_update = log_execution(
        state,
        node=f"worker ({mode})",
        input_summary=truncate(f"Plan: {plan}", 200),
        output_summary=truncate(draft, 200),
        start_time=start,
    )

    return {
        "draft": draft,
        "status": "DRAFTED",
        "error_info": None,
        "execution_log": log_update["execution_log"],
    }
