jest.mock("react-router-dom", () => require("../../test/reactRouterDomMock"), { virtual: true });

import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ComplianceTasksPage from "./ComplianceTasksPage";

const mockLoadTaskDetail = jest.fn();
const mockUpdateTask = jest.fn();
const mockCreateTask = jest.fn();
const mockClearTaskDetail = jest.fn();
const mockSyncAutomationBacklog = jest.fn();
const mockStartNextAutomationTask = jest.fn();
const mockAssignTaskToAutomation = jest.fn();
const mockStartAutomationTask = jest.fn();
const mockBlockAutomationTask = jest.fn();
const mockMarkAutomationTaskReadyForReview = jest.fn();
const mockReturnAutomationTaskToBacklog = jest.fn();
const mockUpdateAutomationTaskMetadata = jest.fn();

const baseTaskDetail = {
  id: 1,
  task_key: "TASK-001",
  title: "Investigate security alert: Token abuse detected",
  description: "Review revoked refresh session reuse.\nReceived HTTP 500 during validation.\nRe-check token revocation handling.",
  status: "todo",
  priority: "critical",
  source_module: "security",
  source_type: "security_alert",
  source: { label: "Token abuse detected", summary: "Review revoked refresh session reuse.", type: "security_alert", module: "security", url: "/dashboard" },
  incident_id: 11,
  incident: {
    id: 11,
    title: "Session misuse investigation",
    status: "investigating",
    severity: "high",
    description: "Suspicious refresh session reuse detected.",
    url: "/compliance/incidents",
  },
  assignee_employee_id: 7,
  assignee_type: "employee",
  assignee_label: null,
  assignee: { id: 7, name: "Ada Lovelace", type: "employee", label: "Ada Lovelace" },
  reporter: { id: 8, name: "Grace Hopper" },
  updated_at: "2026-03-14T10:00:00+00:00",
  due_date: "2026-03-15T10:00:00+00:00",
  workflow: { owner_type: "employee", execution_mode: "manual", review_state: "none", automation_source: null },
  metadata: { event_type: "token_abuse", token_issue: "refresh_session_revoked_session" },
  activity: [
    { id: 1, action: "created", details: "Task created", created_at: "2026-03-14T10:00:00+00:00", actor: { name: "Grace Hopper" } },
  ],
};

const reviewTaskDetail = {
  ...baseTaskDetail,
  id: 2,
  task_key: "TASK-002",
  title: "Review vendor risk: Acme Cloud",
  description: "Confirm remediation evidence and prepare the change for review.",
  status: "ready_for_review",
  priority: "high",
  source_module: "vendors",
  source_type: "vendor_review",
  source: { label: "Vendor Acme Cloud", summary: "Storage | high risk", type: "vendor_review", module: "vendors", url: "/compliance/vendors" },
  incident_id: null,
  incident: null,
  assignee_employee_id: 8,
  assignee_type: "employee",
  assignee_label: null,
  assignee: { id: 8, name: "Grace Hopper", type: "employee", label: "Grace Hopper" },
  due_date: null,
  workflow: { owner_type: "employee", execution_mode: "manual", review_state: "pending_review", automation_source: null },
  metadata: { vendor_name: "Acme Cloud", risk_rating: "high" },
};

const automationTaskDetail = {
  id: 4,
  task_key: "TASK-004",
  title: "Improve task filter clarity",
  description: "Expand the filter controls and clean up spacing for operators.",
  status: "todo",
  priority: "high",
  source_module: "automation",
  source_type: "backlog_improvement",
  source: { label: "Backlog ALEX-IMP-001", summary: "Use larger segmented controls for task filters.", type: "backlog_improvement", module: "automation", url: "/compliance/tasks" },
  incident_id: null,
  incident: null,
  assignee_employee_id: null,
  assignee_type: null,
  assignee_label: null,
  assignee: null,
  reporter: null,
  updated_at: "2026-03-15T12:00:00+00:00",
  due_date: null,
  workflow: { owner_type: "unassigned", execution_mode: "manual", review_state: "none", automation_source: "backlog" },
  metadata: {
    backlog_item_id: "ALEX-IMP-001",
    backlog_file_path: "docs/copilot_improvement_backlog.md",
    area: "Governance Tasks UI",
    risk: "low",
    backlog_status: "open",
    eligible_for_automation: true,
    automation_eligibility_reason: "Low-risk contained improvement eligible for governed automation.",
    suggested_branch: "improvement/alex-imp-001-task-filter-clarity",
    suggested_improvement: "Use larger segmented controls for task filters.",
    branch_name: "improvement/alex-imp-001-task-filter-clarity",
    commit_message: "feat: improve task filter clarity",
    implementation_summary: "Updated the filter controls and queue labels.",
    review_notes: "Verify the segmented controls on desktop and mobile.",
    review_expectation: "Human review is required before the task can be completed.",
  },
  activity: [
    { id: 10, action: "backlog_synced", details: "Created from backlog item ALEX-IMP-001.", created_at: "2026-03-15T12:00:00+00:00", actor: { name: "Automated Changes" } },
  ],
};

