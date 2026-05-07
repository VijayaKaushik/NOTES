# Excerpted from: app/agent/orchestrator/agent.py (home EPM project)
# Shows the `update_context` orchestrator tool — the post-agent write pattern.
#
# This function is called by the orchestrator LLM after every data agent completes.
# It is the ONLY place where turn summaries are written with real employee_ids (not
# the preliminary routing write in route_query, which writes an empty placeholder).
#
# At work, wire an equivalent call after your REST agent returns.

import json
from typing import List, Optional

from google.adk.tools.tool_context import ToolContext

from .context_registry import ContextRegistry

registry = ContextRegistry()


def _parse_summary(summary: Optional[str]) -> dict:
    if not summary:
        return {}
    try:
        return json.loads(summary)
    except (json.JSONDecodeError, ValueError):
        return {"note": summary}


def update_context(
    agent_name: str,
    employee_ids: List[str],
    tool_context: ToolContext,
    vesting_date: Optional[str] = None,
    batch_id: Optional[str] = None,
    summary: Optional[str] = None,
) -> dict:
    """
    Called after an agent completes its response.
    Records lightweight turn summary — keys and scalars only.
    Never stores full records.

    The orchestrator LLM calls this as a tool immediately after a data agent
    (vesting_agent, participant_agent, grant_agent) returns. The LLM extracts
    employee_ids from the agent's response and passes them here.

    Returns: {"status": "success", "turn_recorded": <turn_index>}
    The orchestrator instruction checks this return value — if the agent also
    detected concerns, the return dict will include has_concerns=True and a
    concerns list (home-specific; not included here as it's WIP).
    """
    turn_index = registry.get_turn_index(tool_context)

    # Fallback: if LLM didn't extract employee_ids from response, try session state
    # (vesting_agent writes to last_vesting_employee_ids as a side channel)
    resolved_ids = employee_ids or tool_context.state.get("last_vesting_employee_ids", [])

    registry.write_turn(
        tool_context=tool_context,
        turn_index=turn_index,
        agent_name=agent_name,
        intent="completed",
        employee_ids=resolved_ids,
        vesting_date=vesting_date,
        batch_id=batch_id,
        summary=_parse_summary(summary),
    )
    return {"status": "success", "turn_recorded": turn_index}
