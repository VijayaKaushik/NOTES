# Copilot Prompts — EPM Orchestrator Port

Each step has:
- **Open** — tabs to have open before pasting the prompt (Copilot reads open tabs as context)
- **Prompt** — paste this into Copilot Chat
- **Expected output** — what must exist after the step
- **Gate** — run this check; do not proceed to next step until it passes

Phase 1 and Phase 2 are independent — run them in parallel if you have two workstreams.
Phase 3 requires both Phase 1 and Phase 2 to pass their final gates.

---

## Phase 1 — LLM-Based Planner

### Step 1.1 — Create PlannerOutput schema

**Open:**
- `epm-migration-reference/phase1_planner/planner_schema.py`
- `epm-migration-reference/phase1_planner/planner.py` (for field context from system prompt)
- The new work file you want to create: `work/planner_schema.py`

**Prompt:**
```
I'm porting a routing planner from a Gemini project to OpenAI GPT-5.
The reference schema is open in planner_schema.py.

Create a Pydantic v2 BaseModel called PlannerOutput in the current file.
Copy all 14 fields exactly as they appear in the reference.

Adapt these fields for work's domain:
- The route field stays as `str` (agent names differ at work).
- The `join_key` Literal currently has "employee_id" and "grant_id".
  Widen it to `Optional[str]` — work may have additional entity types.
- All other fields: copy as-is, including Optional/Literal types.

Do not add extra fields. Do not import anything beyond:
  from typing import Literal, Optional
  from pydantic import BaseModel

Add a module-level docstring: "Planner routing output schema. Mirrors the JSON
contract in ROUTING_SYSTEM_PROMPT. All fields must be present in every response."
```

**Expected output:** `work/planner_schema.py`
```python
from typing import Literal, Optional
from pydantic import BaseModel

class PlannerOutput(BaseModel):
    split_type: Literal["rag", "operational", "combo"]
    route: str
    intent: str
    requires_context: bool
    cross_agent: bool
    step_1: Optional[str] = None
    step_2: Optional[str] = None
    join_key: Optional[str] = None       # widened from Literal
    join_field: Optional[str] = None
    operation: Optional[Literal["intersect"]] = None
    context_key: Optional[Literal["employee_ids"]] = None
    rag_agent: Optional[str] = None
    rag_query: Optional[str] = None
    operational_query: Optional[str] = None
```

**Gate — run before Step 1.2:**
```bash
python -c "
from work.planner_schema import PlannerOutput
p = PlannerOutput(split_type='rag', route='any_agent', intent='test',
                  requires_context=False, cross_agent=False)
assert set(p.model_fields.keys()) == {
    'split_type','route','intent','requires_context','cross_agent',
    'step_1','step_2','join_key','join_field','operation',
    'context_key','rag_agent','rag_query','operational_query'
}
print('PASS — 14 fields, schema validates')
"
```
Must print `PASS`. Fix any validation errors before continuing.

---

### Step 1.2 — Adapt RAG registry

**Open:**
- `epm-migration-reference/phase1_planner/rag_registry.py`
- Work's current agent list or orchestrator file (so Copilot sees the real agent names)
- The new work file: `work/rag_registry.py`

**Prompt:**
```
I'm creating a RAG agent registry for a routing planner.
The reference implementation is open in rag_registry.py.

Copy the full file structure verbatim into the current file, then replace the
two home agent entries ("user_guide_agent" and "client_ops_agent") with work's
actual RAG agents. Keep the same dict shape for each entry:
  "description": str,
  "triggers": List[str],
  "topics": List[str],
  "excludes": List[str]

Keep all three functions verbatim:
  get_rag_agent_names() -> list[str]
  get_rag_routing_description() -> str
  is_rag_agent(agent_name: str) -> bool

Do not change the function signatures or logic. Only the RAG_AGENTS dict contents
change — everything else is copied exactly.
```

**Expected output:** `work/rag_registry.py`
- `RAG_AGENTS` dict with work's actual RAG agent names as keys
- All three functions present, signatures unchanged
- `get_rag_routing_description()` returns a non-empty string that mentions each agent

