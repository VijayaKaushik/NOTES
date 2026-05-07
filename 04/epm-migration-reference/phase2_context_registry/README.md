# Phase 2: Context Registry

## What this solves

Today at work, agents run independently per turn. If the user asks "show vesting for next month"
and then "which of those participants have pending KYC?", the second query has no way to know
which employee IDs the first query returned.

The context registry solves this by writing lightweight turn summaries to ADK session state after
each agent call. The next turn reads the registry and injects relevant IDs as a filter.

## Files in this folder

| File | Origin | Status |
|---|---|---|
| `context_registry.py` | Copied verbatim from home | Drop-in — no changes needed |
| `example_tool_writing_to_registry.py` | Excerpted from home orchestrator | Shows the write pattern |
| `PORT_INSTRUCTIONS.md` | New | Full porting guide |

## Key constraint

**Write keys and scalars only. Never write full records.**

```python
# CORRECT
registry.write_turn(..., employee_ids=["E001", "E002", "E003"], vesting_date="2026-06-15")

# WRONG — do not do this
registry.write_turn(..., summary={"employees": [{"id": "E001", "name": "...", "shares": ...}]})
```

Full records go in agent artifacts. The registry is a pointer store, not a data cache.