const assignedAutomationTaskDetail = {
  ...automationTaskDetail,
  assignee_type: "automation",
  assignee_label: "Automated Changes",
  assignee: { id: null, name: "Automated Changes", type: "automation", label: "Automated Changes" },
  workflow: { owner_type: "automation", execution_mode: "governed_automation", review_state: "queued", automation_source: "backlog" },
};

let mockSelectedTaskDetail = null;
let currentAutomationTaskDetail = automationTaskDetail;
let mockTasks = [];
let mockAutomation = null;

jest.mock("./useCompliancePageContext", () => ({
  useCompliancePageContext: () => ({
    data: {
      me: { employee: { id: 7 } },
      directory: {
        employees: [
          { id: 7, first_name: "Ada", last_name: "Lovelace", email: "ada@example.com", status: "active" },
          { id: 8, first_name: "Grace", last_name: "Hopper", email: "grace@example.com", status: "active" },
        ],
      },
      incidents: {
        incidents: [
          {
            record: { id: 21, title: "Session misuse investigation", status: "investigating" },
            incident: { id: 11, severity: "high", description: "Suspicious refresh session reuse detected." },
          },
        ],
      },
      taskSummary: {
        summary: { open: 4, overdue: 1, critical: 1, mine: 1, security: 1, testing: 1 },
      },
      tasks: {
        tasks: mockTasks,
      },
      automation: mockAutomation,
    },
    loading: false,
    selectedTaskDetail: mockSelectedTaskDetail,
    loadTaskDetail: mockLoadTaskDetail,
    updateTask: mockUpdateTask,
    createTask: mockCreateTask,
    clearTaskDetail: mockClearTaskDetail,
    syncAutomationBacklog: mockSyncAutomationBacklog,
    startNextAutomationTask: mockStartNextAutomationTask,
    assignTaskToAutomation: mockAssignTaskToAutomation,
    startAutomationTask: mockStartAutomationTask,
    blockAutomationTask: mockBlockAutomationTask,
    markAutomationTaskReadyForReview: mockMarkAutomationTaskReadyForReview,
    returnAutomationTaskToBacklog: mockReturnAutomationTaskToBacklog,
    updateAutomationTaskMetadata: mockUpdateAutomationTaskMetadata,
  }),
}));

