import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import DashboardFilesPanel from "../components/DashboardFilesPanel";
import { Tabs, TabList, Tab, TabPanels, TabPanel } from "../components/Tabs";
import { useCompanyUsers } from "../hooks/useCompanyUsers";
import { useRedactedFiles } from "../hooks/useRedacted_files";
import { useCurrentUser } from "../hooks/useLoadUser";
import { useAdminOverview } from "../hooks/useAdminOverview";
import { useAuditEvents } from "../hooks/useAuditEvents";
import { useCompanySettings } from "../hooks/useCompanySettings";
import { useSecurityDashboard } from "../hooks/useSecurityDashboard";
import Upload from "./Upload";
import { Button } from "../components/button";

function StatCard({ label, value, tone = "default" }) {
  const toneClass =
    tone === "accent"
      ? "surface-tint text-app"
      : "surface-card text-app";

  return (
    <div className={`rounded-3xl border p-5 ${toneClass}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">
        {label}
      </p>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
    </div>
  );
}

function formatDateTime(value) {
  if (!value) return "Unknown";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Unknown" : parsed.toLocaleString();
}

function formatSecurityEventLabel(value) {
  if (!value) return "Security alert";
  return value
    .split("_")
    .join(" ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function PlanLockNotice({ title, message }) {
  return (
    <div className="rounded-3xl border border-amber-300/35 bg-amber-300/10 p-6 text-amber-700">
      <p className="text-xs font-semibold uppercase tracking-[0.24em]">Plan Restricted</p>
      <p className="mt-2 text-lg font-semibold text-app">{title}</p>
      <p className="mt-2 text-sm text-amber-800 dark:text-amber-100/90">{message}</p>
      <p className="mt-4 text-xs uppercase tracking-[0.2em] text-amber-700 dark:text-amber-200">Available on Pro and Business</p>
    </div>
  );
}

function AdminQuickLinks({ onSelectTab, activeTab }) {
  const links = [
    { key: "analytics", label: "Analytics" },
    { key: "security", label: "Security" },
    { key: "activity", label: "Activity Feed" },
    { key: "settings", label: "Company Settings" },
    { key: "users", label: "Users" },
    { key: "files", label: "Scans" },
  ];

  return (
    <section className="surface-tint p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">Admin Quick Links</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {links.map((link) => (
          <button
            key={link.key}
            onClick={() => onSelectTab(link.key)}
            className={
              activeTab === link.key
                ? "rounded-full border border-cyan-300/40 bg-cyan-300/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-700 dark:text-cyan-100"
                : "rounded-full border border-app px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-app-secondary hover:bg-white/10 dark:hover:bg-white/10"
            }
          >
            {link.label}
          </button>
        ))}
      </div>
    </section>
  );
}

function CompanyUsersPanel({ companyName, users, loading, error, onRetry }) {
  if (loading) {
    return <div className="surface-card p-6 text-sm text-app-secondary">Loading company users...</div>;
  }
  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-200">
        <p>{error.message}</p>
        <button onClick={onRetry} className="mt-4 rounded-full border border-rose-300/40 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-rose-100 transition hover:bg-rose-200/10">Retry</button>
      </div>
    );
  }
  if (!users.length) {
    return (
      <div className="surface-card border-dashed border-cyan-300/30 p-10 text-center">
        <p className="text-app text-lg font-semibold">No company users yet</p>
        <p className="text-app-secondary mt-2 text-sm">No user records are currently available for {companyName}.</p>
      </div>
    );
  }

  return (
    <div className="surface-card overflow-hidden">
      <div className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_120px_100px_170px] gap-4 border-b border-app px-5 py-4 text-xs font-semibold uppercase tracking-[0.2em] text-app-muted">
        <span>Name</span>
        <span>Email</span>
        <span>Role</span>
        <span>Tier</span>
        <span>Last Login</span>
      </div>
      {users.map((user) => {
        const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ") || "Unnamed user";
        return (
          <div key={user.user_id} className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_120px_100px_170px] gap-4 border-t border-app px-5 py-4 text-sm text-app-secondary">
            <div className="truncate">
              <p className="font-semibold text-app">{fullName}</p>
              <p className="text-xs text-app-muted">User ID {user.user_id}</p>
            </div>
            <p className="truncate">{user.email}</p>
            <p className="capitalize">{user.role || "member"}</p>
            <p className="capitalize">{user.tier || "free"}</p>
            <p>{formatDateTime(user.last_login_at)}</p>
          </div>
        );
      })}
    </div>
  );
}

function MeterRow({ label, value, total }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm text-app-secondary">
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-300/40 dark:bg-slate-300/40">
        <div className="h-2 rounded-full bg-cyan-300" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function AdminAnalyticsPanel({ data, loading, error, onRetry, planFeatures }) {
  const analyticsEnabled = data?.analytics_enabled || Boolean(planFeatures?.admin_analytics);
  if (!analyticsEnabled) {
    return <PlanLockNotice title="Company Analytics" message="Company analytics requires a higher plan. Upgrade to unlock scan trends and risk distribution." />;
  }
  if (loading) {
    return <div className="surface-card p-6 text-sm text-app-secondary">Loading analytics...</div>;
  }
  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-200">
        <p>{error.message}</p>
        <Button onClick={onRetry} className="mt-3">Retry analytics</Button>
      </div>
    );
  }

  const summary = data?.summary || {};
  const risk = data?.risk_distribution || { low: 0, medium: 0, high: 0 };
  const riskTotal = risk.low + risk.medium + risk.high;
  const fileTypes = data?.file_type_distribution || {};
  const fileTotal = Object.values(fileTypes).reduce((acc, count) => acc + count, 0);
  const topTypes = data?.top_redacted_types || [];
  const scanTrend = data?.scans_over_time || [];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Total Scans" value={summary.total_scans ?? 0} tone="accent" />
        <StatCard label="Scans This Week" value={summary.scans_this_week ?? 0} />
        <StatCard label="High Risk Scans" value={summary.high_risk_scans ?? 0} />
        <StatCard label="PDF Reports" value={summary.report_activity?.pdf_reports_downloaded ?? 0} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="surface-card p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-app-muted">Risk Distribution</p>
          <div className="mt-4 space-y-3">
            <MeterRow label="Low" value={risk.low} total={riskTotal} />
            <MeterRow label="Medium" value={risk.medium} total={riskTotal} />
            <MeterRow label="High" value={risk.high} total={riskTotal} />
          </div>
          {!riskTotal ? <p className="mt-4 text-sm text-app-muted">No risk data available yet.</p> : null}
        </section>

        <section className="surface-card p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-app-muted">File Type Distribution</p>
          <div className="mt-4 space-y-3">
            {Object.keys(fileTypes).length ? (
              Object.entries(fileTypes).map(([type, count]) => (
                <MeterRow key={type} label={type.toUpperCase()} value={count} total={fileTotal} />
              ))
            ) : (
              <p className="text-sm text-app-muted">No processed file distribution yet.</p>
            )}
          </div>
        </section>

        <section className="surface-card p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-app-muted">Top Redacted Types</p>
          <div className="mt-4 space-y-2 text-sm text-app">
            {topTypes.length ? (
              topTypes.map((item) => (
                <p key={item.type} className="flex items-center justify-between border-b border-app pb-2">
                  <span>{item.type}</span>
                  <span className="text-cyan-700 dark:text-cyan-200">{item.count}</span>
                </p>
              ))
            ) : (
              <p className="text-app-muted">No redaction type summary yet.</p>
            )}
          </div>
        </section>
      </div>

      <section className="surface-card p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-app-muted">Scan Trend (30 Days)</p>
        <div className="mt-4 grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          {scanTrend.length ? (
            scanTrend.slice(-12).map((point) => (
              <div key={point.date} className="surface-card rounded-2xl p-3 text-sm text-app-secondary">
                <p className="text-app-muted">{point.date}</p>
                <p className="mt-1 text-lg font-semibold text-app">{point.count} scan(s)</p>
              </div>
            ))
          ) : (
            <p className="text-sm text-app-muted">No scan trend data available yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}

function ActivityPanel({ events, loading, error, onRetry, planFeatures }) {
  if (!planFeatures?.audit_visibility) {
    return <PlanLockNotice title="Audit Trail Visibility" message="Audit trail visibility is available on Pro and Business plans." />;
  }
  if (loading) {
    return <div className="surface-card p-6 text-sm text-app-secondary">Loading activity feed...</div>;
  }
  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-200">
        <p>{error.message}</p>
        <Button onClick={onRetry} className="mt-3">Retry activity load</Button>
      </div>
    );
  }
  if (!events.length) {
    return <div className="surface-card border-dashed border-cyan-300/30 p-10 text-center text-app-secondary">No recent activity yet for this company.</div>;
  }
  return (
    <div className="surface-card overflow-hidden">
      <div className="grid grid-cols-[170px_150px_1fr_120px] gap-4 border-b border-app px-5 py-4 text-xs font-semibold uppercase tracking-[0.2em] text-app-muted">
        <span>Timestamp</span>
        <span>Event</span>
        <span>Description</span>
        <span>Actor</span>
      </div>
      {events.map((event) => (
        <div key={event.event_id} className="grid grid-cols-[170px_150px_1fr_120px] gap-4 border-t border-app px-5 py-4 text-sm text-app-secondary">
          <span>{formatDateTime(event.created_at)}</span>
          <span className="font-semibold text-cyan-700 dark:text-cyan-100">{event.event_type}</span>
          <span>{event.description}</span>
          <span>{event.user_id ? `User ${event.user_id}` : "System"}</span>
        </div>
      ))}
    </div>
  );
}

function SecurityDashboardPanel({ securityHook }) {
  const navigate = useNavigate();
  const { data, loading, error, reload } = securityHook;
  if (loading) {
    return <div className="surface-card p-6 text-sm text-app-secondary">Loading security dashboard...</div>;
  }
  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-200">
        <p>{error.message}</p>
        <Button onClick={reload} className="mt-3">Retry security load</Button>
      </div>
    );
  }
  const retention = data?.retention_overview || {};
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Failed Logins" value={data?.failed_login_attempts ?? 0} tone="accent" />
        <StatCard label="Security Alerts" value={data?.recent_security_alerts?.length ?? 0} />
        <StatCard label="Open Incidents" value={(data?.incidents || []).filter((incident) => incident.status !== "resolved").length} />
        <StatCard label="Expired Scans" value={retention.expired ?? 0} />
      </div>
      <section className="surface-card p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-app-muted">Recent Security Alerts</p>
        <div className="mt-4 space-y-3 text-sm text-app-secondary">
          {(data?.recent_security_alerts || []).length ? data.recent_security_alerts.map((alert) => (
            <div key={alert.id} className="rounded-2xl border border-app p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-app">{alert.event_label || formatSecurityEventLabel(alert.event_type)}</p>
                  <p className="mt-1 text-app-secondary">{formatDateTime(alert.created_at)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => navigate("/compliance/tasks")}
                  className="rounded-full border border-cyan-300/40 bg-cyan-400/10 px-3 py-1 text-xs font-semibold text-cyan-100"
                >
                  Investigate
                </button>
              </div>
              <p className="mt-2 text-sm text-app-secondary">{alert.description || "No alert description available."}</p>
              <p className="mt-2 text-xs text-app-muted">
                Recommended action: review session activity, linked incidents, and active access for the affected actor.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {(alert.linked_tasks || []).length ? alert.linked_tasks.map((task) => (
                  <button
                    key={task.id}
                    type="button"
                    onClick={() => navigate("/compliance/tasks")}
                    className="rounded-full border border-app px-3 py-1 text-xs font-semibold text-app-secondary hover:bg-white/5 hover:text-app"
                  >
                    {task.task_key} {task.status}
                  </button>
                )) : <span className="text-xs text-app-muted">No linked task yet.</span>}
              </div>
            </div>
          )) : <p>No security alerts detected.</p>}
        </div>
      </section>
      <section className="surface-card p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-app-muted">Incidents</p>
        <div className="mt-4 space-y-3 text-sm text-app-secondary">
          {(data?.incidents || []).length ? data.incidents.map((incident) => (
            <div key={incident.id} className="rounded-2xl border border-app p-4">
              <p className="font-semibold capitalize text-app">{incident.severity} · {incident.status}</p>
              <p className="mt-1">{incident.description}</p>
            </div>
          )) : <p>No incidents logged.</p>}
        </div>
      </section>
    </div>
  );
}

function SettingsPanel({ settingsHook, planFeatures }) {
  const { settings, setSettings, loading, saving, error, saveMessage, save } = settingsHook;

  if (!planFeatures?.company_settings) {
    return <PlanLockNotice title="Company Settings" message="Company settings are currently available on Pro and Business plans." />;
  }
  if (loading) {
    return <div className="surface-card p-6 text-sm text-app-secondary">Loading company settings...</div>;
  }

  const allowedUploadTypes = Array.isArray(settings.allowed_upload_types) ? settings.allowed_upload_types.join(", ") : "";

  return (
    <form
      className="surface-card space-y-5 p-6"
      onSubmit={async (event) => {
        event.preventDefault();
        await save({
          ...settings,
          allowed_upload_types: allowedUploadTypes
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        });
      }}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">Company Settings</p>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-sm text-app-secondary">
          Default Policy Label
          <input className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" value={settings.default_policy_label || ""} onChange={(e) => setSettings((prev) => ({ ...prev, default_policy_label: e.target.value }))} />
        </label>
        <label className="text-sm text-app-secondary">
          Report Display Name
          <input className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" value={settings.default_report_display_name || ""} onChange={(e) => setSettings((prev) => ({ ...prev, default_report_display_name: e.target.value }))} />
        </label>
        <label className="text-sm text-app-secondary">
          Contact/Admin Email
          <input type="email" className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" value={settings.contact_email || ""} onChange={(e) => setSettings((prev) => ({ ...prev, contact_email: e.target.value }))} />
        </label>
        <label className="text-sm text-app-secondary">
          Compliance Mode
          <input className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" value={settings.compliance_mode || ""} onChange={(e) => setSettings((prev) => ({ ...prev, compliance_mode: e.target.value }))} />
        </label>
        <label className="text-sm text-app-secondary">
          Allowed Upload Types (comma-separated)
          <input className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" value={allowedUploadTypes} onChange={(e) => setSettings((prev) => ({ ...prev, allowed_upload_types: e.target.value.split(",").map((item) => item.trim()).filter(Boolean) }))} />
        </label>
        <label className="text-sm text-app-secondary">
          Retention Display Days
          <input type="number" min="1" className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" value={settings.retention_days_display || ""} onChange={(e) => setSettings((prev) => ({ ...prev, retention_days_display: e.target.value }))} />
        </label>
        <label className="text-sm text-app-secondary">
          Retention Enforcement Days
          <input type="number" min="1" className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" value={settings.retention_days || ""} onChange={(e) => setSettings((prev) => ({ ...prev, retention_days: e.target.value }))} />
        </label>
      </div>

      {error ? <p className="text-sm text-rose-200">{error.message}</p> : null}
      {saveMessage ? <p className="text-sm text-emerald-200">{saveMessage}</p> : null}
      <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Save company settings"}</Button>
      <p className="text-xs text-app-muted">Some options are display-ready foundations for upcoming policy and retention controls.</p>
    </form>
  );
}

function Dashboard({ initialTab = "files", showAdminRail = false }) {
  const { user, loading: userLoading, error: userError, reload: reloadUser } = useCurrentUser();
  const plan = user?.plan_features || { tier: user?.tier || "free" };
  const isAdmin = Boolean(user?.permissions?.can_access_admin);
  const isSecurityAdmin = Boolean(user?.permissions?.can_access_security_dashboard);
  const [activeTab, setActiveTab] = useState(initialTab);
  const {
    files,
    archivedFiles,
    loading: filesLoading,
    error: filesError,
    archiveScan,
    restoreScan,
    reload: reloadFiles,
  } = useRedactedFiles();
  const { users: companyUsers, loading: companyUsersLoading, error: companyUsersError, reload: reloadCompanyUsers } = useCompanyUsers(isAdmin);
  const adminOverview = useAdminOverview(isAdmin);
  const auditFeed = useAuditEvents(isAdmin && Boolean(plan.audit_visibility));
  const settingsHook = useCompanySettings(isAdmin && Boolean(plan.company_settings));
  const securityDashboard = useSecurityDashboard(isSecurityAdmin);

  const displayName = user?.first_name || "there";
  const companyName = user?.company_name || "Your Company";
  const latestFile = files[0]?.filename || "No scans yet";

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const handleRetryAll = () => {
    reloadUser();
    reloadFiles();
    if (isAdmin) {
      adminOverview.reload();
      auditFeed.reload();
      settingsHook.reload();
      reloadCompanyUsers();
      if (isSecurityAdmin) {
        securityDashboard.reload();
      }
    }
  };

  return (
    <div className="page-shell px-4 py-8 text-app sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="surface-panel overflow-hidden rounded-[2rem] p-8 shadow-2xl backdrop-blur">
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-app-muted">Operations Dashboard</p>
              <h1 className="text-app mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Welcome back, {displayName}</h1>
              <p className="text-app-secondary mt-4 max-w-2xl text-sm leading-7 sm:text-base">Privacy work should be operational, not aspirational. ALEX helps your team detect sensitive data, apply redaction, and ship audit-ready outputs with clear controls.</p>
            </div>
            <div className="surface-tint rounded-[1.75rem] p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">Current Context</p>
              <p className="mt-4 text-xl font-semibold text-app">{filesLoading ? "Loading latest output..." : latestFile}</p>
              <p className="mt-2 text-sm text-app-secondary">Plan: <span className="font-semibold uppercase">{plan.tier || "FREE"}</span></p>
              {(userError || filesError) ? (
                <div className="mt-5 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4 text-sm text-amber-700">
                  One or more dashboard requests failed.
                  <div className="mt-3"><Button onClick={handleRetryAll}>Retry dashboard data</Button></div>
                </div>
              ) : null}
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label={isAdmin ? "Company Scans" : "Your Scans"} value={filesLoading ? "..." : files.length} tone="accent" />
          <StatCard label="Account Tier" value={userLoading ? "..." : user?.tier || "Unknown"} />
          <StatCard label={isAdmin ? "Company" : "Profile Email"} value={userLoading ? "..." : isAdmin ? companyName : user?.email || "Unavailable"} />
          <StatCard label="Status" value={userError || filesError ? "Attention" : userLoading || filesLoading ? "Syncing" : "Ready"} />
        </section>

        {isAdmin && showAdminRail ? (
          <AdminQuickLinks onSelectTab={setActiveTab} activeTab={activeTab} />
        ) : null}

        <Tabs defaultvalue="files" value={activeTab} onValueChange={setActiveTab}>
          <TabList>
            <Tab value="files">{isAdmin ? "Company Scans" : "Redacted Files"}</Tab>
            {isAdmin ? <Tab value="analytics">Analytics</Tab> : null}
            {isSecurityAdmin ? <Tab value="security">Security</Tab> : null}
            {isAdmin ? <Tab value="activity">Activity Feed</Tab> : null}
            {isAdmin ? <Tab value="settings">Company Settings</Tab> : null}
            {isAdmin ? <Tab value="users">Users</Tab> : null}
            <Tab value="info">Your Info</Tab>
            <Tab value="upload">Upload</Tab>
          </TabList>

          <TabPanels>
            <TabPanel value="files">
              <div className="space-y-6">
                <DashboardFilesPanel
                  files={files}
                  loading={filesLoading}
                  error={filesError}
                  onRetry={reloadFiles}
                  onArchiveScan={archiveScan}
                  title={isAdmin ? "Company Scan Activity" : "Redacted Files"}
                  description={
                    isAdmin
                      ? `Showing company-wide scan activity for ${companyName}.`
                      : "Showing your recent scan activity and protected outputs."
                  }
                  showSubmitter={isAdmin}
                />
                <DashboardFilesPanel
                  files={archivedFiles}
                  loading={filesLoading}
                  error={filesError}
                  onRetry={reloadFiles}
                  onRestoreScan={restoreScan}
                  title="Archived Scans"
                  description="Archived scans are hidden from the main list but retained for audit visibility and restore."
                  showSubmitter={isAdmin}
                  archived
                />
                <div className="surface-card p-4 text-sm text-app-secondary">
                  <p className="font-medium text-app">Retention policy (preview)</p>
                  <p className="mt-1">
                    {plan.tier === "business"
                      ? "Business retention controls are configurable by company policy."
                      : plan.tier === "pro"
                        ? "Pro plan keeps scan history longer and is eligible for company retention settings."
                        : "Free tier uses limited retention windows. Upgrade for extended retention controls."}
                  </p>
                </div>
              </div>
            </TabPanel>

            {isAdmin ? (
              <TabPanel value="analytics">
                <AdminAnalyticsPanel
                  data={adminOverview.data}
                  loading={adminOverview.loading}
                  error={adminOverview.error}
                  onRetry={adminOverview.reload}
                  planFeatures={plan}
                />
              </TabPanel>
            ) : null}

            {isSecurityAdmin ? (
              <TabPanel value="security">
                <SecurityDashboardPanel securityHook={securityDashboard} />
              </TabPanel>
            ) : null}

            {isAdmin ? (
              <TabPanel value="activity">
                <ActivityPanel
                  events={auditFeed.events}
                  loading={auditFeed.loading}
                  error={auditFeed.error}
                  onRetry={auditFeed.reload}
                  planFeatures={plan}
                />
              </TabPanel>
            ) : null}

            {isAdmin ? (
              <TabPanel value="settings">
                <SettingsPanel settingsHook={settingsHook} planFeatures={plan} />
              </TabPanel>
            ) : null}

            {isAdmin ? (
              <TabPanel value="users">
                <CompanyUsersPanel
                  companyName={companyName}
                  users={companyUsers}
                  loading={companyUsersLoading}
                  error={companyUsersError}
                  onRetry={reloadCompanyUsers}
                />
              </TabPanel>
            ) : null}

            <TabPanel value="info">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="surface-card p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">Account Snapshot</p>
                  {userLoading ? (
                    <p className="mt-4 text-sm text-app-secondary">Loading account details...</p>
                  ) : userError ? (
                    <>
                      <p className="mt-4 text-sm text-rose-200">{userError.message}</p>
                      <div className="mt-4"><Button onClick={reloadUser}>Retry user load</Button></div>
                    </>
                  ) : (
                    <dl className="mt-4 space-y-4 text-sm">
                      <div><dt className="text-app-muted">User ID</dt><dd className="mt-1 font-medium text-app">{user?.user_id || "Unavailable"}</dd></div>
                      <div><dt className="text-app-muted">Email</dt><dd className="mt-1 font-medium text-app">{user?.email || "Unavailable"}</dd></div>
                      <div><dt className="text-app-muted">Role</dt><dd className="mt-1 font-medium capitalize text-app">{user?.role || "Unavailable"}</dd></div>
                      <div><dt className="text-app-muted">Company</dt><dd className="mt-1 font-medium text-app">{user?.company_name || "Unavailable"}</dd></div>
                      <div><dt className="text-app-muted">Plan</dt><dd className="mt-1 font-medium capitalize text-app">{plan.tier || user?.tier || "Unavailable"}</dd></div>
                    </dl>
                  )}
                </div>
                <div className="surface-card p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">Plan Access</p>
                  <p className="mt-3 text-sm text-app-secondary">Feature visibility is role- and plan-aware to support commercial rollout and predictable user experience.</p>
                  <ul className="mt-4 space-y-2 text-sm text-app">
                    <li>Admin analytics: {plan.admin_analytics ? "Enabled" : "Locked"}</li>
                    <li>Audit trail visibility: {plan.audit_visibility ? "Enabled" : "Locked"}</li>
                    <li>Company settings: {plan.company_settings ? "Enabled" : "Locked"}</li>
                    <li>Max file size: {plan.max_file_size_mb || 5}MB</li>
                    <li>Daily scan limit: {plan.scan_limit_per_day || 1}</li>
                  </ul>
                </div>
              </div>
            </TabPanel>

            <TabPanel value="upload">
              <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
                <aside className="surface-tint p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">Upload Workflow</p>
                  <h2 className="mt-4 text-2xl font-semibold text-app">Scan a new file</h2>
                  <p className="mt-3 text-sm leading-6 text-app-secondary">Submit a supported file, run detection and redaction, then review your results and reports in the scan activity tab.</p>
                </aside>
                <div className="surface-panel rounded-[2rem] p-4 sm:p-6">
                  <Upload />
                </div>
              </div>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </div>
    </div>
  );
}

export default Dashboard;
