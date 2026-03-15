import { useEffect, useState } from "react";
import { Button } from "../../button";
import DetailDrawer from "../DetailDrawer";
import {
  formatDate,
  formatDateTime,
  formatStatusLabel,
  formatTaskPriorityLabel,
} from "../../../pages/compliance/utils";
import LinkedTaskPill from "./LinkedTaskPill";
import TaskPriorityBadge from "./TaskPriorityBadge";
import TaskStatusBadge from "./TaskStatusBadge";

const STATUS_OPTIONS = [
  { value: "todo", label: "To do" },
  { value: "in_progress", label: "In progress" },
  { value: "blocked", label: "Blocked" },
  { value: "ready_for_review", label: "Ready for review" },
  { value: "done", label: "Done" },
  { value: "canceled", label: "Canceled" },
];

const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

const ACTIVITY_LABELS = {
  created: "Task created",
  reopened: "Task reopened",
  status_changed: "Status changed",
  priority_changed: "Priority changed",
  assignee_changed: "Assignee changed",
  due_date_changed: "Due date changed",
  incident_linked: "Incident linked",
  source_linked: "Source updated",
  title_changed: "Title updated",
  description_changed: "Description updated",
  source_retriggered: "Source triggered again",
  backlog_synced: "Backlog synced",
  automation_started: "Automation started",
  automation_blocked: "Automation blocked",
  automation_ready_for_review: "Automation ready for review",
  returned_to_backlog: "Returned to backlog",
  automation_metadata_updated: "Automation metadata updated",
};

function labelize(value) {
  if (!value) {
    return null;
  }
  return value.replace(/_/g, " ");
}

function formatPersonName(person) {
  return person?.name || "Unassigned";
}

function toDateTimeLocalValue(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16);
}

function summarizeTask(task) {
  const metadataSummary = task.summary || task.metadata?.operator_summary || task.metadata?.summary;
  if (metadataSummary) {
    return metadataSummary;
  }
  if (task.description) {
    const [firstLine] = task.description.split("\n").map((line) => line.trim()).filter(Boolean);
    if (firstLine) {
      return firstLine;
    }
  }
  return task.source?.summary || "Review the task context and linked records to continue this workflow.";
}

function buildContextItems(task) {
  const items = [];
  const lines = (task.description || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const summary = summarizeTask(task);
  lines.forEach((line) => {
    if (line !== summary) {
      items.push(line);
    }
  });

  if (task.source?.summary && task.source.summary !== summary) {
    items.unshift(task.source.summary);
  }

  if (task.metadata?.test_name) {
    items.push(`Failing test: ${task.metadata.test_name}`);
  }
  if (task.metadata?.latest_failed_result_id) {
    items.push(`Latest failed result: #${task.metadata.latest_failed_result_id}`);
  }
  if (task.metadata?.event_type) {
    items.push(`Security event: ${labelize(task.metadata.event_type)}`);
  }
  if (task.metadata?.token_issue) {
    items.push(`Session issue: ${labelize(task.metadata.token_issue)}`);
  }
  if (task.metadata?.employee_name) {
    items.push(`Employee record: ${task.metadata.employee_name}`);
  }
  if (task.metadata?.severity) {
    items.push(`Severity: ${formatTaskPriorityLabel(task.metadata.severity)}`);
  }
  if (task.metadata?.suggested_improvement) {
    items.push(`Suggested improvement: ${task.metadata.suggested_improvement}`);
  }
  if (task.metadata?.automation_eligibility_reason) {
    items.push(`Automation eligibility: ${task.metadata.automation_eligibility_reason}`);
  }

  return [...new Set(items.filter(Boolean))];
}

function formatActivityDetails(entry, employeesById) {
  if (entry.details) {
    return entry.details;
  }
  if (entry.action === "status_changed") {
    return `${formatStatusLabel(entry.from_value)} -> ${formatStatusLabel(entry.to_value)}`;
  }
  if (entry.action === "priority_changed") {
    return `${formatTaskPriorityLabel(entry.from_value)} -> ${formatTaskPriorityLabel(entry.to_value)}`;
  }
  if (entry.action === "assignee_changed") {
    const fromEmployee = employeesById.get(Number(entry.from_value));
    const toEmployee = employeesById.get(Number(entry.to_value));
    const fromLabel = fromEmployee?.name || entry.from_value || "Unassigned";
    const toLabel = toEmployee?.name || entry.to_value || "Unassigned";
    return `${fromLabel} -> ${toLabel}`;
  }
  if (entry.action === "due_date_changed") {
    return `${formatDateTime(entry.from_value)} -> ${formatDateTime(entry.to_value)}`;
  }
  if (entry.action === "incident_linked") {
    return entry.to_value ? `Linked to incident #${entry.to_value}` : "Incident link updated.";
  }
  if (entry.action === "source_linked") {
    return entry.to_value || "Source record updated.";
  }
  if (entry.from_value || entry.to_value) {
    return [entry.from_value, entry.to_value].filter(Boolean).join(" -> ");
  }
  return "No additional details.";
}

function FieldValue({ label, value }) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-app-muted">{label}</p>
      <p className="text-sm text-app-secondary">{value}</p>
    </div>
  );
}

