import { useState } from "react";
import { Button } from "../../components/button";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import RecordTable from "../../components/compliance/RecordTable";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, statusTone } from "./utils";

const initialIncident = { title: "", severity: "medium", description: "", status: "open" };

export default function ComplianceIncidentsPage() {
  const workspace = useCompliancePageContext();
  const incidents = workspace.data?.incidents?.incidents || [];
  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [form, setForm] = useState(initialIncident);
  const [error, setError] = useState(null);

  const filteredIncidents = incidents.filter((item) => {
    const matchesSeverity = !severityFilter || item.incident.severity === severityFilter;
    const matchesStatus = !statusFilter || item.record.status === statusFilter;
    const matchesOwner = !ownerFilter || String(item.incident.assigned_to_employee_id || "") === ownerFilter;
    return matchesSeverity && matchesStatus && matchesOwner;
  });

  async function createIncident(event) {
    event.preventDefault();
    setError(null);
    try {
      await workspace.createIncident(form);
      setForm(initialIncident);
      setCreateOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function openIncident(item) {
    setSelectedIncident(item);
    await workspace.loadRecordTimeline(item.record.id);
  }

  async function updateIncident(payload) {
    if (!selectedIncident) {
      return;
    }
    setError(null);
    try {
      await workspace.updateIncident(selectedIncident.incident.id, payload);
      setSelectedIncident((current) => ({
        ...current,
        record: { ...current.record, ...("status" in payload ? { status: payload.status } : {}) },
        incident: { ...current.incident, ...payload, ...(payload.status === "closed" ? { closed_at: new Date().toISOString() } : {}) },
      }));
    } catch (err) {
      setError(err.message);
    }
  }

  const timeline = selectedIncident ? workspace.timelineCache[selectedIncident.record.id]?.timeline : null;
  const columns = [
    { key: "record", label: "ID", render: (row) => <span className="text-app-muted">INC-{row.incident.id}</span> },
    { key: "title", label: "Title", render: (row) => <span className="font-semibold text-app">{row.record.title}</span> },
    { key: "severity", label: "Severity", render: (row) => <span className={statusTone(row.incident.severity)}>{row.incident.severity}</span> },
    { key: "status", label: "Status", render: (row) => <span className={statusTone(row.record.status)}>{row.record.status}</span> },
    { key: "owner", label: "Owner", render: (row) => row.incident.assigned_to_employee_id || "Unassigned" },
    { key: "detected", label: "Detected At", render: (row) => formatDateTime(row.incident.detected_at) },
    { key: "updated", label: "Last Updated", render: (row) => formatDateTime(row.record.updated_at) },
  ];

  return (
    <div className="space-y-6">
      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Incidents</h2>
            <p className="mt-2 text-sm text-app-secondary">Serious operational incident management with status transitions and response history.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <input value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)} placeholder="Filter severity" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} placeholder="Filter status" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)} placeholder="Filter owner ID" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <Button onClick={() => setCreateOpen(true)}>Log Incident</Button>
          </div>
        </div>
      </section>

      {filteredIncidents.length ? <RecordTable columns={columns} rows={filteredIncidents} onRowClick={openIncident} /> : <WorkspaceEmptyState title="No incidents match" description="Adjust filters or log a new incident." action={<Button onClick={() => setCreateOpen(true)}>Log Incident</Button>} />}

      <DetailDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="Log Incident" subtitle="Create incidents in a dedicated panel, not inside the dashboard grid.">
        <form className="space-y-4" onSubmit={createIncident}>
          <label className="block text-sm text-app-secondary">Title<input required value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Severity<input required value={form.severity} onChange={(event) => setForm((current) => ({ ...current, severity: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Description<textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} className="mt-2 min-h-40 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <Button type="submit">Create Incident</Button>
        </form>
      </DetailDrawer>

      <DetailDrawer open={Boolean(selectedIncident)} onClose={() => setSelectedIncident(null)} title={selectedIncident?.record.title || "Incident Detail"} subtitle={selectedIncident ? `${selectedIncident.incident.severity} · ${selectedIncident.record.status}` : ""}>
        {selectedIncident ? (
          <>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Summary</h3>
              <p className="mt-4 text-sm leading-7 text-app-secondary">{selectedIncident.incident.description}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Actions</h3>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => updateIncident({ status: "investigating" })}>Investigating</Button>
                <Button onClick={() => updateIncident({ status: "contained" })}>Contained</Button>
                <Button onClick={() => updateIncident({ status: "resolved", resolution_notes: "Resolution documented." })}>Resolve</Button>
                <Button onClick={() => updateIncident({ status: "closed", resolution_notes: "Closed from workspace." })}>Close Incident</Button>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Investigation Notes</h3>
              <p className="mt-4 text-sm text-app-secondary">{selectedIncident.incident.resolution_notes || "No investigation notes yet."}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Root Cause</h3>
              <p className="mt-4 text-sm text-app-secondary">{selectedIncident.incident.root_cause || "Root cause not documented yet."}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Lessons Learned</h3>
              <p className="mt-4 text-sm text-app-secondary">{selectedIncident.incident.lessons_learned || "Lessons learned not documented yet."}</p>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Timeline</h3>
              <div className="mt-4 space-y-3">
                {timeline?.activities?.length ? timeline.activities.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">{item.action}</p>
                    <p className="mt-1">{item.details || "No details"}</p>
                    <p className="mt-2 text-xs text-app-muted">{formatDateTime(item.created_at)}</p>
                  </div>
                )) : <p className="text-sm text-app-muted">No incident timeline entries yet.</p>}
              </div>
            </section>
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
