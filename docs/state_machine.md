# State Machine

## Status Values

The workflow uses the following status values:

- `RECEIVED`
- `PLANNED`
- `DRAFTED`
- `REVIEW_PASSED`
- `REVIEW_FAILED`
- `WAITING_HUMAN`
- `APPROVED`
- `REJECTED`
- `FINALIZED`
- `FAILED`

## Transition Rules

```text
START
  |
  v
supervisor
  | \
  |  \ error
  |   v
  | error_handler -- recoverable --> supervisor
  |                 non-recoverable --> FAILED
  v
worker
  | \
  |  \ error
  |   v
  | error_handler
  v
reviewer
  | \
  |  \ fail + revisions remaining --> worker
  |   \
  |    fail + limit reached -------> human_approval
  v
human_approval
  | \
  |  \ reject --> supervisor
  |              |
  |              +-- increments revision_count
  v
finalize
  |
  v
FINALIZED
```

## Guardrails

- Reviewer failures increment `revision_count`.
- Recoverable worker or reviewer failures increment `revision_count` in `error_handler`.
- Human rejection also increments `revision_count`.
- Once `revision_count >= max_revisions`, the workflow stops looping and converges to `FAILED` or an explicit human decision path.

## Observability

Every successful or failed node appends an `execution_log` entry:

```python
{
    "node": "reviewer",
    "input_summary": "Draft preview...",
    "output_summary": "fail (score=4.0/10): Missing concrete examples",
    "duration_ms": 842,
}
```

That log is persisted in checkpointed state, so resumed runs keep their earlier history.

