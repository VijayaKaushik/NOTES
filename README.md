# NOTES
## NLP Parser  --->  NLP Parser → Intent Classifier → Schema-Aware SQL Generator → Database





# Agent System Terminology Mapping

This document defines the canonical terminology for the orchestrator and all specialized agents. When users use synonyms or alternative terms, the orchestrator must normalize them to the canonical terms before delegating to agents.

## Purpose
- Ensure consistent communication between orchestrator and agents
- Map user vocabulary to agent-expected terminology
- Reduce delegation failures due to terminology mismatches
- Provide a single source of truth for domain language

---

## Release Management Domain

### Primary Terms

| Canonical Term | Synonyms / Alternatives | Notes |
|---------------|------------------------|-------|
| `release date` | vesting date, launch date, go-live date, deployment date, ship date | The date when software is released to users |
| `release version` | version, build, build number, version number | Format: Major.Minor.Patch (e.g., 2.5.0) |
| `release` | deployment, rollout, launch, ship | Noun: the software package; Verb: use "deployment" |
| `next release` | upcoming release, future release, next version, next build | The immediately following scheduled release |
| `features` | enhancements, new features, capabilities, functionality, improvements | New or improved capabilities in a release |
| `release notes` | changelog, change log, what's new, release documentation | Documentation of changes in a release |
| `deployment timeline` | rollout schedule, deployment plan, release schedule | The phased plan for releasing software |

### Usage Examples
```
User: "When is the vesting date?"
Normalize to: "When is the release date?"
Agent query: get_release_date()

User: "What's in the next build?"
Normalize to: "What features are in the next release version?"
Agent query: get_features_list(release="next")
```

---

## Reporting Domain

### Primary Terms

| Canonical Term | Synonyms / Alternatives | Notes |
|---------------|------------------------|-------|
| `region` | territory, area, zone, location, geography | Geographic or organizational region |
| `category` | report type, report category, template type, classification | How reports are classified |
| `scheduled report` | recurring report, automated report, periodic report | Reports that run on a schedule |
| `template` | report template, report format, report definition | Reusable report configuration |
| `analysis` | breakdown, summary, statistics, metrics, insights | Analytical view of data |
| `historical data` | past data, previous reports, archived reports | Data from past time periods |

### Region Code Mappings

| User Input | Canonical Code | Full Name |
|-----------|---------------|-----------|
| US West, West Coast, Western US | `US-WEST` | United States West |
| US East, East Coast, Eastern US | `US-EAST` | United States East |
| EMEA, Europe | `EMEA` | Europe, Middle East, Africa |
| APAC, Asia Pacific | `APAC` | Asia Pacific |
| LATAM, Latin America | `LATAM` | Latin America |

### Usage Examples
```
User: "Give me a breakdown of sales in the Western territory"
Normalize to: "Provide analysis of sales reports for region US-WEST"
Agent query: get_report_history(region="US-WEST", category="Sales")

User: "What automated reports do we have?"
Normalize to: "What scheduled reports exist?"
Agent query: list_scheduled_reports()
```

---

## Personnel & Organization Domain

### Primary Terms

| Canonical Term | Synonyms / Alternatives | Notes |
|---------------|------------------------|-------|
| `EPM` | Engineering Program Manager, Program Manager, PMO Manager | Engineering Program Manager role |
| `project manager` | PM, project lead, project owner | Person managing a project |
| `account owner` | account manager, client lead, customer success manager | Person responsible for client account |
| `technical lead` | tech lead, TL, lead engineer, senior engineer | Technical leadership role |
| `stakeholder` | decision maker, business owner, sponsor | Person with vested interest |

### Usage Examples
```
User: "Who's the Program Manager for this release?"
Normalize to: "Who is the EPM for this release?"
Agent query: get_personnel_info(role="EPM", project_id=...)

User: "Find the account manager for Johnson Corp"
Normalize to: "Find the account owner for Johnson Corp"
Agent query: search_personnel(account="Johnson Corp", role="account owner")
```

---

## Document & Artifact Domain

### Primary Terms

