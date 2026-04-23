# Architecture

## Goal

This project packages a focused multi-agent workflow around one central LangGraph state object. The emphasis is on orchestration and lifecycle control, not on tool breadth.

## Runtime Components

- [main.py](/Users/sakura/projects/langgraph-multi-agent-workflow-showcase/main.py): CLI entrypoint for new runs and resume flows
- [app/graph.py](/Users/sakura/projects/langgraph-multi-agent-workflow-showcase/app/graph.py): builds and compiles the LangGraph workflow
- [app/state.py](/Users/sakura/projects/langgraph-multi-agent-workflow-showcase/app/state.py): defines the shared `WorkflowState`
- [app/models.py](/Users/sakura/projects/langgraph-multi-agent-workflow-showcase/app/models.py): wraps `langchain_openai.ChatOpenAI`
- [app/checkpoint.py](/Users/sakura/projects/langgraph-multi-agent-workflow-showcase/app/checkpoint.py): configures SQLite checkpoint persistence
- [app/routing.py](/Users/sakura/projects/langgraph-multi-agent-workflow-showcase/app/routing.py): all conditional edge decisions
- [app/nodes/](/Users/sakura/projects/langgraph-multi-agent-workflow-showcase/app/nodes): node implementations

## Node Responsibilities

### `supervisor`

- reads `user_request`
- creates a concise execution `plan`
- re-plans when `human_rejection_reason` exists

### `worker`

- produces the initial `draft`
- revises the draft when reviewer feedback exists
- can intentionally simulate a timeout for the error-recovery demo

### `reviewer`

- scores completeness, format, and actionability
- writes `review_score` and `review_feedback`
- increments `revision_count` on failure

### `human_approval`

- pauses execution through LangGraph `interrupt()`
- accepts `approve` or `reject`
- stores `human_rejection_reason`
- returns to `supervisor` on rejection unless the guardrail is exhausted

### `error_handler`

- classifies failures as recoverable or non-recoverable
- clears `error_info` and routes back to `supervisor` for recoverable cases
- moves the workflow to `FAILED` for terminal cases

### `finalize`

- polishes the approved draft into `final_output`
- writes the `FINALIZED` terminal state

## Persistence

Checkpoint persistence uses SQLite through LangGraph's `SqliteSaver`. Each run is isolated by `thread_id`, which is also exposed in the CLI so a paused run can be resumed later.

The checkpoint database lives at `data/checkpoints.db` by default and is ignored in git.

