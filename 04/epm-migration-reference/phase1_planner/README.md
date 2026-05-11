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
| `route_query_ref.py` | Full `route_query()` from home orchestrator | Shape reference for step 1.5a — adapt ToolContext → work context |
| `orchestrator_prompt_ref.py` | Orchestrator LLM instruction from home | Prompt reference for step 1.5a — adapt agent names for work |
| `PORT_INSTRUCTIONS.md` | New | Full porting guide (steps 1.1–1.4) |
| `step_1_5_PORT_INSTRUCTIONS.md` | New | Step 1.5 split into 1.5a (add route_query) and 1.5b (shadow mode) |

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
