import { Button } from "../../button";
import DetailDrawer from "../DetailDrawer";
import { formatDateTime } from "../../../pages/compliance/utils";
import LinkedTaskPill from "./LinkedTaskPill";
import TaskPriorityBadge from "./TaskPriorityBadge";
import TaskStatusBadge from "./TaskStatusBadge";

export default function TaskDetailDrawer({
  open,
  task,
  employees = [],
  onClose,
  onChange,
  onViewSource,
}) {
  if (!task) {
    return null;
  }

  return (
    <DetailDrawer open={open} onClose={onClose} title={task.title} subtitle={`${task.task_key} | ${task.source?.label || task.source_module}`}>
      <section className="surface-card rounded-3xl p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              <TaskStatusBadge status={task.status} />
              <TaskPriorityBadge priority={task.priority} />
              {task.is_overdue ? <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-300">Overdue</span> : null}
            </div>
            <p className="text-sm leading-6 text-app-secondary">{task.description || "No description recorded yet."}</p>
          </div>
          {task.source?.label ? <LinkedTaskPill label={task.source.label} onClick={onViewSource} tone="accent" /> : null}
        </div>
      </section>

      <section className="surface-card rounded-3xl p-5">
        <h3 className="text-lg font-semibold text-app">Controls</h3>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="text-sm text-app-secondary">
            Status
            <select
              value={task.status}
              onChange={(event) => onChange?.({ status: event.target.value })}
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            >
              <option value="todo">To do</option>
              <option value="in_progress">In progress</option>
              <option value="blocked">Blocked</option>
              <option value="done">Done</option>
              <option value="canceled">Canceled</option>
            </select>
          </label>
          <label className="text-sm text-app-secondary">
            Priority
            <select
              value={task.priority}
              onChange={(event) => onChange?.({ priority: event.target.value })}
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
          <label className="text-sm text-app-secondary">
            Assignee
            <select
              value={task.assignee_employee_id || ""}
              onChange={(event) => onChange?.({ assignee_employee_id: event.target.value ? Number(event.target.value) : null })}
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            >
              <option value="">Unassigned</option>
              {employees.filter((employee) => employee.status !== "inactive").map((employee) => (
                <option key={employee.id} value={employee.id}>{employee.first_name} {employee.last_name}</option>
              ))}
            </select>
          </label>
          <label className="text-sm text-app-secondary">
            Due date
            <input
              type="datetime-local"
              value={task.due_date ? new Date(task.due_date).toISOString().slice(0, 16) : ""}
              onChange={(event) => onChange?.({ due_date: event.target.value || null })}
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            />
          </label>
        </div>
      </section>

      <section className="surface-card rounded-3xl p-5">
        <h3 className="text-lg font-semibold text-app">Linked Record</h3>
        <div className="mt-4 space-y-3 text-sm text-app-secondary">
          <p><span className="text-app-muted">Source:</span> {task.source?.label || "Manual task"}</p>
          <p><span className="text-app-muted">Assignee:</span> {task.assignee?.name || "Unassigned"}</p>
          <p><span className="text-app-muted">Reporter:</span> {task.reporter?.name || "System"}</p>
          <p><span className="text-app-muted">Due date:</span> {task.due_date ? formatDateTime(task.due_date) : "No due date"}</p>
          <p><span className="text-app-muted">Updated:</span> {formatDateTime(task.updated_at)}</p>
          <p><span className="text-app-muted">Source summary:</span> {task.source?.summary || "No source summary recorded."}</p>
        </div>
        {task.source?.url ? (
          <div className="mt-4">
            <Button onClick={onViewSource}>Open source record</Button>
          </div>
        ) : null}
      </section>

      <section className="surface-card rounded-3xl p-5">
        <h3 className="text-lg font-semibold text-app">Activity</h3>
        <div className="mt-4 space-y-3">
          {task.activity?.length ? task.activity.map((entry) => (
            <div key={entry.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
              <p className="font-semibold text-app">{entry.action}</p>
              <p className="mt-1">{entry.details || [entry.from_value, entry.to_value].filter(Boolean).join(" -> ") || "No additional details."}</p>
              <p className="mt-2 text-xs text-app-muted">{entry.actor?.name || "System"} | {formatDateTime(entry.created_at)}</p>
            </div>
          )) : <p className="text-sm text-app-muted">No activity history yet.</p>}
        </div>
      </section>
    </DetailDrawer>
  );
}
