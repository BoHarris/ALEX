import { useEffect, useMemo, useState } from "react";
import SummaryMetricCard from "../../components/compliance/SummaryMetricCard";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import TestCategoryRail from "../../components/compliance/testing/TestCategoryRail";
import TestDetailPanel from "../../components/compliance/testing/TestDetailPanel";
import TestInventoryTable from "../../components/compliance/testing/TestInventoryTable";
import TestingRunHistoryDrawer from "../../components/compliance/testing/TestingRunHistoryDrawer";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, formatPercent, statusBadgeClass } from "./utils";

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label className="min-w-0 flex flex-col gap-2 text-sm text-app-secondary">
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-app-muted">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="w-full rounded-2xl border border-app bg-app/80 px-3 py-2.5 text-sm text-app shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60">
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}

export default function ComplianceTestingPage() {
  const {
    data,
    testDashboard,
    testCategoryDetail,
    selectedTestCase,
    loadTestCategory,
    loadTestCase,
    createOrAssignTestTask,
    updateTestTask,
  } = useCompliancePageContext();
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [search, setSearch] = useState("");
  const [filePathFilter, setFilePathFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sort, setSort] = useState("last_run");
  const [interactionError, setInteractionError] = useState(null);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyDrawerTest, setHistoryDrawerTest] = useState(null);

  const dashboard = testDashboard || { summary: null, categories: [] };
  const categories = useMemo(() => dashboard.categories || [], [dashboard.categories]);
  const selectedCategoryMeta = categories.find((item) => item.category === selectedCategory) || null;

  useEffect(() => {
    if (!selectedCategory && categories.length) {
      setSelectedCategory(categories[0].category);
    }
  }, [categories, selectedCategory]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedCategory) {
      return undefined;
    }

    async function loadCategory() {
      try {
        setInteractionError(null);
        await loadTestCategory(selectedCategory, {
          search: search.trim() || undefined,
          file_path: filePathFilter.trim() || undefined,
          status: statusFilter || undefined,
          sort,
        });
      } catch (err) {
        if (!cancelled) {
          setInteractionError(err.message);
        }
      }
    }

    loadCategory();
    return () => {
      cancelled = true;
    };
  }, [filePathFilter, loadTestCategory, search, selectedCategory, sort, statusFilter]);

  const categorySummary = useMemo(() => {
    const summary = testCategoryDetail?.summary || {};
    return {
      total: summary.total_tests ?? 0,
      passing: summary.passing ?? 0,
      failing: summary.failing ?? 0,
      skipped: summary.skipped ?? 0,
      notRun: summary.not_run ?? 0,
      flaky: summary.flaky ?? 0,
      passRate: summary.average_pass_rate ?? summary.pass_rate ?? 0,
      lastRun: summary.last_run_timestamp ?? selectedCategoryMeta?.last_run_timestamp ?? null,
    };
  }, [selectedCategoryMeta?.last_run_timestamp, testCategoryDetail?.summary]);

  async function handleSelectTest(test) {
    try {
      setInteractionError(null);
      setHistoryDrawerTest(test);
      setHistoryDrawerOpen(true);
      await loadTestCase(test.test_id);
    } catch (err) {
      setInteractionError(err.message);
    }
  }

  const activeDrawerTest = selectedTestCase?.test_id === historyDrawerTest?.test_id ? selectedTestCase : historyDrawerTest;

  return (
    <div className="mx-auto max-w-[1720px] space-y-6 px-1">
      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <SummaryMetricCard label="Total Tests" value={dashboard.summary?.total_tests ?? 0} />
        <SummaryMetricCard label="Passing" value={dashboard.summary?.passing_tests ?? 0} />
        <SummaryMetricCard label="Failing" value={dashboard.summary?.failing_tests ?? 0} />
        <SummaryMetricCard label="Flaky" value={dashboard.summary?.flaky_tests ?? 0} />
        <SummaryMetricCard label="Avg Pass Rate" value={formatPercent(dashboard.summary?.average_pass_rate ?? 0)} />
        <SummaryMetricCard label="Execs / 7 Days" value={dashboard.summary?.total_executions_last_7_days ?? 0} />
      </section>

      {interactionError ? (
        <div className="surface-card rounded-3xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          {interactionError}
        </div>
      ) : null}

      <TestingRunHistoryDrawer
        open={historyDrawerOpen}
        test={activeDrawerTest}
        onClose={() => setHistoryDrawerOpen(false)}
      />

      <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)] 2xl:grid-cols-[300px_minmax(0,0.92fr)_minmax(560px,1.12fr)]">
        <TestCategoryRail
          categories={categories}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
        />

        <section className="surface-card rounded-3xl p-6">
          {selectedCategory ? (
            <>
              <div className="rounded-2xl border border-app bg-app/30 p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-app-muted">Category Summary</p>
                    <h2 className="mt-3 text-3xl font-semibold leading-tight text-app">{selectedCategory}</h2>
                    <p className="mt-3 max-w-2xl text-sm leading-6 text-app-secondary">{selectedCategoryMeta?.description || "Automated validation suite."}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(selectedCategoryMeta?.status || "unknown")}`}>
                    {selectedCategoryMeta?.status || "unknown"}
                  </span>
                </div>
                <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  <div className="rounded-2xl border border-app/70 bg-app/40 p-4"><p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Total Tests</p><p className="mt-2 text-2xl font-semibold text-app">{categorySummary.total}</p></div>
                  <div className="rounded-2xl border border-app/70 bg-app/40 p-4"><p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Passing</p><p className="mt-2 text-2xl font-semibold text-emerald-300">{categorySummary.passing}</p></div>
                  <div className="rounded-2xl border border-app/70 bg-app/40 p-4"><p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Failing</p><p className="mt-2 text-2xl font-semibold text-rose-300">{categorySummary.failing}</p></div>
                  <div className="rounded-2xl border border-app/70 bg-app/40 p-4"><p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Skipped</p><p className="mt-2 text-2xl font-semibold text-amber-200">{categorySummary.skipped}</p></div>
                  <div className="rounded-2xl border border-app/70 bg-app/40 p-4"><p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Flaky</p><p className="mt-2 text-2xl font-semibold text-cyan-200">{categorySummary.flaky}</p></div>
                  <div className="rounded-2xl border border-app/70 bg-app/40 p-4"><p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Not Run</p><p className="mt-2 text-2xl font-semibold text-amber-200">{categorySummary.notRun}</p></div>
                  <div className="rounded-2xl border border-app/70 bg-app/40 p-4 xl:col-span-2"><p className="text-[11px] uppercase tracking-[0.18em] text-app-muted">Last Run</p><p className="mt-2 text-sm font-medium leading-6 text-app-secondary">{formatDateTime(categorySummary.lastRun)}</p></div>
                </div>
              </div>

              <div className="mt-6 rounded-2xl border border-app/70 bg-app/20 p-4">
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_140px_140px]">
                <label className="min-w-0 flex flex-col gap-2 text-sm text-app-secondary">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-app-muted">Search Tests</span>
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search by name, description, or file"
                    className="w-full rounded-2xl border border-app bg-app/80 px-3 py-2.5 text-sm text-app shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60"
                  />
                </label>
                <label className="min-w-0 flex flex-col gap-2 text-sm text-app-secondary">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-app-muted">File Path</span>
                  <input
                    value={filePathFilter}
                    onChange={(event) => setFilePathFilter(event.target.value)}
                    placeholder="Filter by tests/path.py"
                    className="w-full rounded-2xl border border-app bg-app/80 px-3 py-2.5 text-sm text-app shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60"
                  />
                </label>
                <FilterSelect
                  label="Status"
                  value={statusFilter}
                  onChange={setStatusFilter}
                  options={[
                    { value: "", label: "All statuses" },
                    { value: "passed", label: "Passed" },
                    { value: "failed", label: "Failed" },
                    { value: "skipped", label: "Skipped" },
                    { value: "not_run", label: "Not Run" },
                    { value: "flaky", label: "Flaky" },
                  ]}
                />
                <FilterSelect
                  label="Sort"
                  value={sort}
                  onChange={setSort}
                  options={[
                    { value: "last_run", label: "Latest Run" },
                    { value: "pass_rate", label: "Pass Rate" },
                    { value: "failures", label: "Failures" },
                    { value: "flakiness", label: "Flakiness" },
                    { value: "name", label: "Name" },
                  ]}
                />
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between gap-3 border-b border-app/70 pb-3 text-xs text-app-muted">
                <span>{testCategoryDetail?.tests?.length || 0} tests shown</span>
                <span>{formatPercent(categorySummary.passRate)} average pass rate</span>
              </div>

              <div className="mt-4">
                {testCategoryDetail?.tests?.length ? (
                  <TestInventoryTable
                    tests={testCategoryDetail.tests}
                    selectedTestId={selectedTestCase?.test_id}
                    onSelectTest={handleSelectTest}
                  />
                ) : (
                  <WorkspaceEmptyState title="No tests match" description="Adjust the search, filters, or selected category to find automated test executions." />
                )}
              </div>
            </>
          ) : (
            <WorkspaceEmptyState title="No category selected" description="Choose a test suite from the left panel to inspect automated test inventory and execution history." />
          )}
        </section>

        <TestDetailPanel
          test={selectedTestCase}
          employees={data?.directory?.employees || []}
          onCreateTask={createOrAssignTestTask}
          onUpdateTask={updateTestTask}
        />
      </div>
    </div>
  );
}
