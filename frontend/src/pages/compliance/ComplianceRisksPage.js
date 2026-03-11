import { useState } from "react";
import { Button } from "../../components/button";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import RecordTable from "../../components/compliance/RecordTable";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDate, formatDateTime, statusTone } from "./utils";

const initialRisk = { title: "", risk_title: "", description: "", risk_category: "Security", likelihood: 3, impact: 3, mitigation_plan: "", status: "active" };

export default function ComplianceRisksPage() {
  const workspace = useCompliancePageContext();
  const risks = workspace.data?.risks?.risks || [];
  const [ownerFilter, setOwnerFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [scoreFilter, setScoreFilter] = useState("");
  const [reviewFilter, setReviewFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedRisk, setSelectedRisk] = useState(null);
  const [form, setForm] = useState(initialRisk);
  const [error, setError] = useState(null);

  const filteredRisks = risks.filter((item) => {
    const matchesOwner = !ownerFilter || String(item.risk.owner_employee_id || "") === ownerFilter;
    const matchesCategory = !categoryFilter || item.risk.risk_category === categoryFilter;
    const matchesScore = !scoreFilter || item.risk.risk_score >= Number(scoreFilter);
    const matchesReview = !reviewFilter || (item.risk.review_date || "").includes(reviewFilter);
    return matchesOwner && matchesCategory && matchesScore && matchesReview;
  });

  async function createRisk(event) {
    event.preventDefault();
    setError(null);
    try {
      await workspace.createRisk({ ...form, likelihood: Number(form.likelihood), impact: Number(form.impact) });
      setForm(initialRisk);
      setCreateOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function openRisk(item) {
    setSelectedRisk(item);
    await workspace.loadRecordTimeline(item.record.id);
  }

  async function updateRisk(payload) {
    if (!selectedRisk) {
      return;
    }
    setError(null);
    try {
      await workspace.updateRisk(selectedRisk.risk.id, payload);
      setSelectedRisk((current) => ({
        ...current,
        record: { ...current.record, ...("status" in payload ? { status: payload.status } : {}) },
        risk: {
          ...current.risk,
          ...payload,
          likelihood: payload.likelihood ?? current.risk.likelihood,
          impact: payload.impact ?? current.risk.impact,
          risk_score: (payload.likelihood ?? current.risk.likelihood) * (payload.impact ?? current.risk.impact),
        },
      }));
    } catch (err) {
      setError(err.message);
    }
  }

  const timeline = selectedRisk ? workspace.timelineCache[selectedRisk.record.id]?.timeline : null;
  const columns = [
    { key: "risk_title", label: "Risk Title", render: (row) => <span className="font-semibold text-app">{row.risk.risk_title}</span> },
    { key: "risk_category", label: "Category", render: (row) => row.risk.risk_category },
    { key: "likelihood", label: "Likelihood", render: (row) => row.risk.likelihood },
    { key: "impact", label: "Impact", render: (row) => row.risk.impact },
    { key: "risk_score", label: "Risk Score", render: (row) => <span className={statusTone(row.risk.risk_score >= 12 ? "high" : "active")}>{row.risk.risk_score}</span> },
    { key: "owner", label: "Owner", render: (row) => row.risk.owner_employee_id || "Unassigned" },
    { key: "review_date", label: "Review Date", render: (row) => formatDate(row.risk.review_date) },
    { key: "status", label: "Status", render: (row) => row.record.status },
  ];

  return (
    <div className="space-y-6">
      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Risks</h2>
            <p className="mt-2 text-sm text-app-secondary">Centralized risk register with score-driven prioritization and review tracking.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <input value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)} placeholder="Owner ID" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} placeholder="Category" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={scoreFilter} onChange={(event) => setScoreFilter(event.target.value)} placeholder="Min score" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value)} placeholder="Review date" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <Button onClick={() => setCreateOpen(true)}>Add Risk</Button>
          </div>
        </div>
      </section>

      {filteredRisks.length ? <RecordTable columns={columns} rows={filteredRisks} onRowClick={openRisk} /> : <WorkspaceEmptyState title="No risks match" description="Adjust filters or add a new risk item." action={<Button onClick={() => setCreateOpen(true)}>Add Risk</Button>} />}

      <DetailDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="Add Risk" subtitle="Capture new risk register items in a dedicated drawer.">
        <form className="grid gap-4 md:grid-cols-2" onSubmit={createRisk}>
          <label className="text-sm text-app-secondary">Record Title<input required value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Risk Title<input required value={form.risk_title} onChange={(event) => setForm((current) => ({ ...current, risk_title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Category<input required value={form.risk_category} onChange={(event) => setForm((current) => ({ ...current, risk_category: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Likelihood<input type="number" required value={form.likelihood} onChange={(event) => setForm((current) => ({ ...current, likelihood: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Impact<input type="number" required value={form.impact} onChange={(event) => setForm((current) => ({ ...current, impact: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="md:col-span-2 text-sm text-app-secondary">Description<textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} className="mt-2 min-h-28 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="md:col-span-2 text-sm text-app-secondary">Mitigation Plan<textarea value={form.mitigation_plan} onChange={(event) => setForm((current) => ({ ...current, mitigation_plan: event.target.value }))} className="mt-2 min-h-28 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          {error ? <p className="md:col-span-2 text-sm text-rose-600">{error}</p> : null}
          <div className="md:col-span-2"><Button type="submit">Create Risk</Button></div>
        </form>
      </DetailDrawer>

      <DetailDrawer open={Boolean(selectedRisk)} onClose={() => setSelectedRisk(null)} title={selectedRisk?.risk.risk_title || "Risk Detail"} subtitle={selectedRisk ? `${selectedRisk.risk.risk_category} · Score ${selectedRisk.risk.risk_score}` : ""}>
        {selectedRisk ? (
          <>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Description</h3>
              <p className="mt-4 text-sm leading-7 text-app-secondary">{selectedRisk.risk.description}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Impact & Likelihood</h3>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => updateRisk({ likelihood: Math.min(selectedRisk.risk.likelihood + 1, 5) })}>Increase Likelihood</Button>
                <Button onClick={() => updateRisk({ impact: Math.min(selectedRisk.risk.impact + 1, 5) })}>Increase Impact</Button>
                <Button onClick={() => updateRisk({ status: selectedRisk.record.status === "archived" ? "active" : "archived" })}>{selectedRisk.record.status === "archived" ? "Restore" : "Archive"}</Button>
              </div>
              <p className="mt-4 text-sm text-app-secondary">Current score: {selectedRisk.risk.risk_score}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Mitigation Plan</h3>
              <p className="mt-4 text-sm text-app-secondary">{selectedRisk.risk.mitigation_plan || "No mitigation plan recorded."}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Review History</h3>
              <div className="mt-4 space-y-3">
                {timeline?.activities?.length ? timeline.activities.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">{item.action}</p>
                    <p className="mt-1">{item.details || "No details"}</p>
                    <p className="mt-2 text-xs text-app-muted">{formatDateTime(item.created_at)}</p>
                  </div>
                )) : <p className="text-sm text-app-muted">No review history yet.</p>}
              </div>
            </section>
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
