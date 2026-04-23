"""Error handler node: classifies and routes errors."""

import logging
import time

from app.utils import log_execution, truncate

logger = logging.getLogger(__name__)


def error_handler_node(state: dict) -> dict:
    """Classify an error and decide whether to recover or fail.

    Recoverable errors route back to supervisor for re-planning.
    Non-recoverable errors set status to FAILED.

    The classification uses deterministic keyword matching so error recovery
    does not depend on another model call.
    """
    start = time.time()

    error_info = state.get("error_info", "Unknown error")
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 3)

    non_recoverable_keywords = [
        "invalid api key",
        "authentication",
        "unauthorized",
        "permission denied",
        "auth",
        "prompt injection",
        "inappropriate content",
        "content policy",
        "configuration",
        "missing api key",
        "no module named",
    ]
    recoverable_keywords = [
        "timeout",
        "rate limit",
        "too many requests",
        "json",
        "parse",
        "connection",
        "network",
        "temporary",
        "transient",
        "500",
        "502",
        "503",
        "504",
    ]

    error_lower = error_info.lower()
    recoverable = None

    for kw in non_recoverable_keywords:
        if kw in error_lower:
            recoverable = False
            break

    if recoverable is None:
        for kw in recoverable_keywords:
            if kw in error_lower:
                recoverable = True
                break

    if recoverable is None:
        recoverable = False

    # Check if we've exceeded revision limit even for recoverable errors
    if recoverable and revision_count >= max_revisions:
        logger.warning(
            "Error is recoverable but revision limit reached (%d/%d)",
            revision_count, max_revisions,
        )
        recoverable = False

    if recoverable:
        new_status = "RECEIVED"
        new_revision_count = revision_count + 1
        new_error_info = None
        decision_summary = "Recoverable - routing to supervisor for re-planning"
    else:
        new_status = "FAILED"
        new_revision_count = revision_count
        decision_summary = "Non-recoverable - setting FAILED status"

    log_update = log_execution(
        state,
        node="error_handler",
        input_summary=truncate(error_info, 200),
        output_summary=decision_summary,
        start_time=start,
    )

    logger.info("Error classified: %s (%s)", "recoverable" if recoverable else "non-recoverable", decision_summary)

    return {
        "status": new_status,
        "revision_count": new_revision_count,
        "error_info": new_error_info if recoverable else error_info,
        "execution_log": log_update["execution_log"],
    }
