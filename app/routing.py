"""Routing functions for conditional edges in the workflow graph.

Each routing function examines the current state and returns the
name of the next node to execute.
"""

import logging

logger = logging.getLogger(__name__)


def route_after_supervisor(state: dict) -> str:
    """Route supervisor errors to the error handler, otherwise to worker."""
    if state.get("error_info"):
        logger.info("Routing supervisor -> error_handler (error detected)")
        return "error_handler"
    return "worker"


def route_after_worker(state: dict) -> str:
    """Determine the next node after worker completes.

    If an error occurred during worker execution, route to error_handler.
    Otherwise, route to reviewer.
    """
    if state.get("error_info"):
        logger.info("Routing worker -> error_handler (error detected)")
        return "error_handler"
    return "reviewer"


def route_after_reviewer(state: dict) -> str:
    """Determine the next node after reviewer completes.

    - REVIEW_PASSED -> human_approval
    - REVIEW_FAILED + revisions remaining -> worker (revision loop)
    - REVIEW_FAILED + no revisions remaining -> human_approval (escalate to human)
    """
    if state.get("error_info"):
        logger.info("Routing reviewer -> error_handler (error detected)")
        return "error_handler"

    status = state.get("status", "")
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 3)

    if status == "REVIEW_PASSED":
        logger.info("Routing reviewer -> human_approval (review passed)")
        return "human_approval"

    if status == "REVIEW_FAILED" and revision_count < max_revisions:
        logger.info(
            "Routing reviewer -> worker (revision %d/%d)",
            revision_count,
            max_revisions,
        )
        return "worker"

    logger.info(
        "Routing reviewer -> human_approval (revision limit reached or manual review needed: %d/%d)",
        revision_count,
        max_revisions,
    )
    return "human_approval"


def route_after_human_approval(state: dict) -> str:
    """Determine the next node after human approval/rejection.

    - APPROVED -> finalize
    - REJECTED -> supervisor (re-plan with rejection reason)
    """
    status = state.get("status", "")

    if status == "FAILED":
        logger.info("Routing human_approval -> END (rejection limit reached)")
        return "END"

    if status == "APPROVED":
        logger.info("Routing human_approval -> finalize (approved)")
        return "finalize"
    elif status == "REJECTED":
        logger.info("Routing human_approval -> supervisor (rejected, re-planning)")
        if state.get("revision_count", 0) >= state.get("max_revisions", 3):
            logger.info("Routing human_approval -> END (revision guardrail reached)")
            return "END"
        return "supervisor"

    logger.warning("Unexpected status after human_approval: %s", status)
    return "END"


def route_after_error_handler(state: dict) -> str:
    """Determine the next node after error handler.

    - RECEIVED (recoverable) -> supervisor (re-plan)
    - FAILED (non-recoverable) -> END
    """
    status = state.get("status", "")

    if status == "FAILED":
        logger.info("Routing error_handler -> END (non-recoverable)")
        return "END"
    else:
        logger.info("Routing error_handler -> supervisor (recoverable)")
        return "supervisor"


def route_after_finalize(state: dict) -> str:
    """After finalize, always go to END."""
    return "END"
