import { useParams } from "react-router-dom";

export function DecisionDetailPage() {
  const { threadId } = useParams<{ threadId: string }>();

  return (
    <section>
      <h1>Decision Detail</h1>
      <p>
        Placeholder for a single case's review/decision detail (
        <code>GET /api/v1/reviews/{threadId ?? "{thread_id}"}</code>). Workflow UI is not
        implemented yet.
      </p>
    </section>
  );
}
