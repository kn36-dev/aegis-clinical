import { Link } from "react-router-dom";

/**
 * Application entry point. Static and informational only — there is no
 * backend dashboard/aggregate endpoint, so this page fetches nothing and
 * shows no counts, metrics, or workflow data.
 */
export function DashboardPage() {
  return (
    <section className="dashboard-page">
      <h1>AEGIS Clinical</h1>
      <p>
        AEGIS Clinical turns unstructured clinical notes into structured ICD-11
        classifications. A deterministic pipeline retrieves and ranks candidate codes as
        evidence; a bounded AI reasoning step proposes recommendations from that evidence
        alone — it has no direct access to the underlying clinical data.
      </p>
      <p>
        Every AI-generated recommendation is routed to a physician for review before it is
        accepted, modified, or rejected. Nothing is written to the clinical record without
        that human-in-the-loop decision.
      </p>
      <p className="dashboard-page__actions">
        <Link to="/submit">Submit a clinical note</Link>
        <Link to="/reviews">Open the review queue</Link>
      </p>
    </section>
  );
}
