jest.mock("react-router-dom", () => require("../../test/reactRouterDomMock"), { virtual: true });

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ComplianceTasksPage from "./ComplianceTasksPage";

const mockLoadTaskDetail = jest.fn();
const mockUpdateTask = jest.fn();
const mockCreateTask = jest.fn();
const mockClearTaskDetail = jest.fn();
const baseTaskDetail = {
  id: 1,
  task_key: "TASK-001",
  title: "Investigate security alert: Token abuse detected",
  description: "Review revoked refresh session reuse.",
  status: "todo",
  priority: "critical",
  source_module: "security",
  source: { label: "Token abuse detected", summary: "Review revoked refresh session reuse.", url: "/dashboard" },
  assignee_employee_id: 7,
  assignee: { id: 7, name: "Ada Lovelace" },
  reporter: { id: 8, name: "Grace Hopper" },
  updated_at: "2026-03-14T10:00:00+00:00",
  due_date: "2026-03-15T10:00:00+00:00",
  activity: [
    { id: 1, action: "created", details: "Task created", created_at: "2026-03-14T10:00:00+00:00", actor: { name: "Grace Hopper" } },
  ],
};
const vendorTaskDetail = {
  ...baseTaskDetail,
  id: 2,
  task_key: "TASK-002",
  title: "Review vendor risk: Acme Cloud",
  priority: "high",
  source_module: "vendors",
  source: { label: "Vendor Acme Cloud", summary: "Storage | high risk", url: "/compliance/vendors" },
  assignee_employee_id: 8,
  assignee: { id: 8, name: "Grace Hopper" },
  due_date: null,
};
let mockSelectedTaskDetail = null;

jest.mock("./useCompliancePageContext", () => ({
  useCompliancePageContext: () => ({
    data: {
      me: { employee: { id: 7 } },
      directory: {
        employees: [
          { id: 7, first_name: "Ada", last_name: "Lovelace", status: "active" },
          { id: 8, first_name: "Grace", last_name: "Hopper", status: "active" },
        ],
      },
      taskSummary: {
        summary: { open: 3, overdue: 1, critical: 1, mine: 1, security: 1, testing: 1 },
      },
      tasks: {
        tasks: [
          {
            id: 1,
            task_key: "TASK-001",
            title: "Investigate security alert: Token abuse detected",
            status: "todo",
            priority: "critical",
            source_module: "security",
            source_id: "21",
            source: { label: "Token abuse detected", summary: "Review revoked refresh session reuse.", url: "/dashboard" },
            assignee_employee_id: 7,
            assignee: { id: 7, name: "Ada Lovelace" },
            updated_at: "2026-03-14T10:00:00+00:00",
            due_date: "2026-03-15T10:00:00+00:00",
            is_open: true,
          },
          {
            id: 2,
            task_key: "TASK-002",
            title: "Review vendor risk: Acme Cloud",
            status: "in_progress",
            priority: "high",
            source_module: "vendors",
            source_id: "4",
            source: { label: "Vendor Acme Cloud", summary: "Storage | high risk", url: "/compliance/vendors" },
            assignee_employee_id: 8,
            assignee: { id: 8, name: "Grace Hopper" },
            updated_at: "2026-03-14T11:00:00+00:00",
            due_date: null,
            is_open: true,
          },
        ],
      },
    },
    selectedTaskDetail: mockSelectedTaskDetail,
    loadTaskDetail: mockLoadTaskDetail,
    updateTask: mockUpdateTask,
    createTask: mockCreateTask,
    clearTaskDetail: mockClearTaskDetail,
  }),
}));

beforeEach(() => {
  mockSelectedTaskDetail = null;
  mockLoadTaskDetail.mockClear();
  mockLoadTaskDetail.mockImplementation(async (taskId) => {
    mockSelectedTaskDetail = taskId === 2 ? vendorTaskDetail : baseTaskDetail;
  });
  mockUpdateTask.mockClear();
  mockCreateTask.mockClear();
  mockClearTaskDetail.mockClear();
});

function renderPage() {
  return render(
    <MemoryRouter>
      <ComplianceTasksPage />
    </MemoryRouter>,
  );
}

test("renders the task list with summary cards", () => {
  renderPage();

  expect(screen.getByText("Tasks")).toBeInTheDocument();
  expect(screen.getAllByText("Investigate security alert: Token abuse detected").length).toBeGreaterThan(0);
  expect(screen.getByText("Review vendor risk: Acme Cloud")).toBeInTheDocument();
  expect(screen.getByText("Open Tasks")).toBeInTheDocument();
  expect(screen.getAllByText("Critical").length).toBeGreaterThan(0);
});

test("filters tasks by search and opens the task drawer", async () => {
  const view = renderPage();

  await userEvent.type(screen.getByPlaceholderText("Search tasks, tests, incidents, vendors"), "vendor");

  expect(screen.queryByText("Investigate security alert: Token abuse detected")).not.toBeInTheDocument();
  expect(screen.getByText("Review vendor risk: Acme Cloud")).toBeInTheDocument();

  await userEvent.click(screen.getByText("Review vendor risk: Acme Cloud"));
  expect(mockLoadTaskDetail).toHaveBeenCalledWith(2);
  view.rerender(
    <MemoryRouter>
      <ComplianceTasksPage />
    </MemoryRouter>,
  );

  const dialog = screen.getByRole("dialog", { name: "Review vendor risk: Acme Cloud" });
  expect(dialog).toBeInTheDocument();
  expect(within(dialog).getAllByText("Vendor Acme Cloud").length).toBeGreaterThan(0);
});

test("creates a manual task from the create task drawer", async () => {
  mockCreateTask.mockResolvedValueOnce({});
  renderPage();

  await userEvent.click(screen.getAllByText("Create Task")[0]);
  await userEvent.type(screen.getByLabelText("Title"), "Quarterly access review follow-up");
  await userEvent.type(screen.getByLabelText("Description"), "Complete the remaining access review exceptions.");
  await userEvent.click(screen.getByRole("button", { name: "Create task" }));

  await waitFor(() => {
    expect(mockCreateTask).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Quarterly access review follow-up",
        priority: "medium",
        source_module: "manual",
      }),
    );
  });
});
