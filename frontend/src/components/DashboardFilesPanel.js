import { useEffect, useState } from "react";
import { downloadProtectedAsset } from "../utils/downloads";

function formatLabel(name) {
  const stem = name.replace(/\.[^.]+$/, "");
  return stem.replace(/[_-]+/g, " ");
}
function formatExtension(name) {
  const parts = name.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toUpperCase() : "FILE";
}

function formatScanDate(value) {
  if (!value) return "Unknown scan time";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Unknown scan time" : parsed.toLocaleString();
}

function getRiskTone(riskScore) {
  if (riskScore >= 70) {
    return "border-rose-400/50 bg-rose-200/30 text-rose-900 dark:border-rose-300/40 dark:bg-rose-300/10 dark:text-rose-100";
  }
  if (riskScore >= 40) {
    return "border-amber-400/55 bg-amber-200/35 text-amber-900 dark:border-amber-300/40 dark:bg-amber-300/10 dark:text-amber-100";
  }
  return "border-emerald-400/55 bg-emerald-200/35 text-emerald-900 dark:border-emerald-300/40 dark:bg-emerald-300/10 dark:text-emerald-100";
}

function getBadgeClass(variant) {
  const map = {
    ready: "border-sky-400/55 bg-sky-200/35 text-sky-900 dark:border-sky-300/45 dark:bg-sky-300/10 dark:text-sky-100",
    success: "border-emerald-400/55 bg-emerald-200/35 text-emerald-900 dark:border-emerald-300/45 dark:bg-emerald-300/10 dark:text-emerald-100",
    report: "border-cyan-400/55 bg-cyan-200/35 text-cyan-900 dark:border-cyan-300/45 dark:bg-cyan-300/10 dark:text-cyan-100",
    processing: "border-violet-400/55 bg-violet-200/35 text-violet-900 dark:border-violet-300/45 dark:bg-violet-300/10 dark:text-violet-100",
    failed: "border-rose-400/55 bg-rose-200/35 text-rose-900 dark:border-rose-300/45 dark:bg-rose-300/10 dark:text-rose-100",
  };
  return map[variant] || map.ready;
}

function getStatusBadges(scan, archived) {
  const badges = [];
  const status = (scan.status || "").toLowerCase();
  if (archived) {
    badges.push({ label: "Archived", variant: "processing" });
  } else if (status === "failed") {
    badges.push({ label: "Failed", variant: "failed" });
  } else if (status === "processing") {
    badges.push({ label: "Processing", variant: "processing" });
  } else {
    badges.push({ label: "Ready", variant: "ready" });
  }

  if ((scan.total_pii_found || 0) > 0) {
    badges.push({ label: "Redacted Successfully", variant: "success" });
  }

  if (status !== "processing" && status !== "failed") {
    badges.push({ label: "Report Ready", variant: "report" });
  }

  return badges;
}

function getTypeSummary(scan) {
  const typeCounts = scan.redacted_type_counts;
  if (typeCounts && Object.keys(typeCounts).length > 0) {
    return Object.entries(typeCounts)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 3);
  }

  const piiTypes = Array.isArray(scan.pii_types_found) ? scan.pii_types_found.slice(0, 3) : [];
  return piiTypes.map((label) => [label, null]);
}

