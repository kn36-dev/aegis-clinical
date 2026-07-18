export function ReviewQueuePage() {
  return (
    <section>
      <h1>Review Queue</h1>
      <p>
        Inspecting a single case&apos;s review state and submitting a physician decision are both
        fully implemented — see <code>/reviews/{"{workflow_id}"}</code>, reachable from a clinical
        submission&apos;s result.
      </p>
      <p>
        Listing every case awaiting review is intentionally not implemented here. Enumerating
        pending reviews across workflows is a backend capability — it needs its own
        authorization-aware, persistence-backed listing/monitoring contract (see{" "}
        <code>GET /api/v1/workflows/{"{workflow_id}"}</code> in{" "}
        <code>api_contract_plan.md</code>, not yet built) — not something this page can
        substitute for with client-only state.
      </p>
    </section>
  );
}
