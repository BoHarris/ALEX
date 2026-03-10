import { authFetch } from "../utils/authFetch";

function formatLabel(name) {
  const stem = name.replace(/\.[^.]+$/, "");
  return stem.replace(/[_-]+/g, " ");
}

function formatExtension(name) {
  const parts = name.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toUpperCase() : "FILE";
}

function getFilenameFromDisposition(disposition, fallbackName) {
  const utfMatch = disposition?.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) {
    return decodeURIComponent(utfMatch[1]);
  }
  const asciiMatch = disposition?.match(/filename="?([^"]+)"?/i);
  return asciiMatch?.[1] || fallbackName;
}

async function downloadScanAsset(path, fallbackName) {
  const response = await authFetch(path);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const blob = await response.blob();
  const href = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = getFilenameFromDisposition(
    response.headers.get("Content-Disposition"),
    fallbackName,
  );
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(href);
}

export default function DashboardFilesPanel({
  files,
  loading,
  error,
  onRetry,
}) {
  if (loading) {
    return (
      <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-sm text-slate-300">
        Loading your redacted files...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-200">
        <p>Could not load your redacted files.</p>
        <p className="mt-2 text-rose-100/80">{error.message}</p>
        <button
          onClick={onRetry}
          className="mt-4 rounded-full border border-rose-300/40 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-rose-100 transition hover:bg-rose-200/10"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!files.length) {
    return (
      <div className="rounded-3xl border border-dashed border-cyan-300/30 bg-slate-900/60 p-10 text-center">
        <p className="text-lg font-semibold text-white">
          No redacted files yet
        </p>
        <p className="mt-2 text-sm text-slate-300">
          Upload a document in the Upload tab to generate your first redacted
          result.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {files.map((scan, index) => (
        <div
          key={scan.scan_id}
          className="grid gap-4 rounded-3xl border border-white/10 bg-slate-900/70 p-5 lg:grid-cols-[minmax(0,1fr)_auto]"
        >
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-100">
                {index === 0 ? "Latest" : "Ready"}
              </span>
              <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300">
                {formatExtension(scan.filename)}
              </span>
            </div>
            <p className="mt-4 truncate text-lg font-semibold text-white">
              {scan.filename}
            </p>
            <p className="mt-1 text-sm text-slate-400">
              {formatLabel(scan.filename)}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 lg:justify-end">
            <button
              onClick={() =>
                downloadScanAsset(
                  `/scans/${scan.scan_id}/download`,
                  scan.filename,
                ).catch(onRetry)
              }
              className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
            >
              Download
            </button>
            <button
              onClick={() =>
                downloadScanAsset(
                  `/scans/${scan.scan_id}/report/html`,
                  `${formatLabel(scan.filename)}-report.html`,
                ).catch(onRetry)
              }
              className="rounded-full border border-white/15 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              HTML Report
            </button>
            <button
              onClick={() =>
                downloadScanAsset(
                  `/scans/${scan.scan_id}/report/pdf`,
                  `${formatLabel(scan.filename)}-report.pdf`,
                ).catch(onRetry)
              }
              className="rounded-full border border-white/15 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              PDF Report
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