function ActionMenu({ scan, archived, onArchiveScan, onRestoreScan, onViewReport, onDownload }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={`Open actions menu for ${scan.filename}`}
        aria-expanded={open}
        className="btn-secondary-app px-3 py-2 text-sm"
        onClick={() => setOpen((value) => !value)}
      >
        •••
      </button>
      {open ? (
        <div className="surface-card absolute right-0 z-20 mt-2 min-w-44 p-2 shadow-xl" role="menu" aria-label="Scan actions">
          <button
            type="button"
            role="menuitem"
            className="block w-full rounded-md px-3 py-2 text-left text-sm text-app hover:bg-white/10"
            onClick={() => {
              setOpen(false);
              onViewReport();
            }}
          >
            View Report
          </button>
          <button
            type="button"
            role="menuitem"
            className="block w-full rounded-md px-3 py-2 text-left text-sm text-app hover:bg-white/10"
            onClick={() => {
              setOpen(false);
              onDownload();
            }}
          >
            Download
          </button>
          {archived ? (
            <button
              type="button"
              role="menuitem"
              className="block w-full rounded-md px-3 py-2 text-left text-sm text-app hover:bg-white/10"
              onClick={() => {
                setOpen(false);
                onRestoreScan();
              }}
            >
              Restore Scan
            </button>
          ) : (
            <button
              type="button"
              role="menuitem"
              className="block w-full rounded-md px-3 py-2 text-left text-sm text-app hover:bg-white/10"
              onClick={() => {
                setOpen(false);
                onArchiveScan();
              }}
            >
              Archive Scan
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
}

export default function DashboardFilesPanel({
  files,
  loading,
  error,
  onRetry,
  onArchiveScan,
  onRestoreScan,
  title = "Redacted Files",
  description = null,
  showSubmitter = false,
  archived = false,
}) {
  const [actionError, setActionError] = useState(null);

  useEffect(() => {
    setActionError(null);
  }, [files, archived]);

  if (loading) {
    return <div className="surface-card p-6 text-sm text-app-secondary">Loading your redacted files...</div>;
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-800 dark:text-rose-100">
        <p>Could not load your redacted files.</p>
        <p className="mt-2">{error.message}</p>
        <button
          onClick={onRetry}
          className="mt-4 rounded-full border border-rose-500/50 bg-rose-200/40 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-rose-900 hover:bg-rose-200/60 dark:border-rose-300/40 dark:bg-rose-300/10 dark:text-rose-100"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!files.length) {
    return (
      <div className="surface-card border-dashed border-cyan-300/30 p-10 text-center">
        <p className="text-lg font-semibold text-app">
          {archived ? "No archived scans yet" : "No redacted files yet"}
        </p>
        <p className="mt-2 text-sm text-app-secondary">
          {archived
            ? "Archived scans will appear here and remain available for restoration."
            : "Upload a document in the Upload tab to generate your first redacted result."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="surface-card p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">{title}</p>
        <p className="mt-2 text-sm text-app-secondary">
          {description || "Review recent scan activity and download protected outputs."}
        </p>
      </div>
      {actionError ? (
        <div className="rounded-3xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-800 dark:text-rose-100" role="alert">
          {actionError}
        </div>
      ) : null}
      {files.map((scan) => (
        <article key={scan.scan_id} className="surface-card space-y-5 p-5">
          <section className="space-y-2">
            <p className="truncate text-lg font-semibold text-app">{scan.filename}</p>
            <p className="text-sm text-app-secondary">{formatLabel(scan.filename)}</p>
            <p className="text-xs uppercase tracking-[0.22em] text-app-muted">
              {formatExtension(scan.filename)} • Scan completed {formatScanDate(scan.scanned_at)}
            </p>
            {showSubmitter && scan.submitter ? (
              <p className="text-sm text-app-secondary">
                Submitted by{" "}
                <span className="font-medium text-app">
                  {[scan.submitter.first_name, scan.submitter.last_name].filter(Boolean).join(" ") || scan.submitter.email}
                </span>
                {scan.submitter.email ? <span className="text-app-muted"> ({scan.submitter.email})</span> : null}
              </p>
            ) : null}
          </section>

          <section className="flex flex-wrap items-center gap-2" aria-label="Status badges">
            {getStatusBadges(scan, archived).map((badge) => (
              <span
                key={`${scan.scan_id}-${badge.label}`}
                className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${getBadgeClass(badge.variant)}`}
              >
                {badge.label}
              </span>
            ))}
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <div className="surface-panel rounded-2xl border-2 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-app-muted">Risk Summary</p>
              <div className="mt-3 flex items-center gap-3">
                <span className={`rounded-full border-2 px-3 py-1 text-sm font-semibold ${getRiskTone(scan.risk_score || 0)}`}>
                  {scan.risk_score ?? 0}%
                </span>
                <span className="text-sm text-app">
                  {(scan.total_pii_found || 0) > 0 ? "Sensitive data detected" : "No material findings"}
                </span>
              </div>
              <div className="mt-4 grid gap-3 text-sm text-app sm:grid-cols-2">
                <p><span className="text-app-muted">Sensitive items found:</span> {scan.total_pii_found ?? 0}</p>
                <p><span className="text-app-muted">Redactions applied:</span> {scan.redacted_count ?? scan.total_pii_found ?? 0}</p>
              </div>
            </div>
            <div className="surface-panel rounded-2xl p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-app-muted">Detected Data Types</p>
              <div className="mt-3 space-y-2 text-sm text-app">
                {getTypeSummary(scan).length ? (
                  getTypeSummary(scan).map(([label, count]) => (
                    <p key={label}>
                      {label}
                      {count != null ? ` (${count})` : ""}
                    </p>
                  ))
                ) : (
                  <p className="text-app-muted">No type-level summary available.</p>
                )}
              </div>
            </div>
          </section>

          <section className="surface-panel flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4" aria-label="Scan actions">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() =>
                  downloadProtectedAsset(`/scans/${scan.scan_id}/download`, scan.filename)
                    .then(() => setActionError(null))
                    .catch((downloadError) => setActionError(downloadError.message))
                }
                className="btn-primary-app text-sm"
              >
                Download
              </button>
              <button
                onClick={() =>
                  downloadProtectedAsset(`/scans/${scan.scan_id}/report/html`, `${formatLabel(scan.filename)}-report.html`)
                    .then(() => setActionError(null))
                    .catch((downloadError) => setActionError(downloadError.message))
                }
                className="btn-secondary-app text-sm"
              >
                HTML Report
              </button>
              <button
                onClick={() =>
                  downloadProtectedAsset(`/scans/${scan.scan_id}/report/pdf`, `${formatLabel(scan.filename)}-report.pdf`, "pdf")
                    .then(() => setActionError(null))
                    .catch((downloadError) => setActionError(downloadError.message))
                }
                className="btn-secondary-app text-sm"
              >
                PDF Report
              </button>
            </div>
            <ActionMenu
              scan={scan}
              archived={archived}
              onViewReport={() =>
                downloadProtectedAsset(`/scans/${scan.scan_id}/report/html`, `${formatLabel(scan.filename)}-report.html`)
                  .then(() => setActionError(null))
                  .catch((downloadError) => setActionError(downloadError.message))
              }
              onDownload={() =>
                downloadProtectedAsset(`/scans/${scan.scan_id}/download`, scan.filename)
                  .then(() => setActionError(null))
                  .catch((downloadError) => setActionError(downloadError.message))
              }
              onArchiveScan={() =>
                onArchiveScan
                  ? onArchiveScan(scan.scan_id).catch((archiveError) => setActionError(archiveError.message))
                  : Promise.resolve()
              }
              onRestoreScan={() =>
                onRestoreScan
                  ? onRestoreScan(scan.scan_id).catch((restoreError) => setActionError(restoreError.message))
                  : Promise.resolve()
              }
            />
          </section>
        </article>
      ))}
    </div>
  );
}
