import { NavLink, Outlet } from "react-router-dom";
import { ErrorBoundary } from "./ErrorBoundary";

const NAV_ITEMS = [
  { to: "/submit", label: "Clinical Submission" },
  { to: "/reviews", label: "Review Queue" },
];

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <span className="app-shell__title">AEGIS Clinical</span>
        <nav className="app-shell__nav" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} className="app-shell__nav-link">
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="app-shell__content">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
