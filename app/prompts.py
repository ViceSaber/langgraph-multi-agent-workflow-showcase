"""Prompt templates for all workflow nodes.

Each function returns a (system, user) prompt tuple for the LLM.
"""


def supervisor_prompt(user_request: str, plan: str = "", human_rejection_reason: str = "") -> tuple[str, str]:
    """Generate prompts for the supervisor node.

    If human_rejection_reason is provided, the supervisor is re-planning
    based on the rejection feedback.
    """
    system = (
        "You are a task supervisor in a multi-agent workflow. "
        "Your job is to analyze the user's request and create a concise, structured execution plan. "
        "You do NOT produce the final output - you only define what the worker should do.\n\n"
        "Your plan should:\n"
        "1. Extract the core task objective\n"
        "2. Define the expected deliverable format\n"
        "3. List specific requirements the worker must address\n"
        "4. Keep the plan concise (3-5 bullet points)\n\n"
        "Respond with the plan as plain text, no JSON."
    )

    if human_rejection_reason:
        user = (
            f"Original request: {user_request}\n\n"
            f"Previous plan (rejected by human): {plan}\n\n"
            f"Rejection reason: {human_rejection_reason}\n\n"
            "The human reviewer rejected the previous plan. "
            "Please create a DIFFERENT approach that addresses the rejection reason. "
            "Do NOT repeat the same plan."
        )
    else:
        user = (
            f"Analyze this request and create an execution plan:\n\n"
            f"{user_request}"
        )

    return system, user


def worker_prompt(
    user_request: str,
    plan: str,
    review_feedback: str = "",
    revision_number: int = 0,
) -> tuple[str, str]:
    """Generate prompts for the worker node.

    If review_feedback is provided, the worker is revising based on
    the reviewer's feedback.
    """
    system = (
        "You are a skilled worker agent in a multi-agent workflow. "
        "Your job is to produce a high-quality draft based on the execution plan.\n\n"
        "Requirements:\n"
        "- Follow the plan precisely\n"
        "- Be specific and actionable - avoid vague or generic content\n"
        "- Structure the output clearly with headers, bullet points, or numbered lists\n"
        "- Ensure completeness - address every requirement in the plan\n\n"
        "Respond with the draft as plain text."
    )

    if review_feedback and revision_number > 0:
        user = (
            f"Original request: {user_request}\n\n"
            f"Current plan: {plan}\n\n"
            f"This is revision #{revision_number}. The reviewer found issues:\n"
            f"{review_feedback}\n\n"
            "Please revise your draft to address ALL issues listed above. "
            "Do not simply repeat the previous draft - make concrete improvements."
        )
    else:
        user = (
            f"Original request: {user_request}\n\n"
            f"Execution plan:\n{plan}\n\n"
            "Please produce a complete draft based on this plan."
        )

    return system, user


def reviewer_prompt(user_request: str, plan: str, draft: str) -> tuple[str, str]:
    """Generate prompts for the reviewer node.

    The reviewer scores the draft on completeness, format, and actionability,
    then returns structured JSON with a pass/fail decision.
    """
    system = (
        "You are a quality reviewer in a multi-agent workflow. "
        "Your job is to evaluate the worker's draft against the original plan.\n\n"
        "Score the draft on these three dimensions (each 1-10):\n"
        "1. Completeness - does it cover all requirements from the plan?\n"
        "2. Format consistency - is the output well-structured and clearly formatted?\n"
        "3. Actionability - is the content specific and concrete, not vague?\n\n"
        "The final score = weighted average: completeness (40%), format (30%), actionability (30%).\n\n"
        "Respond with a JSON object with these fields:\n"
        '- "decision": "pass" or "fail"\n'
        '- "score": integer 1-10 (the weighted average)\n'
        '- "issues": array of strings listing specific problems (empty if pass)\n'
        '- "summary": one-sentence overall assessment\n'
        '- "completeness": integer 1-10\n'
        '- "format": integer 1-10\n'
        '- "actionability": integer 1-10'
    )

    user = (
        f"Original request: {user_request}\n\n"
        f"Execution plan:\n{plan}\n\n"
        f"Draft to review:\n{draft}\n\n"
        "Please evaluate this draft against the plan and return your assessment as JSON."
    )

    return system, user


def finalize_prompt(user_request: str, plan: str, draft: str, review_feedback: str, review_score: float) -> tuple[str, str]:
    """Generate prompts for the finalize node.

    The finalize node produces the final polished output.
    """
    system = (
        "You are a finalizer in a multi-agent workflow. "
        "Your job is to take the approved draft and produce the final polished output.\n\n"
        "Requirements:\n"
        "- Clean up any rough edges\n"
        "- Ensure consistent formatting\n"
        "- Add a brief header summarizing what was delivered\n"
        "- Do NOT change the substantive content - just polish the presentation\n\n"
        "Respond with the final output as plain text."
    )

    user = (
        f"Original request: {user_request}\n\n"
        f"Plan: {plan}\n\n"
        f"Approved draft (review score: {review_score}/10):\n{draft}\n\n"
        f"Reviewer notes: {review_feedback}\n\n"
        "Please produce the final polished output."
    )

    return system, user


def error_classifier_prompt(error_info: str, node_name: str) -> tuple[str, str]:
    """Generate prompts for the error handler to classify an error."""
    system = (
        "You are an error classifier in a multi-agent workflow. "
        "Given an error that occurred during execution, classify it as either "
        "recoverable or non-recoverable.\n\n"
        "Recoverable errors include:\n"
        "- LLM timeout or rate limiting\n"
        "- Temporary API errors\n"
        "- JSON parsing failures\n"
        "- Transient network issues\n\n"
        "Non-recoverable errors include:\n"
        "- Invalid API key\n"
        "- Prompt injection detected\n"
        "- Repeated identical errors\n"
        "- Configuration errors\n\n"
        'Respond with JSON: {"recoverable": true/false, "reason": "brief explanation"}'
    )

    user = (
        f"Error occurred in node: {node_name}\n"
        f"Error details: {error_info}\n\n"
        "Classify this error as recoverable or non-recoverable."
    )

    return system, user
