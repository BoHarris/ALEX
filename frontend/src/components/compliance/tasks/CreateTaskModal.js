import { useEffect, useState } from "react";
import { Button } from "../../button";
import DetailDrawer from "../DetailDrawer";

const initialState = {
  title: "",
  description: "",
  priority: "medium",
  due_date: "",
  assignee_employee_id: "",
  source_module: "manual",
};

export default function CreateTaskModal({ open, onClose, onSubmit, employees = [], title = "Create Task", subtitle = "Create a governance follow-up item from anywhere in the workspace." }) {
  const [form, setForm] = useState(initialState);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(initialState);
      setError(null);
      setSaving(false);
    }
  }, [open]);

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const trimmedTitle = form.title.trim();
      const trimmedDescription = form.description.trim();
      await onSubmit?.({
        title: trimmedTitle,
        description: trimmedDescription || null,
        priority: form.priority,
        source_module: form.source_module,
        source_type: form.source_module === "manual" ? "manual" : form.source_module,
        assignee_employee_id: form.assignee_employee_id ? Number(form.assignee_employee_id) : null,
        due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
      });
      onClose?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <DetailDrawer open={open} onClose={onClose} title={title} subtitle={subtitle}>
      <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
        <label className="md:col-span-2 text-sm text-app-secondary">
          Title
          <input
            required
            value={form.title}
            onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
            placeholder="Task title"
            className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
          />
        </label>
        <label className="md:col-span-2 text-sm text-app-secondary">
          Description
          <textarea
            value={form.description}
            onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            className="mt-2 min-h-32 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
          />
        </label>
        <label className="text-sm text-app-secondary">
          Priority
          <select
            value={form.priority}
            onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value }))}
            className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </label>
        <label className="text-sm text-app-secondary">
          Due date
          <input
            type="datetime-local"
            value={form.due_date}
            onChange={(event) => setForm((current) => ({ ...current, due_date: event.target.value }))}
            className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
          />
        </label>
        <label className="text-sm text-app-secondary">
          Assignee
          <select
            value={form.assignee_employee_id}
            onChange={(event) => setForm((current) => ({ ...current, assignee_employee_id: event.target.value }))}
            className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
          >
            <option value="">Unassigned</option>
            {employees.filter((employee) => employee.status !== "inactive").map((employee) => (
              <option key={employee.id} value={employee.id}>{employee.first_name} {employee.last_name}</option>
            ))}
          </select>
        </label>
        <label className="text-sm text-app-secondary">
          Source module
          <select
            value={form.source_module}
            onChange={(event) => setForm((current) => ({ ...current, source_module: event.target.value }))}
            className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
          >
            <option value="manual">Manual</option>
            <option value="security">Security</option>
            <option value="incidents">Incidents</option>
            <option value="vendors">Vendors</option>
            <option value="employees">Employees</option>
            <option value="testing">Testing</option>
          </select>
        </label>
        {error ? <p className="md:col-span-2 text-sm text-rose-300">{error}</p> : null}
        <div className="md:col-span-2 flex justify-end">
          <Button type="submit" disabled={saving}>{saving ? "Creating..." : "Create task"}</Button>
        </div>
      </form>
    </DetailDrawer>
  );
}
