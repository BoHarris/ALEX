import React, { useEffect, useState } from "react";
import { Card, CardContent } from "../components/card";
import { Button } from "../components/button";
import { Input } from "../components/input";
import { FALLBACK_SUPPORTED_EXTENSIONS } from "../utils/fileTypes";
import { authFetch } from "../utils/authFetch";
import { getResponseMessage, readResponseData } from "../utils/http";
import { downloadProtectedAsset, getDownloadErrorMessage } from "../utils/downloads";

export default function PiiSentinelUI({ allowedTypes = FALLBACK_SUPPORTED_EXTENSIONS }) {
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
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [onboarding, setOnboarding] = useState({ has_completed_onboarding: true, steps: {} });

  useEffect(() => {
    let cancelled = false;
    authFetch("/onboarding/status")
      .then(readResponseData)
      .then(({ data }) => {
        if (!cancelled && data) {
          setOnboarding(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setOnboarding({ has_completed_onboarding: true, steps: {} });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!jobId || !jobStatus || jobStatus === "COMPLETED" || jobStatus === "FAILED") {
      return undefined;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const res = await authFetch(`/scan-jobs/${jobId}`);
        const { data, text } = await readResponseData(res);
        if (!res.ok) {
          throw new Error(getResponseMessage(data, `Server error: ${res.statusText}`, text));
        }
        if (cancelled || !data) {
          return;
        }
        setJobStatus(data.status || null);
        if (data.status === "COMPLETED" && data.result) {
          setPiiColumns(data.result.pii_columns || []);
          setRiskScore(data.result.risk_score ?? null);
          setRedactedFile(data.result.redacted_file || null);
          setScanId(data.result.scan_id || null);
          setScannedFilename(data.result.filename || scannedFilename || file?.name || null);
          setTotalValues(data.result.total_values ?? null);
          setRedactedCount(data.result.redacted_count ?? null);
          setRedactionSummary(data.result.redaction_summary || null);
          setHasScanned(true);
          setUploading(false);
        }
        if (data.status === "FAILED") {
          setError(data.error_message || "Scan failed. Please try again.");
          setUploading(false);
        }
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError.message || "Unable to refresh scan status.");
          setUploading(false);
        }
      }
    }, 1000);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [file, jobId, jobStatus, scannedFilename]);

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
    setJobId(null);
    setJobStatus(null);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await authFetch("/scans", {
        method: "POST",
        body: formData,
      });

      const { data, text } = await readResponseData(res);
      if (!res.ok) {
        throw new Error(getResponseMessage(data, `Server error: ${res.statusText}`, text));
      }
      if (!data) {
        throw new Error("Unexpected response from server");
      }

      if (data.job_id && !data.scan_id) {
        setJobId(data.job_id);
        setJobStatus(data.job_status || "QUEUED");
        setScannedFilename(data.filename || file.name || null);
        return;
      }

      setJobId(data.job_id || null);
      setJobStatus(data.job_status || "COMPLETED");
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

  const normalizedRiskScore = Number(riskScore);
  const riskPercent =
    riskScore == null || Number.isNaN(normalizedRiskScore)
      ? null
      : Math.max(0, Math.min(100, normalizedRiskScore));

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

  const onboardingSteps = onboarding?.steps || {};
  const uploadStepDone = Boolean(file) || Boolean(onboardingSteps.upload_first_file);
  const runStepDone = hasScanned || Boolean(onboardingSteps.run_scan);
  const reportStepDone = Boolean(onboarding?.has_completed_onboarding);

  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center space-y-8 px-4 py-12">
      <h1 className="text-3xl font-bold text-app">ALEX Privacy Scan Dashboard</h1>

      {!onboarding?.has_completed_onboarding && (
        <Card className="w-full border border-sky-300/30 bg-sky-300/10 shadow-md">
          <CardContent className="space-y-3 p-6">
            <h2 className="text-xl font-bold text-app">Getting Started</h2>
            <p className="text-sm text-app-secondary">Complete your first scan workflow to finish onboarding.</p>
            <p className="text-sm text-app">{uploadStepDone ? "1. Upload first file - complete" : "1. Upload first file"}</p>
            <p className="text-sm text-app">{runStepDone ? "2. Run scan - complete" : "2. Run scan"}</p>
            <p className="text-sm text-app">{reportStepDone ? "3. View redaction report - complete" : "3. View redaction report"}</p>
          </CardContent>
        </Card>
      )}

      <Card className="w-full shadow-md">
        <CardContent className="space-y-5 p-6">
          <div className="space-y-3">
            <label
              htmlFor="file-upload"
              className="block font-semibold text-app"
            >
              Upload a File
            </label>
            <Input
              id="file-upload"
              type="file"
              accept={allowedTypes.join(",")}
              required
              onChange={handleFileChange}
            />
            {file && (
              <p className="mt-2 text-sm text-app-secondary">
                Selected file: {file.name}
              </p>
            )}

            <Button onClick={handleUpload} disabled={!file || uploading}>
              {uploading ? "Scanning..." : "Scan File for PII"}
            </Button>

            {uploading && (
              <p className="text-sm italic text-app-secondary" role="status" aria-live="polite">
                {jobId && jobStatus ? `Scan job ${jobStatus.toLowerCase()}...` : "Uploading and analyzing file..."}
              </p>
            )}

            {error && !uploading && (
              <p className="text-sm font-medium text-red-600" role="alert">{error}</p>
            )}

            {hasScanned && piiColumns.length === 0 && !uploading && !error && (
              <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300" role="status" aria-live="polite">
                Scan complete. No sensitive field types were detected.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {hasScanned && !uploading && !error && (
        <Card className="w-full shadow-md">
          <CardContent className="space-y-6 p-6">
            <div>
              <h2 className="text-2xl font-bold text-app">Scan Summary</h2>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <p>
                  <span className="font-semibold text-app-secondary">File Name:</span>{" "}
                  {displayFileName}
                </p>
                <p>
                  <span className="font-semibold text-app-secondary">File Type:</span>{" "}
                  {fileType}
                </p>
                <p>
                  <span className="font-semibold text-app-secondary">Scan Status:</span>{" "}
                  Complete
                </p>
                <p>
                  <span className="font-semibold text-app-secondary">Risk Score:</span>{" "}
                  {riskPercent == null ? "Not available" : `${riskPercent}%`}
                </p>
                <p>
                  <span className="font-semibold text-app-secondary">Risk Level:</span>{" "}
                  {riskLevel}
                </p>
                <p>
                  <span className="font-semibold text-app-secondary">Total Values Redacted:</span>{" "}
                  {redactedCount ?? "Not available"}
                </p>
                <p className="sm:col-span-2">
                  <span className="font-semibold text-app-secondary">Sensitive Field Types Detected:</span>{" "}
                  {detectedTypes}
                </p>
              </div>
            </div>

            <div className="surface-panel rounded-2xl p-4">
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-app-muted">
                Redaction Summary
              </h3>
              <div className="mt-3 space-y-2 text-sm text-app">
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
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-700 dark:text-amber-100">
                Recommended Action
              </h3>
              <p className="mt-3 text-sm text-amber-800 dark:text-amber-50">{recommendation}</p>
            </div>

            <div className="surface-panel rounded-2xl p-4">
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-app-secondary">
                Available Outputs
              </h3>
              <div className="mt-3 flex flex-wrap gap-3">
                {redactedFile && scanId ? (
                  <button
                    onClick={() =>
                      downloadProtectedAsset(`/scans/${scanId}/download`, displayFileName)
                        .then(() => setError(null))
                        .catch((downloadError) => {
                          setError(downloadError.message);
                        })
                    }
                    className="btn-primary-app text-sm"
                  >
                    Download Redacted File
                  </button>
                ) : (
                  <span className="text-sm text-app-muted">Redacted file not available.</span>
                )}

                {scanId ? (
                  <button
                    onClick={async () => {
                      const stem = displayFileName.replace(/\.[^.]+$/, "");
                      try {
                        await downloadProtectedAsset(
                          `/scans/${scanId}/report/pdf`,
                          `${stem}-audit-report.pdf`,
                          "pdf",
                        );
                        await authFetch("/onboarding/complete", { method: "POST" });
                        setOnboarding({ has_completed_onboarding: true, steps: onboardingSteps });
                        setError(null);
                      } catch (pdfError) {
                        if (pdfError?.status === 501) {
                          try {
                            await downloadProtectedAsset(
                              `/scans/${scanId}/report/html`,
                              `${stem}-audit-report.html`,
                            );
                            await authFetch("/onboarding/complete", { method: "POST" });
                            setOnboarding({ has_completed_onboarding: true, steps: onboardingSteps });
                            setError(
                              `${getDownloadErrorMessage(501)} Downloaded HTML audit report instead.`,
                            );
                          } catch (reportError) {
                            setError(reportError.message);
                          }
                        } else {
                          setError(pdfError.message);
                        }
                      }
                    }}
                    className="btn-secondary-app text-sm"
                  >
                    Download Audit Report
                  </button>
                ) : (
                  <span className="text-sm text-app-muted">Audit report not available.</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
