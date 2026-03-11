import WorkspaceEmptyState from "../WorkspaceEmptyState";
import { formatDateTime, formatPercent, statusBadgeClass, statusTone } from "../../../pages/compliance/utils";

function DetailField({ label, children }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.18em] text-app-muted">{label}</p>
      <div className="mt-2 text-sm text-app-secondary">{children}</div>
    </div>
  );
}

function HistoryItem({ item }) {
  return (
    <div className="rounded-2xl border border-app p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-app">{item.suite_name}</p>
          <p className="mt-1 text-xs text-app-muted">{formatDateTime(item.last_run_timestamp)} | {item.environment}</p>
          <p className="mt-1 text-[11px] text-app-muted">{item.file_path || item.file_name || "No file path recorded"}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(item.status)}`}>{item.status}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-3 text-xs text-app-secondary">
        <span>Duration: {item.duration_ms != null ? `${item.duration_ms} ms` : "N/A"}</span>
        <span>Confidence: {item.confidence_score != null ? formatPercent(item.confidence_score * 100) : "N/A"}</span>
      </div>
      {item.error_message ? <p className="mt-3 text-xs text-rose-300">{item.error_message}</p> : null}
    </div>
  );
}

export default function TestDetailPanel({ test }) {
  if (!test) {
    return <WorkspaceEmptyState title="Select a test case" description="Choose a test from the center panel to inspect execution history, failures, and quality trends." />;
  }

  const latestExecution = test.latest_execution || {};

  return (
    <section className="surface-card rounded-3xl p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-app-muted">Selected Test</p>
          <h2 className="mt-2 text-2xl font-semibold text-app">{test.test_name}</h2>
          <p className="mt-2 text-sm text-app-secondary">{test.category} | {test.suite_name}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(test.status)}`}>{test.status}</span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <DetailField label="Test ID">{test.test_id}</DetailField>
        <DetailField label="Pytest Node ID">{test.test_node_id || "Not recorded"}</DetailField>
        <DetailField label="File Path">{test.file_path || test.file_name || "Not recorded"}</DetailField>
        <DetailField label="Latest Environment">{test.latest_environment || "default"}</DetailField>
        <DetailField label="Pass Rate">{formatPercent(test.pass_rate)}</DetailField>
        <DetailField label="Flake Rate">{formatPercent((test.flake_rate || 0) * 100)}</DetailField>
        <DetailField label="Current Pass Streak">{test.current_pass_streak}</DetailField>
        <DetailField label="Current Fail Streak">{test.current_fail_streak}</DetailField>
        <DetailField label="Last Successful Run">{formatDateTime(test.last_successful_run)}</DetailField>
        <DetailField label="Last Failed Run">{formatDateTime(test.last_failed_run)}</DetailField>
        <DetailField label="Average Duration">{test.average_duration_ms != null ? `${Math.round(test.average_duration_ms)} ms` : "N/A"}</DetailField>
        <DetailField label="Trend"><span className={statusTone(test.trend)}>{test.trend}</span></DetailField>
      </div>

      <div className="mt-5 space-y-4 text-sm text-app-secondary">
        <DetailField label="Description">{test.description || "No description recorded."}</DetailField>
        <DetailField label="Expected Behavior">{test.expected_result || "No explicit expected result recorded."}</DetailField>
        <DetailField label="Latest Output">
          <pre className="overflow-x-auto rounded-2xl border border-app bg-app px-4 py-4 whitespace-pre-wrap text-xs text-app-secondary">{latestExecution.output || "No output captured."}</pre>
        </DetailField>
        <DetailField label="Latest Failure Reason">
          <pre className="overflow-x-auto rounded-2xl border border-rose-300/40 bg-rose-500/10 px-4 py-4 whitespace-pre-wrap text-xs text-rose-300">{latestExecution.error_message || "No failure recorded."}</pre>
        </DetailField>
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold text-app">Execution History</h3>
          <p className="text-xs text-app-muted">{test.history?.length || 0} recorded runs</p>
        </div>
        <div className="mt-4 space-y-3">
          {test.history?.length ? test.history.map((item) => (
            <HistoryItem key={`${item.run_id}-${item.result_id}`} item={item} />
          )) : <p className="text-sm text-app-muted">No historical executions recorded.</p>}
        </div>
      </div>
    </section>
  );
}