| Canonical Term | Synonyms / Alternatives | Notes |
|---------------|------------------------|-------|
| `documents` | documentation, docs, files, artifacts | General term for stored documents |
| `specification` | spec, requirements doc, requirements, PRD | Product/feature specifications |
| `project documents` | project files, project artifacts, project materials | Documents related to a project |
| `technical documentation` | technical docs, tech docs, API docs | Technical reference materials |

### Usage Examples
```
User: "Find the spec for feature X"
Normalize to: "Find the specification for feature X"
Agent query: search_documents(type="specification", keyword="feature X")

User: "Where are the project artifacts?"
Normalize to: "Where are the project documents?"
Agent query: search_documents(type="project documents")
```

---

## Temporal Terms

### Relative Time Expressions

| User Expression | Normalization Strategy | Example |
|----------------|----------------------|---------|
| `next` | Query agent for "next" or convert to date | "next release" → get_next_release() |
| `upcoming` | Same as "next" | "upcoming deployment" → "next release" |
| `last` | Convert to date range or use "previous" | "last month" → "2025-12-01 to 2025-12-31" |
| `previous` | Use "previous" or convert to specific identifier | "previous version" → get_previous_version() |
| `current` | Query for "current" state | "current release" → get_current_release() |
| `this week/month/quarter` | Convert to specific date range | "this month" → "2026-01-01 to 2026-01-31" |

### Fiscal Periods

| User Term | Date Range (assuming fiscal year = calendar year) |
|-----------|---------------------------------------------------|
| Q1 | January 1 - March 31 |
| Q2 | April 1 - June 30 |
| Q3 | July 1 - September 30 |
| Q4 | October 1 - December 31 |
| H1 | January 1 - June 30 |
| H2 | July 1 - December 31 |

### Usage Examples
```
User: "Show me reports from last quarter"
Current date: January 12, 2026
Normalize to: "Show me reports from 2025-10-01 to 2025-12-31"
Agent query: get_report_history(start_date="2025-10-01", end_date="2025-12-31")

User: "What's the upcoming launch?"
Normalize to: "What is the next release?"
Agent query: get_next_release()
```

---

## Action Verbs

### Common User Actions → Agent Operations

| User Verb | Agent Operation | Domain |
|-----------|----------------|--------|
| schedule, set up, create schedule | `schedule_report()` | Reporting |
| find, search, look for, get | `search_*()` or `get_*()` | All |
| list, show all, what are | `list_*()` | All |
| create, make, build, generate | `create_*()` | Reporting, Documents |
| update, modify, change, edit | `update_*()` | All |
| delete, remove, cancel | `delete_*()` | All |
| analyze, break down, summarize | `analyze_*()` or `get_*_analysis()` | Reporting |

---

## Implementation Guidelines

### For the Orchestrator

1. **Pre-processing Step**: Before delegating to any agent:
   ```
   - Scan user input for all terms in this mapping
   - Replace with canonical terms
   - Convert relative dates to absolute date ranges when possible
   - Normalize region names to codes
   ```

2. **Context Preservation**: 
   - Maintain user's original terminology in responses back to user
   - Use canonical terms only in agent communications

3. **Ambiguity Handling**:
   - If a term could map to multiple canonical terms, ask for clarification
   - Example: "manager" could be "project manager", "account owner", or "EPM"

4. **Logging**: 
   - Log all terminology transformations for debugging
   - Track unmapped terms to expand this dictionary

### For Agent Developers

1. **Tool Parameter Naming**: Use canonical terms from this document in tool parameters
2. **Documentation**: Reference this document in agent documentation
3. **Error Messages**: When rejecting queries, suggest correct canonical terminology
4. **Feedback**: Report commonly missed synonyms to expand this mapping

---

## Maintenance

### Adding New Terms

When adding new synonyms or canonical terms:

1. Add to the appropriate domain section
2. Include usage examples
3. Update the orchestrator prompt to reference new terms
4. Notify all agent teams of changes
5. Version this document (Current: v1.0)

### Review Cycle

- Review quarterly
- Update based on user query logs
- Incorporate feedback from agent teams
- Add newly identified synonyms

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-12 | Initial terminology mapping |

---

## Contact

For questions or suggestions about terminology:
- Orchestrator team: [contact]
- To propose new terms: [process]
