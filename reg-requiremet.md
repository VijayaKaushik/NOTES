# EPM Regression — Ground Truth Manager
## Product Requirements

---

## What this app is

This is an internal web tool for managing test questions used in regression
testing of an AI orchestrator. The orchestrator routes equity plan management
questions to the right AI agents. For each question we need to record what
the correct behaviour should look like — this is called the ground truth.

The tool lets us author those ground truth records, browse them, filter them,
and view a dashboard that slices them across different dimensions so we can
understand the coverage and shape of our test suite.

It is a single-user internal tool. No login or authentication required.

---

## Tech stack

- Python 3.12
- FastAPI as the web framework
- Jinja2 for HTML templates — every page is a full server-rendered HTML page
- openpyxl for reading and writing the Excel file
- uv as the package manager
- Vanilla JavaScript for one purpose only — showing and hiding form fields
  based on what the user selects. No API calls, no fetch, no state management
  in JavaScript. Every form submission is a regular HTML form POST that
  redirects on success.

---

## Storage

All data lives in a single Excel file called ground_truth.xlsx with two
sheets: one for questions and one for agents.

The storage layer must be isolated in one file called storage.py. All reads
and writes go through that file. When we switch to Postgres later only
storage.py changes — the routes, templates, and business logic stay untouched.

On startup: read both sheets from ground_truth.xlsx into memory. If the file
does not exist, create it with two empty sheets named questions and agents,
write the two seed agent rows described below, then start the server.

On every save: read the full file first, update only the relevant sheet, then
write all sheets back together. Never overwrite a sheet you did not touch.

Run command:
```
uv run uvicorn regression.main:app --reload --port 8080
```

---

## Project structure

```
regression/
├── main.py               ← FastAPI app and all route definitions
├── storage.py            ← all Excel read/write logic, isolated here
├── schemas.py            ← Pydantic models for validation
├── templates/
│   ├── base.html             ← shared sidebar and topbar layout
│   ├── questions/
│   │   ├── list.html         ← question list with filters
│   │   └── form.html         ← add and edit form
│   ├── dashboard/
│   │   └── index.html        ← dashboard with group-by
│   └── agents/
│       └── list.html         ← agent registry
└── static/
    ├── style.css
    └── form.js               ← conditional show/hide only
```

---

## Questions — fields

Every question has the following fields. In the form, group them into the
named sections below.

**Basic info**

- Question ID: auto-generated on save, read-only, format Q-001 Q-002 and
  so on padded to three digits
- Question text: the exact question the admin would type to the orchestrator
- Category: dropdown — vesting, participant, grant, cross_agent,
  user_guidance, client_ops, out_of_scope, equity_not_built
- Priority: dropdown — high, medium, low. Default is medium
- Authored by: free text
- Tags: free text, comma separated, for example routing, guardrail, kyc
- Active: checkbox, default checked. Inactive questions are excluded from
  test runs but still stored
- Notes: free text for authoring notes and known traps about this question

**Scope**

This is the most important field. It determines which other sections of the
form are shown.

- Expected scope: dropdown with three options
  - in_scope — the orchestrator should handle this by calling an agent
  - equity_not_built — valid equity topic but no agent handles it yet
  - out_of_scope — nothing to do with equity plan management
- Scope notes: optional free text explaining the classification decision

**Routing** — show this entire section only when expected scope is in_scope

- Expected agents: one checkbox per active agent in the agent registry.
  The user selects which agents should be called for this question
- Expected route type: never set by the user. Derive it server-side from
  how many agents are selected. One agent selected means single. Two or more
  agents selected means cross_agent. Display as read-only text in the form
  so the user can see the derived value
- Scope level: dropdown — release, client, grant, participant. Release means
  the question is scoped to a specific vesting event. Client means it applies
  across all participants for the whole client

**Sub-questions** — show this sub-section only when two or more agents are
selected

For each selected agent show one textarea labelled with the agent name. The
user writes the exact question fragment that should be sent to that agent,
word for word with no rephrasing. Show a note under each textarea reminding
the user not to rephrase.

**Guardrail** — show this section only when expected scope is not in_scope

- Guardrail type: dropdown — off_topic, equity_not_built, email_misuse,
  impersonation, fabrication_request
- Scope level: same dropdown as in the routing section

