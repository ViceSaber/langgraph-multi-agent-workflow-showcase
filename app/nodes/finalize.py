"""Finalize node: produces the final polished output."""

import time
import logging

from app.models import call_llm
from app.prompts import finalize_prompt
from app.utils import log_execution, truncate

logger = logging.getLogger(__name__)


def finalize_node(state: dict) -> dict:
    """Polish the approved draft into the final output.

    Takes the approved draft and produces a clean, well-formatted
    final output ready for delivery.
    """
    start = time.time()

    user_request = state["user_request"]
    plan = state["plan"]
    draft = state["draft"]
    review_feedback = state.get("review_feedback", "")
    review_score = state.get("review_score", 0)

    system, user = finalize_prompt(user_request, plan, draft, review_feedback, review_score)

    logger.info("Finalizing output for task %s", state.get("task_id", "unknown"))
    try:
        final_output = call_llm(user, system=system)
    except Exception as exc:
        from app.utils import error_update

        logger.exception("Finalize failed")
        return error_update(state, "finalize", exc, start)

    log_update = log_execution(
        state,
        node="finalize",
        input_summary=truncate(draft, 150),
        output_summary=truncate(final_output, 150),
        start_time=start,
    )

    return {
        "final_output": final_output,
        "status": "FINALIZED",
        "error_info": None,
        "execution_log": log_update["execution_log"],
    }