**Gate — run before Step 1.3:**
```bash
python -c "
from work.rag_registry import get_rag_agent_names, get_rag_routing_description, is_rag_agent
names = get_rag_agent_names()
assert len(names) >= 1, 'no agents registered'
desc = get_rag_routing_description()
assert len(desc) > 100, 'description too short — check get_rag_routing_description()'
for name in names:
    assert is_rag_agent(name), f'{name} not found by is_rag_agent'
print(f'PASS — {len(names)} RAG agent(s): {names}')
"
```
Must print `PASS` with at least one agent name.

---

### Step 1.3 — Build Planner class

**Open:**
- `epm-migration-reference/phase1_planner/planner.py` (annotated reference — all TODO[port] comments)
- `work/planner_schema.py` (Step 1.1 output)
- `work/rag_registry.py` (Step 1.2 output)
- The new work file: `work/planner.py`

**Prompt:**
```
I'm porting a routing classifier from Gemini to OpenAI GPT-5 structured output.
The annotated reference is open in planner.py. Every # TODO[port]: comment
marks a line that needs replacing. The target schema is in planner_schema.py.
The RAG agent descriptions are in rag_registry.py.

Create work/planner.py with these changes from the reference:

1. Replace the Gemini import and client:
   REMOVE:  from google import genai
   ADD:     from openai import OpenAI

2. Replace client initialization in _get_client():
   REMOVE:  self._client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
   ADD:     self._client = OpenAI()
   Change the type annotation from `genai.Client | None` to `OpenAI | None`.

3. Replace the generate_content call in classify() with:
   response = self._get_client().chat.completions.parse(
       model="gpt-5",
       messages=[
           {"role": "system", "content": ROUTING_SYSTEM_PROMPT},
           {"role": "user", "content": prompt},
       ],
       response_format=PlannerOutput,
   )
   return response.choices[0].message.parsed.model_dump()

4. Delete the markdown-stripping block entirely (the `if text.startswith("```")` block
   and the `json.loads` call). Structured output never needs it.

5. Add at the top of the file:
   from .planner_schema import PlannerOutput

6. The ROUTING_SYSTEM_PROMPT string, RAG_SECTION, and RAG_AGENT_NAMES module-level
   variables: copy verbatim from the reference. The prompt content does not change.

7. The classify() method signature stays identical:
   def classify(self, query: str, context_registry: Dict) -> Dict

The return value must still be a plain dict (model_dump() achieves this).
```

**Expected output:** `work/planner.py`
- Imports `OpenAI`, `PlannerOutput` — no `genai` import
- `_get_client()` returns `OpenAI` instance
- `classify()` calls `chat.completions.parse` with `response_format=PlannerOutput`
- No `json.loads`, no markdown stripping
- Returns `dict` from `model_dump()`

**Gate — run before Step 1.4:**
```bash
# Requires OPENAI_API_KEY set and gpt-5 access.
# If not yet available, use the mock gate below instead.

python -c "
from work.planner import Planner
p = Planner()
result = p.classify(
    query='show me next vesting date',
    context_registry={}
)
assert isinstance(result, dict), 'classify() must return dict'
assert 'split_type' in result, 'missing split_type'
assert result['split_type'] in ('rag', 'operational', 'combo'), f'bad split_type: {result[\"split_type\"]}'
print(f'PASS — split_type={result[\"split_type\"]}, route={result[\"route\"]}')
"

# Mock gate (if no API key yet):
python -c "
from unittest.mock import MagicMock, patch
from work.planner import Planner
from work.planner_schema import PlannerOutput

mock_plan = PlannerOutput(split_type='operational', route='vesting_agent',
    intent='test', requires_context=False, cross_agent=False)
mock_response = MagicMock()
mock_response.choices[0].message.parsed = mock_plan

with patch('work.planner.OpenAI') as MockOpenAI:
    MockOpenAI.return_value.chat.completions.parse.return_value = mock_response
    p = Planner()
    result = p.classify('show vesting dates', {})

assert result['split_type'] == 'operational'
assert result['route'] == 'vesting_agent'
print('PASS — mock gate passed, real API gate pending')
"
```
Must print `PASS` (either gate). Run real gate before enabling shadow mode.

---

### Step 1.4 — Unit tests for Planner

