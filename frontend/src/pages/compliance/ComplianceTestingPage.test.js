jest.mock("react-router-dom", () => require("../../test/reactRouterDomMock"), { virtual: true });

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ComplianceTestingPage from "./ComplianceTestingPage";

const mockLoadTestCategory = jest.fn();
const mockLoadTestCase = jest.fn();
const mockLoadTestRunDetail = jest.fn();
const mockRunFullTestSuite = jest.fn();
const mockRunTestCase = jest.fn();
const mockRunTestCategory = jest.fn();
const mockRefreshTestingWorkspace = jest.fn();
const mockClearTestRunDetail = jest.fn();
const mockLoadTaskDetail = jest.fn();
const mockCreateOrAssignTestTask = jest.fn();
const mockUpdateTestTask = jest.fn();

let mockContextValue;

jest.mock("./useCompliancePageContext", () => ({
  useCompliancePageContext: () => mockContextValue,
}));

function buildContext(overrides = {}) {
  return {
    testDashboard: {
      summary: {
        total_tests: 12,
        passing_tests: 9,
        failing_tests: 2,
        flaky_tests: 1,
        not_run_tests: 1,
        average_pass_rate: 87,
        total_executions_last_7_days: 34,
        running_runs: 1,
        open_failure_tasks: 2,
        last_full_suite_run: {
          id: 41,
          status: "failed",
          completed_at: "2026-03-11T12:10:00+00:00",
          run_at: "2026-03-11T12:00:00+00:00",
        },
      },
      categories: [
        {
          category: "privacy tests",
          description: "PII detection and redaction validation.",
          total_tests: 4,
          passing: 2,
          failing: 1,
          skipped: 0,
          not_run: 0,
          flaky: 1,
          average_pass_rate: 76,
          status: "failed",
          last_run_timestamp: "2026-03-11T12:00:00+00:00",
        },
      ],
    },
    testCategoryDetail: {
      category: "privacy tests",
      summary: {
        total_tests: 3,
        passing: 1,
        failing: 1,
        skipped: 0,
        not_run: 1,
        flaky: 1,
        average_pass_rate: 50,
        last_run_timestamp: "2026-03-11T12:00:00+00:00",
      },
      tests: [
        {
          test_id: "tests%2Fprivacy_tests.py%3A%3Atest_detect_email",
          test_node_id: "tests/privacy_tests.py::test_detect_email",
          test_name: "test_detect_email",
          category: "privacy tests",
          suite_name: "PII validation suite",
          status: "failed",
          quality_label: "Regressed",
          pass_rate: 50,
          total_runs: 2,
          failed_runs: 1,
          flake_rate: 1,
          flaky: true,
          file_path: "tests/privacy_tests.py",
          last_duration_ms: 8,
          last_run_timestamp: "2026-03-11T12:00:00+00:00",
          latest_run_id: 41,
          execution_supported: true,
          execution_engine: "pytest",
        },
        {
          test_id: "tests%2Fprivacy_tests.py%3A%3Atest_detect_phone",
          test_node_id: "tests/privacy_tests.py::test_detect_phone",
          test_name: "test_detect_phone",
          category: "privacy tests",
          suite_name: "PII validation suite",
          status: "passed",
          quality_label: "Stable",
          pass_rate: 100,
          total_runs: 2,
          failed_runs: 0,
          flake_rate: 0,
          flaky: false,
          file_path: "tests/privacy_tests.py",
          last_duration_ms: 7,
          last_run_timestamp: "2026-03-11T11:00:00+00:00",
          latest_run_id: 40,
          execution_supported: true,
          execution_engine: "pytest",
        },
        {
          test_id: "tests%2Fprivacy_tests.py%3A%3Atest_detect_ssn",
          test_node_id: "tests/privacy_tests.py::test_detect_ssn",
          test_name: "test_detect_ssn",
          category: "privacy tests",
          suite_name: "PII validation suite",
          status: "not_run",
          quality_label: "Not Run",
          pass_rate: 0,
          total_runs: 0,
          failed_runs: 0,
          flake_rate: 0,
          flaky: false,
          file_path: "tests/privacy_tests.py",
          last_duration_ms: null,
          last_run_timestamp: null,
          latest_run_id: null,
          execution_supported: true,
          execution_engine: "pytest",
        },
      ],
    },
    selectedTestCase: {
      test_id: "tests%2Fprivacy_tests.py%3A%3Atest_detect_email",
      test_node_id: "tests/privacy_tests.py::test_detect_email",
      test_name: "test_detect_email",
      file_path: "tests/privacy_tests.py",
      category: "privacy tests",
      suite_name: "PII validation suite",
      status: "failed",
      quality_label: "Regressed",
      pass_rate: 50,
      flake_rate: 1,
      latest_environment: "synthetic_history",
      current_pass_streak: 0,
      current_fail_streak: 1,
      last_successful_run: "2026-03-10T12:00:00+00:00",
      last_failed_run: "2026-03-11T12:00:00+00:00",
      average_duration_ms: 9,
      trend: "unstable",
      expected_result: "PII_EMAIL",
      description: "Email detection should classify as PII_EMAIL.",
      execution_supported: true,
      latest_run_id: 41,
      latest_execution: {
        output: "classification mismatch",
        error_message: "Detector missed expected email classification.",
      },
      task: {
        id: 17,
        status: "open",
        priority: "medium",
        assignee_employee_id: null,
        assignee: null,
        title: "Investigate failing test: test_detect_email",
        created_at: "2026-03-11T12:05:00+00:00",
        updated_at: "2026-03-11T12:05:00+00:00",
      },
      history: [
        {
          run_id: 41,
          result_id: 22,
          suite_name: "PII validation suite",
          status: "failed",
          duration_ms: 8,
          last_run_timestamp: "2026-03-11T12:00:00+00:00",
          environment: "synthetic_history",
          file_path: "tests/privacy_tests.py",
          error_message: "Detector missed expected email classification.",
          confidence_score: 0.19,
          output: "classification mismatch",
        },
      ],
      linked_tasks: [
        {
          id: 90,
          task_key: "TASK-090",
          status: "in_progress",
        },
      ],
    },
    selectedTestRun: null,
    loadTestCategory: mockLoadTestCategory,
    loadTestCase: mockLoadTestCase,
    loadTestRunDetail: mockLoadTestRunDetail,
    createOrAssignTestTask: mockCreateOrAssignTestTask,
    updateTestTask: mockUpdateTestTask,
    runFullTestSuite: mockRunFullTestSuite,
    runTestCase: mockRunTestCase,
    runTestCategory: mockRunTestCategory,
    refreshTestingWorkspace: mockRefreshTestingWorkspace,
    clearTestRunDetail: mockClearTestRunDetail,
    loadTaskDetail: mockLoadTaskDetail,
    data: {
      directory: {
        employees: [
          { id: 1, first_name: "Bo", last_name: "Harris", status: "active" },
        ],
      },
      testRuns: {
        runs: [
          {
            id: 41,
            suite_name: "Backend pytest suite",
            category: "backend tests",
            run_type: "full_suite",
            status: "failed",
            started_at: "2026-03-11T12:00:00+00:00",
            completed_at: "2026-03-11T12:10:00+00:00",
            failure_summary: "test_detect_email: Detector missed expected email classification.",
          },
          {
            id: 42,
            suite_name: "PII validation suite",
            category: "privacy tests",
            run_type: "single_test",
            status: "running",
            pytest_node_id: "tests/privacy_tests.py::test_detect_email",
            started_at: "2026-03-11T12:11:00+00:00",
            completed_at: null,
          },
        ],
      },
    },
    ...overrides,
  };
}

