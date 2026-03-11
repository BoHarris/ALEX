import { useState } from "react";
import { Button } from "../../components/button";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import RecordTable from "../../components/compliance/RecordTable";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDate, formatDateTime, statusTone } from "./utils";

const initialVendor = { title: "", vendor_name: "", service_category: "", data_access_level: "restricted", risk_rating: "medium", security_review_status: "pending", notes: "" };

export default function ComplianceVendorsPage() {
  const workspace = useCompliancePageContext();
  const vendors = workspace.data?.vendors?.vendors || [];
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [reviewFilter, setReviewFilter] = useState("");
  const [contractFilter, setContractFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState(null);
  const [form, setForm] = useState(initialVendor);
  const [error, setError] = useState(null);

  const filteredVendors = vendors.filter((item) => {
    const contractStatus = item.vendor.contract_end_date && new Date(item.vendor.contract_end_date) < new Date() ? "expired" : "active";
    const matchesSearch = !search || item.vendor.vendor_name.toLowerCase().includes(search.toLowerCase());
    const matchesRisk = !riskFilter || item.vendor.risk_rating === riskFilter;
    const matchesReview = !reviewFilter || item.vendor.security_review_status === reviewFilter;
    const matchesContract = !contractFilter || contractStatus === contractFilter;
    return matchesSearch && matchesRisk && matchesReview && matchesContract;
  });

  async function createVendor(event) {
    event.preventDefault();
    setError(null);
    try {
      await workspace.createVendor({ ...form, document_links: [] });
      setForm(initialVendor);
      setCreateOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function openVendor(item) {
    setSelectedVendor(item);
    await workspace.loadRecordTimeline(item.record.id);
  }

  async function updateVendor(payload) {
    if (!selectedVendor) {
      return;
    }
    setError(null);
    try {
      await workspace.updateVendor(selectedVendor.vendor.id, payload);
      setSelectedVendor((current) => ({
        ...current,
        record: { ...current.record, ...("status" in payload ? { status: payload.status } : {}) },
        vendor: { ...current.vendor, ...payload },
      }));
    } catch (err) {
      setError(err.message);
    }
  }

  const timeline = selectedVendor ? workspace.timelineCache[selectedVendor.record.id]?.timeline : null;
  const columns = [
    { key: "vendor_name", label: "Vendor Name", render: (row) => <span className="font-semibold text-app">{row.vendor.vendor_name}</span> },
    { key: "service_category", label: "Category", render: (row) => row.vendor.service_category },
    { key: "data_access_level", label: "Data Access", render: (row) => row.vendor.data_access_level },
    { key: "risk_rating", label: "Risk Rating", render: (row) => <span className={statusTone(row.vendor.risk_rating)}>{row.vendor.risk_rating || "unrated"}</span> },
    { key: "security_review_status", label: "Review Status", render: (row) => row.vendor.security_review_status },
    { key: "contract_end_date", label: "Contract End", render: (row) => formatDate(row.vendor.contract_end_date) },
    { key: "last_review_date", label: "Last Review", render: (row) => formatDate(row.vendor.last_review_date) },
  ];

  return (
    <div className="space-y-6">
      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Vendors</h2>
            <p className="mt-2 text-sm text-app-secondary">Track vendor risk, contract timing, and review evidence.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search vendors" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)} placeholder="Risk rating" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value)} placeholder="Review status" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={contractFilter} onChange={(event) => setContractFilter(event.target.value)} placeholder="Contract status" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <Button onClick={() => setCreateOpen(true)}>Add Vendor</Button>
          </div>
        </div>
      </section>

      {filteredVendors.length ? <RecordTable columns={columns} rows={filteredVendors} onRowClick={openVendor} /> : <WorkspaceEmptyState title="No vendors match" description="Adjust filters or add a new vendor review record." action={<Button onClick={() => setCreateOpen(true)}>Add Vendor</Button>} />}

      <DetailDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="Add Vendor" subtitle="Create a vendor risk record in a dedicated drawer.">
        <form className="grid gap-4 md:grid-cols-2" onSubmit={createVendor}>
          <label className="text-sm text-app-secondary">Record Title<input required value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Vendor Name<input required value={form.vendor_name} onChange={(event) => setForm((current) => ({ ...current, vendor_name: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Service Category<input required value={form.service_category} onChange={(event) => setForm((current) => ({ ...current, service_category: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Data Access<input required value={form.data_access_level} onChange={(event) => setForm((current) => ({ ...current, data_access_level: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Risk Rating<input value={form.risk_rating} onChange={(event) => setForm((current) => ({ ...current, risk_rating: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Review Status<input value={form.security_review_status} onChange={(event) => setForm((current) => ({ ...current, security_review_status: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="md:col-span-2 text-sm text-app-secondary">Notes<textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} className="mt-2 min-h-32 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          {error ? <p className="md:col-span-2 text-sm text-rose-600">{error}</p> : null}
          <div className="md:col-span-2"><Button type="submit">Create Vendor</Button></div>
        </form>
      </DetailDrawer>

      <DetailDrawer open={Boolean(selectedVendor)} onClose={() => setSelectedVendor(null)} title={selectedVendor?.vendor.vendor_name || "Vendor Detail"} subtitle={selectedVendor ? `${selectedVendor.vendor.service_category} · ${selectedVendor.vendor.security_review_status}` : ""}>
        {selectedVendor ? (
          <>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Profile</h3>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm text-app-secondary">
                <p><span className="text-app-muted">Data access:</span> {selectedVendor.vendor.data_access_level}</p>
                <p><span className="text-app-muted">Risk rating:</span> <span className={statusTone(selectedVendor.vendor.risk_rating)}>{selectedVendor.vendor.risk_rating}</span></p>
                <p><span className="text-app-muted">Contract end:</span> {formatDate(selectedVendor.vendor.contract_end_date)}</p>
                <p><span className="text-app-muted">Last review:</span> {formatDate(selectedVendor.vendor.last_review_date)}</p>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Risk Review</h3>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => updateVendor({ security_review_status: "approved" })}>Approve</Button>
                <Button onClick={() => updateVendor({ security_review_status: "needs follow-up" })}>Needs Follow-up</Button>
                <Button onClick={() => updateVendor({ status: selectedVendor.record.status === "archived" ? "active" : "archived" })}>{selectedVendor.record.status === "archived" ? "Restore" : "Archive"}</Button>
              </div>
              <p className="mt-4 text-sm text-app-secondary">{selectedVendor.record.notes || "No review notes recorded."}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Linked Documents</h3>
              <div className="mt-4 space-y-2">
                {selectedVendor.vendor.document_links.length ? selectedVendor.vendor.document_links.map((link) => <a key={link} href={link} className="block text-sm text-cyan-500 underline" target="_blank" rel="noreferrer">{link}</a>) : <p className="text-sm text-app-muted">No linked documents recorded.</p>}
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Activity History</h3>
              <div className="mt-4 space-y-3">
                {timeline?.activities?.length ? timeline.activities.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">{item.action}</p>
                    <p className="mt-1">{item.details || "No details"}</p>
                    <p className="mt-2 text-xs text-app-muted">{formatDateTime(item.created_at)}</p>
                  </div>
                )) : <p className="text-sm text-app-muted">No activity history yet.</p>}
              </div>
            </section>
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
