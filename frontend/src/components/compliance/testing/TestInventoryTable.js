import { formatDateTime, formatPercent, statusBadgeClass, statusTone } from "../../../pages/compliance/utils";

function QualityIndicator({ label }) {
  return <span className={`font-medium ${statusTone(label)}`}>{label}</span>;
}

function formatCompactDateTime(value) {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    month: "numeric",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function TestInventoryTable({ tests, selectedTestId, onSelectTest }) {
  return (
    <div className="surface-card overflow-hidden rounded-3xl border border-app/80">
      <div className="hidden gap-4 border-b border-app/80 bg-white/[0.03] px-5 py-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-app-muted xl:grid xl:grid-cols-[minmax(0,2.5fr)_0.95fr_0.85fr_0.65fr_1fr_0.8fr_0.85fr]">
        <div>Test Case</div>
        <div>Status</div>
        <div>Pass Rate</div>
        <div>Runs</div>
        <div>Last Run</div>
        <div>Duration</div>
        <div>Quality</div>
      </div>
      <div>
        {tests.map((test) => (
          <button
            key={test.test_id}
            type="button"
            onClick={() => onSelectTest(test)}
            className={`grid w-full gap-4 border-t border-app/80 px-5 py-5 text-left text-sm transition hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 md:grid-cols-[minmax(0,1.35fr)_auto] xl:grid-cols-[minmax(0,2.5fr)_0.95fr_0.85fr_0.65fr_1fr_0.8fr_0.85fr] ${selectedTestId === test.test_id ? "bg-white/5" : ""}`}
          >
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p
                  className="max-w-full overflow-hidden text-base font-semibold leading-7 text-app"
                  style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}
                  title={test.test_name}
                >
                  {test.test_name}
                </p>
                <span className="rounded-full border border-app/70 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">{test.category}</span>
              </div>
              <p
                className="mt-2 overflow-hidden text-xs leading-5 text-app-muted"
                style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}
                title={test.file_path || test.file_name || test.category}
              >
                {test.file_path || test.file_name || test.category}
              </p>
              <p
                className="mt-1 overflow-hidden font-mono text-[11px] leading-5 text-slate-400"
                style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}
                title={test.test_node_id}
              >
                {test.test_node_id}
              </p>
            </div>
            <div className="grid gap-3 md:min-w-[250px] md:grid-cols-2 xl:contents">
              <div className="flex items-start md:justify-end xl:items-center xl:justify-start"><span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(test.status)}`}>{test.status}</span></div>
              <div className="hidden xl:block text-sm font-medium text-app-secondary xl:pt-1">{formatPercent(test.pass_rate)}</div>
              <div className="hidden xl:block text-sm font-medium text-app-secondary xl:pt-1">{test.total_runs}</div>
              <div className="hidden xl:block text-sm leading-6 text-app-secondary xl:pt-1">{formatDateTime(test.last_run_timestamp)}</div>
              <div className="hidden xl:block text-sm font-medium text-app-secondary xl:pt-1">{test.last_duration_ms != null ? `${test.last_duration_ms} ms` : "N/A"}</div>
              <div className="hidden xl:block text-sm font-medium text-app-secondary xl:pt-1"><QualityIndicator label={test.quality_label || (test.flaky ? "Flaky" : "Stable")} /></div>

              <div className="grid gap-2 rounded-2xl border border-app/70 bg-app/25 p-3 text-xs text-app-secondary xl:hidden">
                <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                  <span className="text-app-muted">Pass Rate</span><span className="text-right font-medium text-app-secondary">{formatPercent(test.pass_rate)}</span>
                  <span className="text-app-muted">Runs</span><span className="text-right font-medium text-app-secondary">{test.total_runs}</span>
                  <span className="text-app-muted">Last Run</span><span className="text-right font-medium text-app-secondary">{formatCompactDateTime(test.last_run_timestamp)}</span>
                  <span className="text-app-muted">Duration</span><span className="text-right font-medium text-app-secondary">{test.last_duration_ms != null ? `${test.last_duration_ms} ms` : "N/A"}</span>
                  <span className="text-app-muted">Quality</span><span className="text-right font-medium"><QualityIndicator label={test.quality_label || (test.flaky ? "Flaky" : "Stable")} /></span>
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