**Open:**
- `work/planner.py` (Step 1.3 output)
- `work/planner_schema.py` (Step 1.1 output)
- `work/rag_registry.py` (Step 1.2 output)
- New file: `work/tests/test_planner.py`

**Prompt:**
```
Write unit tests for the Planner class in work/planner.py.
Use pytest and unittest.mock. Patch openai.OpenAI so no real API calls are made.

Write exactly these 6 tests:

1. test_rag_classification:
   Query "how do I do X?" → expect split_type="rag", route in rag_registry names

2. test_operational_classification:
   Query "show vesting dates" → expect split_type="operational",
   route in ["vesting_agent","participant_agent","grant_agent"]

3. test_combo_classification:
   Query "What is KYC and who has pending KYC?" → expect split_type="combo",
   rag_query is not None, operational_query is not None

4. test_context_only:
   Query "common participants across those vestings" with context_registry containing
   two prior turns with employee_ids → expect route="context_only"

5. test_returns_dict_not_pydantic:
   Any query → result must be a plain dict, not a PlannerOutput instance

6. test_all_14_fields_present:
   Any query → result dict must contain all 14 keys from PlannerOutput.model_fields

Helper: create a fixture `mock_planner(split_type, route, **kwargs)` that patches
the OpenAI client and returns a Planner instance that will produce the given output.
Use this fixture in all tests to avoid repeating the mock setup.

Each test must have a clear docstring stating what behavior it verifies.
```

**Expected output:** `work/tests/test_planner.py` with 6 passing tests

**Gate — run before Step 1.5:**
```bash
pytest work/tests/test_planner.py -v
```
All 6 must pass. If any fail, fix before wiring shadow mode — a failing test here means
the Planner class has a bug that will surface in production.

---

### Step 1.5 — Wire shadow mode in orchestrator

**Open:**
- `work/planner.py` (Step 1.3 output)
- `work/rag_registry.py` (Step 1.2 output)
- Work's existing orchestrator `route_query` function (the one to modify)
- `epm-migration-reference/phase1_planner/PORT_INSTRUCTIONS.md` (shadow mode section)

**Prompt:**
```
I'm adding a shadow-mode planner to the existing route_query function.
The Planner class is in work/planner.py. The existing route_query function
is in the current file.

At the TOP of route_query(), before any existing routing logic, add this block:

    # --- PLANNER SHADOW MODE ---
    if os.getenv("PLANNER_SHADOW_ENABLED") == "1":
        try:
            _shadow_context = registry.read_registry(tool_context) if registry else {}
            _shadow_plan = _planner.classify(query=query, context_registry=_shadow_context)
            _legacy_route = <existing route variable or "unknown">
            print(f"[SHADOW] query={query!r}")
            print(f"[SHADOW] planner={json.dumps(_shadow_plan)}")
            print(f"[SHADOW] legacy_route={_legacy_route!r}")
            if _shadow_plan.get("route") != _legacy_route:
                print(f"[SHADOW MISMATCH] planner={_shadow_plan['route']!r} legacy={_legacy_route!r}")
        except Exception as e:
            print(f"[SHADOW ERROR] {e}")
    # --- END SHADOW MODE ---

At module level, add:
    import json, os
    from .planner import Planner
    _planner = Planner()

The existing routing logic must be completely unchanged. The shadow block only
logs — it never modifies the return value of route_query.
```

**Expected output:**
- Work orchestrator has `_planner = Planner()` at module level
- `route_query` has the shadow block at top, existing logic untouched
- `[SHADOW]` log lines appear when `PLANNER_SHADOW_ENABLED=1`

