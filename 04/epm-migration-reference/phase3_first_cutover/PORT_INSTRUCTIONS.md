# Phase 3 Port Instructions — First Agent Cutover

## What this phase delivers

The planner (Phase 1) stops being a shadow and starts driving real agent calls — but only
for one agent at a time. The legacy router still handles everything else. Each agent cutover
is gated by its own feature flag so any one can be rolled back independently.

After this phase: the selected agent routes via planner + context registry. The registry
write in `update_context` means the next turn can use its output as a filter — this is when
key-passing actually starts working end-to-end.

## Cutover strategy

**Pick the lowest-risk agent first.** Criteria:
1. Low query volume — fewer users affected if routing is wrong
2. Simple, self-contained input/output — no upstream ID dependency
3. No cross-agent join — agent doesn't need employee_ids from a prior turn
4. High planner agreement rate in shadow mode (≥90%)

Start with `grant_agent` unless work's query distribution suggests otherwise. It satisfies
all four criteria and is isolated enough that a miscategorized query just returns a polite
"I couldn't find that" rather than returning wrong data.

## Order of operations

1. **Add the planner-driven branch alongside the legacy router.** Do NOT replace the legacy
   router — add a conditional branch that runs before it:

   ```python
   # Inside your orchestrator's routing function:
   agent_name = plan["route"]  # from planner.classify()

   if os.getenv(f"PLANNER_ROUTING_{agent_name.upper()}_ENABLED") == "1":
       # Planner-driven path
       result = call_remote_agent(agent_name, query, tool_context)
       employee_ids = result.get("employee_ids", [])
       update_context(agent_name, employee_ids, tool_context,
                      vesting_date=result.get("vesting_date"),
                      batch_id=result.get("batch_id"))
       return result
   else:
       # Legacy router — unchanged
       return legacy_route(query, tool_context)
   ```

2. **Wire `update_context` immediately after the REST call returns.** This is when
   key-passing starts. If you skip this, Phase 4+ cross-agent queries won't work.

3. **Enable the flag for one agent.** Start with `PLANNER_ROUTING_GRANT_AGENT_ENABLED=1`.
   Leave all other agents on legacy.

4. **Run the regression test plan** (see below). Fix misroutes before expanding to the
   next agent.

5. **Expand one agent at a time.** Each expansion is: enable flag → regression test →
   monitor 48h → proceed or rollback.

## Feature flag pattern

One flag per agent — each cutover is independently rollback-able:

```
PLANNER_ROUTING_GRANT_AGENT_ENABLED=1
PLANNER_ROUTING_VESTING_AGENT_ENABLED=0
PLANNER_ROUTING_PARTICIPANT_AGENT_ENABLED=0
```

Set in your deployment config or `.env`. A flip takes effect on next request — no restart
needed as long as your app reads env vars at call time (not at startup).

## Regression test plan

For each agent being cut over, run the relevant slice of your query catalog:

1. **Positive tests**: queries that should route to this agent — verify they do.
   Check: correct agent called, result is non-empty, latency within acceptable range.

2. **Negative tests**: queries for other agents — verify they still fall through to legacy.
   Check: planner classifies to a different route, legacy branch executes correctly.

3. **Context passthrough test**: 2-turn sequence.
   - Turn 1: query that routes to the cut-over agent, returns employee_ids
   - Turn 2: query that uses `requires_context=True` (e.g., filter previous results)
   - Verify: turn 2 receives the IDs from turn 1 via context registry

4. **Edge cases**: empty result set, single result, very large result set (> 100 IDs).

## Monitoring

After enabling a new agent flag in production, watch for 48 hours:

| Metric | Check |
|---|---|
| p95 latency | Compare to prior week baseline for same query type |
| Error rate | Should be ≤ prior week — planner call failure should fall through to legacy |
| Routing accuracy | Add logging: `[PLANNER_ROUTE] agent={name} intent={intent}` — grep to verify distribution looks sane |
| Token spend | Planner is now live (not shadow) — confirm within budget |

## Rollback

Set `PLANNER_ROUTING_{AGENT}_ENABLED=0`. Takes effect immediately on next request.
No database rollback needed — context registry writes are additive and harmless even if
legacy routing takes over on the next turn.

## Watch out for

**update_context must be called even on error.** If `call_remote_agent` raises, catch the
exception, write a minimal turn summary with an empty employee_ids list (so the registry
index advances), then re-raise. Otherwise `turn_index` gets out of sync and subsequent
context reads return stale data.

```python
try:
    result = call_remote_agent(agent_name, query, tool_context)
    update_context(agent_name, result.get("employee_ids", []), tool_context)
    return result
except Exception as e:
    update_context(agent_name, [], tool_context, summary=f"error: {e}")
    raise
```

**Planner agreement threshold before going live**: do not enable live routing if shadow-mode
agreement rate for the target agent is below 85%. Fix the planner first — add few-shot
examples for the misclassified query types, then re-run shadow mode.

**REST vs AgentTool result handling**: AgentTool returns text (the agent's full reply as a
string). REST returns a JSON dict. At work you read `result["employee_ids"]` directly —
there is no text-parsing step. This also means the CONCERNS_JSON text-marker hack from home
is unnecessary at work — just include `"concerns": [...]` as a proper field in the agent's
JSON response.
