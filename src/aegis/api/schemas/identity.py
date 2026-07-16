# src/aegis/api/schemas/identity.py
"""
API identity boundary schema.

``RequestIdentityContext`` is the shape through which caller identity
would enter AEGIS from HTTP. No authentication mechanism exists yet
(see CLAUDE.md "Development status"): every field is optional and,
today, always resolves to ``None`` -- see
``aegis.api.dependencies.get_identity_context`` for how a future
authentication adapter attaches a populated context to
``request.state`` before this schema is ever constructed with real
values.

This is a pure API-boundary DTO, not a runtime domain contract. It is
intentionally NOT threaded into ``ClinicalNoteSubmission``,
``PhysicianDecisionSubmission``, ``AegisWorkflowState``, or
``ClinicalDecision`` -- none of those define an actor/institution field
today (see ``runtime_domain_contracts/clinical_decision.md``'s Identity
section), and adding one is an architectural decision for the contract
owner, not something an API slice makes unilaterally. Routers accept
this context so a future authorization/audit layer has somewhere to
attach; they must never synthesize a default actor (e.g. a hardcoded
"doctor"/"admin") to fill it in, and must never read HTTP headers or
``Request`` objects directly to derive identity themselves -- that
stays inside ``get_identity_context``.
"""

from __future__ import annotations

from pydantic import BaseModel


class RequestIdentityContext(BaseModel):
    """
    Caller identity as observed at the API boundary.

    ``actor_id``/``actor_type`` identify who is acting (e.g. a
    physician); ``institution_reference`` scopes them to an
    institution. All three are extension points for a future
    authentication adapter -- none are populated, validated, or
    trusted as authenticated truth by anything in this codebase today.
    An all-``None`` context means "identity not yet established," not
    "anonymous" or "unauthorized"; no authorization decision is made
    here or implied by this schema.
    """

    actor_id: str | None = None
    actor_type: str | None = None
    institution_reference: str | None = None