**Gate — Phase 1 complete:**
```bash
# Send a test query through the API with the env var set:
PLANNER_SHADOW_ENABLED=1 <your server start command>

# Then in another terminal:
curl -X POST <your chat endpoint> -d '{"message": "show vesting dates"}' -H "Content-Type: application/json"

# Check server logs for:
grep "\[SHADOW\]" <your log file or stdout>
```
Must see `[SHADOW] planner={"split_type": ...}` in logs.
Must see `[SHADOW MISMATCH]` when planner disagrees (expected early on — that's the point).
Must NOT see any change in the API response itself.

**Phase 1 is complete when:** shadow mode runs on all queries, agreement rate ≥85% per
category (measure over 48h of traffic or replay the query catalog).

---
---

## Phase 2 — Context Registry

### Step 2.1 — Add context_registry.py to work project

**Open:**
- `epm-migration-reference/phase2_context_registry/context_registry.py`
- Work's orchestrator `__init__.py` or imports file

**Prompt:**
```
Copy the ContextRegistry class from context_registry.py verbatim into
work/context_registry.py. Do not change any logic, method signatures, or docstrings.

Then verify the import resolves:
  from google.adk.tools.tool_context import ToolContext

If ToolContext is imported differently in this work project (different ADK version
or import path), update only that import line — no other changes.

After copying, add one line at the bottom of the file:
  # Source: app/agent/orchestrator/context_registry.py (epm-chatbot home project)
```

**Expected output:** `work/context_registry.py` — identical to reference except possibly
the ToolContext import path

**Gate — run before Step 2.2:**
```bash
python -c "
from work.context_registry import ContextRegistry
from unittest.mock import MagicMock

ctx = MagicMock()
ctx.state = {}
reg = ContextRegistry()
reg.write_turn(ctx, 0, 'test_agent', 'test_intent', employee_ids=['ID1'])
assert ctx.state['context_registry']['turn_0']['employee_ids'] == ['ID1']
assert ctx.state['turn_index'] == 1
print('PASS — ContextRegistry write/read works')
"
```
Must print `PASS`.

---

### Step 2.2 — Create update_context orchestrator tool

**Open:**
- `epm-migration-reference/phase2_context_registry/example_tool_writing_to_registry.py`
- `work/context_registry.py` (Step 2.1 output)
- Work's orchestrator tools file or agent.py

**Prompt:**
```
Create an update_context function in the current file, following the pattern in
example_tool_writing_to_registry.py.

The function signature must be:
def update_context(
    agent_name: str,
    employee_ids: List[str],
    tool_context: ToolContext,
    vesting_date: Optional[str] = None,
    batch_id: Optional[str] = None,
    summary: Optional[str] = None,
) -> dict:

The function must:
1. Get turn_index from registry.get_turn_index(tool_context)
2. Resolve employee_ids: use the passed list, fall back to
   tool_context.state.get("last_agent_employee_ids", []) if empty
   (rename "last_vesting_employee_ids" → "last_agent_employee_ids" to be domain-neutral)
3. Parse summary string as JSON via _parse_summary() helper (copy verbatim from reference)
4. Call registry.write_turn() with all fields
5. Return {"status": "success", "turn_recorded": turn_index}

At module level, add:
    from .context_registry import ContextRegistry
    registry = ContextRegistry()

Register this function as a tool in the orchestrator's tools list.
```

**Expected output:** `update_context` function in orchestrator file, `ContextRegistry`
instantiated at module level, function in tools list

**Gate — run before Step 2.3:**
```bash
python -c "
from unittest.mock import MagicMock
# Import from wherever you placed update_context:
from work.orchestrator import update_context

ctx = MagicMock()
ctx.state = {}
result = update_context(
    agent_name='grant_agent',
    employee_ids=['A1', 'A2'],
    tool_context=ctx,
    vesting_date='2026-08-15',
)
assert result == {'status': 'success', 'turn_recorded': 0}
assert ctx.state['context_registry']['turn_0']['employee_ids'] == ['A1', 'A2']
assert ctx.state['context_registry']['turn_0']['vesting_date'] == '2026-08-15'
print('PASS — update_context writes correct registry entry')
"
```
Must print `PASS`.

---

### Step 2.3 — Wire update_context after each REST agent call

**Open:**
- `work/orchestrator.py` or wherever REST agent calls happen (the file with `call_remote_agent`)
- `epm-migration-reference/phase3_first_cutover/route_query_excerpt.py` (pattern reference)
- `work/context_registry.py` (so Copilot sees the method signatures)

**Prompt:**
```
I need to call update_context immediately after every data agent REST call returns.
Data agents are: <list work's operational agent names here>.
RAG agents do NOT get update_context calls.

For each place in this file where a data agent is called via REST
(look for call_remote_agent, invoke_agent, or similar), add immediately after the call:

    _ids = result.get("employee_ids", [])
    _vdate = result.get("vesting_date")
    _batch = result.get("batch_id")
    update_context(
        agent_name=<agent_name_variable>,
        employee_ids=_ids,
        tool_context=tool_context,
        vesting_date=_vdate,
        batch_id=_batch,
    )

Also add error handling so update_context is called even when the REST call fails:
    try:
        result = call_remote_agent(agent_name, query, tool_context)
        _ids = result.get("employee_ids", [])
        update_context(agent_name, _ids, tool_context,
                       vesting_date=result.get("vesting_date"),
                       batch_id=result.get("batch_id"))
        return result
    except Exception as e:
        update_context(agent_name, [], tool_context, summary=f"error: {str(e)}")
        raise

This pattern must be applied consistently for every data agent call site.
```

**Expected output:** Every data agent call site in the orchestrator has the try/except
pattern with `update_context` in both branches.

**Gate — run before Step 2.4:**
```bash
# Verify no data agent call site is missing the update_context pattern.
# Search for call_remote_agent (or your REST wrapper name) and confirm each
# occurrence is followed by update_context within the same try block.
grep -n "call_remote_agent\|update_context" work/orchestrator.py
```
Every `call_remote_agent` line must have a matching `update_context` within 5 lines.
If any `call_remote_agent` appears without `update_context` nearby, fix before continuing.

---

### Step 2.4 — Unit tests for context registry

**Open:**
- `work/context_registry.py`
- `epm-migration-reference/phase2_context_registry/PORT_INSTRUCTIONS.md` (test plan section)
- New file: `work/tests/test_context_registry.py`

**Prompt:**
```
Write unit tests for ContextRegistry in work/context_registry.py.
Use pytest and unittest.mock.MagicMock for tool_context.

Write exactly these 5 tests:

1. test_write_and_read_employee_ids:
   Write two turns with different employee_ids.
   Assert get_latest_employee_ids returns the SECOND turn's IDs (most recent).

2. test_get_latest_vesting_date:
   Write a turn with vesting_date="2026-08-15".
   Assert get_latest_vesting_date returns "2026-08-15".

3. test_empty_registry_returns_defaults:
   On a fresh mock context (state={}):
   - get_latest_employee_ids returns []
   - get_latest_vesting_date returns None
   - get_turn_index returns 0

4. test_turn_index_increments:
   Write 3 turns. Assert get_turn_index returns 3 after the third write.

5. test_write_does_not_store_full_records:
   Write a turn with summary={"note": "small"}.
   Assert the summary stored is a dict with ONE key only — not a large object.
   (This enforces the contract: summary must stay small.)

Helper fixture: `make_ctx()` returns a MagicMock with `state = {}`.
```

**Expected output:** `work/tests/test_context_registry.py` with 5 passing tests

**Gate — run before Step 2.5:**
```bash
pytest work/tests/test_context_registry.py -v
```
All 5 must pass. A failure here means the registry implementation has a bug.

---

### Step 2.5 — Integration test through session DB

**Open:**
- `work/context_registry.py`
- Work's `DatabaseSessionService` or session service file
- Work's test database configuration
- New file: `work/tests/test_context_registry_integration.py`

**Prompt:**
```
Write an integration test that confirms ContextRegistry survives a round-trip
through DatabaseSessionService (the real SQLite-backed session service).

The test must do exactly these 5 steps:

Step 1 — Create a real session:
    session_service = DatabaseSessionService("sqlite:///test_integration.db")
    session = await session_service.create_session(app_name="work_chatbot", user_id="test_user")

Step 2 — Get a real ToolContext and write to registry:
    # Use ADK's InvocationContext or a test runner to get a real tool_context
    # bound to the session above. Write one turn:
    reg = ContextRegistry()
    reg.write_turn(tool_context, 0, "grant_agent", "test_intent",
                   employee_ids=["G001", "G002"], vesting_date="2026-09-01")

Step 3 — Flush and reload the session (simulates end-of-turn):
    # ADK persists state at end of turn. Simulate by reading session from DB:
    reloaded = await session_service.get_session(
        app_name="work_chatbot", user_id="test_user", session_id=session.id)

Step 4 — Read registry from reloaded session:
    # Bind a new tool_context to reloaded session, read registry:
    ids = reg.get_latest_employee_ids(reloaded_tool_context)
    assert ids == ["G001", "G002"], f"IDs lost in round-trip: {ids}"
    vdate = reg.get_latest_vesting_date(reloaded_tool_context)
    assert vdate == "2026-09-01"

Step 5 — Cleanup:
    # Delete test DB file after test completes.
    import os; os.remove("test_integration.db")

If ADK's session setup for tests is different in this project, adapt the session
creation to match the existing test patterns in this codebase — but keep the
5-step assertion structure identical.
```

**Expected output:** `work/tests/test_context_registry_integration.py` — integration test
that passes when run against real session DB

**Gate — Phase 2 complete:**
```bash
pytest work/tests/test_context_registry_integration.py -v -s
```
Must pass. A failure here means nested dict serialization through SQLite is broken —
the most common cause is ADK serializing `context_registry` as a JSON string instead of
a nested dict on reload. If that happens, wrap `read_registry` with:
```python
raw = tool_context.state.get("context_registry", {})
return json.loads(raw) if isinstance(raw, str) else raw
```

**Phase 2 is complete when:** integration test passes and `update_context` is wired
at every data agent call site.

---
---

## Phase 3 — First Agent Cutover

> **Prerequisite:** Phase 1 gate (shadow mode live, ≥85% agreement) AND Phase 2 gate
> (integration test passing) must both be complete before starting Phase 3.

### Step 3.1 — Feature flag helper

**Open:**
- Work's orchestrator config or settings file
- Work's orchestrator `route_query` file

**Prompt:**
```
Create a feature flag helper function for per-agent planner routing.

Add this to the orchestrator or a shared config module:

    import os

    def is_planner_routing_enabled(agent_name: str) -> bool:
        """
        Returns True if planner-driven routing is enabled for this agent.
        Controlled by env var PLANNER_ROUTING_{AGENT_NAME_UPPER}_ENABLED=1.
        Example: PLANNER_ROUTING_GRANT_AGENT_ENABLED=1
        """
        flag_name = f"PLANNER_ROUTING_{agent_name.upper()}_ENABLED"
        return os.getenv(flag_name) == "1"

Then add a constant listing which agents are eligible for planner routing
(start with just one — the safest first choice):

    PLANNER_ELIGIBLE_AGENTS = [
        "grant_agent",   # Phase 3 first cutover
        # "vesting_agent",    # Phase 4
        # "participant_agent", # Phase 5
    ]
```

**Expected output:** `is_planner_routing_enabled` function available in orchestrator scope,
`PLANNER_ELIGIBLE_AGENTS` list defined

**Gate — run before Step 3.2:**
```bash
python -c "
import os
from work.orchestrator import is_planner_routing_enabled

os.environ['PLANNER_ROUTING_GRANT_AGENT_ENABLED'] = '1'
assert is_planner_routing_enabled('grant_agent') == True
assert is_planner_routing_enabled('vesting_agent') == False

del os.environ['PLANNER_ROUTING_GRANT_AGENT_ENABLED']
assert is_planner_routing_enabled('grant_agent') == False
print('PASS — flag on/off works correctly')
"
```
Must print `PASS`.

---

### Step 3.2 — Wire planner branch for first agent (grant_agent)

**Open:**
- `epm-migration-reference/phase3_first_cutover/route_query_excerpt.py` (annotated pattern)
- `work/planner.py` (Step 1.3 output)
- `work/context_registry.py` (Step 2.1 output)
- Work orchestrator file containing `route_query` and the existing legacy router

**Prompt:**
```
I'm adding a planner-driven routing branch to route_query. The reference pattern
is in route_query_excerpt.py. The existing legacy routing must remain completely
unchanged — I'm adding a new branch that runs BEFORE legacy if the flag is on.

Inside route_query(), after the existing context reads and BEFORE the legacy routing,
add this block:

    # --- PLANNER-DRIVEN ROUTING ---
    plan = _planner.classify(query=query, context_registry=context)
    agent_name = plan.get("route")

    if agent_name in PLANNER_ELIGIBLE_AGENTS and is_planner_routing_enabled(agent_name):
        print(f"[PLANNER] routing to {agent_name} | intent={plan['intent']}")

        # Inject context IDs if prior turn has them and planner says to use them
        agent_query = query
        if plan.get("requires_context"):
            prior_ids = registry.get_latest_employee_ids(tool_context)
            if prior_ids:
                agent_query = f"{query}\nFilter to these IDs: {prior_ids}"

        try:
            result = call_remote_agent(agent_name, agent_query, tool_context)
            _ids = result.get("employee_ids", [])
            update_context(agent_name, _ids, tool_context,
                           vesting_date=result.get("vesting_date"),
                           batch_id=result.get("batch_id"))
            return result
        except Exception as e:
            update_context(agent_name, [], tool_context, summary=f"error: {e}")
            print(f"[PLANNER] error in {agent_name}: {e} — falling through to legacy")
            # Fall through to legacy router below
    # --- END PLANNER-DRIVEN ROUTING ---

    # [existing legacy routing code — unchanged]
    ...

Note: `_planner`, `registry`, `PLANNER_ELIGIBLE_AGENTS`, and `is_planner_routing_enabled`
are already available at module level from Steps 1.5 and 3.1.
The `call_remote_agent` call should use whatever the existing REST wrapper is called in
this file — don't rename it.
```

**Expected output:**
- `route_query` has planner branch ABOVE the legacy router
- When `PLANNER_ROUTING_GRANT_AGENT_ENABLED=1` and planner routes to `grant_agent`,
  the REST call happens and `update_context` is called
- On exception, falls through to legacy router — no 500 error
- All non-grant-agent queries still hit legacy router unchanged

**Gate — run before Step 3.3:**
```bash
# Test 1: flag OFF — should use legacy router
PLANNER_ROUTING_GRANT_AGENT_ENABLED=0 python -c "
from unittest.mock import patch, MagicMock
from work.orchestrator import route_query

ctx = MagicMock(); ctx.state = {}
with patch('work.orchestrator._planner') as mock_p, \
     patch('work.orchestrator.call_remote_agent') as mock_rest:
    mock_p.classify.return_value = {'route': 'grant_agent', 'intent': 'test',
        'split_type': 'operational', 'requires_context': False, 'cross_agent': False}
    route_query('show grants', ctx)
    mock_rest.assert_not_called()   # legacy ran, not planner branch
    print('PASS — flag OFF: legacy router used')
"

# Test 2: flag ON — should call REST and write context
PLANNER_ROUTING_GRANT_AGENT_ENABLED=1 python -c "
from unittest.mock import patch, MagicMock
from work.orchestrator import route_query

ctx = MagicMock(); ctx.state = {}
with patch('work.orchestrator._planner') as mock_p, \
     patch('work.orchestrator.call_remote_agent') as mock_rest, \
     patch('work.orchestrator.update_context') as mock_uc:
    mock_p.classify.return_value = {'route': 'grant_agent', 'intent': 'test',
        'split_type': 'operational', 'requires_context': False, 'cross_agent': False}
    mock_rest.return_value = {'employee_ids': ['G1', 'G2'], 'grants': [...]}
    route_query('show grants', ctx)
    mock_rest.assert_called_once()
    mock_uc.assert_called_once()
    print('PASS — flag ON: REST called, context written')
"
```
Both must print `PASS`.

---

### Step 3.3 — Regression tests for first cutover

**Open:**
- `work/orchestrator.py` (with planner branch from Step 3.2)
- Work's existing grant_agent test queries (if any)
- New file: `work/tests/test_cutover_grant_agent.py`

**Prompt:**
```
Write regression tests for the grant_agent planner cutover. Use pytest.
Patch _planner, call_remote_agent, and update_context throughout.

Write exactly these 4 tests:

1. test_grant_query_routes_to_grant_agent_when_flag_on:
   Input: query "show total grants by type"
   Planner mock returns: route="grant_agent", split_type="operational"
   Flag: PLANNER_ROUTING_GRANT_AGENT_ENABLED=1
   Assert: call_remote_agent called with agent_name="grant_agent"
   Assert: update_context called with agent_name="grant_agent"

2. test_grant_query_uses_legacy_when_flag_off:
   Same query, same planner mock.
   Flag: PLANNER_ROUTING_GRANT_AGENT_ENABLED=0 (or unset)
   Assert: call_remote_agent NOT called via planner branch
   (The legacy router may still call it — that's fine. This test verifies
   the planner branch specifically is skipped.)

3. test_non_grant_query_unaffected:
   Input: query "show vesting dates"
   Planner mock returns: route="vesting_agent"
   Flag: PLANNER_ROUTING_GRANT_AGENT_ENABLED=1  (grant flag on, but query → vesting)
   Assert: call_remote_agent NOT called via planner branch for vesting_agent
   (vesting_agent is not in PLANNER_ELIGIBLE_AGENTS yet)

4. test_context_passthrough:
   Two-turn sequence:
   - Turn 1: query "show grants", planner → grant_agent, REST returns employee_ids=["E1","E2"]
     Assert: update_context called with employee_ids=["E1","E2"]
   - Turn 2: planner returns requires_context=True for same session
     Assert: route_query appends "Filter to these IDs: ['E1', 'E2']" to the agent query
     (mock registry.get_latest_employee_ids to return ["E1","E2"])

Use @pytest.fixture for repeated mock setup.
Each test must be independently runnable (no shared state between tests).
```

**Expected output:** `work/tests/test_cutover_grant_agent.py` with 4 passing tests

**Gate — run before Step 3.4:**
```bash
pytest work/tests/test_cutover_grant_agent.py -v
```
All 4 must pass. A failure in test 3 (non-grant unaffected) is the most dangerous — it
means a query could route to an agent that hasn't been regression-tested yet.

---

### Step 3.4 — Enable in production and verify

**This is an operational step, not a Copilot code step.**

**Pre-flight checklist before flipping the flag:**

- [ ] All 4 tests in `test_cutover_grant_agent.py` pass
- [ ] Shadow mode (Phase 1) shows ≥85% agreement for grant_agent queries
- [ ] Integration test (Phase 2 Step 2.5) passes
- [ ] Baseline metrics recorded: p95 latency for grant_agent queries (last 7 days)

**Enable:**
```bash
# In your deployment config / environment:
PLANNER_ROUTING_GRANT_AGENT_ENABLED=1
# Leave PLANNER_SHADOW_ENABLED=1 as well — now shadow logs show planner vs. planner (self-check)
```

**Monitor for 48 hours:**
```bash
# Agreement rate (should now be ~100% — planner IS the router for grant_agent):
grep "\[PLANNER\] routing to grant_agent" <log> | wc -l

# Error rate — any [PLANNER] error lines falling through to legacy:
grep "\[PLANNER\] error" <log>

# Latency regression — compare p95 for grant_agent queries to baseline
```

**Rollback if needed:**
```bash
PLANNER_ROUTING_GRANT_AGENT_ENABLED=0
# Takes effect immediately. No DB migration. No restart needed.
```

**Phase 3 complete when:** grant_agent has run planner-driven for 48h with no
error-rate regression and latency within 10% of baseline.

**Next:** Repeat Step 3.2 → 3.4 for `vesting_agent`, then `participant_agent`.
Each expansion: add to `PLANNER_ELIGIBLE_AGENTS`, write equivalent regression tests,
enable flag, monitor.

---
---

## Handshake Summary

```
Step 1.1 → 1.2   Gate: PlannerOutput imports and validates (14 fields)
Step 1.2 → 1.3   Gate: get_rag_agent_names() returns work agent names
Step 1.3 → 1.4   Gate: classify() returns dict with split_type (mock or real API)
Step 1.4 → 1.5   Gate: 6 unit tests pass
Step 1.5 → done  Gate: [SHADOW] lines appear in logs, no response change

Step 2.1 → 2.2   Gate: write_turn / read round-trip with mock context
Step 2.2 → 2.3   Gate: update_context writes correct registry entry
Step 2.3 → 2.4   Gate: grep confirms every call_remote_agent has update_context
Step 2.4 → 2.5   Gate: 5 unit tests pass
Step 2.5 → done  Gate: integration test passes through real session DB

Phase 1+2 → 3.1  Gate: both Phase 1 and Phase 2 final gates passed
Step 3.1 → 3.2   Gate: flag on/off works correctly
Step 3.2 → 3.3   Gate: both mock gate tests pass (flag on + flag off)
Step 3.3 → 3.4   Gate: 4 regression tests pass
Step 3.4 → next  Gate: 48h monitoring with no error regression
```
