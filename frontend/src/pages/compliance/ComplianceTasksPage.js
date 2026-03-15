import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/button";
import SummaryMetricCard from "../../components/compliance/SummaryMetricCard";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import AutomationQueuePanel from "../../components/compliance/tasks/AutomationQueuePanel";
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
  const incidents = workspace.data?.incidents?.incidents || [];
  const automation = workspace.data?.automation || null;
  const summary = workspace.data?.taskSummary?.summary || workspace.data?.overview?.task_summary || {};
  const employees = workspace.data?.directory?.employees || [];
  const currentEmployeeId = workspace.data?.me?.employee?.id || null;
  const [filters, setFilters] = useState(initialFilters);
  const [createOpen, setCreateOpen] = useState(false);
  const [pageError, setPageError] = useState(null);
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [taskDetailLoading, setTaskDetailLoading] = useState(false);
  const [taskSaving, setTaskSaving] = useState(false);
  const [automationBusy, setAutomationBusy] = useState(false);

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
    setSelectedTaskId(task.id);
    setTaskDetailLoading(true);
    setPageError(null);
    workspace.clearTaskDetail?.();
    try {
      await workspace.loadTaskDetail(task.id);
    } catch (err) {
      setSelectedTaskId(null);
      setPageError(err.message);
    } finally {
      setTaskDetailLoading(false);
    }
  }

  function closeTask() {
    setSelectedTaskId(null);
    setTaskDetailLoading(false);
    workspace.clearTaskDetail?.();
  }

  async function handleTaskChange(payload) {
    if (!selectedTaskId) {
      return;
    }
    try {
      setPageError(null);
      setTaskSaving(true);
      await workspace.updateTask(selectedTaskId, payload);
      await workspace.loadTaskDetail(selectedTaskId);
    } catch (err) {
      setPageError(err.message);
    } finally {
      setTaskSaving(false);
    }
  }

  async function runAutomationMutation(mutateFn, resolveTaskId = (result) => result?.payload?.task?.id ?? selectedTaskId) {
    try {
      setPageError(null);
      setAutomationBusy(true);
      const result = await mutateFn();
      const nextTaskId = resolveTaskId(result);
      if (nextTaskId) {
        setSelectedTaskId(nextTaskId);
        await workspace.loadTaskDetail(nextTaskId);
      }
      return result;
    } catch (err) {
      setPageError(err.message);
      return null;
    } finally {
      setAutomationBusy(false);
    }
  }

  async function handleCreateTask(payload) {
    setPageError(null);
    return workspace.createTask(payload);
  }

  function handleViewSource() {
    const task = workspace.selectedTaskDetail;
    if (!task?.source?.url) {
      return;
    }
    navigate(task.source.url, { state: { sourceId: task.source?.id } });
  }

  function handleViewIncident() {
    const task = workspace.selectedTaskDetail;
    if (!task?.incident_id) {
      return;
    }
    navigate(task.incident?.url || "/compliance/incidents", { state: { incidentId: task.incident_id } });
  }

  const drawerOpen = selectedTaskId != null;
  const activeAutomationTaskId = automation?.active_task?.id || null;

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

      <AutomationQueuePanel
        automation={automation}
        loading={workspace.loading}
        busy={automationBusy || taskSaving}
        onSyncBacklog={() => runAutomationMutation(() => workspace.syncAutomationBacklog(), () => selectedTaskId)}
        onStartNext={() => runAutomationMutation(() => workspace.startNextAutomationTask(), (result) => result?.payload?.task?.id || null)}
        onOpenTask={openTask}
      />

      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Tasks</h2>
            <p className="mt-2 text-sm text-app-secondary">A unified governance work queue across incidents, vendors, employees, testing, security alerts, and governed automation changes.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setCreateOpen(true)}>Create Task</Button>
            <Button onClick={() => navigate("/compliance/testing")}>Review Testing</Button>
            <Button onClick={() => navigate("/compliance/vendors")}>Review Vendors</Button>
          </div>
        </div>

        <TaskFilters filters={filters} setFilters={setFilters} assignees={employees} />

        <div className="mt-6">
          {filteredTasks.length ? (
            <TaskTable tasks={filteredTasks} onSelectTask={openTask} selectedTaskId={selectedTaskId} />
          ) : (
            <WorkspaceEmptyState
              title="No tasks match"
              description="Create a manual task or adjust filters to surface governance work across the workspace."
              action={<Button onClick={() => setCreateOpen(true)}>Create Task</Button>}
            />
          )}
        </div>
      </section>

      <CreateTaskModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreateTask}
        employees={employees}
      />

      <TaskDetailDrawer
        open={drawerOpen}
        loading={taskDetailLoading}
        saving={taskSaving || automationBusy}
        task={workspace.selectedTaskDetail}
        employees={employees}
        incidents={incidents}
        activeAutomationTaskId={activeAutomationTaskId}
        onClose={closeTask}
        onChange={handleTaskChange}
        onViewSource={handleViewSource}
        onViewIncident={handleViewIncident}
        onAssignAutomation={() => runAutomationMutation(() => workspace.assignTaskToAutomation(selectedTaskId))}
        onStartAutomation={() => runAutomationMutation(() => workspace.startAutomationTask(selectedTaskId))}
        onCompleteAutomation={(payload) => runAutomationMutation(() => workspace.completeAutomationTask(selectedTaskId, payload))}
        onFailAutomation={(payload) => runAutomationMutation(() => workspace.failAutomationTask(selectedTaskId, payload || { next_status: "blocked" }))}
        onBlockAutomation={(payload) => runAutomationMutation(() => workspace.blockAutomationTask(selectedTaskId, payload || { reason: "Blocked during automation work." }))}
        onMarkAutomationReady={(payload) => runAutomationMutation(() => workspace.markAutomationTaskReadyForReview(selectedTaskId, payload))}
        onReturnAutomationToBacklog={(payload) => runAutomationMutation(() => workspace.returnAutomationTaskToBacklog(selectedTaskId, payload))}
        onSaveAutomationMetadata={(payload) => runAutomationMutation(() => workspace.updateAutomationTaskMetadata(selectedTaskId, payload))}
      />

      {pageError ? <div className="surface-card rounded-3xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-300">{pageError}</div> : null}
    </div>
  );
}
