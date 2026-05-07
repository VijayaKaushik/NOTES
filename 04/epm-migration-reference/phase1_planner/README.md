# Phase 1: LLM-Based Planner

## What this replaces

At work, the orchestrator routes by matching agent `description` fields against the user query
(ADK's built-in description-based routing). This phase replaces that with an explicit LLM
classification step that returns a structured routing plan.

## Files in this folder

| File | Origin | Status |
|---|---|---|
| `planner.py` | Copied verbatim from home, annotated | Needs `# TODO[port]:` lines addressed |
| `planner_schema.py` | Derived from home planner's JSON output spec | Verify fields match work domain |
| `rag_registry.py` | Copied verbatim from home | Replace home agent names with work agent names |
| `PORT_INSTRUCTIONS.md` | New | Full porting guide |

## Key insight

The planner is a **pure classifier** — it takes a query + session context and returns a routing
plan JSON. It has no tools, no state, no memory. It is not an ADK agent. It's a plain Python
class with one method (`classify`). The orchestrator calls it inside `route_query()` before
deciding which agent to delegate to.

## Scope of change at work

1. Build `PlannerOutput` Pydantic schema (adapt `planner_schema.py` to work's agent names)
2. Build `Planner` class (`planner.py`, replacing Gemini calls with OpenAI)
3. Build `RagRegistry` with work's actual RAG agents (`rag_registry.py`)
4. Wire shadow mode in the orchestrator's `route_query` function — call planner but still use
   legacy routing for now
5. Graduate to live routing per Phase 3
