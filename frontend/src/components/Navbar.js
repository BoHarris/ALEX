import React from "react";
import { Link } from "react-router-dom";
import LogoutButton from "./logout";
import AccessibilityPanel from "./AccessibilityPanel";
import { getAccessToken } from "../utils/tokenStore";
import { useCurrentUser } from "../hooks/useLoadUser";

function Navbar() {
  const hasToken = Boolean(getAccessToken());
  const { user } = useCurrentUser();
  const isAdmin = Boolean(user?.permissions?.can_access_admin);

  return (
    <header className="border-b border-app bg-app/95 px-6 py-4 text-app shadow-md backdrop-blur">
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-6" aria-label="Primary navigation">
        <div className="text-xl font-bold tracking-[0.2em]">
          <Link to="/" aria-current={window.location.pathname === "/" ? "page" : undefined}>
            ALEX
          </Link>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <Link to="/" className="text-app-secondary transition-colors hover:text-app" aria-current={window.location.pathname === "/" ? "page" : undefined}>Home</Link>
          <Link to="/pricing" className="text-app-secondary transition-colors hover:text-app" aria-current={window.location.pathname === "/pricing" ? "page" : undefined}>Plans</Link>
          <Link to="/trust" className="text-app-secondary transition-colors hover:text-app" aria-current={window.location.pathname === "/trust" ? "page" : undefined}>Trust</Link>
          <Link to="/privacy" className="text-app-secondary transition-colors hover:text-app" aria-current={window.location.pathname === "/privacy" ? "page" : undefined}>Privacy</Link>
          <Link to="/employee-login" className="text-app-secondary transition-colors hover:text-app" aria-current={window.location.pathname === "/employee-login" ? "page" : undefined}>Employee</Link>
          <Link to="/about" className="text-app-secondary transition-colors hover:text-app" aria-current={window.location.pathname === "/about" ? "page" : undefined}>About</Link>
          <Link to="/careers" className="text-app-secondary transition-colors hover:text-app" aria-current={window.location.pathname === "/careers" ? "page" : undefined}>Careers</Link>
          {hasToken ? <Link to="/dashboard" className="text-app transition-colors hover:text-app-secondary" aria-current={window.location.pathname === "/dashboard" ? "page" : undefined}>Dashboard</Link> : null}
          {hasToken && isAdmin ? <Link to="/admin" className="text-app transition-colors hover:text-app-secondary" aria-current={window.location.pathname === "/admin" ? "page" : undefined}>Admin</Link> : null}
          {!hasToken ? <Link to="/login" className="text-app-secondary transition-colors hover:text-app" aria-current={window.location.pathname === "/login" ? "page" : undefined}>Login</Link> : null}
          {!hasToken ? <Link to="/register" className="btn-secondary-app px-4 py-1.5 text-sm" aria-current={window.location.pathname === "/register" ? "page" : undefined}>Get Started</Link> : null}
          <AccessibilityPanel />
          <LogoutButton />
        </div>
      </nav>
    </header>
  );
}
export default Navbar;