beforeEach(() => {
  mockLoadTestCategory.mockClear();
  mockLoadTestCase.mockClear();
  mockLoadTestRunDetail.mockClear();
  mockRunFullTestSuite.mockClear();
  mockRunTestCase.mockClear();
  mockRunTestCategory.mockClear();
  mockRefreshTestingWorkspace.mockClear();
  mockClearTestRunDetail.mockClear();
  mockLoadTaskDetail.mockClear();
  mockCreateOrAssignTestTask.mockClear();
  mockUpdateTestTask.mockClear();
  mockRunFullTestSuite.mockResolvedValue(undefined);
  mockRunTestCase.mockResolvedValue(undefined);
  mockRunTestCategory.mockResolvedValue(undefined);
  mockLoadTestRunDetail.mockResolvedValue(undefined);
  mockContextValue = buildContext();
});

function renderPage() {
  return render(
    <MemoryRouter>
      <ComplianceTestingPage />
    </MemoryRouter>,
  );
}

test("renders individual tests from the same file separately and shows node metadata", async () => {
  renderPage();

  expect(screen.getByText("test_detect_email")).toBeInTheDocument();
  expect(screen.getByText("test_detect_phone")).toBeInTheDocument();
  expect(screen.getByText("test_detect_ssn")).toBeInTheDocument();
  expect(screen.getAllByText("tests/privacy_tests.py").length).toBeGreaterThan(0);
  expect(screen.queryByText("Pytest Node ID")).not.toBeInTheDocument();

  await waitFor(() => {
    expect(mockLoadTestCategory).toHaveBeenCalled();
  });
});

