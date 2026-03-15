import DetailDrawer from "../DetailDrawer";
import LinkedTaskPill from "../tasks/LinkedTaskPill";
import { formatDateTime, statusBadgeClass } from "../../../pages/compliance/utils";

function ResultRow({ result, onViewTask }) {
  const firstLinkedTask = result.linked_tasks?.[0] || null;

  return (
    <div className="rounded-2xl border border-app/70 bg-app/25 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-app">{result.test_name}</p>
          <p className="mt-1 break-all font-mono text-[11px] leading-5 text-slate-400">{result.test_node_id}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(result.status)}`}>{result.status}</span>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 text-xs text-app-secondary">
        <div>Duration: {result.duration_ms != null ? `${result.duration_ms} ms` : "N/A"}</div>
        <div>Finished: {formatDateTime(result.last_run_timestamp)}</div>
      </div>
      {result.error_details || result.error_message ? (
        <div className="mt-3 rounded-2xl border border-rose-300/30 bg-rose-500/10 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-rose-200">Failure Reason</p>
          <pre className="mt-2 whitespace-pre-wrap break-words text-xs leading-6 text-rose-300">{result.error_details || result.error_message}</pre>
        </div>
      ) : null}
      {result.output_summary || result.output ? (
        <div className="mt-3 rounded-2xl border border-app/70 bg-app/30 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Execution Output</p>
          <pre className="mt-2 whitespace-pre-wrap break-words text-xs leading-6 text-app-secondary">{result.output_summary || result.output}</pre>
        </div>
      ) : null}
      {firstLinkedTask ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <LinkedTaskPill label={`${firstLinkedTask.task_key} ${firstLinkedTask.status}`} onClick={() => onViewTask?.(firstLinkedTask)} tone="accent" />
          <span className="text-xs text-app-muted">Linked remediation task</span>
        </div>
      ) : null}
    </div>
  );
}

export default function TestRunDetailDrawer({ open, runDetail, onClose, onViewTask }) {
  const run = runDetail?.run || null;
  const results = runDetail?.results || [];
  const linkedTasks = runDetail?.linked_tasks || [];

  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      title={run?.suite_name || "Run Detail"}
      subtitle={run ? `${run.run_type?.replace("_", " ")} | ${run.category || "testing"}` : "Inspect execution output and related remediation work."}
      widthClass="max-w-2xl"
      containerClass="pt-20 sm:pt-24 sm:px-4 sm:pb-4"
    >
      {run ? (
        <div className="space-y-5">
          <section className="surface-card rounded-3xl p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Execution Summary</p>
                <h3 className="mt-2 text-lg font-semibold text-app">{run.suite_name}</h3>
                <p className="mt-2 text-sm text-app-secondary">{run.category} | {run.run_type?.replace("_", " ")}</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(run.status)}`}>{run.status}</span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-app/70 bg-app/25 p-3 text-sm text-app-secondary">Started: {formatDateTime(run.started_at || run.created_at)}</div>
              <div className="rounded-2xl border border-app/70 bg-app/25 p-3 text-sm text-app-secondary">Completed: {formatDateTime(run.completed_at)}</div>
              <div className="rounded-2xl border border-app/70 bg-app/25 p-3 text-sm text-app-secondary">Return Code: {run.return_code != null ? run.return_code : "Pending"}</div>
              <div className="rounded-2xl border border-app/70 bg-app/25 p-3 text-sm text-app-secondary">Results: {run.passed_tests}/{run.total_tests} passed</div>
            </div>
            {run.failure_summary ? (
              <div className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-500/10 p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-rose-200">Failure Summary</p>
                <pre className="mt-2 whitespace-pre-wrap break-words text-xs leading-6 text-rose-300">{run.failure_summary}</pre>
              </div>
            ) : null}
          </section>

          {run.stdout ? (
            <section className="surface-card rounded-3xl p-5">
              <p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Stdout</p>
              <pre className="mt-3 whitespace-pre-wrap break-words text-xs leading-6 text-app-secondary">{run.stdout}</pre>
            </section>
          ) : null}

          {run.stderr ? (
            <section className="surface-card rounded-3xl p-5">
              <p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Stderr</p>
              <pre className="mt-3 whitespace-pre-wrap break-words text-xs leading-6 text-rose-300">{run.stderr}</pre>
            </section>
          ) : null}

          {linkedTasks.length ? (
            <section className="surface-card rounded-3xl p-5">
              <div className="flex flex-wrap items-center gap-2">
                {linkedTasks.map((task) => (
                  <LinkedTaskPill key={task.id} label={`${task.task_key} ${task.status}`} onClick={() => onViewTask?.(task)} tone="accent" />
                ))}
              </div>
            </section>
          ) : null}

          <section className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-app">Recorded Results</h3>
              <span className="text-xs text-app-muted">{results.length} tests</span>
            </div>
            {results.length ? results.map((result) => (
              <ResultRow key={`${result.id || result.result_id || result.test_node_id}`} result={result} onViewTask={onViewTask} />
            )) : <p className="text-sm text-app-muted">This run has not produced per-test results yet.</p>}
          </section>
        </div>
      ) : (
        <p className="text-sm text-app-secondary">Select a run to inspect execution output.</p>
      )}
    </DetailDrawer>
  );
}