**Clarification**

- Clarification needed: checkbox. True when the question is genuinely
  ambiguous and the orchestrator should ask one short clarifying question
  before routing rather than guessing
- Ambiguity reason: textarea, shown only when clarification needed is checked.
  The user explains what is ambiguous and what the orchestrator should ask

**Session sequencing**

- Retain session: checkbox. When checked this question continues the same
  conversation session as the previous question in the list. Used for testing
  multi-turn conversations where the orchestrator should remember context from
  the prior turn
- If previous failed: dropdown — block or run. Shown only when retain session
  is checked. Block means skip this question and mark it as blocked if the
  previous question failed. Run means run it regardless

---

## Agents — fields

Each agent has a name such as release_agent stored in snake_case, a
description of one or two sentences about what the agent handles, a phase
number as an integer starting at 1 for which development phase the agent
was added, and an active flag for whether it appears in the question form.

Seed data written on first run if the agents sheet is empty:
- release_agent, phase 1, active: handles vesting schedules, release events,
  tax calculations, batch creation and approval workflows
- document_agent, phase 1, active: handles client-specific documentation,
  contacts, SLAs, policies, and how-to guides

---

## Question ID generation

When saving a new question read all existing question IDs from the questions
sheet, find the highest number, add one, and format as Q-XXX with zero
padding to three digits. If no questions exist yet start at Q-001.

---

## Validation — enforced server-side

- Question text, expected scope, and category are required on every question
- When expected scope is in_scope, at least one agent must be selected
- When two or more agents are selected, every selected agent must have a
  non-empty sub-question textarea
- When clarification needed is checked, ambiguity reason must be filled in
- When retain session is checked, if previous failed must have a value

If validation fails re-render the form with the submitted values preserved
and an error message shown inline next to each field that failed. Never lose
the user's input on a validation error.

---

## Views

### Questions list

This is the default landing page at the root URL.

In the top right show two buttons: Load sample data and Add question. Load
sample data inserts a set of pre-written example questions covering the main
question types so the user can see the tool working without authoring anything
first. The sample questions should cover at least one example of each scope
value, one cross-agent question, one guardrail question, one question with
clarification needed, and one sequential question.

Below the topbar show a filter bar with a text search box that searches
question text and question ID, and dropdowns to filter by scope, category,
priority, and active status. All filters work by reloading the page with the
filter values as URL query parameters so any filtered view is bookmarkable.

Below the filter bar show five count cards for the currently filtered set:
total questions, in scope, guardrail tests, cross-agent, and sequential.

The main content is a table with these columns:
- Question ID in monospace font
- Question text truncated to two lines with the full text visible on hover
- Scope badge coloured green for in_scope, amber for equity_not_built,
  red for out_of_scope
- Route type badge coloured blue for single, purple for cross_agent,
  grey dash when not applicable
- Agent tags shown as small dark pills, one per expected agent
- Priority badge coloured red tint for high, amber tint for medium,
  green tint for low
- A chain link symbol in the session column if retain session is true
- An active dot — green when active, grey when inactive
- Edit button and Delete button

### Add and edit form

The form renders the field groups as visible labelled sections with dividers
between them. Conditional sections show and hide via JavaScript toggling CSS
display — no page reload for show/hide.

On successful save redirect to the questions list with a success flash message.
On validation failure re-render the form with errors shown inline.

When editing an existing question all fields are pre-filled with the current
values. The question ID field is always read-only.

### Agent registry

A page showing all agents in a table with columns for name, description,
phase, active status, and how many questions reference this agent.

At the top of the page is a small inline form to add a new agent with inputs
for name, description, and phase and an Add button.

The remove button for each agent is disabled if that agent is referenced by
any questions. Show a tooltip on the disabled button saying the agent must
be removed from all questions first. Removing an agent that is not used by
any questions removes it from the Excel file and from the question form
checkboxes immediately.

### Dashboard

The dashboard has one main control in the topbar: a group-by dropdown. The
group-by selection changes how all data on the page is sliced. Options are:

- Category
- Scope
- Route type
- Priority
- Scope level
- Agent
- Guardrail type
- Session sequential
- Clarification needed

The default group-by on first load is Category.

The dashboard has three blocks stacked vertically.

**Block 1 — Summary cards**

