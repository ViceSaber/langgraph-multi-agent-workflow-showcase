"""CLI entrypoint for the LangGraph multi-agent workflow showcase."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from app.graph import get_graph, thread_config
from app.state import create_initial_state
from app.utils import format_execution_log, print_state_summary

logger = logging.getLogger(__name__)


def load_environment() -> None:
    """Load a local .env file when python-dotenv is available."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="LangGraph multi-agent workflow showcase",
    )
    parser.add_argument("--input", help="Path to a text file with the user request.")
    parser.add_argument("--request", help="Inline user request text.")
    parser.add_argument("--resume", help="Resume an existing thread id from checkpoint.")
    parser.add_argument(
        "--decision",
        choices=["approve", "reject"],
        help="Human decision to submit when resuming or auto-resuming an interrupted run.",
    )
    parser.add_argument("--reason", default="", help="Reason for a human rejection.")
    parser.add_argument("--thread-id", help="Optional thread/task id for a new run.")
    parser.add_argument("--max-revisions", type=int, default=3, help="Revision guardrail for a new run.")
    parser.add_argument("--quiet", action="store_true", help="Reduce console output.")
    return parser.parse_args()


def configure_logging(quiet: bool) -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.WARNING if quiet else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def read_request(args: argparse.Namespace) -> str:
    """Load the user request from --request or --input."""
    if args.request:
        return args.request.strip()
    if args.input:
        return Path(args.input).read_text(encoding="utf-8").strip()
    raise ValueError("Provide either --request or --input for a new run.")


def get_snapshot_state(graph: Any, config: dict) -> dict:
    """Return the current checkpointed state values for a thread."""
    snapshot = graph.get_state(config)
    values = getattr(snapshot, "values", None) or {}
    return dict(values)


def get_interrupt_payload(result: Any, graph: Any, config: dict) -> Any | None:
    """Extract a human-approval interrupt payload from the latest run."""
    if isinstance(result, dict) and "__interrupt__" in result and result["__interrupt__"]:
        interrupt_obj = result["__interrupt__"][0]
        return getattr(interrupt_obj, "value", interrupt_obj)

    snapshot = graph.get_state(config)
    for task in getattr(snapshot, "tasks", []) or []:
        for interrupt_obj in getattr(task, "interrupts", []) or []:
            return getattr(interrupt_obj, "value", interrupt_obj)
    return None


def print_interrupt_help(thread_id: str, payload: Any) -> None:
    """Print the pending human-approval payload and resume instructions."""
    print(f"Thread paused for human approval: {thread_id}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("")
    print(f"Resume with approval: python3 main.py --resume {thread_id} --decision approve")
    print(
        "Resume with rejection: "
        f'python3 main.py --resume {thread_id} --decision reject --reason "Need a different approach"'
    )


def print_final_state(thread_id: str, state: dict) -> None:
    """Print the final state summary and execution log."""
    print(f"Thread completed: {thread_id}")
    print_state_summary(state)
    print("Execution Log:")
    print(format_execution_log(state.get("execution_log", [])))


def build_resume_payload(args: argparse.Namespace) -> dict[str, str]:
    """Build the resume payload consumed by the human approval node."""
    payload = {"decision": args.decision}
    if args.reason:
        payload["reason"] = args.reason
    return payload


def start_run(args: argparse.Namespace) -> int:
    """Start a new workflow run."""
    user_request = read_request(args)
    state = create_initial_state(
        user_request=user_request,
        task_id=args.thread_id or "",
        max_revisions=args.max_revisions,
    )
    graph = get_graph(use_checkpoint=True)
    config = thread_config(state["task_id"])

    result = graph.invoke(state, config=config)
    interrupt_payload = get_interrupt_payload(result, graph, config)

    if interrupt_payload is not None and args.decision:
        try:
            from langgraph.types import Command
        except ImportError as exc:
            raise RuntimeError(
                "Resuming an interrupt requires langgraph. Install dependencies first."
            ) from exc
        result = graph.invoke(Command(resume=build_resume_payload(args)), config=config)
        interrupt_payload = get_interrupt_payload(result, graph, config)

    latest_state = get_snapshot_state(graph, config)
    if interrupt_payload is not None:
        print_interrupt_help(state["task_id"], interrupt_payload)
        if latest_state:
            print_state_summary(latest_state)
        return 0

    final_state = latest_state or dict(result)
    print_final_state(state["task_id"], final_state)
    return 0


def resume_run(args: argparse.Namespace) -> int:
    """Resume or inspect an existing workflow thread."""
    graph = get_graph(use_checkpoint=True)
    config = thread_config(args.resume)

    try:
        current_state = get_snapshot_state(graph, config)
    except Exception as exc:
        raise RuntimeError(f"Unable to load checkpoint for thread {args.resume}: {exc}") from exc

    if not current_state:
        raise RuntimeError(f"No checkpointed state found for thread {args.resume}.")

    if not args.decision:
        print(f"Current checkpoint state for thread {args.resume}:")
        print_state_summary(current_state)
        print("Execution Log:")
        print(format_execution_log(current_state.get("execution_log", [])))
        print("")
        print(f"Resume with approval: python3 main.py --resume {args.resume} --decision approve")
        print(
            "Resume with rejection: "
            f'python3 main.py --resume {args.resume} --decision reject --reason "Need a different approach"'
        )
        return 0

    try:
        from langgraph.types import Command
    except ImportError as exc:
        raise RuntimeError(
            "Resuming an interrupt requires langgraph. Install dependencies first."
        ) from exc

    result = graph.invoke(Command(resume=build_resume_payload(args)), config=config)
    interrupt_payload = get_interrupt_payload(result, graph, config)
    latest_state = get_snapshot_state(graph, config)

    if interrupt_payload is not None:
        print_interrupt_help(args.resume, interrupt_payload)
        if latest_state:
            print_state_summary(latest_state)
        return 0

    final_state = latest_state or dict(result)
    print_final_state(args.resume, final_state)
    return 0


def main() -> int:
    """Run the CLI."""
    load_environment()
    args = parse_args()
    configure_logging(args.quiet)

    try:
        if args.resume:
            return resume_run(args)
        return start_run(args)
    except Exception as exc:
        logger.exception("Workflow execution failed")
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

