import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DashboardFilesPanel from "./DashboardFilesPanel";

jest.mock("../utils/downloads", () => ({
  downloadProtectedAsset: jest.fn().mockResolvedValue(undefined),
}));

const BASE_SCAN = {
  scan_id: 101,
  filename: "customer_export.csv",
  file_type: "csv",
  risk_score: 52,
  total_pii_found: 3,
  redacted_count: 3,
  redacted_type_counts: { EMAIL: 2, PHONE: 1 },
  pii_types_found: ["EMAIL", "PHONE"],
  status: "ready",
  scanned_at: "2026-03-10T10:00:00Z",
};

describe("DashboardFilesPanel", () => {
  test("renders scan card with grouped actions and readable badges", () => {
    render(
      <DashboardFilesPanel
        files={[BASE_SCAN]}
        loading={false}
        error={null}
        onRetry={jest.fn()}
      />,
    );

    expect(screen.getByText("customer_export.csv")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Redacted Successfully")).toBeInTheDocument();
    expect(screen.getByText("Report Ready")).toBeInTheDocument();
    expect(screen.getByLabelText(/scan actions/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "HTML Report" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "PDF Report" })).toBeInTheDocument();
  });

  test("opens action menu and archives a scan", async () => {
    const user = userEvent.setup();
    const onArchiveScan = jest.fn().mockResolvedValue(undefined);

    render(
      <DashboardFilesPanel
        files={[BASE_SCAN]}
        loading={false}
        error={null}
        onRetry={jest.fn()}
        onArchiveScan={onArchiveScan}
      />,
    );

    await user.click(screen.getByRole("button", { name: /open actions menu/i }));
    await user.click(screen.getByRole("menuitem", { name: "Archive Scan" }));

    expect(onArchiveScan).toHaveBeenCalledWith(101);
  });

  test("shows restore action for archived scans", async () => {
    const user = userEvent.setup();
    const onRestoreScan = jest.fn().mockResolvedValue(undefined);

    render(
      <DashboardFilesPanel
        files={[BASE_SCAN]}
        loading={false}
        error={null}
        onRetry={jest.fn()}
        onRestoreScan={onRestoreScan}
        archived
      />,
    );

    expect(screen.getByText("Archived")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /open actions menu/i }));
    await user.click(screen.getByRole("menuitem", { name: "Restore Scan" }));

    expect(onRestoreScan).toHaveBeenCalledWith(101);
  });
});

