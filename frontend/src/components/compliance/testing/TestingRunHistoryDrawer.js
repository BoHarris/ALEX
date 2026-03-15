import DetailDrawer from "../DetailDrawer";
import { formatDateTime, formatPercent, statusBadgeClass } from "../../../pages/compliance/utils";
import TestDetailPanel from "./TestDetailPanel";

function RunHistoryCard({ item }) {
  return (
    <div className="rounded-3xl border border-app/80 bg-app/25 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 pr-3">
          <p className="text-base font-semibold text-app">{item.suite_name || item.test_name}</p>
          <p className="mt-1 text-xs leading-5 text-app-muted">
            {formatDateTime(item.last_run_timestamp)} | {item.environment || "default"}
          </p>
          <p className="mt-2 break-all font-mono text-[11px] leading-5 text-slate-400">
            {item.file_path || item.file_name || item.test_node_id || "No path recorded"}
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(item.status)}`}>{item.status}</span>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <div className="rounded-2xl border border-app/70 bg-app/35 px-3 py-3 text-xs text-app-secondary">
          Duration: {item.duration_ms != null ? `${item.duration_ms} ms` : "N/A"}
        </div>
        <div className="rounded-2xl border border-app/70 bg-app/35 px-3 py-3 text-xs text-app-secondary">
          Confidence: {item.confidence_score != null ? formatPercent(item.confidence_score * 100) : "N/A"}
        </div>
      </div>

      {item.output ? (
        <div className="mt-4 rounded-2xl border border-app/70 bg-app/30 p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Execution Output</p>
          <pre className="mt-2 whitespace-pre-wrap break-words text-xs leading-6 text-app-secondary">{item.output}</pre>
        </div>
      ) : null}

      {item.error_message ? (
        <div className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-500/10 p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-rose-200">Failure Reason</p>
          <p className="mt-2 whitespace-pre-wrap break-words text-xs leading-6 text-rose-300">{item.error_message}</p>
        </div>
      ) : null}
    </div>
  );
}

export default function TestingRunHistoryDrawer({
  open,
  test,
  employees,
  onClose,
  onCreateTask,
  onUpdateTask,
  onRunTest,
  onViewLatestRun,
  runPending = false,
}) {
  const history = test?.history || [];
  const title = test?.test_name || "Execution History";
  const subtitle = test
    ? `${test.category || "Test"} | ${test.suite_name || "Execution timeline"}`
    : "Review recent runs, evidence, and failure details for the selected test.";

  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      side="left"
      widthClass="max-w-2xl"
      containerClass="pt-20 sm:pt-24 sm:px-4 sm:pb-4"
      panelClass="rounded-r-[2rem] border-y sm:rounded-[2rem]"
    >
      {test ? (
        <div className="space-y-5">
          <div className="rounded-3xl border border-app/80 bg-app/25 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-app-muted">Run History Inspector</p>
                <p className="mt-3 text-sm leading-6 text-app-secondary">
                  Selected test summary, remediation workflow, and execution timeline in one dedicated inspector.
                </p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(test.status || "unknown")}`}>
                {test.status || "unknown"}
              </span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-app/70 bg-app/35 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Runs</p>
                <p className="mt-2 text-lg font-semibold text-app">{test.total_runs || history.length}</p>
              </div>
              <div className="rounded-2xl border border-app/70 bg-app/35 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Latest Failure</p>
                <p className="mt-2 text-sm font-medium text-app-secondary">{formatDateTime(test.last_failed_run)}</p>
              </div>
              <div className="rounded-2xl border border-app/70 bg-app/35 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Latest Success</p>
                <p className="mt-2 text-sm font-medium text-app-secondary">{formatDateTime(test.last_successful_run)}</p>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-app/80 bg-app/20 p-5">
            <TestDetailPanel
              test={test}
              employees={employees}
              onCreateTask={onCreateTask}
              onUpdateTask={onUpdateTask}
              onRunTest={onRunTest}
              onViewLatestRun={onViewLatestRun}
              runPending={runPending}
              embedded
            />
          </div>

          <div>
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-app">Execution History</h3>
              <p className="text-xs text-app-muted">{history.length} recorded runs</p>
            </div>
            <div className="space-y-4">
            {history.length ? history.map((item) => (
              <RunHistoryCard key={`${item.run_id}-${item.result_id}`} item={item} />
            )) : <p className="text-sm text-app-muted">No historical executions recorded.</p>}
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm leading-6 text-app-secondary">Select a test to inspect run history.</p>
      )}
    </DetailDrawer>
  );
}
