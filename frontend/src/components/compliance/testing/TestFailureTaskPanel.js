import { useEffect, useState } from "react";
import { formatDateTime, statusBadgeClass } from "../../../pages/compliance/utils";

export default function TestFailureTaskPanel({ test, employees, onCreateTask, onUpdateTask }) {
  const task = test?.task || null;
  const assignableEmployees = (employees || []).filter((employee) => employee.status !== "inactive");
  const [assigneeEmployeeId, setAssigneeEmployeeId] = useState(task?.assignee_employee_id ? String(task.assignee_employee_id) : "");
  const [priority, setPriority] = useState(task?.priority || "medium");
  const [status, setStatus] = useState(task?.status || "open");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setAssigneeEmployeeId(task?.assignee_employee_id ? String(task.assignee_employee_id) : "");
    setPriority(task?.priority || "medium");
    setStatus(task?.status || "open");
    setError(null);
  }, [task?.assignee_employee_id, task?.id, task?.priority, task?.status]);

  if (!test || test.status !== "failed") {
    return null;
  }

  async function handleCreateTask() {
    if (!onCreateTask) {
      return;
    }
    try {
      setSaving(true);
      setError(null);
      await onCreateTask(test.test_id, {
        assignee_employee_id: assigneeEmployeeId ? Number(assigneeEmployeeId) : null,
        priority,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveTask() {
    if (!task || !onUpdateTask) {
      return;
    }
    try {
      setSaving(true);
      setError(null);
      await onUpdateTask(task.id, {
        assignee_employee_id: assigneeEmployeeId ? Number(assigneeEmployeeId) : null,
        priority,
        status,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl border border-app/70 bg-app/25 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Failure Task</p>
          <h3 className="mt-2 text-base font-semibold text-app">{task?.title || "Create remediation task"}</h3>
          <p className="mt-2 text-sm leading-6 text-app-secondary">
            {task?.description || "Open a remediation task for this failing test and assign it to an engineer."}
          </p>
        </div>
        {task ? <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(task.status)}`}>{task.status}</span> : null}
      </div>

      {task ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-app/70 bg-app/35 p-3">
            <p className="text-[10px] uppercase tracking-[0.16em] text-app-muted">Priority</p>
            <p className="mt-2 text-sm font-medium text-app-secondary">{task.priority}</p>
          </div>
          <div className="rounded-2xl border border-app/70 bg-app/35 p-3">
            <p className="text-[10px] uppercase tracking-[0.16em] text-app-muted">Assignee</p>
            <p className="mt-2 text-sm font-medium text-app-secondary">{task.assignee?.name || "Unassigned"}</p>
          </div>
          <div className="rounded-2xl border border-app/70 bg-app/35 p-3">
            <p className="text-[10px] uppercase tracking-[0.16em] text-app-muted">Created</p>
            <p className="mt-2 text-sm font-medium text-app-secondary">{formatDateTime(task.created_at)}</p>
          </div>
          <div className="rounded-2xl border border-app/70 bg-app/35 p-3">
            <p className="text-[10px] uppercase tracking-[0.16em] text-app-muted">Updated</p>
            <p className="mt-2 text-sm font-medium text-app-secondary">{formatDateTime(task.updated_at)}</p>
          </div>
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <label className="flex flex-col gap-2 text-sm text-app-secondary">
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Assignee</span>
          <select
            value={assigneeEmployeeId}
            onChange={(event) => setAssigneeEmployeeId(event.target.value)}
            className="rounded-2xl border border-app bg-app/80 px-3 py-2.5 text-sm text-app focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60"
          >
            <option value="">Unassigned</option>
            {assignableEmployees.map((employee) => (
              <option key={employee.id} value={employee.id}>{employee.first_name} {employee.last_name}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-2 text-sm text-app-secondary">
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Priority</span>
          <select
            value={priority}
            onChange={(event) => setPriority(event.target.value)}
            className="rounded-2xl border border-app bg-app/80 px-3 py-2.5 text-sm text-app focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <label className="flex flex-col gap-2 text-sm text-app-secondary">
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Status</span>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="rounded-2xl border border-app bg-app/80 px-3 py-2.5 text-sm text-app focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60"
            disabled={!task}
          >
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
          </select>
        </label>
      </div>

      {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}

      <div className="mt-4 flex justify-end">
        {task ? (
          <button
            type="button"
            onClick={handleSaveTask}
            disabled={saving}
            className="rounded-full border border-cyan-300/40 bg-cyan-400/15 px-4 py-2 text-sm font-semibold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving..." : "Update task"}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleCreateTask}
            disabled={saving}
            className="rounded-full border border-cyan-300/40 bg-cyan-400/15 px-4 py-2 text-sm font-semibold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Creating..." : "Create remediation task"}
          </button>
        )}
      </div>
    </div>
  );
}
