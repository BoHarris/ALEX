import { formatDateTime, formatPercent, statusBadgeClass } from "../../../pages/compliance/utils";

function StatPill({ label, value, tone }) {
  return (
    <div className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${tone}`}>
      {label}: {value}
    </div>
  );
}

export default function TestCategoryRail({ categories, selectedCategory, onSelectCategory }) {
  return (
    <section className="surface-card rounded-3xl p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-app">Test Suites</h2>
          <p className="mt-2 text-sm leading-6 text-app-secondary">Automated validation coverage across security, privacy, and compliance workflows.</p>
        </div>
      </div>
      <div className="mt-6 space-y-4">
        {categories.length ? categories.map((item) => (
          <button
            key={item.category}
            type="button"
            onClick={() => onSelectCategory(item.category)}
            className={`w-full rounded-3xl border border-app/80 bg-app/30 p-5 text-left transition hover:border-cyan-300/30 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${selectedCategory === item.category ? "border-cyan-300/30 bg-white/5 shadow-[0_0_0_1px_rgba(103,232,249,0.18)]" : ""}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 pr-2">
                <p className="text-lg font-semibold capitalize text-app">{item.category}</p>
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-app-secondary">{item.description}</p>
              </div>
              <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(item.status)}`}>{item.status}</span>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <StatPill label="Pass" value={item.passing} tone="bg-emerald-500/10 text-emerald-300" />
              <StatPill label="Fail" value={item.failing} tone="bg-rose-500/10 text-rose-300" />
              <StatPill label="Flaky" value={item.flaky} tone="bg-cyan-500/10 text-cyan-200" />
              <StatPill label="Skip" value={item.skipped} tone="bg-amber-500/10 text-amber-200" />
              <StatPill label="Not run" value={item.not_run || 0} tone="bg-amber-500/10 text-amber-100" />
            </div>
            <div className="mt-5 grid gap-3 rounded-2xl border border-app/70 bg-app/35 p-3 text-left sm:grid-cols-2">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Inventory</p>
                <p className="mt-1 text-sm font-medium text-app">{item.total_tests} tests</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-app-muted">Avg Pass Rate</p>
                <p className="mt-1 text-sm font-medium text-app">{formatPercent(item.average_pass_rate)}</p>
              </div>
            </div>
            <p className="mt-3 text-xs leading-5 text-app-muted">Last run {formatDateTime(item.last_run_timestamp)}</p>
          </button>
        )) : <p className="text-sm text-app-muted">No test categories available.</p>}
      </div>
    </section>
  );
}
