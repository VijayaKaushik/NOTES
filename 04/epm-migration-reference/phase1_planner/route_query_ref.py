# Reference: full route_query() from home EPM project
# Source: app/agent/orchestrator/agent.py
#
# Use this as the shape reference when writing the work version in step 1.5a.
# Every TODO[port]: comment marks a line that must change at work.
#
# KEY STRUCTURAL DIFFERENCE
# -------------------------
# Home: route_query is an ADK tool — the orchestrator LLM calls it via ToolContext.
#       Context is read/written through tool_context.state (ADK session).
# Work: route_query is a plain Python function called directly by your REST handler.
#       Replace every tool_context reference with your work context object/dict.
#       The function signature and return dict shape stay the same.

import json
import os
from typing import Optional

# TODO[port]: remove ToolContext import — not used at work
from google.adk.tools.tool_context import ToolContext

from .context_registry import ContextRegistry   # TODO[port]: adjust import path for work
from .planner import Planner                    # TODO[port]: adjust import path for work
from .rag_registry import is_rag_agent          # TODO[port]: adjust import path for work

planner = Planner()
registry = ContextRegistry()


def route_query(query: str, tool_context: ToolContext) -> dict:
    # TODO[port]: change signature to:
    #   def route_query(query: str, context: dict) -> dict:
    # where `context` is whatever your work orchestrator passes for session state.
    # Remove ToolContext entirely.

    # Step 1 — read current context
    # TODO[port]: replace registry.read_registry(tool_context) with your context read.
    # At work this might be: context  (already passed in as a plain dict)
    context = registry.read_registry(tool_context)
    turn_index = registry.get_turn_index(tool_context)
    # TODO[port]: turn_index — if work context registry tracks turns, adapt accordingly.
    # If not, this can be a simple counter you maintain in session state.

    print(f"\n📥 ROUTE QUERY CALLED")
    print(f"📝 Query: {query}")
    print(f"📚 Context registry: {json.dumps(context, indent=2)}")

    # Step 2 — classify intent
    plan = planner.classify(query=query, context_registry=context)
    # TODO[port]: no change needed here — planner.classify() interface is identical at work.

    print(f"\n🔍 PLANNER RESULT: {json.dumps(plan, indent=2)}\n")

    # Step 3 — handle context_only (no agent call needed)
    if plan["route"] == "context_only":
        # TODO[port]: replace registry calls with work equivalents
        employee_ids = registry.get_latest_employee_ids(tool_context)
        operation = plan.get("operation", "filter")

        if operation == "intersect":
            all_ids = [
                set(turn.get("employee_ids", []))
                for turn in context.values()
                if turn.get("employee_ids")
            ]
            if all_ids:
                result_ids = list(set.intersection(*all_ids))
            else:
                result_ids = []

            # TODO[port]: replace registry.write_turn with work context write
            registry.write_turn(
                tool_context=tool_context,
                turn_index=turn_index,
                agent_name="context_only",
                intent=plan["intent"],
                employee_ids=result_ids,
                summary={"operation": "intersect", "result_count": len(result_ids)},
            )
            return {
                "status":       "success",
                "route":        "context_only",
                "operation":    "intersect",
                "employee_ids": result_ids,
                "count":        len(result_ids),
                "message":      f"Found {len(result_ids)} common participants",
            }

        return {
            "status":       "success",
            "route":        "context_only",
            "operation":    operation,
            "employee_ids": employee_ids,
            "message":      "Use existing context to answer this query",
        }

    split_type = plan.get("split_type", "operational")

    print(f"🔀 SPLIT_TYPE: {split_type} | ROUTE: {plan['route']}")

    # RAG handler — works for all RAG agents
    if split_type == "rag":
        rag_agent_name = plan["route"]
        print(f"📖 RAG → {rag_agent_name} | query: {query}")
        # TODO[port]: replace registry.write_turn with work context write
        registry.write_turn(
            tool_context=tool_context,
            turn_index=turn_index,
            agent_name=rag_agent_name,
            intent=plan["intent"],
            summary={"plan": plan},
        )
        return {
            "status":     "success",
            "route":      rag_agent_name,
            "split_type": "rag",
            "intent":     plan["intent"],
            "rag_query":  plan.get("rag_query") or query,
            "message":    f"Routing to {rag_agent_name} for documentation search",
        }

    # Combo handler
    if split_type == "combo":
        rag_agent_name = plan.get("rag_agent", "user_guide_agent")
        # TODO[port]: replace "user_guide_agent" default with work equivalent RAG agent name
        print(f"🔀 COMBO → rag_agent: {rag_agent_name} | rag_query: {plan.get('rag_query')} | operational_query: {plan.get('operational_query')}")
        # TODO[port]: replace registry.write_turn with work context write
        registry.write_turn(
            tool_context=tool_context,
            turn_index=turn_index,
            agent_name="combo",
            intent=plan["intent"],
            summary={
                "rag_agent":         rag_agent_name,
                "rag_query":         plan.get("rag_query"),
                "operational_query": plan.get("operational_query"),
            },
        )
        return {
            "status":            "success",
            "route":             "combo",
            "split_type":        "combo",
            "intent":            plan["intent"],
            "rag_agent":         rag_agent_name,
            "rag_query":         plan.get("rag_query") or query,
            "operational_query": plan.get("operational_query") or query,
            "message":           f"Combo — {rag_agent_name} + operational agent",
        }

    # Operational path — record plan, dispatch to data agent
    print(f"⚙️  OPERATIONAL → {plan['route']} | intent: {plan['intent']}")
    # TODO[port]: replace registry.write_turn with work context write
    registry.write_turn(
        tool_context=tool_context,
        turn_index=turn_index,
        agent_name=plan["route"],
        intent=plan["intent"],
        summary={"plan": plan},
    )

    # TODO[port]: replace tool_context.state with work session state equivalent
    context_employee_ids = (
        registry.get_latest_employee_ids(tool_context)
        or tool_context.state.get("last_vesting_employee_ids", [])
    )

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
    # NOTE: at work (Phase 3+) you can dispatch to the agent here in Python
    # instead of returning this dict for the LLM to act on. See phase3 excerpt.