test("supports selecting a single test case and filtering by search and file path", async () => {
  const user = userEvent;
  renderPage();

  await user.click(screen.getByText("test_detect_phone"));
  expect(mockLoadTestCase).toHaveBeenCalledWith("tests%2Fprivacy_tests.py%3A%3Atest_detect_phone");

  await user.type(screen.getByPlaceholderText("Search by name, description, or file"), "email");
  await user.type(screen.getByPlaceholderText("Filter by tests/path.py"), "privacy_tests.py");

  await waitFor(() => {
    expect(mockLoadTestCategory).toHaveBeenLastCalledWith(
      "privacy tests",
      expect.objectContaining({
        search: "email",
        file_path: "privacy_tests.py",
        sort: "last_run",
      }),
    );
  });
});

test("opens a run history drawer for the selected test and supports closing it", async () => {
  const user = userEvent;
  renderPage();

  await user.click(screen.getByText("test_detect_email"));

  expect(screen.getByRole("dialog", { name: "test_detect_email" })).toBeInTheDocument();
  expect(screen.getByText("Run History Inspector")).toBeInTheDocument();
  expect(screen.getByText("Pytest Node ID")).toBeInTheDocument();
  expect(screen.getAllByText("tests/privacy_tests.py::test_detect_email").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Detector missed expected email classification.").length).toBeGreaterThan(0);

  await user.click(screen.getByRole("button", { name: "Close" }));

  await waitFor(() => {
    expect(screen.queryByRole("dialog", { name: "test_detect_email" })).not.toBeInTheDocument();
  });
  expect(screen.queryByText("Selected Test")).not.toBeInTheDocument();
});

test("triggers full-suite and category execution controls from the testing console", async () => {
  const user = userEvent;
  renderPage();

  await user.click(screen.getByRole("button", { name: "Run Full Test Suite" }));
  await waitFor(() => {
    expect(mockRunFullTestSuite).toHaveBeenCalledTimes(1);
  });

  await user.click(screen.getByRole("button", { name: "Run privacy tests" }));
  await waitFor(() => {
    expect(mockRunTestCategory).toHaveBeenCalledWith("privacy tests");
  });
});

test("triggers a single test run from the inspector and opens run detail from recent history", async () => {
  const user = userEvent;
  mockContextValue = buildContext({
    data: {
      directory: {
        employees: [{ id: 1, first_name: "Bo", last_name: "Harris", status: "active" }],
      },
      testRuns: {
        runs: [
          {
            id: 41,
            suite_name: "Backend pytest suite",
            category: "backend tests",
            run_type: "full_suite",
            status: "failed",
            started_at: "2026-03-11T12:00:00+00:00",
            completed_at: "2026-03-11T12:10:00+00:00",
            failure_summary: "test_detect_email: Detector missed expected email classification.",
          },
        ],
      },
    },
  });
  renderPage();

  await user.click(screen.getByText("test_detect_email"));
  await user.click(screen.getByRole("button", { name: "Run Test" }));
  await waitFor(() => {
    expect(mockRunTestCase).toHaveBeenCalledWith("tests%2Fprivacy_tests.py%3A%3Atest_detect_email");
  });

  await user.click(screen.getByRole("button", { name: /Backend pytest suite/i }));
  await waitFor(() => {
    expect(mockLoadTestRunDetail).toHaveBeenCalledWith(41);
  });
});

test("renders run detail with linked remediation tasks when a run is selected", async () => {
  mockContextValue = buildContext({
    selectedTestRun: {
      run: {
        id: 41,
        suite_name: "Backend pytest suite",
        category: "backend tests",
        run_type: "full_suite",
        status: "failed",
        started_at: "2026-03-11T12:00:00+00:00",
        completed_at: "2026-03-11T12:10:00+00:00",
        return_code: 1,
        passed_tests: 1,
        total_tests: 2,
        failure_summary: "test_detect_email: Detector missed expected email classification.",
        stdout: "collected 2 items",
        stderr: "1 failed, 1 passed",
      },
      results: [
        {
          id: 22,
          test_name: "test_detect_email",
          test_node_id: "tests/privacy_tests.py::test_detect_email",
          status: "failed",
          duration_ms: 8,
          last_run_timestamp: "2026-03-11T12:00:00+00:00",
          error_details: "Detector missed expected email classification.",
          linked_tasks: [{ id: 90, task_key: "TASK-090", status: "in_progress" }],
        },
      ],
      linked_tasks: [{ id: 90, task_key: "TASK-090", status: "in_progress" }],
    },
  });

  renderPage();

  expect(screen.getByRole("dialog", { name: "Backend pytest suite" })).toBeInTheDocument();
  expect(screen.getByText("Recorded Results")).toBeInTheDocument();
  expect(screen.getAllByText(/TASK-090/i).length).toBeGreaterThan(0);
});