function LoadingState() {
  return (
    <section className="surface-card rounded-3xl p-5">
      <p className="text-sm text-app-secondary">Loading task details...</p>
    </section>
  );
}

function automationFormFromTask(task) {
  return {
    branch_name: task?.metadata?.branch_name || "",
    commit_message: task?.metadata?.commit_message || "",
    implementation_summary: task?.metadata?.implementation_summary || "",
    review_notes: task?.metadata?.review_notes || "",
  };
}

function isAutomationTask(task) {
  return Boolean(task?.source_type === "backlog_improvement" || task?.assignee_type === "automation" || task?.workflow?.automation_source);
}

export default function TaskDetailDrawer({
  open,
  loading = false,
  saving = false,
  task,
  employees = [],
  incidents = [],
  onClose,
  onChange,
  onViewSource,
  onViewIncident,
  onAssignAutomation,
  onStartAutomation,
  onBlockAutomation,
  onMarkAutomationReady,
  onReturnAutomationToBacklog,
  onSaveAutomationMetadata,
  activeAutomationTaskId = null,
}) {
  const [automationForm, setAutomationForm] = useState(automationFormFromTask(task));

  useEffect(() => {
    setAutomationForm(automationFormFromTask(task));
  }, [task?.id, task?.metadata?.branch_name, task?.metadata?.commit_message, task?.metadata?.implementation_summary, task?.metadata?.review_notes]);

  const employeesById = new Map(employees.map((employee) => [
    employee.id,
    { name: `${employee.first_name} ${employee.last_name}`.trim() || employee.email },
  ]));
  const linkedIncident = task?.incident || incidents.find((entry) => entry.incident.id === task?.incident_id);
  const contextItems = task ? buildContextItems(task) : [];
  const automationTask = isAutomationTask(task);
  const automationAssigned = task?.assignee_type === "automation";
  const anotherAutomationTaskActive = activeAutomationTaskId != null && activeAutomationTaskId !== task?.id;
  const automationFormChanged = Boolean(task) && ["branch_name", "commit_message", "implementation_summary", "review_notes"].some(
    (field) => (automationForm[field] || "") !== (task.metadata?.[field] || ""),
  );

  async function handleSaveAutomationMetadata() {
    if (!task || !onSaveAutomationMetadata) {
      return;
    }
    await onSaveAutomationMetadata({
      branch_name: automationForm.branch_name.trim() || null,
      commit_message: automationForm.commit_message.trim() || null,
      implementation_summary: automationForm.implementation_summary.trim() || null,
      review_notes: automationForm.review_notes.trim() || null,
    });
  }

  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      title={task?.title || "Task details"}
      subtitle={task ? `${task.task_key} | ${task.source?.label || task.source_module}` : "Task workflow"}
      side="center"
      widthClass="max-w-[min(96vw,96rem)]"
      panelClass="mx-auto"
    >
      {loading ? <LoadingState /> : null}

      {!loading && !task ? (
        <section className="surface-card rounded-3xl p-5">
          <p className="text-sm text-app-secondary">Select a task to review workflow details.</p>
        </section>
      ) : null}

      {!loading && task ? (
        <>
          <section className="surface-card rounded-3xl p-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-app px-3 py-1 text-xs font-semibold text-app-secondary">{task.task_key}</span>
                  <TaskStatusBadge status={task.status} />
                  <TaskPriorityBadge priority={task.priority} />
                  <span className="rounded-full border border-app px-3 py-1 text-xs font-semibold text-app-secondary">{task.source?.type || task.source_type}</span>
                  {automationAssigned ? <span className="rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3 py-1 text-xs font-semibold text-cyan-200">Automated Changes</span> : null}
                  {task.is_overdue ? <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-300">Overdue</span> : null}
                </div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <FieldValue label="Assignee" value={task.assignee?.name || task.assignee_label || "Unassigned"} />
                  <FieldValue label="Reporter" value={task.reporter?.name || "System"} />
                  <FieldValue label="Due date" value={task.due_date ? formatDateTime(task.due_date) : "No due date"} />
                  <FieldValue label="Updated" value={formatDateTime(task.updated_at)} />
                </div>
              </div>
              <div className="flex flex-wrap gap-2 xl:justify-end">
                {automationTask ? (
                  <>
                    {!automationAssigned ? (
                      <Button onClick={() => onAssignAutomation?.()} disabled={saving}>Assign to Automated Changes</Button>
                    ) : null}
                    {automationAssigned && task.status !== "in_progress" && task.status !== "ready_for_review" && task.status !== "done" && task.status !== "canceled" ? (
                      <Button onClick={() => onStartAutomation?.()} disabled={saving || anotherAutomationTaskActive}>Start Automated Work</Button>
                    ) : null}
                    {automationAssigned && task.status === "in_progress" ? (
                      <Button onClick={() => onBlockAutomation?.({ reason: automationForm.review_notes.trim() || null })} disabled={saving}>Mark Blocked</Button>
                    ) : null}
                    {automationAssigned && task.status !== "ready_for_review" && task.status !== "done" && task.status !== "canceled" ? (
                      <Button onClick={() => onMarkAutomationReady?.({
                        branch_name: automationForm.branch_name.trim() || null,
                        commit_message: automationForm.commit_message.trim() || null,
                        implementation_summary: automationForm.implementation_summary.trim() || null,
                        review_notes: automationForm.review_notes.trim() || null,
                      })} disabled={saving}>Mark Ready for Review</Button>
                    ) : null}
                    {(automationAssigned || task.status === "ready_for_review" || task.status === "blocked") ? (
                      <Button onClick={() => onReturnAutomationToBacklog?.({ review_notes: automationForm.review_notes.trim() || null })} disabled={saving}>Return to Backlog</Button>
                    ) : null}
                  </>
                ) : (
                  <Button onClick={() => onChange?.({ status: "ready_for_review" })} disabled={saving || task.status === "ready_for_review"}>
                    Mark Ready for Review
                  </Button>
                )}
                {task.source?.url ? <LinkedTaskPill label="View source" onClick={onViewSource} tone="accent" /> : null}
                {linkedIncident ? <LinkedTaskPill label="View linked incident" onClick={onViewIncident} /> : null}
              </div>
            </div>
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.4fr,1fr]">
            <div className="space-y-6">
              <section className="surface-card rounded-3xl p-5">
                <h3 className="text-lg font-semibold text-app">Summary</h3>
                <p className="mt-3 text-sm leading-6 text-app-secondary">{summarizeTask(task)}</p>
              </section>

              <section className="surface-card rounded-3xl p-5">
                <h3 className="text-lg font-semibold text-app">Description</h3>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-app-secondary">{task.description || "No description recorded yet."}</p>
              </section>

              <section className="surface-card rounded-3xl p-5">
                <h3 className="text-lg font-semibold text-app">Source Information</h3>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <FieldValue label="Source type" value={labelize(task.source?.type) || "Manual"} />
                  <FieldValue label="Source module" value={labelize(task.source?.module) || "Manual"} />
                  <FieldValue label="Source id" value={task.source?.id || task.source_id || "Not recorded"} />
                  <FieldValue label="Source label" value={task.source?.label || "Manual task"} />
                </div>
                <div className="mt-4 rounded-2xl border border-app bg-app/40 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-app-muted">Linked record summary</p>
                  <p className="mt-2 text-sm leading-6 text-app-secondary">{task.source?.summary || "No source summary recorded."}</p>
                </div>
                {task.source?.url ? (
                  <div className="mt-4">
                    <Button onClick={onViewSource}>Open source record</Button>
                  </div>
                ) : null}
              </section>

              <section className="surface-card rounded-3xl p-5">
                <h3 className="text-lg font-semibold text-app">Failure / Risk Context</h3>
                <div className="mt-4 space-y-3">
                  {contextItems.length ? contextItems.map((item) => (
                    <div key={item} className="rounded-2xl border border-app bg-app/40 p-4 text-sm leading-6 text-app-secondary">
                      {item}
                    </div>
                  )) : <p className="text-sm text-app-muted">No additional failure or risk context was recorded for this task.</p>}
                </div>
              </section>

              {automationTask ? (
                <section className="surface-card rounded-3xl p-5">
                  <h3 className="text-lg font-semibold text-app">Backlog Source</h3>
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <FieldValue label="Backlog item" value={task.metadata?.backlog_item_id || task.source_id || "Not recorded"} />
                    <FieldValue label="Backlog file" value={task.metadata?.backlog_file_path || "docs/copilot_improvement_backlog.md"} />
                    <FieldValue label="Area" value={task.metadata?.area || "Platform"} />
                    <FieldValue label="Risk" value={formatTaskPriorityLabel(task.metadata?.risk || "medium")} />
                    <FieldValue label="Backlog status" value={formatStatusLabel(task.metadata?.backlog_status || "open")} />
                    <FieldValue label="Dependencies" value={task.metadata?.dependencies || "None"} />
                  </div>
                  <div className="mt-4 rounded-2xl border border-app bg-app/40 p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">Suggested improvement</p>
                    <p className="mt-2 leading-6">{task.metadata?.suggested_improvement || "No suggested improvement recorded."}</p>
                    <p className="mt-3 text-xs text-app-muted">{task.metadata?.automation_eligibility_reason || "No automation eligibility notes recorded."}</p>
                  </div>
                </section>
              ) : null}

              <section className="surface-card rounded-3xl p-5">
                <h3 className="text-lg font-semibold text-app">Activity / History</h3>
                <div className="mt-4 space-y-3">
                  {task.activity?.length ? task.activity.map((entry) => (
                    <div key={entry.id} className="rounded-2xl border border-app bg-app/40 p-4 text-sm text-app-secondary">
                      <p className="font-semibold text-app">{ACTIVITY_LABELS[entry.action] || labelize(entry.action) || "Task updated"}</p>
                      <p className="mt-1 leading-6">{formatActivityDetails(entry, employeesById)}</p>
                      <p className="mt-2 text-xs text-app-muted">{entry.actor?.name || "System"} | {formatDateTime(entry.created_at)}</p>
                    </div>
                  )) : <p className="text-sm text-app-muted">No activity history yet.</p>}
                </div>
              </section>
            </div>

            <div className="space-y-6">
              <section className="surface-card rounded-3xl p-5">
                <h3 className="text-lg font-semibold text-app">Assignment and Workflow</h3>
                <div className="mt-4 grid gap-4">
                  <label className="text-sm text-app-secondary">
                    Status
                    <select
                      value={task.status}
                      disabled={saving}
                      onChange={(event) => onChange?.({ status: event.target.value })}
                      className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {STATUS_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm text-app-secondary">
                    Priority
                    <select
                      value={task.priority}
                      disabled={saving}
                      onChange={(event) => onChange?.({ priority: event.target.value })}
                      className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {PRIORITY_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm text-app-secondary">
                    Assignee
                    <select
                      value={task.assignee_type === "automation" ? "__automation__" : (task.assignee_employee_id || "")}
                      disabled={saving}
                      onChange={(event) => {
                        const { value } = event.target;
                        if (value === "__automation__") {
                          onAssignAutomation?.();
                          return;
                        }
                        onChange?.({ assignee_employee_id: value ? Number(value) : null });
                      }}
                      className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <option value="">Unassigned</option>
                      <option value="__automation__">Automated Changes</option>
                      {employees.filter((employee) => employee.status !== "inactive").map((employee) => (
                        <option key={employee.id} value={employee.id}>{employee.first_name} {employee.last_name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm text-app-secondary">
                    Due date
                    <input
                      type="datetime-local"
                      value={toDateTimeLocalValue(task.due_date)}
                      disabled={saving}
                      onChange={(event) => onChange?.({ due_date: event.target.value ? new Date(event.target.value).toISOString() : null })}
                      className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app disabled:cursor-not-allowed disabled:opacity-60"
                    />
                  </label>
                  <div className="flex justify-end">
                    <button
                      type="button"
                      disabled={saving || !task.due_date}
                      onClick={() => onChange?.({ due_date: null })}
                      className="text-sm text-app-secondary underline-offset-4 hover:text-app hover:underline disabled:cursor-not-allowed disabled:no-underline disabled:opacity-60"
                    >
                      Clear due date
                    </button>
                  </div>
                </div>
              </section>

              {automationTask ? (
                <section className="surface-card rounded-3xl p-5">
                  <h3 className="text-lg font-semibold text-app">Automation Execution</h3>
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <FieldValue label="Owner type" value={task.workflow?.owner_type || "unassigned"} />
                    <FieldValue label="Execution mode" value={task.workflow?.execution_mode || "manual"} />
                    <FieldValue label="Review state" value={task.workflow?.review_state || "none"} />
                    <FieldValue label="Review expectation" value={task.metadata?.review_expectation || "Human review required."} />
                  </div>
                  <div className="mt-4 grid gap-4">
                    <label className="text-sm text-app-secondary">
                      Branch name
                      <input
                        value={automationForm.branch_name}
                        onChange={(event) => setAutomationForm((current) => ({ ...current, branch_name: event.target.value }))}
                        disabled={saving}
                        className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app disabled:cursor-not-allowed disabled:opacity-60"
                        placeholder="improvement/alex-imp-001-task-filter-clarity"
                      />
                    </label>
                    <label className="text-sm text-app-secondary">
                      Commit message
                      <input
                        value={automationForm.commit_message}
                        onChange={(event) => setAutomationForm((current) => ({ ...current, commit_message: event.target.value }))}
                        disabled={saving}
                        className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app disabled:cursor-not-allowed disabled:opacity-60"
                        placeholder="feat: improve task filter control clarity"
                      />
                    </label>
                    <label className="text-sm text-app-secondary">
                      Implementation summary
                      <textarea
                        value={automationForm.implementation_summary}
                        onChange={(event) => setAutomationForm((current) => ({ ...current, implementation_summary: event.target.value }))}
                        disabled={saving}
                        rows={4}
                        className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app disabled:cursor-not-allowed disabled:opacity-60"
                        placeholder="Summarize what the automation changed for the reviewer."
                      />
                    </label>
                    <label className="text-sm text-app-secondary">
                      Review notes
                      <textarea
                        value={automationForm.review_notes}
                        onChange={(event) => setAutomationForm((current) => ({ ...current, review_notes: event.target.value }))}
                        disabled={saving}
                        rows={3}
                        className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app disabled:cursor-not-allowed disabled:opacity-60"
                        placeholder="Capture reviewer guidance, validation notes, or reopen context."
                      />
                    </label>
                    <div className="flex justify-end">
                      <Button onClick={handleSaveAutomationMetadata} disabled={saving || !automationFormChanged}>Save Automation Notes</Button>
                    </div>
                  </div>
                </section>
              ) : null}

              <section className="surface-card rounded-3xl p-5">
                <h3 className="text-lg font-semibold text-app">Incident Linkage</h3>
                <div className="mt-4 space-y-4">
                  <label className="text-sm text-app-secondary">
                    Linked incident
                    <select
                      value={task.incident_id || ""}
                      disabled={saving || !incidents.length}
                      onChange={(event) => onChange?.({ incident_id: event.target.value ? Number(event.target.value) : null })}
                      className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <option value="">No linked incident</option>
                      {incidents.map((entry) => (
                        <option key={entry.incident.id} value={entry.incident.id}>
                          {`INC-${entry.incident.id} | ${entry.record.title}`}
                        </option>
                      ))}
                    </select>
                  </label>
                  {linkedIncident ? (
                    <div className="rounded-2xl border border-app bg-app/40 p-4 text-sm text-app-secondary">
                      <p className="font-semibold text-app">{linkedIncident.record?.title || linkedIncident.title || `Incident #${linkedIncident.incident?.id || linkedIncident.id}`}</p>
                      <p className="mt-2">Severity: {formatTaskPriorityLabel(linkedIncident.incident?.severity || linkedIncident.severity || "Not set")}</p>
                      <p className="mt-1">Status: {formatStatusLabel(linkedIncident.record?.status || linkedIncident.status)}</p>
                      <p className="mt-2 leading-6">{linkedIncident.incident?.description || linkedIncident.description || "No incident summary available."}</p>
                    </div>
                  ) : (
                    <p className="text-sm text-app-muted">Link this task to an incident when remediation needs to be tracked alongside incident response.</p>
                  )}
                  {linkedIncident ? <Button onClick={onViewIncident}>Open incidents workspace</Button> : null}
                </div>
              </section>

              <section className="surface-card rounded-3xl p-5">
                <h3 className="text-lg font-semibold text-app">Metadata / Technical Details</h3>
                <details className="mt-4 rounded-2xl border border-app bg-app/40 p-4">
                  <summary className="cursor-pointer text-sm font-semibold text-app">Show raw task metadata</summary>
                  <div className="mt-4 space-y-3 text-sm text-app-secondary">
                    <FieldValue label="Task id" value={String(task.id)} />
                    <FieldValue label="Created" value={formatDateTime(task.created_at)} />
                    <FieldValue label="Resolved" value={task.resolved_at ? formatDateTime(task.resolved_at) : "Not resolved"} />
                    <FieldValue label="Workflow owner type" value={task.workflow?.owner_type || "employee"} />
                    <FieldValue label="Execution mode" value={task.workflow?.execution_mode || "manual"} />
                    <FieldValue label="Review state" value={task.workflow?.review_state || (task.status === "ready_for_review" ? "pending_review" : "none")} />
                    <FieldValue label="Automation source" value={task.workflow?.automation_source || "None"} />
                    <FieldValue label="Due date only" value={task.due_date ? formatDate(task.due_date) : "No due date"} />
                    <pre className="overflow-x-auto rounded-2xl border border-app bg-slate-950/40 p-4 text-xs text-app-secondary">
                      {JSON.stringify(task.metadata || {}, null, 2)}
                    </pre>
                  </div>
                </details>
              </section>
            </div>
          </section>
        </>
      ) : null}
    </DetailDrawer>
  );
}
