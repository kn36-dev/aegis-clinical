export function ReviewQueuePage() {
  return (
    <section>
      <h1>Review Queue</h1>
      <p>
        Placeholder for the physician review queue. The backend does not yet expose a
        listing endpoint for pending reviews — the only implemented review route,{" "}
        <code>GET /api/v1/reviews/{"{thread_id}"}</code>, fetches a single workflow's
        state by id. This page is not wired to real data until that listing endpoint
        exists.
      </p>
    </section>
  );
}
