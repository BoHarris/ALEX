import RecordTable from "../RecordTable";
import { formatDateTime } from "../../../pages/compliance/utils";
import TaskPriorityBadge from "./TaskPriorityBadge";
import TaskStatusBadge from "./TaskStatusBadge";

export default function TaskTable({ tasks, onSelectTask }) {
  const columns = [
    {
      key: "title",
      label: "Task",
      render: (task) => (
        <div>
          <p className="font-semibold text-app">{task.title}</p>
          <p className="mt-1 text-xs text-app-muted">{task.task_key}</p>
        </div>
      ),
    },
    { key: "status", label: "Status", render: (task) => <TaskStatusBadge status={task.status} /> },
    { key: "priority", label: "Priority", render: (task) => <TaskPriorityBadge priority={task.priority} /> },
    { key: "source", label: "Source", render: (task) => <span className="text-app-secondary">{task.source?.label || task.source_module}</span> },
    { key: "assignee", label: "Assignee", render: (task) => task.assignee?.name || "Unassigned" },
    {
      key: "due_date",
      label: "Due",
      render: (task) => (
        <span className={task.is_overdue ? "font-medium text-rose-300" : "text-app-secondary"}>
          {task.due_date ? formatDateTime(task.due_date) : "No due date"}
        </span>
      ),
    },
    { key: "updated_at", label: "Updated", render: (task) => formatDateTime(task.updated_at) },
  ];

  return <RecordTable columns={columns} rows={tasks} onRowClick={onSelectTask} />;
}
