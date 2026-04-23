"""Tests covering quantified review and revision loop behavior."""

from app.nodes.error_handler import error_handler_node
from app.nodes.reviewer import reviewer_node
from app.routing import route_after_reviewer
from app.state import create_initial_state


def _draft_state() -> dict:
    state = create_initial_state(
        "Write a structured onboarding guide for backend engineers.",
        task_id="review-loop",
        max_revisions=3,
    )
    state["plan"] = "1. Explain the onboarding goals\n2. Include concrete examples"
    state["draft"] = "A short and generic guide."
    state["status"] = "DRAFTED"
    return state


def test_reviewer_fail_increments_revision_count(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.nodes.reviewer.call_llm_json",
        lambda prompt, system="": {
            "decision": "fail",
            "score": 4,
            "issues": ["Missing examples", "Not structured as requested"],
            "summary": "Revise the draft before finalization.",
        },
    )

    result = reviewer_node(_draft_state())

    assert result["status"] == "REVIEW_FAILED"
    assert result["review_score"] == 4.0
    assert result["revision_count"] == 1
    assert "Missing examples" in result["review_feedback"]
    assert route_after_reviewer({**_draft_state(), **result}) == "worker"


def test_reviewer_pass_routes_to_human_approval(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.nodes.reviewer.call_llm_json",
        lambda prompt, system="": {
            "decision": "pass",
            "score": 8,
            "issues": [],
            "summary": "Draft is acceptable and can proceed to human approval.",
        },
    )

    result = reviewer_node(_draft_state())

    assert result["status"] == "REVIEW_PASSED"
    assert result["revision_count"] == 0
    assert route_after_reviewer({**_draft_state(), **result}) == "human_approval"


def test_error_handler_recovers_timeout_errors() -> None:
    state = create_initial_state("Test recoverable error", task_id="recoverable")
    state["error_info"] = "worker: TimeoutError: simulated worker timeout"
    state["revision_count"] = 0
    state["max_revisions"] = 3

    result = error_handler_node(state)

    assert result["status"] == "RECEIVED"
    assert result["revision_count"] == 1
    assert result["error_info"] is None


def test_error_handler_fails_for_auth_errors() -> None:
    state = create_initial_state("Test auth error", task_id="nonrecoverable")
    state["error_info"] = "worker: AuthenticationError: invalid api key"
    state["revision_count"] = 0
    state["max_revisions"] = 3

    result = error_handler_node(state)

    assert result["status"] == "FAILED"
    assert "invalid api key" in result["error_info"]

