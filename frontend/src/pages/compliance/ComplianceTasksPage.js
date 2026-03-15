import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/button";
import SummaryMetricCard from "../../components/compliance/SummaryMetricCard";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import CreateTaskModal from "../../components/compliance/tasks/CreateTaskModal";
import TaskDetailDrawer from "../../components/compliance/tasks/TaskDetailDrawer";
import TaskFilters from "../../components/compliance/tasks/TaskFilters";
import TaskTable from "../../components/compliance/tasks/TaskTable";
import { useCompliancePageContext } from "./useCompliancePageContext";

const initialFilters = {
  search: "",
  status: "",
  priority: "",
  sourceModule: "",
  assigneeEmployeeId: "",
  dueDate: "",
  myTasks: false,
  openOnly: true,
};

export default function ComplianceTasksPage() {
  const navigate = useNavigate();
  const workspace = useCompliancePageContext();
  const tasks = workspace.data?.tasks?.tasks || [];
  const summary = workspace.data?.taskSummary?.summary || workspace.data?.overview?.task_summary || {};
  const employees = workspace.data?.directory?.employees || [];
  const currentEmployeeId = workspace.data?.me?.employee?.id || null;
  const [filters, setFilters] = useState(initialFilters);
  const [createOpen, setCreateOpen] = useState(false);
  const [pageError, setPageError] = useState(null);

  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      const searchValue = filters.search.trim().toLowerCase();
      const matchesSearch = !searchValue || [task.title, task.task_key, task.source?.label, task.source?.summary, task.assignee?.name, task.source_id]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(searchValue));
      const matchesStatus = !filters.status || task.status === filters.status;
      const matchesPriority = !filters.priority || task.priority === filters.priority;
      const matchesSource = !filters.sourceModule || task.source_module === filters.sourceModule;
      const matchesAssignee = !filters.assigneeEmployeeId || String(task.assignee_employee_id || "") === filters.assigneeEmployeeId;
      const matchesDueDate = !filters.dueDate || (task.due_date && new Date(task.due_date).toISOString().slice(0, 10) <= filters.dueDate);
      const matchesMine = !filters.myTasks || (currentEmployeeId != null && task.assignee_employee_id === currentEmployeeId);
      const matchesOpen = !filters.openOnly || task.is_open;
      return matchesSearch && matchesStatus && matchesPriority && matchesSource && matchesAssignee && matchesDueDate && matchesMine && matchesOpen;
    });
  }, [currentEmployeeId, filters, tasks]);

  async function openTask(task) {
    try {
      setPageError(null);
      await workspace.loadTaskDetail(task.id);
    } catch (err) {
      setPageError(err.message);
    }
  }

  async function handleTaskChange(payload) {
    if (!workspace.selectedTaskDetail) {
      return;
    }
    try {
      setPageError(null);
      await workspace.updateTask(workspace.selectedTaskDetail.id, payload);
      await workspace.loadTaskDetail(workspace.selectedTaskDetail.id);
    } catch (err) {
      setPageError(err.message);
    }
  }

  async function handleCreateTask(payload) {
    setPageError(null);
    await workspace.createTask(payload);
  }

  function handleViewSource() {
    const task = workspace.selectedTaskDetail;
    if (!task?.source?.url) {
      return;
    }
    navigate(task.source.url);
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <SummaryMetricCard label="Open Tasks" value={summary.open ?? 0} />
        <SummaryMetricCard label="Overdue" value={summary.overdue ?? 0} />
        <SummaryMetricCard label="Critical" value={summary.critical ?? 0} />
        <SummaryMetricCard label="My Tasks" value={summary.mine ?? 0} />
        <SummaryMetricCard label="From Security" value={summary.security ?? 0} />
        <SummaryMetricCard label="From Testing" value={summary.testing ?? 0} />
      </section>

      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Tasks</h2>
            <p className="mt-2 text-sm text-app-secondary">A unified governance work queue across incidents, vendors, employees, testing, and security alerts.</p>
          </div>
          <div className="flex gap-2">
            <Button label="Create Task" onClick={() => setCreateOpen(true)} />
            <Button label="Create from Test Failure" onClick={() => workspace.createTaskFromSource("test-failure")} />
            <Button label="Create from Vendor" onClick={() => workspace.createTaskFromSource("vendor")} />
          </div>
        </div>

        <TaskFilters filters={filters} onChange={setFilters} />
        <TaskTable tasks={filteredTasks} onRowClick={openTask} />
      </section>

      <CreateTaskModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreateTask}
      />

      <TaskDetailDrawer
        task={workspace.selectedTaskDetail}
        onChange={handleTaskChange}
        onViewSource={handleViewSource}
      />

      {pageError ? <div className="surface-card rounded-3xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-300">{pageError}</div> : null}

      {filteredTasks.length ? (
        <TaskTable tasks={filteredTasks} onSelectTask={openTask} />
      ) : (
        <WorkspaceEmptyState
          title="No tasks match"
          description="Create a manual task or adjust filters to surface governance work across the workspace."
          action={<Button onClick={() => setCreateOpen(true)}>Create Task</Button>}
        />
      )}
    </div>
  );
}
