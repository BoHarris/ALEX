import { Button } from "../../button";
import TaskPriorityBadge from "./TaskPriorityBadge";
import TaskStatusBadge from "./TaskStatusBadge";

function SummaryPill({ label, value }) {
  return (
    <div className="rounded-2xl border border-app bg-app/40 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-app-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-app">{value}</p>
    </div>
  );
}

function QueueTaskCard({ task, onOpen }) {
  return (
    <button
      type="button"
      onClick={() => onOpen?.(task)}
      className="w-full rounded-2xl border border-app bg-app/40 p-4 text-left transition hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-app px-3 py-1 text-xs font-semibold text-app-secondary">{task.task_key}</span>
        <TaskStatusBadge status={task.status} />
        <TaskPriorityBadge priority={task.priority} />
      </div>
      <p className="mt-3 text-sm font-semibold text-app">{task.title}</p>
      <p className="mt-2 text-sm leading-6 text-app-secondary">{task.summary || task.description || "No summary available."}</p>
      <p className="mt-3 text-xs text-app-muted">{task.metadata?.backlog_item_id || task.source_id || "No backlog id"}</p>
    </button>
  );
}

function BacklogRow({ item, onOpenTask }) {
  return (
    <div className="rounded-2xl border border-app bg-app/30 p-4">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-app-muted">{item.id}</p>
          <h4 className="mt-2 text-sm font-semibold text-app">{item.title}</h4>
          <p className="mt-2 text-sm leading-6 text-app-secondary">{item.suggested_improvement || item.description || "No suggested improvement recorded."}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 xl:justify-end">
          <TaskPriorityBadge priority={item.priority} />
          <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${item.eligible_for_automation ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200" : "border-amber-400/30 bg-amber-500/10 text-amber-200"}`}>
            {item.eligible_for_automation ? "Eligible" : "Needs review"}
          </span>
          {item.task_id ? <span className="rounded-full border border-app px-3 py-1 text-xs font-semibold text-app-secondary">{item.task_key || `TASK-${item.task_id}`}</span> : null}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-app-muted">
        <span>Area: {item.area}</span>
        <span>Risk: {item.risk}</span>
        <span>Status: {item.status.replace(/_/g, " ")}</span>
      </div>
      <p className="mt-2 text-xs leading-5 text-app-muted">{item.eligibility_reason}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {item.task_id ? <Button onClick={() => onOpenTask?.({ id: item.task_id })}>Open Task</Button> : null}
        {item.suggested_branch ? <span className="rounded-full border border-app px-3 py-1 text-xs font-semibold text-app-secondary">{item.suggested_branch}</span> : null}
      </div>
    </div>
  );
}

export default function AutomationQueuePanel({
  automation,
  loading = false,
  busy = false,
  onSyncBacklog,
  onStartNext,
  onOpenTask,
}) {
  const summary = automation?.summary || {};
  const activeTask = automation?.active_task || null;
  const eligibleTasks = automation?.eligible_tasks || [];
  const readyForReviewTasks = automation?.ready_for_review_tasks || [];
  const backlogItems = automation?.backlog_items || [];

  return (
    <section className="surface-card rounded-3xl p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-app">Automated Changes</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-app-secondary">
            Governed backlog sync for low-risk improvement work. Automation can take one eligible task at a time, move it into progress, and hand it back in Ready for Review for human approval.
          </p>
          <p className="mt-2 text-xs text-app-muted">Backlog source: {automation?.backlog_path || "docs/copilot_improvement_backlog.md"}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={onSyncBacklog} disabled={busy || loading}>Sync Backlog</Button>
          <Button onClick={onStartNext} disabled={busy || loading || !!activeTask || !eligibleTasks.length}>Start Next Eligible</Button>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <SummaryPill label="Backlog Items" value={summary.backlog_items ?? 0} />
        <SummaryPill label="Synced Tasks" value={summary.synced_tasks ?? 0} />
        <SummaryPill label="Eligible" value={summary.eligible_tasks ?? 0} />
        <SummaryPill label="Active" value={summary.active_tasks ?? 0} />
        <SummaryPill label="Ready For Review" value={summary.ready_for_review ?? 0} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <div className="space-y-6">
          <section className="rounded-3xl border border-app bg-app/25 p-5">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-app">Current Automation Slot</h3>
              {activeTask ? <TaskStatusBadge status={activeTask.status} /> : null}
            </div>
            {activeTask ? (
              <div className="mt-4">
                <QueueTaskCard task={activeTask} onOpen={onOpenTask} />
              </div>
            ) : (
              <p className="mt-4 text-sm text-app-secondary">No automation task is currently in progress. Start the next eligible item when you are ready.</p>
            )}
          </section>

          <section className="rounded-3xl border border-app bg-app/25 p-5">
            <h3 className="text-lg font-semibold text-app">Eligible Queue</h3>
            <div className="mt-4 space-y-3">
              {eligibleTasks.length ? eligibleTasks.map((task) => (
                <QueueTaskCard key={task.id} task={task} onOpen={onOpenTask} />
              )) : <p className="text-sm text-app-secondary">No eligible queued tasks are available yet. Sync the backlog or review blocked items.</p>}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="rounded-3xl border border-app bg-app/25 p-5">
            <h3 className="text-lg font-semibold text-app">Ready for Review</h3>
            <div className="mt-4 space-y-3">
              {readyForReviewTasks.length ? readyForReviewTasks.map((task) => (
                <QueueTaskCard key={task.id} task={task} onOpen={onOpenTask} />
              )) : <p className="text-sm text-app-secondary">Automation-completed work will appear here once it is ready for human review.</p>}
            </div>
          </section>

          <section className="rounded-3xl border border-app bg-app/25 p-5">
            <h3 className="text-lg font-semibold text-app">Backlog Traceability</h3>
            <div className="mt-4 space-y-3">
              {backlogItems.length ? backlogItems.map((item) => (
                <BacklogRow key={item.id} item={item} onOpenTask={onOpenTask} />
              )) : <p className="text-sm text-app-secondary">No backlog items were found yet.</p>}
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}
