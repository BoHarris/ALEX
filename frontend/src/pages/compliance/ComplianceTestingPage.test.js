import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ComplianceTestingPage from "./ComplianceTestingPage";

const mockLoadTestCategory = jest.fn();
const mockLoadTestCase = jest.fn();

jest.mock("./useCompliancePageContext", () => ({
  useCompliancePageContext: () => ({
    testDashboard: {
      summary: {
        total_tests: 12,
        passing_tests: 9,
        failing_tests: 2,
        flaky_tests: 1,
        not_run_tests: 1,
        average_pass_rate: 87,
        total_executions_last_7_days: 34,
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
          run_id: 2,
          result_id: 22,
          suite_name: "PII validation suite",
          status: "failed",
          duration_ms: 8,
          last_run_timestamp: "2026-03-11T12:00:00+00:00",
          environment: "synthetic_history",
          file_path: "tests/privacy_tests.py",
          error_message: "Detector missed expected email classification.",
          confidence_score: 0.19,
        },
      ],
    },
    loadTestCategory: mockLoadTestCategory,
    loadTestCase: mockLoadTestCase,
    createOrAssignTestTask: jest.fn(),
    updateTestTask: jest.fn(),
    data: {
      directory: {
        employees: [
          { id: 1, first_name: "Bo", last_name: "Harris", status: "active" },
        ],
      },
    },
  }),
}));

beforeEach(() => {
  mockLoadTestCategory.mockClear();
  mockLoadTestCase.mockClear();
});

test("renders individual tests from the same file separately and shows node metadata", async () => {
  render(<ComplianceTestingPage />);

  expect(screen.getByText("test_detect_email")).toBeInTheDocument();
  expect(screen.getByText("test_detect_phone")).toBeInTheDocument();
  expect(screen.getByText("test_detect_ssn")).toBeInTheDocument();
  expect(screen.getAllByText("tests/privacy_tests.py").length).toBeGreaterThan(0);
  expect(screen.getByText("Pytest Node ID")).toBeInTheDocument();
  expect(screen.getByText("tests/privacy_tests.py::test_detect_email")).toBeInTheDocument();
  expect(screen.getAllByText(/Regressed/i).length).toBeGreaterThan(0);

  await waitFor(() => {
    expect(mockLoadTestCategory).toHaveBeenCalled();
  });
});

test("supports selecting a single test case and filtering by search and file path", async () => {
  const user = userEvent.setup();
  render(<ComplianceTestingPage />);

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
