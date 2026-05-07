# Excerpted from: app/agent/orchestrator/agent.py (home EPM project)
#
# Shows two functions:
#   1. The operational dispatch section of route_query() — takes a planner
#      decision and returns a routing dict that the orchestrator LLM uses to
#      decide which AgentTool to call next.
#   2. update_context() — the post-agent write that records turn summary and
#      makes employee_ids available to the next turn.
#
# At work, agents are called via REST (not AgentTool). The dispatch pattern
# is structurally simpler: call the REST wrapper, get JSON back directly.
# No agent text parsing needed. See TODO[port]: comments throughout.
#
# The full route_query function also handles rag, combo, and context_only
# branches — those are omitted here. This excerpt covers the operational
# single-agent dispatch path only, which is what Phase 3 wires first.

import json
import os
from typing import List, Optional

from google.adk.tools.tool_context import ToolContext

# TODO[port]: AgentTool is the home mechanism for calling sub-agents.
# At work, replace with a REST wrapper function. The wrapper likely already
# exists — search for a function like call_remote_agent(agent_name, query, context)
# or invoke_agent(name, payload) in your orchestrator utils. Point Copilot to that
# file and it will complete the pattern.
from google.adk.tools import AgentTool

from .context_registry import ContextRegistry
from .planner import Planner

planner = Planner()
registry = ContextRegistry()


# ---------------------------------------------------------------------------
# Operational dispatch — excerpt from route_query()
# ---------------------------------------------------------------------------
# This is the tail of route_query(), reached when split_type = "operational".
# At this point, plan["route"] is one of: "vesting_agent", "participant_agent",
# "grant_agent", "both", or "context_only".
#
# The function returns a dict. The orchestrator LLM reads this dict and decides
# which AgentTool to invoke next (at home). At work, you can make this dispatch
# in Python directly — call the REST wrapper based on plan["route"] and return
# the result. The LLM doesn't need to be in the loop for the dispatch step.

def route_query_operational_excerpt(query: str, tool_context: ToolContext) -> dict:
    """
    Illustrates the operational dispatch section only.
    In production, this is the tail of the full route_query() function.
    """
    context = registry.read_registry(tool_context)
    turn_index = registry.get_turn_index(tool_context)
    plan = planner.classify(query=query, context_registry=context)

    # OPERATIONAL: record routing plan, let sub_agent handle the rest
    print(f"⚙️  OPERATIONAL → {plan['route']} | intent: {plan['intent']}")
    registry.write_turn(
        tool_context=tool_context,
        turn_index=turn_index,
        agent_name=plan["route"],
        intent=plan["intent"],
        summary={"plan": plan},
    )

    context_employee_ids = registry.get_latest_employee_ids(tool_context) or \
                           tool_context.state.get("last_vesting_employee_ids", [])

    # TODO[port]: At home, this dict is returned to the orchestrator LLM, which then
    # calls the appropriate AgentTool based on route field. At work (REST), you can
    # instead dispatch here in Python:
    #
    #   agent_name = plan["route"]  # e.g. "grant_agent"
    #   if os.getenv(f"PLANNER_ROUTING_{agent_name.upper()}_ENABLED") == "1":
    #       result = call_remote_agent(agent_name, query, tool_context)
    #       # call_remote_agent returns JSON — no text parsing needed
    #       return result
    #   else:
    #       # fall through to legacy router
    #       return legacy_route(query, tool_context)
    return {
        "status":               "success",
        "route":                plan["route"],
        "intent":               plan["intent"],
        "split_type":           "operational",
        "cross_agent":          plan.get("cross_agent", False),
        "join_key":             plan.get("join_key"),
        "join_field":           plan.get("join_field"),
        "requires_context":     plan.get("requires_context", False),
        "context_employee_ids": context_employee_ids,
        "message":              f"Routing to {plan['route']}",
    }


# ---------------------------------------------------------------------------
# Post-agent context write — update_context()
# ---------------------------------------------------------------------------
# Called after the data agent returns. Writes employee_ids and other scalars
# to the registry so the next turn can use them as filters.
#
# At home: the orchestrator LLM calls this as a tool after AgentTool returns.
# At work: call this directly in Python after call_remote_agent() returns,
# passing the IDs from the REST response.

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

    At home: orchestrator LLM extracts employee_ids from AgentTool text response
    and passes them here. AgentTool returns text, so extraction is implicit (LLM reads it).

    TODO[port]: At work, REST returns JSON. employee_ids will be a proper list field
    in the response dict — extract directly:
        ids = rest_response.get("employee_ids", [])
        update_context(agent_name, ids, tool_context, ...)
    No LLM extraction step needed. This is simpler and more reliable than the home approach.
    """
    turn_index = registry.get_turn_index(tool_context)

    # Fallback: if employee_ids not extracted from response, check session state side channel
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


# ---------------------------------------------------------------------------
# Home tools list — for reference only, shows how AgentTool wraps agents
# ---------------------------------------------------------------------------
# At home, sub-agents are wrapped in AgentTool and passed to the orchestrator's
# tools list. The orchestrator LLM picks which one to call based on the route_query
# return value.
#
# TODO[port]: At work, there are no AgentTool wraps. Instead, you have a REST
# wrapper (call_remote_agent or equivalent). Replace the tools list pattern with
# a registry dict or dispatch table:
#
#   AGENT_DISPATCH = {
#       "grant_agent":       lambda q, ctx: call_remote_agent("grant_agent", q, ctx),
#       "vesting_agent":     lambda q, ctx: call_remote_agent("vesting_agent", q, ctx),
#       "participant_agent": lambda q, ctx: call_remote_agent("participant_agent", q, ctx),
#   }
#
# Then in route_query (work version):
#   handler = AGENT_DISPATCH.get(plan["route"])
#   if handler:
#       result = handler(query, tool_context)
#
# Home reference (do not copy — AgentTool is home-only):
#
# tools=[
#     route_query,
#     update_context,
#     AgentTool(agent=vesting_agent),      # TODO[port]: replace with REST wrapper
#     AgentTool(agent=participant_agent),  # TODO[port]: replace with REST wrapper
#     AgentTool(agent=grant_agent),        # TODO[port]: replace with REST wrapper
#     AgentTool(agent=user_guide_agent),   # TODO[port]: replace with REST wrapper
#     AgentTool(agent=client_ops_agent),   # TODO[port]: replace with REST wrapper
# ]
#
# Result handling difference:
#   AgentTool returns: str (agent's full text response — LLM must parse)
#   REST returns:      dict (structured JSON — read fields directly)
# This is why concern detection is broken at home (smuggled via CONCERNS_JSON text marker)
# but will be clean at work (just a "concerns" key in the JSON response).
