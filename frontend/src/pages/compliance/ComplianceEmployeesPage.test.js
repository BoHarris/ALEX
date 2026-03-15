jest.mock("react-router-dom", () => require("../../test/reactRouterDomMock"), {
  virtual: true,
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ComplianceEmployeesPage from "./ComplianceEmployeesPage";

const mockCreateEmployee = jest.fn();
const mockUpdateEmployee = jest.fn();
const mockDeactivateEmployee = jest.fn();
const mockCreateTaskFromEmployee = jest.fn();

let mockContextValue;

jest.mock("./useCompliancePageContext", () => ({
  useCompliancePageContext: () => mockContextValue,
}));

function buildContext(overrides = {}) {
  return {
    data: {
      directory: {
        employees: [
          {
            id: 1,
            employee_id: "EMP-0001",
            first_name: "Ada",
            last_name: "Lovelace",
            email: "ada@example.com",
            role: "security_admin",
            department: "Security",
            job_title: "Security Admin",
            status: "active",
            last_login: "2026-03-11T10:00:00+00:00",
          },
          {
            id: 2,
            employee_id: "EMP-0002",
            first_name: "Bashir",
            last_name: "Cole",
            email: "bashir@example.com",
            role: "operations_admin",
            department: "",
            job_title: null,
            status: "inactive",
            last_login: null,
          },
          {
            id: 3,
            employee_id: "EMP-0003",
            first_name: "Mina",
            last_name: "Patel",
            email: "mina@example.com",
            role: "compliance_admin",
            department: "Compliance",
            job_title: "Analyst",
            status: "active",
            last_login: "2026-03-12T09:00:00+00:00",
          },
        ],
      },
      tasks: {
        tasks: [
          {
            id: 31,
            task_key: "TASK-031",
            source_type: "employee_followup",
            source_id: "2",
            status: "todo",
            is_open: true,
          },
          {
            id: 32,
            task_key: "TASK-032",
            source_type: "employee_followup",
            source_id: "1",
            status: "done",
            is_open: false,
          },
        ],
      },
      assignments: { assignments: [] },
      reviews: { access_reviews: [] },
      auditLog: { events: [] },
    },
    createEmployee: mockCreateEmployee,
    updateEmployee: mockUpdateEmployee,
    deactivateEmployee: mockDeactivateEmployee,
    createTaskFromEmployee: mockCreateTaskFromEmployee,
    ...overrides,
  };
}

beforeEach(() => {
  mockCreateEmployee.mockClear();
  mockUpdateEmployee.mockClear();
  mockDeactivateEmployee.mockClear();
  mockCreateTaskFromEmployee.mockClear();
  mockCreateEmployee.mockResolvedValue({});
  mockUpdateEmployee.mockResolvedValue({});
  mockDeactivateEmployee.mockResolvedValue({});
  mockCreateTaskFromEmployee.mockResolvedValue({});
  mockContextValue = buildContext();
});

function renderPage() {
  return render(
    <MemoryRouter>
      <ComplianceEmployeesPage />
    </MemoryRouter>,
  );
}

test("renders employee summary metrics and filters the directory by status", async () => {
  renderPage();

  expect(screen.getByText("Directory")).toBeInTheDocument();
  expect(screen.getByText("Incomplete Profiles")).toBeInTheDocument();
  expect(screen.getByText("Open Follow-ups")).toBeInTheDocument();
  expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
  expect(screen.getByText("Bashir Cole")).toBeInTheDocument();

  await userEvent.selectOptions(
    screen.getByLabelText("Filter by status"),
    "inactive",
  );

  expect(screen.queryByText("Ada Lovelace")).not.toBeInTheDocument();
  expect(screen.getByText("Bashir Cole")).toBeInTheDocument();
  expect(screen.getByText("Clear Filters")).toBeInTheDocument();

  await userEvent.click(screen.getByText("Clear Filters"));

  expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
  expect(screen.getByText("Mina Patel")).toBeInTheDocument();
});

test("submits a trimmed employee payload from the create drawer", async () => {
  renderPage();

  await userEvent.click(screen.getByText("Add Employee"));
  await userEvent.type(screen.getByLabelText("First Name"), "  Nia  ");
  await userEvent.type(screen.getByLabelText("Last Name"), "  Stone ");
  await userEvent.type(screen.getByLabelText("Email"), "  NIA.STONE@EXAMPLE.COM ");
  await userEvent.clear(screen.getByLabelText("Role"));
  await userEvent.type(screen.getByLabelText("Role"), " compliance_admin ");
  await userEvent.type(screen.getByLabelText("Department"), "  Legal ");
  await userEvent.type(screen.getByLabelText("Job Title"), "  Counsel  ");
  await userEvent.selectOptions(screen.getByLabelText("Status"), "inactive");
  await userEvent.click(screen.getByRole("button", { name: "Create employee" }));

  await waitFor(() => {
    expect(mockCreateEmployee).toHaveBeenCalledWith({
      first_name: "Nia",
      last_name: "Stone",
      email: "nia.stone@example.com",
      role: "compliance_admin",
      department: "Legal",
      job_title: "Counsel",
      status: "inactive",
    });
  });
});

test("shows profile attention details for incomplete employee records", async () => {
  renderPage();

  await userEvent.click(screen.getByText("Bashir Cole"));

  expect(
    screen.getByRole("dialog", { name: "Bashir Cole" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Profile Attention")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Employee inactive" }),
  ).toBeDisabled();
});
