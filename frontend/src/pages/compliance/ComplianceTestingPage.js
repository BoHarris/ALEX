import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/button";
import SummaryMetricCard from "../../components/compliance/SummaryMetricCard";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import TestCategoryRail from "../../components/compliance/testing/TestCategoryRail";
import TestInventoryTable from "../../components/compliance/testing/TestInventoryTable";
import TestRunDetailDrawer from "../../components/compliance/testing/TestRunDetailDrawer";
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

function RunCard({ run, onSelect }) {
  const runTypeLabel = (run.run_type || "recorded").replace(/_/g, " ");

  return (
    <button
      type="button"
      onClick={() => onSelect?.(run.id)}
      className="rounded-2xl border border-app/70 bg-app/20 p-4 text-left transition hover:bg-white/5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-app">{run.suite_name}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-app-muted">{runTypeLabel} | {run.category}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(run.status)}`}>{run.status}</span>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-app-secondary sm:grid-cols-2">
        <div>Started: {formatDateTime(run.started_at || run.run_at)}</div>
        <div>Completed: {formatDateTime(run.completed_at)}</div>
      </div>
      {run.failure_summary ? (
        <p className="mt-3 line-clamp-2 text-sm text-rose-300">{run.failure_summary}</p>
      ) : null}
    </button>
  );
}

