"""Checkpoint persistence using SQLite backend."""

import logging
import os
import sqlite3
from typing import Any

from app.config import CHECKPOINT_DB_PATH

logger = logging.getLogger(__name__)

_checkpointer: Any | None = None
_connection: sqlite3.Connection | None = None


def get_checkpointer() -> Any:
    """Get or create a LangGraph SQLite checkpointer.

    The import is intentionally lazy so tests that only exercise routing and
    state transitions can run before the LangGraph dependencies are installed.
    """
    global _checkpointer, _connection
    if _checkpointer is None:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ImportError as exc:
            raise RuntimeError(
                "SQLite checkpointing requires langgraph-checkpoint-sqlite. "
                "Install dependencies with `pip install -r requirements.txt`."
            ) from exc

        db_dir = os.path.dirname(CHECKPOINT_DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        _connection = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
        _checkpointer = SqliteSaver(_connection)
        logger.info("Checkpoint database initialized at %s", CHECKPOINT_DB_PATH)

    return _checkpointer
