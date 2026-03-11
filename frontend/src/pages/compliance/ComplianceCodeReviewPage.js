import { useState } from "react";
import { Button } from "../../components/button";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import RecordTable from "../../components/compliance/RecordTable";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, statusTone } from "./utils";

const initialReview = {
  title: "",
  summary: "",
  review_type: "internal_change",
  status: "Draft",
  risk_level: "medium",
  assigned_reviewer_employee_id: "",
  target_release: "",
  prompt_text: "",
  design_notes: "",
  code_notes: "",
  files_impacted: "",
  testing_notes: "",
  security_review_notes: "",
  privacy_review_notes: "",
  reviewer_comments: "",
};

export default function ComplianceCodeReviewPage() {
  const workspace = useCompliancePageContext();
  const reviews = workspace.data?.codeReviews?.code_reviews || [];
  const employees = workspace.data?.directory?.employees || [];
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [reviewerFilter, setReviewerFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [releaseFilter, setReleaseFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedReview, setSelectedReview] = useState(null);
  const [form, setForm] = useState(initialReview);
  const [error, setError] = useState(null);

  const filteredReviews = reviews.filter((item) => {
    const matchesSearch = !search || `${item.record.title} ${item.review.summary}`.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = !statusFilter || item.record.status === statusFilter;
    const matchesReviewer = !reviewerFilter || String(item.review.assigned_reviewer_employee_id || "") === reviewerFilter;
    const matchesRisk = !riskFilter || item.review.risk_level === riskFilter;
    const matchesRelease = !releaseFilter || (item.review.target_release || "").toLowerCase().includes(releaseFilter.toLowerCase());
    const matchesType = !typeFilter || item.review.review_type === typeFilter;
    return matchesSearch && matchesStatus && matchesReviewer && matchesRisk && matchesRelease && matchesType;
  });

  async function createReview(event) {
    event.preventDefault();
    setError(null);
    try {
      await workspace.createCodeReview({
        ...form,
        assigned_reviewer_employee_id: form.assigned_reviewer_employee_id ? Number(form.assigned_reviewer_employee_id) : null,
        files_impacted: form.files_impacted.split(",").map((item) => item.trim()).filter(Boolean),
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

  async function updateSelectedReview(payload) {
    if (!selectedReview) {
      return;
    }
    setError(null);
    try {
      await workspace.updateCodeReview(selectedReview.review.id, payload);
      setSelectedReview((current) => ({
        ...current,
        record: { ...current.record, ...("status" in payload ? { status: payload.status } : {}) },
        review: { ...current.review, ...payload, ...(payload.files_impacted ? { files_impacted: payload.files_impacted } : {}) },
      }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function recordDecision(decision) {
    if (!selectedReview) {
      return;
    }
    setError(null);
    try {
      await workspace.decideCodeReview(selectedReview.review.id, {
        decision,
        reviewer_comments: selectedReview.review.reviewer_comments || `${decision} from workspace.`,
      });
      const statusMap = {
        Approve: "Approved",
        "Request Changes": "Changes Requested",
        Block: "Blocked",
        "Mark Ready for Production": "Ready for Production",
      };
      setSelectedReview((current) => ({
        ...current,
        record: { ...current.record, status: statusMap[decision] || current.record.status },
        review: {
          ...current.review,
          reviewer_decision: decision,
          approved_at: decision === "Approve" ? new Date().toISOString() : current.review.approved_at,
        },
      }));
    } catch (err) {
      setError(err.message);
    }
  }

  const timeline = selectedReview ? workspace.timelineCache[selectedReview.record.id]?.timeline : null;
  const reviewerName = (employeeId) => {
    const employee = employees.find((item) => item.id === employeeId);
    return employee ? `${employee.first_name} ${employee.last_name}` : employeeId || "Unassigned";
  };

  const columns = [
    { key: "title", label: "Review Title", render: (row) => <span className="font-semibold text-app">{row.record.title}</span> },
    { key: "reviewer", label: "Reviewer", render: (row) => reviewerName(row.review.assigned_reviewer_employee_id) },
    { key: "status", label: "Status", render: (row) => <span className={statusTone(row.record.status)}>{row.record.status}</span> },
    { key: "risk", label: "Risk Level", render: (row) => <span className={statusTone(row.review.risk_level)}>{row.review.risk_level}</span> },
    { key: "release", label: "Target Release", render: (row) => row.review.target_release || "Not set" },
    { key: "updated", label: "Last Updated", render: (row) => formatDateTime(row.record.updated_at) },
  ];

  return (
    <div className="space-y-6">
      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Code Review</h2>
            <p className="mt-2 text-sm text-app-secondary">Centralized pre-production review for internal changes, prompt-driven implementations, security review, privacy review, and release decisions.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search reviews" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} placeholder="Status" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={reviewerFilter} onChange={(event) => setReviewerFilter(event.target.value)} placeholder="Reviewer ID" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)} placeholder="Risk level" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={releaseFilter} onChange={(event) => setReleaseFilter(event.target.value)} placeholder="Target release" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} placeholder="Review type" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <Button onClick={() => setCreateOpen(true)}>Create Review</Button>
          </div>
        </div>
      </section>

      {filteredReviews.length ? (
        <RecordTable columns={columns} rows={filteredReviews} onRowClick={openReview} />
      ) : (
        <WorkspaceEmptyState title="No code reviews match" description="Adjust filters or create a new pre-production review record." action={<Button onClick={() => setCreateOpen(true)}>Create Review</Button>} />
      )}

      <DetailDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="Create Code Review" subtitle="Capture the change request, prompt, design, risk level, and release target in one review record.">
        <form className="space-y-4" onSubmit={createReview}>
          <label className="block text-sm text-app-secondary">Title<input required value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Summary<textarea required value={form.summary} onChange={(event) => setForm((current) => ({ ...current, summary: event.target.value }))} className="mt-2 min-h-24 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm text-app-secondary">Review Type<input value={form.review_type} onChange={(event) => setForm((current) => ({ ...current, review_type: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
            <label className="text-sm text-app-secondary">Risk Level<input value={form.risk_level} onChange={(event) => setForm((current) => ({ ...current, risk_level: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
            <label className="text-sm text-app-secondary">Assigned Reviewer ID<input value={form.assigned_reviewer_employee_id} onChange={(event) => setForm((current) => ({ ...current, assigned_reviewer_employee_id: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
            <label className="text-sm text-app-secondary">Target Release<input value={form.target_release} onChange={(event) => setForm((current) => ({ ...current, target_release: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          </div>
          <label className="block text-sm text-app-secondary">Prompt / Request<textarea required value={form.prompt_text} onChange={(event) => setForm((current) => ({ ...current, prompt_text: event.target.value }))} className="mt-2 min-h-28 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Proposed Design<textarea value={form.design_notes} onChange={(event) => setForm((current) => ({ ...current, design_notes: event.target.value }))} className="mt-2 min-h-28 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Files Impacted (comma-separated)<input value={form.files_impacted} onChange={(event) => setForm((current) => ({ ...current, files_impacted: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Testing Checklist<textarea value={form.testing_notes} onChange={(event) => setForm((current) => ({ ...current, testing_notes: event.target.value }))} className="mt-2 min-h-24 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Security Review<textarea value={form.security_review_notes} onChange={(event) => setForm((current) => ({ ...current, security_review_notes: event.target.value }))} className="mt-2 min-h-24 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Privacy Review<textarea value={form.privacy_review_notes} onChange={(event) => setForm((current) => ({ ...current, privacy_review_notes: event.target.value }))} className="mt-2 min-h-24 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <Button type="submit">Create Review</Button>
        </form>
      </DetailDrawer>

      <DetailDrawer
        open={Boolean(selectedReview)}
        onClose={() => setSelectedReview(null)}
        title={selectedReview?.record.title || "Code Review Detail"}
        subtitle={selectedReview ? `${selectedReview.review.review_type} · ${selectedReview.record.status} · risk ${selectedReview.review.risk_level}` : ""}
      >
        {selectedReview ? (
          <>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Summary</h3>
              <p className="mt-4 text-sm leading-7 text-app-secondary">{selectedReview.review.summary}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Prompt / Request</h3>
              <pre className="mt-4 whitespace-pre-wrap text-sm leading-7 text-app-secondary">{selectedReview.review.prompt_text || "No prompt text recorded."}</pre>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Proposed Design</h3>
              <p className="mt-4 text-sm leading-7 text-app-secondary">{selectedReview.review.design_notes || "No design notes recorded."}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Files Impacted</h3>
              <div className="mt-4 flex flex-wrap gap-2">
                {selectedReview.review.files_impacted?.length ? selectedReview.review.files_impacted.map((file) => <span key={file} className="rounded-full border border-app px-3 py-1 text-xs text-app-secondary">{file}</span>) : <p className="text-sm text-app-muted">No impacted files recorded.</p>}
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Testing Checklist</h3>
              <p className="mt-4 text-sm leading-7 text-app-secondary">{selectedReview.review.testing_notes || "No testing checklist recorded."}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Security Review</h3>
              <p className="mt-4 text-sm leading-7 text-app-secondary">{selectedReview.review.security_review_notes || "No security review notes recorded."}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Privacy Review</h3>
              <p className="mt-4 text-sm leading-7 text-app-secondary">{selectedReview.review.privacy_review_notes || "No privacy review notes recorded."}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Reviewer Comments</h3>
              <textarea
                value={selectedReview.review.reviewer_comments || ""}
                onChange={(event) => setSelectedReview((current) => ({ ...current, review: { ...current.review, reviewer_comments: event.target.value } }))}
                className="mt-4 min-h-28 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
              />
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => updateSelectedReview({ reviewer_comments: selectedReview.review.reviewer_comments, assigned_reviewer_employee_id: selectedReview.review.assigned_reviewer_employee_id, security_review_notes: selectedReview.review.security_review_notes, privacy_review_notes: selectedReview.review.privacy_review_notes })}>Save Notes</Button>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Decision</h3>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => recordDecision("Approve")}>Approve</Button>
                <Button onClick={() => recordDecision("Request Changes")}>Request Changes</Button>
                <Button onClick={() => recordDecision("Block")}>Block</Button>
                <Button onClick={() => recordDecision("Mark Ready for Production")}>Mark Ready for Production</Button>
              </div>
              <p className="mt-4 text-sm text-app-secondary">Current decision: <span className={statusTone(selectedReview.review.reviewer_decision || selectedReview.record.status)}>{selectedReview.review.reviewer_decision || selectedReview.record.status}</span></p>
              <p className="mt-2 text-xs text-app-muted">Reviewer: {reviewerName(selectedReview.review.assigned_reviewer_employee_id)} · Approved at {formatDateTime(selectedReview.review.approved_at)}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Audit History</h3>
              <div className="mt-4 space-y-3">
                {timeline?.activities?.length ? timeline.activities.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">{item.action}</p>
                    <p className="mt-1">{item.details || "No details"}</p>
                    <p className="mt-2 text-xs text-app-muted">{formatDateTime(item.created_at)}</p>
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
