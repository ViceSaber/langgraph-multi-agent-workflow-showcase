"""Supervisor node: analyzes user request and creates an execution plan."""

import time
import logging

from app.models import call_llm
from app.prompts import supervisor_prompt
from app.utils import log_execution, truncate

logger = logging.getLogger(__name__)


def supervisor_node(state: dict) -> dict:
    """Analyze the user request and generate an execution plan.

    If human_rejection_reason is present, the supervisor re-plans
    using the rejection feedback to produce a different approach.
    """
    start = time.time()

    user_request = state["user_request"]
    existing_plan = state.get("plan", "")
    rejection_reason = state.get("human_rejection_reason", "")

    system, user = supervisor_prompt(
        user_request=user_request,
        plan=existing_plan,
        human_rejection_reason=rejection_reason,
    )

    logger.info("Supervisor planning for task %s", state.get("task_id", "unknown"))
    try:
        plan = call_llm(user, system=system)
    except Exception as exc:
        from app.utils import error_update

        logger.exception("Supervisor failed")
        return error_update(state, "supervisor", exc, start)

    log_update = log_execution(
        state,
        node="supervisor",
        input_summary=truncate(user_request, 200),
        output_summary=truncate(plan, 200),
        start_time=start,
    )

    return {
        "plan": plan,
        "status": "PLANNED",
        "human_decision": None,
        "review_feedback": "",
        "review_score": 0.0,
        "error_info": None,
        "execution_log": log_update["execution_log"],
    }
