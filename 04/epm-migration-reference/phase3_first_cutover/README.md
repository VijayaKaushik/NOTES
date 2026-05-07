# Phase 3: First Agent Cutover

## What this phase does

Wires the planner (Phase 1) to actually drive a real agent call for the first time.
The selected agent runs through the planner-driven branch; all other agents still use
the legacy router. Each agent gets its own feature flag so cutover is independently
rollback-able.

## Prerequisite: Phase 1 and Phase 2 both done

- Phase 1: planner has been running in shadow mode; agreement rate is acceptable
- Phase 2: context registry is wired and round-trips through the session DB correctly

## Which agent to cut over first

Criteria for the lowest-risk first cutover:
1. **Low query volume** — fewer users affected if something goes wrong
2. **Simple, well-defined input/output** — agent takes a plain query, returns clear data
3. **No cross-agent dependency** — agent does not need IDs from a prior agent turn
4. **Well-tested** — has existing regression queries in the catalog

At home, `grant_agent` fits best: it's queried less often than vesting or participant, it
returns self-contained grant data, and it has no upstream dependency on employee_ids from
vesting. Start there unless work's query distribution differs significantly.

## Files in this folder

| File | Origin | Status |
|---|---|---|
| `route_query_excerpt.py` | Excerpted from home orchestrator | Shows dispatch + context write pattern; TODO[port] marks REST replacements |
| `PORT_INSTRUCTIONS.md` | New | Full cutover guide |
