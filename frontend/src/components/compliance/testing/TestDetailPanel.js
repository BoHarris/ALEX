import WorkspaceEmptyState from "../WorkspaceEmptyState";
import { formatDateTime, formatPercent, statusBadgeClass, statusTone } from "../../../pages/compliance/utils";
import TestFailureTaskPanel from "./TestFailureTaskPanel";

function DetailField({ label, children }) {
  return (
    <div className="rounded-2xl border border-app/70 bg-app/25 p-4">
      <p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">{label}</p>
      <div className="mt-2 text-sm leading-6 text-app-secondary">{children}</div>
    </div>
  );
}

export default function TestDetailPanel({ test, employees, onCreateTask, onUpdateTask, embedded = false }) {
  if (!test) {
    return <WorkspaceEmptyState title="Select a test case" description="Choose a test from the center panel to inspect execution history, failures, and quality trends." />;
  }

  const latestExecution = test.latest_execution || {};
  const wrapperClass = embedded ? "space-y-0" : "surface-card rounded-3xl p-7 2xl:sticky 2xl:top-6";

  return (
    <section className={wrapperClass}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 pr-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-app-muted">Selected Test</p>
          <h2 className="mt-3 break-words text-[1.9rem] font-semibold leading-tight text-app 2xl:text-[2.2rem]">{test.test_name}</h2>
          <p className="mt-3 text-sm leading-6 text-app-secondary">{test.category} | {test.suite_name}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(test.status)}`}>{test.status}</span>
      </div>

      <div className="mt-7 grid gap-4 sm:grid-cols-2">
        <DetailField label="Test ID"><div className="break-all font-mono text-xs text-slate-300">{test.test_id}</div></DetailField>
        <DetailField label="Pytest Node ID"><div className="break-all font-mono text-xs text-slate-300">{test.test_node_id || "Not recorded"}</div></DetailField>
        <DetailField label="File Path"><div className="break-all font-mono text-xs text-slate-300">{test.file_path || test.file_name || "Not recorded"}</div></DetailField>
        <DetailField label="Latest Environment">{test.latest_environment || "default"}</DetailField>
        <DetailField label="Pass Rate">{formatPercent(test.pass_rate)}</DetailField>
        <DetailField label="Flake Rate">{formatPercent((test.flake_rate || 0) * 100)}</DetailField>
        <DetailField label="Current Pass Streak">{test.current_pass_streak}</DetailField>
        <DetailField label="Current Fail Streak">{test.current_fail_streak}</DetailField>
        <DetailField label="Last Successful Run">{formatDateTime(test.last_successful_run)}</DetailField>
        <DetailField label="Last Failed Run">{formatDateTime(test.last_failed_run)}</DetailField>
        <DetailField label="Average Duration">{test.average_duration_ms != null ? `${Math.round(test.average_duration_ms)} ms` : "N/A"}</DetailField>
        <DetailField label="Quality"><span className={statusTone(test.quality_label || test.trend)}>{test.quality_label || test.trend}</span></DetailField>
        <DetailField label="Trend"><span className={statusTone(test.trend)}>{test.trend}</span></DetailField>
      </div>

      <div className="mt-7 space-y-5 text-sm text-app-secondary">
        <DetailField label="Description">{test.description || "No description recorded."}</DetailField>
        <DetailField label="Expected Behavior">{test.expected_result || "No explicit expected result recorded."}</DetailField>
        <DetailField label="Latest Output">
          <pre className="overflow-x-auto rounded-2xl border border-app/80 bg-app px-4 py-4 whitespace-pre-wrap break-words text-xs leading-6 text-app-secondary">{latestExecution.output || "No output captured."}</pre>
        </DetailField>
        <DetailField label="Latest Failure Reason">
          <pre className="overflow-x-auto rounded-2xl border border-rose-300/40 bg-rose-500/10 px-4 py-4 whitespace-pre-wrap break-words text-xs leading-6 text-rose-300">{latestExecution.error_message || "No failure recorded."}</pre>
        </DetailField>
        <TestFailureTaskPanel test={test} employees={employees} onCreateTask={onCreateTask} onUpdateTask={onUpdateTask} />
      </div>
    </section>
  );
}
