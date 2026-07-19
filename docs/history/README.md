# docs/history — Superseded & historical documentation

These documents are **retained for historical / portfolio context** and do **not** describe
the current system. They fall into two groups:

## Superseded snapshots / duplicates

- **`runtime_domain_contract.md`** — a point-in-time architectural summary from just after
  offline knowledge compilation ("Ready to Begin Runtime Orchestration"). The LangGraph
  workflow is now fully wired, and this duplicates higher-authority sources. Current truth:
  `domain_contract_finalized.md`, `runtime_domain_contracts/`, `docs/orchestration.md`.
- **`application-service-layer.md`** — accurate but a duplicate of
  `application_service_finalized.md` + `application_service_contracts/` (the authoritative
  home). Kept here to preserve one authoritative home per concept.

## Historical diagrams (dropped trial-matching design)

- **`conceptual_execution_map.mmd`**, **`data_transformation.mmd`**, **`state_machine.mmd`**
  — depict an earlier LoadPatient → ExtractSymptoms → … → MatchTrials pipeline with an
  "Approved?" branch. None of that was built. The current diagrams live at the repo root:
  `workflow_state_machine.mmd` and `data_transformation.mmd`. Clinical trial matching is a
  **Future v2** capability.

## Frontend mockups

- **`frontend/DashboardLayout.md`**, **`frontend/NewDashboardLayout.md`** — ASCII mockups
  referencing `Dashboard.tsx` / `ReviewConsole.tsx` components that were never built. The
  shipped UI is a feature-based React tree (`frontend/src/features/…`:
  `clinical-submission`, `review-queue`, `decision-detail`, `workflow-visibility`).

For the current architecture, start at `README.md`, `system_architecture_v2.md`, and
`docs/architecture.md`.
