# Derived from the output format specification in planner.py's ROUTING_SYSTEM_PROMPT.
# No Pydantic model existed in the home project — the planner returned raw JSON
# and called json.loads() manually. This schema is provided so OpenAI's
# structured-output mode (chat.completions.parse) can enforce it at the model level,
# eliminating the markdown-strip + json.loads pattern entirely.
#
# ACTION REQUIRED before use:
#   1. Verify every field name matches what the work orchestrator expects.
#   2. Replace home agent names in Literal types with work agent names.
#   3. See TODO[port]: comment on join_key below.

from typing import Literal, Optional
from pydantic import BaseModel


class PlannerOutput(BaseModel):
    split_type: Literal["rag", "operational", "combo"]
    route: str  # agent name, "combo", or "context_only"
    intent: str  # human-readable label for this routing decision

    requires_context: bool  # True → planner expects prior turn data to be relevant
    cross_agent: bool       # True → result of step_1 is passed as filter to step_2

    # Cross-agent sequencing (operational only)
    step_1: Optional[str] = None   # first agent to call; null if not cross-agent
    step_2: Optional[str] = None   # second agent to call; null if not cross-agent

    # TODO[port]: join_key Literal may need widening for work's domain.
    # Home only joins on employee_id or grant_id.
    # Work may have additional entity types (e.g., account_id, position_id).
    # Widen the Literal or change to Optional[str] if needed.
    join_key: Optional[Literal["employee_id", "grant_id"]] = None
    join_field: Optional[str] = None  # specific field name to join on
    operation: Optional[Literal["intersect"]] = None  # set operation for context_only
    context_key: Optional[Literal["employee_ids"]] = None

    # Combo routing
    rag_agent: Optional[str] = None        # which RAG agent handles the doc part
    rag_query: Optional[str] = None        # sub-query for the RAG agent
    operational_query: Optional[str] = None  # sub-query for the data agent
