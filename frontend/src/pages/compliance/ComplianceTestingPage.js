import { useEffect } from "react";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, statusTone } from "./utils";

export default function ComplianceTestingPage() {
  const { data, testCategoryDetail, selectedTestCase, loadTestCategory, loadTestCase } = useCompliancePageContext();
  const categories = data?.overview?.testing_summary;
  const categoryList = categories || [];

  useEffect(() => {
    if (!testCategoryDetail && categories?.length) {
      loadTestCategory(categories[0].category);
    }
  }, [categories, loadTestCategory, testCategoryDetail]);

  return (
    <div className="grid gap-6 xl:grid-cols-[260px_minmax(0,1fr)_minmax(320px,0.8fr)]">
      <section className="surface-card rounded-3xl p-5">
        <h2 className="text-lg font-semibold text-app">Test Categories</h2>
        <div className="mt-4 space-y-3">
          {categoryList.length ? categoryList.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => loadTestCategory(item.category)}
              className={`w-full rounded-2xl border border-app p-4 text-left hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${testCategoryDetail?.category === item.category ? "bg-white/5" : ""}`}
            >
              <p className="font-semibold text-app">{item.category}</p>
              <p className="mt-1 text-sm text-app-secondary">{item.suite_name}</p>
              <p className={`mt-2 text-xs font-medium ${statusTone(item.status)}`}>{item.status}</p>
            </button>
          )) : <p className="text-sm text-app-muted">No test categories available.</p>}
        </div>
      </section>

      <section className="surface-card rounded-3xl p-5">
        {testCategoryDetail ? (
          <>
            <div className="rounded-2xl border border-app p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-app-muted">Category Summary</p>
              <h2 className="mt-2 text-2xl font-semibold text-app">{testCategoryDetail.category}</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Total</p><p className="mt-1 text-lg font-semibold text-app">{testCategoryDetail.summary.total_tests}</p></div>
                <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Passed</p><p className="mt-1 text-lg font-semibold text-emerald-600">{testCategoryDetail.summary.passing}</p></div>
                <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Failed</p><p className="mt-1 text-lg font-semibold text-rose-600">{testCategoryDetail.summary.failing}</p></div>
                <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Skipped</p><p className="mt-1 text-lg font-semibold text-amber-600">{testCategoryDetail.summary.skipped}</p></div>
                <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Pass Rate</p><p className="mt-1 text-lg font-semibold text-app">{testCategoryDetail.summary.pass_rate}%</p></div>
                <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Last Run</p><p className="mt-1 text-sm font-medium text-app-secondary">{formatDateTime(testCategoryDetail.summary.last_run_timestamp)}</p></div>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              {testCategoryDetail.tests.map((test) => (
                <button
                  key={test.id}
                  type="button"
                  onClick={() => loadTestCase(test.id)}
                  className={`w-full rounded-2xl border border-app p-4 text-left hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${selectedTestCase?.id === test.id ? "bg-white/5" : ""}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-app">{test.test_name}</p>
                      <p className="mt-1 text-sm text-app-secondary">{test.file_name || "Unknown file"}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-semibold ${statusTone(test.status)}`}>{test.status}</p>
                      <p className="mt-1 text-xs text-app-muted">{test.duration_ms ?? "?"} ms</p>
                    </div>
                  </div>
                  <p className="mt-3 text-sm text-app-secondary">{test.description}</p>
                </button>
              ))}
            </div>
          </>
        ) : (
          <WorkspaceEmptyState title="No category selected" description="Choose a test category to inspect individual test runs and evidence." />
        )}
      </section>

      <section className="surface-card rounded-3xl p-5">
        {selectedTestCase ? (
          <>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-app-muted">Selected Test</p>
            <h2 className="mt-2 text-2xl font-semibold text-app">{selectedTestCase.test_name}</h2>
            <p className="mt-2 text-sm text-app-secondary">
              {selectedTestCase.category} · {selectedTestCase.suite_name} · <span className={statusTone(selectedTestCase.status)}>{selectedTestCase.status}</span>
            </p>
            <div className="mt-5 space-y-4 text-sm text-app-secondary">
              <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Last Execution</p><p className="mt-1">{formatDateTime(selectedTestCase.last_execution_time)}</p></div>
              <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">File</p><p className="mt-1">{selectedTestCase.file_name || "Unknown file"}</p></div>
              <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Duration</p><p className="mt-1">{selectedTestCase.duration_ms ?? "Not recorded"} ms</p></div>
              <div><p className="text-xs uppercase tracking-[0.18em] text-app-muted">Description</p><p className="mt-1 leading-7">{selectedTestCase.description}</p></div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-app-muted">Output</p>
                <pre className="mt-2 overflow-x-auto rounded-2xl border border-app bg-app px-4 py-4 whitespace-pre-wrap text-xs text-app-secondary">{selectedTestCase.output || "No output captured."}</pre>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-app-muted">Failure Message</p>
                <pre className="mt-2 overflow-x-auto rounded-2xl border border-rose-300/40 bg-rose-500/10 px-4 py-4 whitespace-pre-wrap text-xs text-rose-700">{selectedTestCase.error_message || "No failure recorded."}</pre>
              </div>
            </div>
          </>
        ) : (
          <WorkspaceEmptyState title="Select a test case" description="Choose a test from the center panel to inspect output, failure details, and execution evidence." />
        )}
      </section>
    </div>
  );
}
