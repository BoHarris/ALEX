import { Navigate } from "react-router-dom";
import Dashboard from "./Dashboard";
import { useCurrentUser } from "../hooks/useLoadUser";

export default function Admin() {
  const { user, loading } = useCurrentUser();

  if (loading) {
    return (
      <div className="page-shell flex min-h-[60vh] items-center justify-center px-6">
        <div className="surface-card px-6 py-4 text-sm text-app-secondary">
          Loading admin workspace...
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.permissions?.can_access_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Dashboard initialTab="analytics" showAdminRail />;
}
