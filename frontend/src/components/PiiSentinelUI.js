import React, { useState } from "react";
import { Card, CardContent } from "../components/card";
import { Button } from "../components/button";
import { Input } from "../components/input";
import { SUPPORTED_EXTENSIONS } from "../utils/constants";
import { authFetch } from "../utils/authFetch";

async function downloadAsset(path, fallbackName, expectedType = null) {
  const response = await authFetch(path);

  if (!response.ok) {
    throw new Error(`Server error: ${response.statusText}`);
  }

  const contentType = (response.headers.get("Content-Type") || "").toLowerCase();
  if (expectedType === "pdf" && !contentType.includes("application/pdf")) {
    throw new Error("Audit report PDF is unavailable.");
  }

  const blob = await response.blob();
  const href = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = fallbackName || "redacted-file";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(href);
}

export default function PiiSentinelUI() {
  const [file, setFile] = useState(null);
  const [piiColumns, setPiiColumns] = useState([]);
  const [riskScore, setRiskScore] = useState(null);
  const [redactedFile, setRedactedFile] = useState(null);
  const [scanId, setScanId] = useState(null);
  const [scannedFilename, setScannedFilename] = useState(null);
  const [totalValues, setTotalValues] = useState(null);
  const [redactedCount, setRedactedCount] = useState(null);
  const [redactionSummary, setRedactionSummary] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [hasScanned, setHasScanned] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setPiiColumns([]);
    setRiskScore(null);
    setRedactedFile(null);
    setScanId(null);
    setScannedFilename(null);
    setTotalValues(null);
    setRedactedCount(null);
    setRedactionSummary(null);
    setError(null);
    setHasScanned(false);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await authFetch("/predict/", {
        method: "POST",
        body: formData,
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Server error: ${res.statusText}`);
      }

      setPiiColumns(data.pii_columns || []);
      setRiskScore(data.risk_score ?? null);
      setRedactedFile(data.redacted_file || null);
      setScanId(data.scan_id || null);
      setScannedFilename(data.filename || file.name || null);
      setTotalValues(data.total_values ?? null);
      setRedactedCount(data.redacted_count ?? null);
      setRedactionSummary(data.redaction_summary || null);
      setHasScanned(true);
    } catch (uploadError) {
      setError(
        uploadError.message.includes("Network")
          ? "Network error. Please check your connection."
          : uploadError.message || "Failed to scan file. Please try again.",
      );
    } finally {
      setUploading(false);
    }
  };

  const riskPercent =
    riskScore == null ? null : Math.round(Math.max(0, Math.min(1, riskScore)) * 100);

  const riskLevel =
    riskPercent == null ? "Not available" : riskPercent >= 70 ? "High" : riskPercent >= 40 ? "Moderate" : "Low";

  const recommendation =
    riskLevel === "Low"
      ? "Minimal sensitive information detected. File may be suitable for internal use with standard review."
      : riskLevel === "Moderate"
        ? "Sensitive information was detected and redacted. Review the redacted output before distribution."
        : riskLevel === "High"
          ? "Significant sensitive information was detected. Additional review is recommended before sharing."
          : "Risk guidance is not available for this scan.";

  const detectedTypes =
    piiColumns.length > 0 ? piiColumns.join(", ") : "Not available";

  const displayFileName = scannedFilename || file?.name || "Not available";
  const fileType = displayFileName.includes(".")
    ? displayFileName.split(".").pop().toUpperCase()
    : "Not available";

  const typedRedactionRows =
    redactionSummary && typeof redactionSummary === "object"
      ? Object.entries(redactionSummary)
      : [];

  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center space-y-8 px-4 py-12">
      <h1 className="text-3xl font-bold text-white">ALEX Privacy Scan Dashboard</h1>

      <Card className="w-full border border-white/10 bg-slate-900/70 text-white shadow-md">
        <CardContent className="space-y-5 p-6">
          <div className="space-y-3">
            <label
              htmlFor="file-upload"
              className="block font-semibold text-slate-100"
            >
              Upload a File
            </label>
            <Input
              id="file-upload"
              type="file"
              accept={SUPPORTED_EXTENSIONS.join(",")}
              required
              onChange={handleFileChange}
            />
            {file && (
              <p className="mt-2 text-sm text-slate-300">
                Selected file: {file.name}
              </p>
            )}

            <Button onClick={handleUpload} disabled={!file || uploading}>
              {uploading ? "Scanning..." : "Scan File for PII"}
            </Button>

            {uploading && (
              <p className="text-sm italic text-slate-300">
                Uploading and analyzing file...
              </p>
            )}

            {error && !uploading && (
              <p className="text-sm font-medium text-red-600">{error}</p>
            )}

            {hasScanned && piiColumns.length === 0 && !uploading && !error && (
              <p className="text-sm font-medium text-emerald-300">
                Scan complete. No sensitive field types were detected.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {hasScanned && !uploading && !error && (
        <Card className="w-full border border-cyan-300/20 bg-slate-900/80 text-white shadow-md">
          <CardContent className="space-y-6 p-6">
            <div>
              <h2 className="text-2xl font-bold text-white">Scan Summary</h2>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <p>
                  <span className="font-semibold text-slate-300">File Name:</span>{" "}
                  {displayFileName}
                </p>
                <p>
                  <span className="font-semibold text-slate-300">File Type:</span>{" "}
                  {fileType}
                </p>
                <p>
                  <span className="font-semibold text-slate-300">Scan Status:</span>{" "}
                  Complete
                </p>
                <p>
                  <span className="font-semibold text-slate-300">Risk Score:</span>{" "}
                  {riskPercent == null ? "Not available" : `${riskPercent}%`}
                </p>
                <p>
                  <span className="font-semibold text-slate-300">Risk Level:</span>{" "}
                  {riskLevel}
                </p>
                <p>
                  <span className="font-semibold text-slate-300">Total Values Redacted:</span>{" "}
                  {redactedCount ?? "Not available"}
                </p>
                <p className="sm:col-span-2">
                  <span className="font-semibold text-slate-300">Sensitive Field Types Detected:</span>{" "}
                  {detectedTypes}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-100">
                Redaction Summary
              </h3>
              <div className="mt-3 space-y-2 text-sm text-slate-200">
                {typedRedactionRows.length > 0 ? (
                  typedRedactionRows.map(([type, count]) => (
                    <p key={type}>
                      {type} redacted: <span className="font-semibold">{count}</span>
                    </p>
                  ))
                ) : (
                  <>
                    <p>
                      Total values redacted:{" "}
                      <span className="font-semibold">{redactedCount ?? "Not available"}</span>
                    </p>
                    <p>
                      Total values analyzed:{" "}
                      <span className="font-semibold">{totalValues ?? "Not available"}</span>
                    </p>
                  </>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4">
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-100">
                Recommended Action
              </h3>
              <p className="mt-3 text-sm text-amber-50">{recommendation}</p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-200">
                Available Outputs
              </h3>
              <div className="mt-3 flex flex-wrap gap-3">
                {redactedFile && scanId ? (
                  <button
                    onClick={() =>
                      downloadAsset(`/scans/${scanId}/download`, displayFileName).catch(() => {
                        setError("Failed to download redacted file.");
                      })
                    }
                    className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
                  >
                    Download Redacted File
                  </button>
                ) : (
                  <span className="text-sm text-slate-400">Redacted file not available.</span>
                )}

                {scanId ? (
                  <button
                    onClick={async () => {
                      const stem = displayFileName.replace(/\.[^.]+$/, "");
                      try {
                        await downloadAsset(
                          `/scans/${scanId}/report/pdf`,
                          `${stem}-audit-report.pdf`,
                          "pdf",
                        );
                      } catch {
                        try {
                          await downloadAsset(
                            `/scans/${scanId}/report/html`,
                            `${stem}-audit-report.html`,
                          );
                          setError("PDF unavailable. Downloaded HTML audit report instead.");
                        } catch {
                          setError("Failed to download audit report.");
                        }
                      }
                    }}
                    className="rounded-full border border-white/20 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
                  >
                    Download Audit Report
                  </button>
                ) : (
                  <span className="text-sm text-slate-400">Audit report not available.</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
