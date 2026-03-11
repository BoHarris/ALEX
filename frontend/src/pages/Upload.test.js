import { render, screen, waitFor } from "@testing-library/react";
import Upload from "./Upload";

jest.mock("../components/PiiSentinelUI", () => jest.fn(({ allowedTypes }) => (
  <div data-testid="pii-ui">{allowedTypes.join(",")}</div>
)));

jest.mock("../utils/fileTypes", () => ({
  FALLBACK_SUPPORTED_EXTENSIONS: [".csv", ".xls"],
  fetchSupportedFileTypes: jest.fn(),
}));

const PiiSentinelUI = require("../components/PiiSentinelUI");
const { fetchSupportedFileTypes } = require("../utils/fileTypes");

describe("Upload", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders backend-supported file types including .xls", async () => {
    fetchSupportedFileTypes.mockResolvedValue([".csv", ".xls", ".xlsx"]);

    render(<Upload />);

    await waitFor(() => {
      expect(screen.getByText(/\.csv,\.xls,\.xlsx/i)).toBeInTheDocument();
    });
    expect(PiiSentinelUI).toHaveBeenLastCalledWith(
      expect.objectContaining({ allowedTypes: [".csv", ".xls", ".xlsx"] }),
      expect.anything(),
    );
  });

  test("falls back to local contract when backend types cannot be loaded", async () => {
    fetchSupportedFileTypes.mockRejectedValue(new Error("network"));

    render(<Upload />);

    await waitFor(() => {
      expect(screen.getByText(/\.csv,\.xls/i)).toBeInTheDocument();
    });
    expect(PiiSentinelUI).toHaveBeenLastCalledWith(
      expect.objectContaining({ allowedTypes: [".csv", ".xls"] }),
      expect.anything(),
    );
  });
});
