## {Agent Name}

### Identity
One sentence. What this agent IS, not what it does.

### Owns (authoritative for)
- Topic / domain area
- Topic / domain area

### Does NOT own (route elsewhere)
- Topic → {other_agent}
- Topic → {other_agent}

### Data schema
Grouped fields the agent can answer questions about.
  Identity & Employment: participantId, firstName, ...
  Compliance: kycStatus, taxStatus, ...

### Capabilities
- {verb} {object} — e.g. "filter participants by status"
- {verb} {object} — e.g. "aggregate counts by country"

### Trigger phrases
Words/intents that should route here:
  "tax summary", "withholding", "release date", ...

### Counter-triggers (looks similar, routes elsewhere)
- "who is the CRM contact" → document_agent (not participant_agent)
- "how do I reset password" → document_agent (not participant_agent)

### Examples
✅ "List participants with pending KYC" → handled
✅ "Tax summary for next release" → handled
❌ "What's the SLA for KYC issues?" → route to document_agent

### Returns
Shape of typical output — keys, summary fields. This is what the
orchestrator and downstream agents can consume.
  { employee_ids: [...], counts: {...}, summary: "..." }