beforeEach(() => {
  mockSelectedTaskDetail = null;
  currentAutomationTaskDetail = automationTaskDetail;
  mockTasks = [
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
      assignee_type: "employee",
      assignee_label: null,
      assignee: { id: 7, name: "Ada Lovelace" },
      updated_at: "2026-03-14T10:00:00+00:00",
      due_date: "2026-03-15T10:00:00+00:00",
      is_open: true,
    },
    {
      id: 2,
      task_key: "TASK-002",
      title: "Review vendor risk: Acme Cloud",
      status: "ready_for_review",
      priority: "high",
      source_module: "vendors",
      source_id: "4",
      source: { label: "Vendor Acme Cloud", summary: "Storage | high risk", url: "/compliance/vendors" },
      assignee_employee_id: 8,
      assignee_type: "employee",
      assignee_label: null,
      assignee: { id: 8, name: "Grace Hopper" },
      updated_at: "2026-03-14T11:00:00+00:00",
      due_date: null,
      is_open: true,
    },
    {
      id: 3,
      task_key: "TASK-003",
      title: "Close out historical follow-up",
      status: "done",
      priority: "low",
      source_module: "manual",
      source_id: null,
      source: { label: "Manual task", summary: "Previously completed follow-up.", url: "/compliance/tasks" },
      assignee_employee_id: null,
      assignee_type: null,
      assignee_label: null,
      assignee: null,
      updated_at: "2026-03-13T12:00:00+00:00",
      due_date: null,
      is_open: false,
    },
    {
      id: 4,
      task_key: "TASK-004",
      title: "Improve task filter clarity",
      status: "todo",
      priority: "high",
      source_module: "automation",
      source_id: "ALEX-IMP-001",
      source: { label: "Backlog ALEX-IMP-001", summary: "Use larger segmented controls for task filters.", url: "/compliance/tasks" },
      assignee_employee_id: null,
      assignee_type: null,
      assignee_label: null,
      assignee: null,
      updated_at: "2026-03-15T12:00:00+00:00",
      due_date: null,
      is_open: true,
    },
  ];
  mockAutomation = {
    backlog_path: "docs/copilot_improvement_backlog.md",
    summary: { backlog_items: 3, synced_tasks: 3, eligible_tasks: 1, active_tasks: 0, ready_for_review: 1, completed: 0 },
    active_task: null,
    eligible_tasks: [
      {
        id: 4,
        task_key: "TASK-004",
        title: "Improve task filter clarity",
        status: "todo",
        priority: "high",
        summary: "Use larger segmented controls for task filters.",
        metadata: { backlog_item_id: "ALEX-IMP-001", eligible_for_automation: true },
      },
    ],
    ready_for_review_tasks: [
      {
        id: 2,
        task_key: "TASK-002",
        title: "Review vendor risk: Acme Cloud",
        status: "ready_for_review",
        priority: "high",
        summary: "Confirm remediation evidence and prepare the change for review.",
        metadata: { backlog_item_id: null, eligible_for_automation: false },
      },
    ],
    completed_tasks: [],
    backlog_items: [
      {
        id: "ALEX-IMP-001",
        title: "Improve task filter clarity",
        area: "Governance Tasks UI",
        priority: "high",
        risk: "low",
        status: "open",
        description: "Improve filter clarity in the tasks workspace.",
        suggested_improvement: "Use larger segmented controls for operator filters.",
        dependencies: "None",
        suggested_branch: "improvement/alex-imp-001-task-filter-clarity",
        notes: "Safe UI work.",
        eligible_for_automation: true,
        eligibility_reason: "Low-risk contained improvement eligible for governed automation.",
        task_id: 4,
        task_key: "TASK-004",
        task_status: "todo",
      },
      {
        id: "ALEX-IMP-003",
        title: "Rework auth boundaries",
        area: "Platform Security",
        priority: "critical",
        risk: "high",
        status: "open",
        description: "Revisit workspace authorization boundaries.",
        suggested_improvement: "Requires explicit human review before planning.",
        dependencies: "Security review",
        suggested_branch: "improvement/alex-imp-003-auth-boundaries",
        notes: "Too risky for automation.",
        eligible_for_automation: false,
        eligibility_reason: "Risk is too high for automated execution without explicit approval.",
        task_id: null,
        task_key: null,
        task_status: null,
      },
    ],
  };

  mockLoadTaskDetail.mockReset();
  mockLoadTaskDetail.mockImplementation(async (taskId) => {
    if (taskId === 4) {
      mockSelectedTaskDetail = currentAutomationTaskDetail;
      return currentAutomationTaskDetail;
    }
    mockSelectedTaskDetail = taskId === 2 ? reviewTaskDetail : baseTaskDetail;
    return mockSelectedTaskDetail;
  });
  mockUpdateTask.mockReset();
  mockUpdateTask.mockResolvedValue({});
  mockCreateTask.mockReset();
  mockCreateTask.mockResolvedValue({});
  mockClearTaskDetail.mockReset();
  mockSyncAutomationBacklog.mockReset();
  mockSyncAutomationBacklog.mockResolvedValue({ payload: { automation: mockAutomation } });
  mockStartNextAutomationTask.mockReset();
  mockStartNextAutomationTask.mockResolvedValue({ payload: { task: { id: 4 } } });
  mockAssignTaskToAutomation.mockReset();
  mockAssignTaskToAutomation.mockImplementation(async () => {
    currentAutomationTaskDetail = assignedAutomationTaskDetail;
    return { payload: { task: { id: 4 } } };
  });
  mockStartAutomationTask.mockReset();
  mockStartAutomationTask.mockResolvedValue({ payload: { task: { id: 4 } } });
  mockBlockAutomationTask.mockReset();
  mockBlockAutomationTask.mockResolvedValue({ payload: { task: { id: 4 } } });
  mockMarkAutomationTaskReadyForReview.mockReset();
  mockMarkAutomationTaskReadyForReview.mockResolvedValue({ payload: { task: { id: 4 } } });
  mockReturnAutomationTaskToBacklog.mockReset();
  mockReturnAutomationTaskToBacklog.mockResolvedValue({ payload: { task: { id: 4 } } });
  mockUpdateAutomationTaskMetadata.mockReset();
  mockUpdateAutomationTaskMetadata.mockResolvedValue({ payload: { task: { id: 4 } } });
});

function renderPage() {
  return render(
    <MemoryRouter>
      <ComplianceTasksPage />
    </MemoryRouter>,
  );
}

