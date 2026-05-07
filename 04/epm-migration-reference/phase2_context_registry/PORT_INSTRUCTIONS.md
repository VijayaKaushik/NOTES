# Phase 2 Port Instructions — Context Registry

## What context_registry does and why it matters

This is the primary pain point you're solving: passing agent output keys to downstream agents
across turns without re-fetching data.

**Without context registry:**
- Turn 1: "show participants in next vesting" → vesting_agent returns 47 employee IDs
- Turn 2: "which of those have pending KYC?" → participant_agent has no idea about those 47 IDs
  → either calls with no filter (returns all 500+ participants) or asks user to repeat themselves

**With context registry:**
- Turn 1: vesting_agent returns → `update_context` writes employee_ids to registry
- Turn 2: planner classifies as `requires_context=True` → orchestrator reads registry →
  injects "Filter to employee_ids: [E001, E002, ...]" into participant_agent's query
  → participant_agent returns only the relevant 47

## Drop-in port

`context_registry.py` uses only `tool_context.state` (a dict) and standard Python types.
ADK's `tool_context.state` is identical across home and work — backed by
`DatabaseSessionService` using the same SQLite schema in both setups.

**No changes needed** to `context_registry.py` itself. The only adaptation is wiring the
write call after your REST agent returns (shown in `example_tool_writing_to_registry.py`).

## The summary contract

**Write these** — scalars and ID lists only:
- `employee_ids: List[str]` — IDs of employees touched this turn
- `vesting_date: str` — ISO date string (e.g., `"2026-06-15"`)
- `batch_id: str` — batch or release identifier
- `intent: str` — human-readable label (e.g., `"get_vesting_participants"`)
- `summary: dict` — small metadata dict (plan type, count, operation) — no nested records

**Never write these:**
- Full employee records (name, address, account details)
- Raw API response payloads
- Large lists of objects
- Anything you'd need to re-paginate

The registry is a **pointer store**, not a cache. If the next agent needs full data, it
fetches it using the IDs as a filter — it does not read data from the registry.

## Pruning behavior

**At home there is no MAX_TURNS constant** — the registry grows unbounded within a session.
Sessions are typically short (< 20 turns) so this hasn't caused problems.

For work, if sessions can be long-lived, add pruning in `write_turn`:
```python
MAX_TURNS = 10  # keep only the last 10 turns in memory

# At the end of write_turn, after setting registry[f"turn_{turn_index}"]:
if len(registry) > MAX_TURNS:
    # Remove oldest turns (lowest turn_N index)
    oldest_keys = sorted(registry.keys())[:len(registry) - MAX_TURNS]
    for k in oldest_keys:
        del registry[k]
tool_context.state["context_registry"] = registry
```

A value of 10 is reasonable for most conversational flows. Set higher if cross-agent
intersection queries span many turns (e.g., "common participants across 5 different vestings").

## How to test

Write unit tests using a mock `tool_context`:

```python
from unittest.mock import MagicMock
from context_registry import ContextRegistry

def make_ctx(state=None):
    ctx = MagicMock()
    ctx.state = state or {}
    return ctx

def test_write_and_read():
    reg = ContextRegistry()
    ctx = make_ctx()
    reg.write_turn(ctx, turn_index=0, agent_name="vesting_agent",
                   intent="get_participants", employee_ids=["E001", "E002"])
    reg.write_turn(ctx, turn_index=1, agent_name="participant_agent",
                   intent="get_kyc", employee_ids=["E001"])
    assert reg.get_latest_employee_ids(ctx) == ["E001"]
    assert reg.get_turn_index(ctx) == 2

def test_pruning():
    reg = ContextRegistry()
    ctx = make_ctx()
    for i in range(15):
        reg.write_turn(ctx, turn_index=i, agent_name="vesting_agent",
                       intent="test", employee_ids=[f"E{i:03d}"])
    # After adding pruning logic: only MAX_TURNS entries should remain
    assert len(ctx.state["context_registry"]) <= MAX_TURNS

def test_empty_registry_returns_empty_list():
    reg = ContextRegistry()
    ctx = make_ctx()
    assert reg.get_latest_employee_ids(ctx) == []
    assert reg.get_latest_vesting_date(ctx) is None
```

## Integration test

After wiring at work, confirm round-trip through `DatabaseSessionService`:

1. Start a session
2. Call an agent that writes to the registry via `update_context`
3. End the turn (ADK persists state to DB)
4. Start a new turn in the same session
5. Call `registry.read_registry(tool_context)` — verify the prior turn's data is present
6. Verify `get_latest_employee_ids` returns the IDs from step 2

This confirms ADK is serializing and deserializing the nested dict correctly through SQLite.

## Watch out for

**Nested dict serialization**: `tool_context.state["context_registry"]` is a dict of dicts.
Some backends serialize this as JSON string, others as a native nested object. If you see
`str` instead of `dict` when reading back, wrap `read_registry` with `json.loads` if the
value is a string. Test this in your integration test before relying on the registry in prod.

**Concurrent writes within a turn**: If two tools write to the registry in the same turn
(rare but possible in combo routing), the second write wins because both read the current
state, mutate it, and write back. This is not a problem in practice — in combo routing, only
the data agent writes real IDs; the RAG agent doesn't write to the registry at all.

**turn_index drift**: `get_turn_index` reads `state["turn_index"]`, which is incremented
by `write_turn`. If `write_turn` is called multiple times in one turn (e.g., once for routing
plan, once for completion), the index advances faster than the conversational turn count.
This is intentional at home — each registry write gets its own slot. At work, decide whether
you want one slot per conversational turn or one slot per registry write, then set
`tool_context.state["turn_index"]` accordingly in your orchestrator.
