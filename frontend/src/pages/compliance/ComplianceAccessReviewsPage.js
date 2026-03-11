import { useState } from "react";
import { Button } from "../../components/button";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import RecordTable from "../../components/compliance/RecordTable";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, statusTone } from "./utils";

const initialReview = { title: "", reviewed_employee_id: "", permissions_snapshot: "{\"admin\": false}", status: "pending" };

export default function ComplianceAccessReviewsPage() {
  const workspace = useCompliancePageContext();
  const reviews = workspace.data?.reviews?.access_reviews || [];
  const [decisionFilter, setDecisionFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedReview, setSelectedReview] = useState(null);
  const [form, setForm] = useState(initialReview);
  const [error, setError] = useState(null);

  const filteredReviews = reviews.filter((item) => {
    const matchesDecision = !decisionFilter || item.review.decision === decisionFilter;
    const matchesStatus = !statusFilter || item.record.status === statusFilter;
    return matchesDecision && matchesStatus;
  });

  async function createReview(event) {
    event.preventDefault();
    setError(null);
    try {
      await workspace.createAccessReview({
        ...form,
        reviewed_employee_id: Number(form.reviewed_employee_id),
        permissions_snapshot: JSON.parse(form.permissions_snapshot || "{}"),
      });
      setForm(initialReview);
      setCreateOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function openReview(item) {
    setSelectedReview(item);
    await workspace.loadRecordTimeline(item.record.id);
  }

  async function decideReview(decision) {
    if (!selectedReview) {
      return;
    }
    setError(null);
    try {
      await workspace.decideAccessReview(selectedReview.review.id, { decision, notes: `${decision} from workspace.` });
      setSelectedReview((current) => ({
        ...current,
        record: { ...current.record, status: "completed" },
        review: { ...current.review, decision, reviewed_at: new Date().toISOString() },
      }));
    } catch (err) {
      setError(err.message);
    }
  }

  const timeline = selectedReview ? workspace.timelineCache[selectedReview.record.id]?.timeline : null;
  const columns = [
    { key: "title", label: "Review Name", render: (row) => <span className="font-semibold text-app">{row.record.title}</span> },
    { key: "reviewer", label: "Reviewer", render: (row) => row.review.reviewer_employee_id },
    { key: "reviewed", label: "Reviewed User", render: (row) => row.review.reviewed_employee_id },
    { key: "decision", label: "Decision", render: (row) => <span className={statusTone(row.review.decision)}>{row.review.decision}</span> },
    { key: "status", label: "Status", render: (row) => row.record.status },
    { key: "due", label: "Due Date", render: (row) => row.record.due_date || "Not set" },
    { key: "completed", label: "Completed At", render: (row) => formatDateTime(row.review.reviewed_at) },
  ];

  return (
    <div className="space-y-6">
      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Access Reviews</h2>
            <p className="mt-2 text-sm text-app-secondary">Review, approve, revoke, or flag internal access with auditable decision history.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <input value={decisionFilter} onChange={(event) => setDecisionFilter(event.target.value)} placeholder="Decision" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} placeholder="Status" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <Button onClick={() => setCreateOpen(true)}>Start Review</Button>
          </div>
        </div>
      </section>

      {filteredReviews.length ? <RecordTable columns={columns} rows={filteredReviews} onRowClick={openReview} /> : <WorkspaceEmptyState title="No access reviews match" description="Adjust filters or start a new review." action={<Button onClick={() => setCreateOpen(true)}>Start Review</Button>} />}

      <DetailDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="Start Access Review" subtitle="Create access governance records in a dedicated drawer.">
        <form className="space-y-4" onSubmit={createReview}>
          <label className="block text-sm text-app-secondary">Review Title<input required value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Reviewed Employee ID<input required type="number" value={form.reviewed_employee_id} onChange={(event) => setForm((current) => ({ ...current, reviewed_employee_id: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Permissions Snapshot<textarea value={form.permissions_snapshot} onChange={(event) => setForm((current) => ({ ...current, permissions_snapshot: event.target.value }))} className="mt-2 min-h-32 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <Button type="submit">Create Review</Button>
        </form>
      </DetailDrawer>

      <DetailDrawer open={Boolean(selectedReview)} onClose={() => setSelectedReview(null)} title={selectedReview?.record.title || "Access Review"} subtitle={selectedReview ? `Reviewed employee #${selectedReview.review.reviewed_employee_id}` : ""}>
        {selectedReview ? (
          <>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Current Permissions</h3>
              <pre className="mt-4 whitespace-pre-wrap rounded-2xl border border-app bg-app px-4 py-4 text-xs text-app-secondary">{JSON.stringify(selectedReview.review.permissions_snapshot, null, 2)}</pre>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Decision Actions</h3>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => decideReview("approved")}>Approve</Button>
                <Button onClick={() => decideReview("revoked")}>Revoke</Button>
                <Button onClick={() => decideReview("flagged")}>Flag</Button>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Decision Log</h3>
              <p className={`mt-4 text-sm font-medium ${statusTone(selectedReview.review.decision)}`}>{selectedReview.review.decision}</p>
              <p className="mt-2 text-sm text-app-secondary">{formatDateTime(selectedReview.review.reviewed_at)}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Audit History</h3>
              <div className="mt-4 space-y-3">
                {timeline?.activities?.length ? timeline.activities.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">{item.action}</p>
                    <p className="mt-1">{item.details || "No details"}</p>
                  </div>
                )) : <p className="text-sm text-app-muted">No audit history yet.</p>}
              </div>
            </section>
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