test("renders the task list, automation queue, and filter controls", async () => {
  renderPage();

  expect(screen.getByText("Tasks")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Automated Changes" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Assigned to Me" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Open Tasks Only" })).toBeInTheDocument();
  const eligibleQueue = screen.getByRole("heading", { name: "Eligible Queue" }).closest("section");
  expect(eligibleQueue).not.toBeNull();
  expect(within(eligibleQueue).getByText("Improve task filter clarity")).toBeInTheDocument();
  expect(screen.getByText("Backlog Traceability")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Open Tasks Only" }));
  expect(screen.getByText("Close out historical follow-up")).toBeInTheDocument();
});

test("clicking a task row opens the detail drawer with ready-for-review rendering", async () => {
  const view = renderPage();

  await userEvent.type(screen.getByPlaceholderText("Search tasks, tests, incidents, vendors"), "vendor");
  await act(async () => {
    await userEvent.click(screen.getAllByText("Review vendor risk: Acme Cloud")[0]);
  });

  expect(mockClearTaskDetail).toHaveBeenCalled();
  await waitFor(() => expect(mockLoadTaskDetail).toHaveBeenCalledWith(2));

  view.rerender(
    <MemoryRouter>
      <ComplianceTasksPage />
    </MemoryRouter>,
  );

  const dialog = screen.getByRole("dialog", { name: "Review vendor risk: Acme Cloud" });
  expect(dialog).toBeInTheDocument();
  expect(within(dialog).getAllByText("Ready for review").length).toBeGreaterThan(0);
  expect(within(dialog).getByText("Source Information")).toBeInTheDocument();
});

test("automation task detail renders backlog and branch metadata", async () => {
  const view = renderPage();

  await act(async () => {
    await userEvent.click(screen.getAllByText("Improve task filter clarity")[0]);
  });
  await waitFor(() => expect(mockLoadTaskDetail).toHaveBeenCalledWith(4));

  view.rerender(
    <MemoryRouter>
      <ComplianceTasksPage />
    </MemoryRouter>,
  );

  const dialog = screen.getByRole("dialog", { name: "Improve task filter clarity" });
  expect(within(dialog).getByText("Backlog Source")).toBeInTheDocument();
  expect(within(dialog).getByText("Automation Execution")).toBeInTheDocument();
  expect(within(dialog).getByText("ALEX-IMP-001")).toBeInTheDocument();
  expect(within(dialog).getByDisplayValue("improvement/alex-imp-001-task-filter-clarity")).toBeInTheDocument();
  expect(within(dialog).getByDisplayValue("Updated the filter controls and queue labels.")).toBeInTheDocument();
});

test("automation task can be assigned to Automated Changes from the assignee control", async () => {
  const view = renderPage();

  await act(async () => {
    await userEvent.click(screen.getAllByText("Improve task filter clarity")[0]);
  });
  await waitFor(() => expect(mockLoadTaskDetail).toHaveBeenCalledWith(4));

  view.rerender(
    <MemoryRouter>
      <ComplianceTasksPage />
    </MemoryRouter>,
  );

  const dialog = screen.getByRole("dialog", { name: "Improve task filter clarity" });
  await userEvent.selectOptions(within(dialog).getByLabelText("Assignee"), "__automation__");
  await waitFor(() => expect(mockAssignTaskToAutomation).toHaveBeenCalledWith(4));
});

test("automation task can be moved to ready for review with implementation metadata", async () => {
  const view = renderPage();

  await act(async () => {
    await userEvent.click(screen.getAllByText("Improve task filter clarity")[0]);
  });
  await waitFor(() => expect(mockLoadTaskDetail).toHaveBeenCalledWith(4));

  view.rerender(
    <MemoryRouter>
      <ComplianceTasksPage />
    </MemoryRouter>,
  );

  let dialog = screen.getByRole("dialog", { name: "Improve task filter clarity" });
  await userEvent.selectOptions(within(dialog).getByLabelText("Assignee"), "__automation__");
  await waitFor(() => expect(mockAssignTaskToAutomation).toHaveBeenCalledWith(4));

  view.rerender(
    <MemoryRouter>
      <ComplianceTasksPage />
    </MemoryRouter>,
  );

  dialog = screen.getByRole("dialog", { name: "Improve task filter clarity" });
  await userEvent.click(within(dialog).getByRole("button", { name: "Mark Ready for Review" }));

  await waitFor(() => {
    expect(mockMarkAutomationTaskReadyForReview).toHaveBeenCalledWith(
      4,
      expect.objectContaining({
        branch_name: "improvement/alex-imp-001-task-filter-clarity",
        commit_message: "feat: improve task filter clarity",
      }),
    );
  });
});

test("the queue disables starting a second automation task while one is already active", () => {
  mockAutomation = {
    ...mockAutomation,
    summary: { ...mockAutomation.summary, active_tasks: 1 },
    active_task: {
      id: 99,
      task_key: "TASK-099",
      title: "Active automation task",
      status: "in_progress",
      priority: "medium",
      summary: "Existing automation work in progress.",
      metadata: { backlog_item_id: "ALEX-IMP-999", eligible_for_automation: true },
      assignee_type: "automation",
    },
  };

  renderPage();

  expect(screen.getByRole("button", { name: "Start Next Eligible" })).toBeDisabled();
});
