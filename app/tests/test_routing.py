"""Routing tests for the workflow graph."""

from app.routing import (
    route_after_error_handler,
    route_after_human_approval,
    route_after_reviewer,
    route_after_supervisor,
    route_after_worker,
)


def test_route_after_supervisor_uses_error_handler_on_error() -> None:
    assert route_after_supervisor({"error_info": "supervisor failed"}) == "error_handler"


def test_route_after_worker_routes_success_to_reviewer() -> None:
    assert route_after_worker({"status": "DRAFTED", "error_info": None}) == "reviewer"


def test_route_after_worker_routes_error_to_error_handler() -> None:
    assert route_after_worker({"error_info": "worker: TimeoutError"}) == "error_handler"


def test_route_after_reviewer_routes_pass_to_human() -> None:
    state = {"status": "REVIEW_PASSED", "revision_count": 0, "max_revisions": 3}
    assert route_after_reviewer(state) == "human_approval"


def test_route_after_reviewer_routes_fail_to_worker_when_budget_remains() -> None:
    state = {"status": "REVIEW_FAILED", "revision_count": 1, "max_revisions": 3}
    assert route_after_reviewer(state) == "worker"


def test_route_after_reviewer_routes_limit_to_human() -> None:
    state = {"status": "REVIEW_FAILED", "revision_count": 3, "max_revisions": 3}
    assert route_after_reviewer(state) == "human_approval"


def test_route_after_human_approval_routes_reject_to_supervisor() -> None:
    state = {"status": "REJECTED", "revision_count": 1, "max_revisions": 3}
    assert route_after_human_approval(state) == "supervisor"


def test_route_after_human_approval_routes_failed_to_end() -> None:
    state = {"status": "FAILED", "revision_count": 3, "max_revisions": 3}
    assert route_after_human_approval(state) == "END"


def test_route_after_error_handler_routes_recoverable_to_supervisor() -> None:
    assert route_after_error_handler({"status": "RECEIVED"}) == "supervisor"


def test_route_after_error_handler_routes_failed_to_end() -> None:
    assert route_after_error_handler({"status": "FAILED"}) == "END"

