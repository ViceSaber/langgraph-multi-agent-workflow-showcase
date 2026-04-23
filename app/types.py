"""Shared type definitions for the workflow."""

from typing import Literal, Optional, TypedDict


class ReviewResult(TypedDict, total=False):
    """Structured output from the reviewer node."""

    decision: Literal["pass", "fail"]
    score: float  # 1-10
    issues: list[str]
    summary: str
    completeness: float
    format: float
    actionability: float


class ExecutionLogEntry(TypedDict):
    """Single entry in the execution log."""

    node: str
    input_summary: str
    output_summary: str
    duration_ms: int


class ErrorClassification(TypedDict):
    """Result of error classification."""

    recoverable: bool
    reason: str