Always shown regardless of group-by. Six metric cards in a row showing counts
across all active questions regardless of any group-by selection:
- Total active questions
- In scope
- Guardrail tests
- Cross-agent
- Sequential
- High priority

**Block 2 — Ground truth breakdown**

A horizontal bar chart where each row is one value of the selected group-by
dimension. Each bar is proportional to the count of questions in that group.
Show the count number and the percentage of total active questions at the
right end of each bar.

Colour the bars meaningfully. When grouped by scope use the same green, amber,
red as the table badges. When grouped by route type use blue for single and
purple for cross-agent. For all other groupings use a consistent blue.

When grouping by agent a cross-agent question belongs to multiple agents so
it must be counted in each relevant agent's row.

Below the chart show a detail table with the same rows and these columns:
group value label, count, percentage of total, in scope count, guardrail
count, cross-agent count, sequential count, high priority count.

**Block 3 — Section coverage matrix**

A grid showing which of the seven prompt sections are exercised by questions
in each category.

Rows are each category value that has at least one question. Columns are
the seven sections:
- S1 Scope classification
- S2 Routing accuracy
- S3 Professional response
- S4 Sub-question fidelity
- S5 No generic knowledge
- S6 No internals revealed
- S7 Clarification

A section is exercised by a question according to these rules:
- S1 every question exercises this section
- S2 only in-scope questions
- S3 every question
- S4 only cross-agent questions
- S5 only in-scope questions
- S6 every question
- S7 only questions where clarification needed is true

Show a filled green circle with the count when there are questions in that
cell. Show an empty grey circle when the section is applicable to this
category but zero questions currently exercise it — this signals a coverage
gap. Show a dash when the section is not applicable to this category at all.

---

## Export

Provide two export links in the sidebar.

Export to Excel downloads ground_truth.xlsx as it is on disk. Filename
includes today's date: ground_truth_YYYY-MM-DD.xlsx

Export to JSON downloads the questions sheet as a JSON array compatible with
the ground_truth.json format used by the Python evaluator. Each question is
one JSON object. Arrays such as expected_agents are proper JSON arrays not
pipe-separated strings. The sub_questions field is a proper JSON object.
Filename is ground_truth.json.

---

## Flash messages

After every POST action show a flash message at the top of the content area.
Use green for success, red for error, amber for warning.

Example messages:
- Question Q-042 saved.
- Question Q-042 deleted.
- Agent participant_agent added.
- Cannot remove release_agent — used in 14 questions.
- Validation error: sub-questions are required for all selected agents.

Pass flash messages via a URL query parameter on the redirect. Render once
on the next page load then discard.

---

## Page layout

Fixed sidebar on the left 220px wide with a dark navy background. Main
content area fills the remaining width.

Sidebar top: app name and subtitle. Navigation links: Questions, Dashboard,
Agent Registry. Below navigation: export links for Export to Excel and
Export to JSON. Sidebar bottom: a row of small pills showing the names of
currently active agents so the user can see at a glance which agents are
configured.

Main area: a topbar with the page title on the left and the primary action
button on the right. Page content below the topbar. Flash message rendered
at the top of the page content when present.

---

## What is not in scope for this version




Updated requirements sentences to replace
In the form section replace:

Category: dropdown — vesting, participant, grant, cross_agent, user_guidance, client_ops, out_of_scope, equity_not_built

With:

Category: multi-select checkboxes — vesting, participant, grant, client_ops, user_guidance. At least one must be selected. A question can belong to multiple categories when it spans more than one topic domain.

In the storage section replace any mention of category as a single value with:

Category is stored as a comma-separated string in Excel and as a JSON array in the JSON export.

In the dashboard section add this note under Block 2:

When grouping by category, a question with multiple categories is counted in each relevant category row, the same way a cross-agent question is counted in each relevant agent row.

In the filter bar section replace:

dropdowns to filter by scope, category, priority, and active status

With:

dropdowns to filter by scope, category, priority, and active status. The category filter matches any question that includes the selected category — a question with categories vesting and participant appears in both the vesting filter result and the participant filter result.

- Run results — will be added later as a third Excel sheet, an import route,
  and a fourth dashboard block
- Authentication or user accounts
- Multi-user concurrent editing
- Any database — storage is Excel only for now, Postgres comes later via
  a swap of storage.py only
