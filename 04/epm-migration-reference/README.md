# EPM Orchestrator → Work Chatbot Migration Reference

**Purpose**: Migration reference only — not for import. Built from the home EPM chatbot project
(`~/PycharmProjects/epm-chatbot`) as Copilot context for the work port. Once migration is
complete, delete this folder.

## How to use

Open the relevant files in tabs adjacent to where you're writing the work versions. Copilot reads
open tabs as primary context and will pick up patterns, naming, and signatures automatically.
Annotated `# TODO[port]:` comments mark every line that needs changing — use them as a checklist.

## What's included

| Phase | What it ports | Depends on |
|---|---|---|
| Phase 1 | LLM-based planner (structured routing decisions) | Nothing — can start now |
| Phase 2 | Context registry (cross-turn key passing) | Nothing — can start now |
| Phase 3 | First agent cutover (planner drives one real agent) | Phase 1 + Phase 2 both done |

**Phase 1 and Phase 2 can be built in parallel.** Phase 3 requires both.

## Gemini → OpenAI swap pattern

Every place the planner calls the Gemini SDK, the equivalent OpenAI call looks like this:

**Before (Gemini):**
```python
from google import genai
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config={"system_instruction": SYSTEM_PROMPT},
)
text = response.text.strip()
# strip markdown fences before json.loads ...
result = json.loads(text)
```

**After (OpenAI structured output):**
```python
from openai import OpenAI
client = OpenAI()  # reads OPENAI_API_KEY from env automatically
response = client.chat.completions.parse(
    model="gpt-5",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ],
    response_format=PlannerOutput,  # Pydantic model — schema enforced at model level
)
result = response.choices[0].message.parsed  # already a PlannerOutput instance
```

The markdown-stripping logic (`if text.startswith("```")`) disappears entirely — OpenAI
structured outputs never wrap in fences.

## What is NOT included

**Concern detection / enrichment** (`enrich_from_concerns`, `concern_registry.py`, the
`CONCERNS_JSON:` text extraction pattern): this is WIP at home and broken due to an AgentTool
limitation — AgentTool returns text, so structured data has to be smuggled out via a regex marker.
At work, agents are called over REST and return JSON natively, so the whole problem evaporates.
Revisit concern detection after Phase 5 (cross-agent joins) is stable at work — the logic will be
cleaner because you can use a proper return schema instead of the text marker hack.

## Source files used

All content was read verbatim from `~/PycharmProjects/epm-chatbot/app/agent/orchestrator/` on
2026-05-07. If the home project has changed since, re-read the source before relying on these
copies.

## Reminder

Delete `~/epm-migration-reference/` after the work migration is complete.
