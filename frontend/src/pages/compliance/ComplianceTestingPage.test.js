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
          flaky: 1,
          average_pass_rate: 76,
          status: "failed",
          last_run_timestamp: "2026-03-11T12:00:00+00:00",
        },
        {
          category: "security tests",
          description: "Authentication and hardening coverage.",
          total_tests: 3,
          passing: 3,
          failing: 0,
          skipped: 0,
          flaky: 0,
          average_pass_rate: 100,
          status: "passed",
          last_run_timestamp: "2026-03-10T12:00:00+00:00",
        },
      ],
    },
    testCategoryDetail: {
      category: "privacy tests",
      summary: {
        total_tests: 2,
        passing: 1,
        failing: 1,
        skipped: 0,
        flaky: 1,
        average_pass_rate: 50,
        last_run_timestamp: "2026-03-11T12:00:00+00:00",
      },
      tests: [
        {
          test_id: "privacy%20tests%3A%3Adetect_email",
          test_name: "detect_email",
          category: "privacy tests",
          suite_name: "PII validation suite",
          status: "failed",
          pass_rate: 50,
          total_runs: 2,
          failed_runs: 1,
          flake_rate: 1,
          flaky: true,
          file_name: "tests/test_pii_validation.py",
          last_duration_ms: 8,
          last_run_timestamp: "2026-03-11T12:00:00+00:00",
        },
        {
          test_id: "privacy%20tests%3A%3Adetect_phone",
          test_name: "detect_phone",
          category: "privacy tests",
          suite_name: "PII validation suite",
          status: "passed",
          pass_rate: 100,
          total_runs: 2,
          failed_runs: 0,
          flake_rate: 0,
          flaky: false,
          file_name: "tests/test_pii_validation.py",
          last_duration_ms: 7,
          last_run_timestamp: "2026-03-11T11:00:00+00:00",
        },
      ],
    },
    selectedTestCase: {
      test_id: "privacy%20tests%3A%3Adetect_email",
      test_name: "detect_email",
      category: "privacy tests",
      suite_name: "PII validation suite",
      status: "failed",
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
      history: [
        {
          run_id: 2,
          result_id: 22,
          suite_name: "PII validation suite",
          status: "failed",
          duration_ms: 8,
          last_run_timestamp: "2026-03-11T12:00:00+00:00",
          environment: "synthetic_history",
          error_message: "Detector missed expected email classification.",
          confidence_score: 0.19,
        },
        {
          run_id: 1,
          result_id: 21,
          suite_name: "PII validation suite",
          status: "passed",
          duration_ms: 10,
          last_run_timestamp: "2026-03-10T12:00:00+00:00",
          environment: "synthetic_history",
          error_message: null,
          confidence_score: 0.88,
        },
      ],
    },
    loadTestCategory: mockLoadTestCategory,
    loadTestCase: mockLoadTestCase,
  }),
}));

beforeEach(() => {
  mockLoadTestCategory.mockClear();
  mockLoadTestCase.mockClear();
});

test("renders category rail, summary metrics, and selected test history", async () => {
  render(<ComplianceTestingPage />);

  expect(screen.getByText("Test Suites")).toBeInTheDocument();
  expect(screen.getByText("Total Tests")).toBeInTheDocument();
  expect(screen.getByText("12")).toBeInTheDocument();
  expect(screen.getByText("privacy tests")).toBeInTheDocument();
  expect(screen.getByText("detect_email")).toBeInTheDocument();
  expect(screen.getByText("Execution History")).toBeInTheDocument();
  expect(screen.getByText("Detector missed expected email classification.")).toBeInTheDocument();

  await waitFor(() => {
    expect(mockLoadTestCategory).toHaveBeenCalled();
  });
});

test("supports selecting a test and changing filters", async () => {
  const user = userEvent.setup();
  render(<ComplianceTestingPage />);

  await user.click(screen.getByText("detect_phone"));
  expect(mockLoadTestCase).toHaveBeenCalledWith("privacy%20tests%3A%3Adetect_phone");

  await user.type(screen.getByPlaceholderText("Search by name, description, or file"), "email");
  await waitFor(() => {
    expect(mockLoadTestCategory).toHaveBeenLastCalledWith(
      "privacy tests",
      expect.objectContaining({
        search: "email",
        sort: "last_run",
      }),
    );
  });
});
