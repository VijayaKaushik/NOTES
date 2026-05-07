# Phase 1 Port Instructions — LLM-Based Planner

## What this phase delivers

A structured routing decision for every user query. Instead of ADK's description-based
agent matching, the orchestrator calls a Planner that returns a typed JSON plan:
which agent to call, whether the query is doc vs. data vs. both, and — for cross-agent
queries — which agent runs first and what key to pass to the second.

**No behavior change yet.** The planner runs in shadow mode alongside the existing router.
Phase 3 is when planner decisions actually drive agent calls.

## Prerequisite checks

Before writing any code:

```bash
# OpenAI SDK version — need ≥1.40 for chat.completions.parse
pip show openai | grep Version

# GPT-5 access — confirm the model name resolves
python -c "from openai import OpenAI; c = OpenAI(); print(c.models.retrieve('gpt-5').id)"

# API key
echo $OPENAI_API_KEY  # must be set
```

## Order of operations

1. **Adapt `planner_schema.py`** — replace home agent names in `Literal` types with work
   agent names. Widen `join_key` if work has entity types beyond employee/grant.
   Verify with a Pydantic validator: `PlannerOutput.model_validate(sample_dict)`.

2. **Adapt `rag_registry.py`** — replace home RAG agent entries with work RAG agents.
   Keep the same dict shape (`description`, `triggers`, `topics`, `excludes`). The planner
   prompt is built from this at startup — no other file needs touching when you add an agent.

3. **Port `planner.py`** — address every `# TODO[port]:` comment. The class interface
   (`classify(query, context_registry) -> dict`) stays identical. Only the SDK calls change.

4. **Wire shadow mode** — inside your orchestrator's `route_query` function, add:
   ```python
   if os.getenv("PLANNER_SHADOW_ENABLED") == "1":
       shadow_plan = planner.classify(query=query, context_registry=context)
       print(f"[SHADOW] planner={json.dumps(shadow_plan)}")
       print(f"[SHADOW] legacy_route={legacy_route}")
   # legacy routing continues as normal — shadow output is log-only
   ```

5. **Run shadow mode** against the regression catalog (see Test plan below).

## Shadow mode test plan

Build a regression query catalog: at minimum 30 queries covering all split_type categories.
Replay against shadow mode and compute agreement rate per category:

| Category | Target agreement |
|---|---|
| rag — how-to | ≥95% |
| rag — client ops | ≥90% |
| operational — single agent | ≥90% |
| combo | ≥80% (combo is harder to classify) |
| context_only | ≥95% (clear from context signals) |

Log mismatches with `[SHADOW MISMATCH]` prefix so they're greppable in prod logs.
Review mismatches before Phase 3 cutover — they become the tuning backlog.

## Rollback

Feature flag: `PLANNER_SHADOW_ENABLED` env var.
- Shadow mode: set to `"1"` — planner runs but output is log-only, no behavior change.
- Off: unset or `"0"` — planner not called at all.

No database migration, no schema change. Safe to enable/disable at runtime.

## Watch out for

**Cost**: The planner adds 1 LLM call per user query. Monitor daily token spend for the
first week after enabling shadow mode. GPT-5 input tokens are cheap for a ~3KB prompt,
but at scale this adds up. If cost is a concern, evaluate `gpt-5-mini` — run both models
in shadow mode simultaneously (two shadow calls, one live) and compare agreement rates before
committing to a model.

**Latency**: Planner adds 1–3s before the agent call. In shadow mode this is hidden (parallel
with legacy routing). In live mode (Phase 3) it's sequential. Benchmark p95 latency in shadow
mode so you have a baseline before Phase 3.

**System prompt size**: `ROUTING_SYSTEM_PROMPT` is ~3KB including few-shot examples. OpenAI
charges for every token on every call. Consider caching the compiled prompt string (already
done at module load via `RAG_SECTION = get_rag_routing_description()`).

**json.loads removal**: Once you switch to `chat.completions.parse`, remove the `json.loads`
call and the markdown-strip block. If you leave both in, you'll try to JSON-parse an already-
parsed Pydantic object and get a confusing error.