export default function ComplianceTestingPage() {
  const navigate = useNavigate();
  const workspace = useCompliancePageContext();
  const {
    data,
    testDashboard,
    testCategoryDetail,
    selectedTestCase,
    selectedTestRun,
    loadTestCategory,
    loadTestCase,
    loadTestRunDetail,
    createOrAssignTestTask,
    updateTestTask,
    runFullTestSuite,
    runTestCase,
    runTestCategory,
    refreshTestingWorkspace,
    clearTestRunDetail,
    loadTaskDetail,
  } = workspace;
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [search, setSearch] = useState("");
  const [filePathFilter, setFilePathFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sort, setSort] = useState("last_run");
  const [interactionError, setInteractionError] = useState(null);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyDrawerTest, setHistoryDrawerTest] = useState(null);
  const [launchingRunKey, setLaunchingRunKey] = useState(null);

  const dashboard = testDashboard || { summary: null, categories: [], recent_runs: [] };
  const categories = useMemo(() => dashboard.categories || [], [dashboard.categories]);
  const testRuns = data?.testRuns?.runs || [];
  const selectedCategoryMeta = categories.find((item) => item.category === selectedCategory) || null;
  const activeRuns = useMemo(() => testRuns.filter((run) => ["queued", "running"].includes((run.status || "").toLowerCase())), [testRuns]);
  const activeFullSuiteRun = activeRuns.find((run) => run.run_type === "full_suite") || null;
  const activeCategoryRun = activeRuns.find((run) => run.run_type === "category" && run.category === selectedCategory) || null;
  const activeTestRun = selectedTestCase ? activeRuns.find((run) => run.run_type === "single_test" && run.pytest_node_id === selectedTestCase.test_node_id) : null;

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

  useEffect(() => {
    if (!activeRuns.length) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      refreshTestingWorkspace().catch(() => null);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [activeRuns.length, refreshTestingWorkspace]);

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

  async function handleSelectRun(runId) {
    try {
      setInteractionError(null);
      await loadTestRunDetail(runId);
    } catch (err) {
      setInteractionError(err.message);
    }
  }

  async function handleRun(actionKey, callback) {
    try {
      setLaunchingRunKey(actionKey);
      setInteractionError(null);
      await callback();
    } catch (err) {
      setInteractionError(err.message);
    } finally {
      setLaunchingRunKey(null);
    }
  }

  async function handleRunFullSuite() {
    await handleRun("full_suite", runFullTestSuite);
  }

  async function handleRunCategory() {
    if (!selectedCategory) {
      return;
    }
    await handleRun(`category:${selectedCategory}`, () => runTestCategory(selectedCategory));
  }

  async function handleRunTest(testId) {
    await handleRun(`test:${testId}`, () => runTestCase(testId));
  }

  async function handleViewLinkedTask(task) {
    try {
      await loadTaskDetail(task.id);
    } catch (_err) {
      return navigate("/compliance/tasks");
    }
    navigate("/compliance/tasks");
  }

  const activeDrawerTest = selectedTestCase?.test_id === historyDrawerTest?.test_id ? selectedTestCase : historyDrawerTest;
  const lastFullSuiteRun = dashboard.summary?.last_full_suite_run || null;

  return (
    <div className="mx-auto max-w-[1720px] space-y-6 px-1">
      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <SummaryMetricCard label="Total Tests" value={dashboard.summary?.total_tests ?? 0} />
        <SummaryMetricCard label="Passing" value={dashboard.summary?.passing_tests ?? 0} />
        <SummaryMetricCard label="Failing" value={dashboard.summary?.failing_tests ?? 0} />
        <SummaryMetricCard label="Running Runs" value={dashboard.summary?.running_runs ?? 0} />
        <SummaryMetricCard label="Failure Tasks" value={dashboard.summary?.open_failure_tasks ?? 0} />
        <SummaryMetricCard label="Last Full Suite" value={lastFullSuiteRun?.run_at ? formatDateTime(lastFullSuiteRun.run_at) : "Not run"} />
      </section>

      {interactionError ? (
        <div className="surface-card rounded-3xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          {interactionError}
        </div>
      ) : null}

      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-app-muted">Execution Console</p>
            <h2 className="mt-3 text-3xl font-semibold leading-tight text-app">Run and monitor governance validations</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-app-secondary">
              Trigger the backend pytest suite, run a single recorded Python test, and inspect run output alongside remediation tasks.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={handleRunFullSuite} disabled={Boolean(activeFullSuiteRun) || launchingRunKey === "full_suite"}>
              {activeFullSuiteRun ? "Full suite running" : launchingRunKey === "full_suite" ? "Starting..." : "Run Full Test Suite"}
            </Button>
            {selectedCategory ? (
              <button
                type="button"
                onClick={handleRunCategory}
                disabled={Boolean(activeCategoryRun) || launchingRunKey === `category:${selectedCategory}`}
                className="rounded-full border border-app px-4 py-2 text-sm font-semibold text-app-secondary transition hover:bg-white/5 hover:text-app disabled:cursor-not-allowed disabled:opacity-50"
              >
                {activeCategoryRun ? "Category running" : launchingRunKey === `category:${selectedCategory}` ? "Starting..." : `Run ${selectedCategory}`}
              </button>
            ) : null}
          </div>
        </div>

        <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div className="rounded-2xl border border-app/70 bg-app/20 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-app">Recent Runs</h3>
              <span className="text-xs text-app-muted">{testRuns.length} recorded</span>
            </div>
            <div className="mt-4 space-y-3">
              {testRuns.length ? testRuns.map((run) => (
                <RunCard key={run.id} run={run} onSelect={handleSelectRun} />
              )) : <p className="text-sm text-app-muted">No governed executions have been recorded yet.</p>}
            </div>
          </div>

          <div className="rounded-2xl border border-app/70 bg-app/20 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-app">Operational Snapshot</h3>
              <span className="text-xs text-app-muted">{formatPercent(dashboard.summary?.average_pass_rate ?? 0)} avg pass rate</span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-app/70 bg-app/25 p-4">
                <p className="text-[10px] uppercase tracking-[0.16em] text-app-muted">Executions / 7 Days</p>
                <p className="mt-2 text-2xl font-semibold text-app">{dashboard.summary?.total_executions_last_7_days ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-app/70 bg-app/25 p-4">
                <p className="text-[10px] uppercase tracking-[0.16em] text-app-muted">Flaky Tests</p>
                <p className="mt-2 text-2xl font-semibold text-cyan-200">{dashboard.summary?.flaky_tests ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-app/70 bg-app/25 p-4 sm:col-span-2">
                <p className="text-[10px] uppercase tracking-[0.16em] text-app-muted">Latest Full Suite Status</p>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(lastFullSuiteRun?.status || "not_run")}`}>
                    {lastFullSuiteRun?.status || "not run"}
                  </span>
                  <span className="text-sm text-app-secondary">{formatDateTime(lastFullSuiteRun?.completed_at || lastFullSuiteRun?.run_at)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <TestingRunHistoryDrawer
        open={historyDrawerOpen}
        test={activeDrawerTest}
        employees={data?.directory?.employees || []}
        onCreateTask={createOrAssignTestTask}
        onUpdateTask={updateTestTask}
        onRunTest={handleRunTest}
        onViewLatestRun={handleSelectRun}
        runPending={Boolean(activeTestRun) || launchingRunKey === `test:${activeDrawerTest?.test_id}`}
        onClose={() => setHistoryDrawerOpen(false)}
      />

      <TestRunDetailDrawer
        open={Boolean(selectedTestRun)}
        runDetail={selectedTestRun}
        onClose={clearTestRunDetail}
        onViewTask={handleViewLinkedTask}
      />

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
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
                  <div className="flex flex-col items-end gap-3">
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(selectedCategoryMeta?.status || "unknown")}`}>
                      {selectedCategoryMeta?.status || "unknown"}
                    </span>
                    <button
                      type="button"
                      onClick={handleRunCategory}
                      disabled={Boolean(activeCategoryRun) || launchingRunKey === `category:${selectedCategory}`}
                      className="rounded-full border border-app px-4 py-2 text-sm font-semibold text-app-secondary transition hover:bg-white/5 hover:text-app disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {activeCategoryRun ? "Category running" : launchingRunKey === `category:${selectedCategory}` ? "Starting..." : "Run Category"}
                    </button>
                  </div>
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
      </div>
    </div>
  );
}
