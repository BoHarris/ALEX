import { Link } from "react-router-dom";
import SummaryMetricCard from "../../components/compliance/SummaryMetricCard";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, statusTone } from "./utils";

function SimpleList({ title, items, renderItem, emptyText }) {
  return (
    <section className="surface-card rounded-3xl p-6">
      <h2 className="text-lg font-semibold text-app">{title}</h2>
      <div className="mt-4 space-y-3">
        {items.length ? items.map(renderItem) : <p className="text-sm text-app-muted">{emptyText}</p>}
      </div>
    </section>
  );
}

export default function ComplianceOverviewPage() {
  const { data } = useCompliancePageContext();
  const overview = data?.overview || {};
  const summary = overview.summary || {};
  const testing = overview.testing_summary || [];
  const codeReviewSnapshot = overview.code_review_snapshot || [];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-3">
        <SummaryMetricCard label="Policies" value={summary.policy_coverage ?? 0} />
        <SummaryMetricCard label="Vendors" value={summary.vendor_risk_status ?? 0} />
        <SummaryMetricCard label="Open Incidents" value={summary.open_incidents ?? 0} />
        <SummaryMetricCard label="Open Tasks" value={summary.open_tasks ?? 0} />
        <SummaryMetricCard label="Overdue Tasks" value={summary.overdue_tasks ?? 0} />
        <SummaryMetricCard label="Critical Tasks" value={summary.critical_tasks ?? 0} />
        <SummaryMetricCard label="Pending Reviews" value={summary.access_review_status ?? 0} />
        <SummaryMetricCard label="Training %" value={summary.training_completion_rate ?? 0} />
        <SummaryMetricCard label="High Risks" value={summary.high_risk_items ?? 0} />
        <SummaryMetricCard label="Pending Code Reviews" value={summary.pending_code_reviews ?? 0} />
        <SummaryMetricCard label="Approved Reviews" value={summary.approved_code_reviews ?? 0} />
        <SummaryMetricCard label="Blocked Reviews" value={summary.blocked_code_reviews ?? 0} />
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="space-y-6">
          <SimpleList
            title="Recent Activity"
            items={overview.recent_activity || []}
            emptyText="No recent activity yet."
            renderItem={(item) => (
              <div key={item.id} className="rounded-2xl border border-app p-4">
                <p className="font-semibold text-app">{item.title}</p>
                <p className="mt-1 text-sm text-app-secondary">{item.module} | <span className={statusTone(item.status)}>{item.status}</span></p>
                <p className="mt-2 text-xs text-app-muted">{formatDateTime(item.updated_at)}</p>
              </div>
            )}
          />
          <SimpleList
            title="Open Incidents"
            items={overview.open_incidents || []}
            emptyText="No open incidents."
            renderItem={(item) => (
              <div key={item.incident.id} className="rounded-2xl border border-app p-4">
                <p className="font-semibold text-app">{item.record.title}</p>
                <p className="mt-1 text-sm text-app-secondary">
                  <span className={statusTone(item.incident.severity)}>{item.incident.severity}</span> | {item.record.status}
                </p>
                <p className="mt-2 text-xs text-app-muted">Detected {formatDateTime(item.incident.detected_at)}</p>
              </div>
            )}
          />
          <SimpleList
            title="Open Tasks"
            items={overview.recent_tasks || []}
            emptyText="No open governance tasks."
            renderItem={(item) => (
              <div key={item.id} className="rounded-2xl border border-app p-4">
                <p className="font-semibold text-app">{item.task_key} | {item.title}</p>
                <p className="mt-1 text-sm text-app-secondary">{item.source?.label || item.source_module} | <span className={statusTone(item.status)}>{item.status}</span></p>
                <p className="mt-2 text-xs text-app-muted">{item.assignee?.name || "Unassigned"} | updated {formatDateTime(item.updated_at)}</p>
              </div>
            )}
          />
          <SimpleList
            title="Pending Access Reviews"
            items={overview.pending_reviews || []}
            emptyText="No pending access reviews."
            renderItem={(item) => (
              <div key={item.review.id} className="rounded-2xl border border-app p-4">
                <p className="font-semibold text-app">{item.record.title}</p>
                <p className="mt-1 text-sm text-app-secondary">Reviewed employee #{item.review.reviewed_employee_id}</p>
                <p className="mt-2 text-xs text-app-muted">Status {item.record.status}</p>
              </div>
            )}
          />
        </div>

        <div className="space-y-6">
          <SimpleList
            title="Recent Policy Updates"
            items={overview.policy_updates || []}
            emptyText="No policy updates yet."
            renderItem={(item) => (
              <div key={item.page.id} className="rounded-2xl border border-app p-4">
                <p className="font-semibold text-app">{item.record.title}</p>
                <p className="mt-1 text-sm text-app-secondary">{item.page.category} | v{item.page.version}</p>
                <p className="mt-2 text-xs text-app-muted">{formatDateTime(item.record.updated_at)}</p>
              </div>
            )}
          />
          <SimpleList
            title="Vendor Reviews Due"
            items={overview.vendor_reviews_due || []}
            emptyText="No vendors awaiting review."
            renderItem={(item) => (
              <div key={item.vendor.id} className="rounded-2xl border border-app p-4">
                <p className="font-semibold text-app">{item.vendor.vendor_name}</p>
                <p className="mt-1 text-sm text-app-secondary">{item.vendor.security_review_status} | {item.vendor.risk_rating || "unrated"}</p>
                <p className="mt-2 text-xs text-app-muted">Last review {item.vendor.last_review_date ? formatDateTime(item.vendor.last_review_date) : "Not recorded"}</p>
              </div>
            )}
          />
          <SimpleList
            title="Testing Summary"
            items={testing}
            emptyText="No test runs available."
            renderItem={(item) => (
              <div key={item.id} className="rounded-2xl border border-app p-4">
                <p className="font-semibold text-app">{item.category}</p>
                <p className="mt-1 text-sm text-app-secondary">{item.suite_name} | <span className={statusTone(item.status)}>{item.status}</span></p>
                <p className="mt-2 text-xs text-app-muted">{item.coverage_percent ?? "N/A"}% coverage | {formatDateTime(item.run_at)}</p>
              </div>
            )}
          />
          <SimpleList
            title="Code Review Snapshot"
            items={codeReviewSnapshot}
            emptyText="No code reviews recorded yet."
            renderItem={(item) => (
              <div key={item.review.id} className="rounded-2xl border border-app p-4">
                <p className="font-semibold text-app">{item.record.title}</p>
                <p className="mt-1 text-sm text-app-secondary">{item.review.review_type} | <span className={statusTone(item.record.status)}>{item.record.status}</span></p>
                <p className="mt-2 text-xs text-app-muted">{item.review.target_release || "No release target"} | risk {item.review.risk_level}</p>
              </div>
            )}
          />
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <SimpleList
          title="Overdue Training"
          items={overview.overdue_training || []}
          emptyText="No overdue training."
          renderItem={(item) => (
            <div key={item.assignment.id} className="rounded-2xl border border-app p-4">
              <p className="font-semibold text-app">{item.record.title}</p>
              <p className="mt-1 text-sm text-app-secondary">Employee #{item.assignment.employee_id}</p>
              <p className="mt-2 text-xs text-amber-600">Due {formatDateTime(item.assignment.due_date)}</p>
            </div>
          )}
        />
        <section className="surface-card rounded-3xl p-6">
          <h2 className="text-lg font-semibold text-app">Quick Actions</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/employees">Add employee</Link>
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/policies">Create policy page</Link>
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/vendors">Add vendor</Link>
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/incidents">Log incident</Link>
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/tasks">View tasks</Link>
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/risks">Add risk</Link>
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/access-reviews">Start access review</Link>
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/training">Assign training</Link>
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/code-review">Create code review</Link>
            <Link className="rounded-2xl border border-app px-4 py-3 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app" to="/compliance/testing">Review testing evidence</Link>
          </div>
        </section>
      </div>

      {!overview.recent_activity?.length && !overview.open_incidents?.length ? (
        <WorkspaceEmptyState
          title="Overview is ready"
          description="As records, incidents, reviews, training assignments, and release checks accumulate, this page will surface what needs attention first."
        />
      ) : null}
    </div>
  );
}
