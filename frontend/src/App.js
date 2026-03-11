import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useEffect } from "react";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Login from "./pages/Login";
import EmployeeLogin from "./pages/EmployeeLogin";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard"; // or wherever your file lives
import Admin from "./pages/Admin";
import About from "./pages/About";
import Careers from "./pages/Careers";
import Trust from "./pages/Trust";
import Pricing from "./pages/Pricing";
import Privacy from "./pages/Privacy";
import ComplianceLayout from "./pages/compliance/ComplianceLayout";
import ComplianceOverviewPage from "./pages/compliance/ComplianceOverviewPage";
import ComplianceEmployeesPage from "./pages/compliance/ComplianceEmployeesPage";
import CompliancePoliciesPage from "./pages/compliance/CompliancePoliciesPage";
import ComplianceVendorsPage from "./pages/compliance/ComplianceVendorsPage";
import ComplianceIncidentsPage from "./pages/compliance/ComplianceIncidentsPage";
import ComplianceRisksPage from "./pages/compliance/ComplianceRisksPage";
import ComplianceAccessReviewsPage from "./pages/compliance/ComplianceAccessReviewsPage";
import ComplianceTrainingPage from "./pages/compliance/ComplianceTrainingPage";
import ComplianceCodeReviewPage from "./pages/compliance/ComplianceCodeReviewPage";
import ComplianceTestingPage from "./pages/compliance/ComplianceTestingPage";
import ComplianceAuditLogPage from "./pages/compliance/ComplianceAuditLogPage";
import { initializeSessionCoordinator, useSessionState } from "./utils/sessionCoordinator";
import { rehydrateSession } from "./utils/session";
import SiteFooter from "./components/SiteFooter";

function ProtectedRoute({ children }) {
  const session = useSessionState();

  if (session.status === "loading") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center px-6">
        <div className="surface-card px-6 py-4 text-sm text-app-secondary">
          Loading session...
        </div>
      </div>
    );
  }

  if (session.status !== "authenticated") {
    return (
      <Navigate
        to="/login"
        replace
        state={session.message ? { flashMessage: session.message, flashTone: session.messageTone } : undefined}
      />
    );
  }

  return children;
}

function AppShell() {
  const session = useSessionState();
  const location = useLocation();

  useEffect(() => {
    const teardown = initializeSessionCoordinator();
    void rehydrateSession();
    return teardown;
  }, []);

  const shouldRedirectAuthenticatedUser =
    session.status === "authenticated" &&
    (location.pathname === "/login" || location.pathname === "/register");

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <Navbar />
      <main id="main-content" tabIndex={-1} className="min-h-screen bg-app text-app">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/careers" element={<Careers />} />
          <Route path="/trust" element={<Trust />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route
            path="/upload"
            element={
              <ProtectedRoute>
                <Upload />
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={shouldRedirectAuthenticatedUser ? <Navigate to="/dashboard" replace /> : <Login />} />
          <Route path="/employee-login" element={<EmployeeLogin />} />
          <Route path="/register" element={shouldRedirectAuthenticatedUser ? <Navigate to="/dashboard" replace /> : <Register />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/admin" element={<Admin />} />
          <Route
            path="/compliance"
            element={
              <ProtectedRoute>
                <ComplianceLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<ComplianceOverviewPage />} />
            <Route path="employees" element={<ComplianceEmployeesPage />} />
            <Route path="policies" element={<CompliancePoliciesPage />} />
            <Route path="vendors" element={<ComplianceVendorsPage />} />
            <Route path="incidents" element={<ComplianceIncidentsPage />} />
            <Route path="risks" element={<ComplianceRisksPage />} />
            <Route path="access-reviews" element={<ComplianceAccessReviewsPage />} />
            <Route path="training" element={<ComplianceTrainingPage />} />
            <Route path="code-review" element={<ComplianceCodeReviewPage />} />
            <Route path="testing" element={<ComplianceTestingPage />} />
            <Route path="audit-log" element={<ComplianceAuditLogPage />} />
          </Route>
        </Routes>
      </main>
      <SiteFooter />
    </>
  );
}

function App() {
  return (
    <Router>
      <AppShell />
    </Router>
  );
}

export default App;
