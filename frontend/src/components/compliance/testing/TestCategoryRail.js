import { formatDateTime, formatPercent, statusBadgeClass } from "../../../pages/compliance/utils";

function StatPill({ label, value, tone }) {
  return (
    <div className={`rounded-xl px-2 py-1 text-[11px] font-semibold ${tone}`}>
      {label}: {value}
    </div>
  );
}

export default function TestCategoryRail({ categories, selectedCategory, onSelectCategory }) {
  return (
    <section className="surface-card rounded-3xl p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-app">Test Suites</h2>
          <p className="mt-1 text-sm text-app-secondary">Automated validation coverage across security, privacy, and compliance workflows.</p>
        </div>
      </div>
      <div className="mt-4 space-y-3">
        {categories.length ? categories.map((item) => (
          <button
            key={item.category}
            type="button"
            onClick={() => onSelectCategory(item.category)}
            className={`w-full rounded-2xl border border-app p-4 text-left transition hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${selectedCategory === item.category ? "bg-white/5 shadow-[0_0_0_1px_rgba(103,232,249,0.2)]" : ""}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-app">{item.category}</p>
                <p className="mt-1 text-sm text-app-secondary">{item.description}</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(item.status)}`}>{item.status}</span>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <StatPill label="Pass" value={item.passing} tone="bg-emerald-500/10 text-emerald-300" />
              <StatPill label="Fail" value={item.failing} tone="bg-rose-500/10 text-rose-300" />
              <StatPill label="Flaky" value={item.flaky} tone="bg-cyan-500/10 text-cyan-200" />
              <StatPill label="Skip" value={item.skipped} tone="bg-amber-500/10 text-amber-200" />
              <StatPill label="Not run" value={item.not_run || 0} tone="bg-amber-500/10 text-amber-100" />
            </div>
            <div className="mt-4 flex items-center justify-between text-xs text-app-muted">
              <span>{item.total_tests} tests</span>
              <span>{formatPercent(item.average_pass_rate)} avg pass rate</span>
            </div>
            <p className="mt-2 text-xs text-app-muted">Last run {formatDateTime(item.last_run_timestamp)}</p>
          </button>
        )) : <p className="text-sm text-app-muted">No test categories available.</p>}
      </div>
    </section>
  );
}
