"""Configuration for the LangGraph multi-agent workflow."""

import os

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))

# Review Configuration
REVIEW_PASS_THRESHOLD = float(os.getenv("REVIEW_PASS_THRESHOLD", "7.0"))

# Revision Guardrail
MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "3"))

# Checkpoint Configuration
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "./data/checkpoints.db")

# Error Handler Configuration
MAX_CONSECUTIVE_ERRORS = int(os.getenv("MAX_CONSECUTIVE_ERRORS", "3"))
