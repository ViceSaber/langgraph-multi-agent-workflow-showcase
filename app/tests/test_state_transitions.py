"""State transition tests for the node implementations."""

from app.nodes.finalize import finalize_node
from app.nodes.human_approval import human_approval_node
from app.nodes.supervisor import supervisor_node
from app.nodes.worker import worker_node
from app.state import create_initial_state


def test_supervisor_worker_finalize_path(monkeypatch) -> None:
    monkeypatch.setattr("app.nodes.supervisor.call_llm", lambda prompt, system="": "1. Define goals\n2. Draft output")
    monkeypatch.setattr("app.nodes.worker.call_llm", lambda prompt, system="": "Draft body with clear sections.")
    monkeypatch.setattr("app.nodes.finalize.call_llm", lambda prompt, system="": "Delivery Summary\n\nDraft body with clear sections.")

    state = create_initial_state("Create a rollout plan.", task_id="happy-path")

    supervisor_result = supervisor_node(state)
    worker_result = worker_node({**state, **supervisor_result})
    approval_result = human_approval_node({**state, **supervisor_result, **worker_result, "human_decision": "approve"})
    finalize_result = finalize_node({**state, **supervisor_result, **worker_result, **approval_result})

    assert supervisor_result["status"] == "PLANNED"
    assert worker_result["status"] == "DRAFTED"
    assert approval_result["status"] == "APPROVED"
    assert finalize_result["status"] == "FINALIZED"
    assert "Delivery Summary" in finalize_result["final_output"]


def test_human_rejection_increments_revision_count() -> None:
    state = create_initial_state("Prepare a stakeholder update.", task_id="human-reject", max_revisions=3)
    state["draft"] = "Technical draft."
    state["review_score"] = 8.0
    state["review_feedback"] = "Looks good."
    state["revision_count"] = 1
    state["human_decision"] = "reject"
    state["human_rejection_reason"] = "Too technical for executives"

    result = human_approval_node(state)

    assert result["status"] == "REJECTED"
    assert result["revision_count"] == 2
    assert result["human_rejection_reason"] == "Too technical for executives"


def test_human_rejection_can_hit_guardrail() -> None:
    state = create_initial_state("Prepare a stakeholder update.", task_id="human-guardrail", max_revisions=2)
    state["draft"] = "Technical draft."
    state["review_score"] = 8.0
    state["review_feedback"] = "Looks good."
    state["revision_count"] = 1
    state["human_decision"] = "reject"
    state["human_rejection_reason"] = "Still too technical"

    result = human_approval_node(state)

    assert result["status"] == "FAILED"
    assert result["revision_count"] == 2
    assert "guardrail" in result["error_info"]


def test_worker_simulated_timeout_routes_into_error_path() -> None:
    monkeypatch_state = create_initial_state(
        "SIMULATE_WORKER_TIMEOUT Create a launch checklist.",
        task_id="worker-timeout",
        max_revisions=3,
    )
    monkeypatch_state["plan"] = "1. Draft the checklist"

    result = worker_node(monkeypatch_state)

    assert result["status"] == "FAILED"
    assert "TimeoutError" in result["error_info"]

