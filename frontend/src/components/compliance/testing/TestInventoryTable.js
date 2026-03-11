import { formatDateTime, formatPercent, statusBadgeClass } from "../../../pages/compliance/utils";

function FlakyIndicator({ flaky }) {
  if (!flaky) {
    return <span className="text-app-muted">Stable</span>;
  }
  return <span className="text-cyan-300">Flaky</span>;
}

export default function TestInventoryTable({ tests, selectedTestId, onSelectTest }) {
  return (
    <div className="surface-card overflow-hidden rounded-3xl">
      <div className="grid gap-3 border-b border-app px-5 py-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-app-muted md:grid-cols-[2.4fr_0.9fr_0.9fr_0.8fr_1fr_0.9fr_0.8fr]">
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
            className={`grid w-full gap-3 border-t border-app px-5 py-4 text-left text-sm transition hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 md:grid-cols-[2.4fr_0.9fr_0.9fr_0.8fr_1fr_0.9fr_0.8fr] ${selectedTestId === test.test_id ? "bg-white/5" : ""}`}
          >
            <div>
              <p className="font-semibold text-app">{test.test_name}</p>
              <p className="mt-1 text-xs text-app-muted">{test.file_path || test.file_name || test.category}</p>
              <p className="mt-1 text-[11px] text-app-muted">{test.test_node_id}</p>
            </div>
            <div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(test.status)}`}>{test.status}</span></div>
            <div className="text-app-secondary">{formatPercent(test.pass_rate)}</div>
            <div className="text-app-secondary">{test.total_runs}</div>
            <div className="text-app-secondary">{formatDateTime(test.last_run_timestamp)}</div>
            <div className="text-app-secondary">{test.last_duration_ms != null ? `${test.last_duration_ms} ms` : "N/A"}</div>
            <div className="text-app-secondary"><FlakyIndicator flaky={test.flaky} /></div>
          </button>
        ))}
      </div>
    </div>
  );
}
