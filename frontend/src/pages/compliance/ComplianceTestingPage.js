import { useEffect, useMemo, useState } from "react";
import SummaryMetricCard from "../../components/compliance/SummaryMetricCard";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import TestCategoryRail from "../../components/compliance/testing/TestCategoryRail";
import TestDetailPanel from "../../components/compliance/testing/TestDetailPanel";
import TestInventoryTable from "../../components/compliance/testing/TestInventoryTable";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, formatPercent, statusBadgeClass } from "./utils";

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label className="flex flex-col gap-2 text-sm text-app-secondary">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="rounded-2xl border border-app bg-app px-3 py-3 text-sm text-app focus-visible:outline-none">
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}

export default function ComplianceTestingPage() {
  const {
    testDashboard,
    testCategoryDetail,
    selectedTestCase,
    loadTestCategory,
    loadTestCase,
  } = useCompliancePageContext();
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [search, setSearch] = useState("");
  const [filePathFilter, setFilePathFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sort, setSort] = useState("last_run");
  const [interactionError, setInteractionError] = useState(null);

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
      await loadTestCase(test.test_id);
    } catch (err) {
      setInteractionError(err.message);
    }
  }

  return (
    <div className="space-y-6">
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

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1.2fr)_minmax(340px,0.95fr)]">
        <TestCategoryRail
          categories={categories}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
        />

        <section className="surface-card rounded-3xl p-5">
          {selectedCategory ? (
            <>
              <div className="rounded-2xl border border-app p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-app-muted">Category Summary</p>
                    <h2 className="mt-2 text-2xl font-semibold text-app">{selectedCategory}</h2>
                    <p className="mt-2 text-sm text-app-secondary">{selectedCategoryMeta?.description || "Automated validation suite."}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(selectedCategoryMeta?.status || "unknown")}`}>
                    {selectedCategoryMeta?.status || "unknown"}
                  </span>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Total Tests</p><p className="mt-1 text-lg font-semibold text-app">{categorySummary.total}</p></div>
                  <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Passing</p><p className="mt-1 text-lg font-semibold text-emerald-300">{categorySummary.passing}</p></div>
                  <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Failing</p><p className="mt-1 text-lg font-semibold text-rose-300">{categorySummary.failing}</p></div>
                  <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Skipped</p><p className="mt-1 text-lg font-semibold text-amber-200">{categorySummary.skipped}</p></div>
                  <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Flaky</p><p className="mt-1 text-lg font-semibold text-cyan-200">{categorySummary.flaky}</p></div>
                  <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Not Run</p><p className="mt-1 text-lg font-semibold text-amber-200">{categorySummary.notRun}</p></div>
                  <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Last Run</p><p className="mt-1 text-sm font-medium text-app-secondary">{formatDateTime(categorySummary.lastRun)}</p></div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_1.1fr_1fr_1fr]">
                <label className="flex flex-col gap-2 text-sm text-app-secondary">
                  <span>Search Tests</span>
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search by name, description, or file"
                    className="rounded-2xl border border-app bg-app px-3 py-3 text-sm text-app focus-visible:outline-none"
                  />
                </label>
                <label className="flex flex-col gap-2 text-sm text-app-secondary">
                  <span>File Path</span>
                  <input
                    value={filePathFilter}
                    onChange={(event) => setFilePathFilter(event.target.value)}
                    placeholder="Filter by tests/path.py"
                    className="rounded-2xl border border-app bg-app px-3 py-3 text-sm text-app focus-visible:outline-none"
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

              <div className="mt-4 flex items-center justify-between gap-3 text-xs text-app-muted">
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

        <TestDetailPanel test={selectedTestCase} />
      </div>
    </div>
  );
}
