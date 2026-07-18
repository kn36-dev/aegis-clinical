import { Link } from "react-router-dom";

/** Rendered for any URL that doesn't match a known route. */
export function NotFoundPage() {
  return (
    <section className="not-found-page">
      <h1>Page not found</h1>
      <p>The page you're looking for doesn't exist.</p>
      <Link to="/submit">Return to Clinical Submission</Link>
    </section>
  );
}
