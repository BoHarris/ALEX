import { useState } from "react";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import RecordTable from "../../components/compliance/RecordTable";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime } from "./utils";

export default function ComplianceAuditLogPage() {
  const { data } = useCompliancePageContext();
  const events = data?.auditLog?.events || [];
  const [actorFilter, setActorFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [resourceFilter, setResourceFilter] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [selectedEvent, setSelectedEvent] = useState(null);

  const filteredEvents = events.filter((event) => {
    const matchesActor = !actorFilter || `${event.actor_name || ""} ${event.actor_email || ""}`.toLowerCase().includes(actorFilter.toLowerCase());
    const matchesAction = !actionFilter || event.action.toLowerCase().includes(actionFilter.toLowerCase());
    const matchesResource = !resourceFilter || (event.resource_type || "").toLowerCase().includes(resourceFilter.toLowerCase());
    const matchesDate = !dateFilter || (event.timestamp || "").includes(dateFilter);
    return matchesActor && matchesAction && matchesResource && matchesDate;
  });

  const columns = [
    { key: "timestamp", label: "Timestamp", render: (row) => formatDateTime(row.timestamp) },
    { key: "actor", label: "Actor", render: (row) => row.actor_name || row.actor_email || "System" },
    { key: "action", label: "Action" },
    { key: "resource_type", label: "Resource", render: (row) => row.resource_type || "N/A" },
    { key: "resource_id", label: "Resource ID", render: (row) => row.resource_id || "N/A" },
    { key: "outcome", label: "Outcome" },
    { key: "details", label: "Details", render: (row) => typeof row.details === "string" ? row.details : JSON.stringify(row.details || {}) },
  ];

  return (
    <div className="space-y-6">
      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Audit Log</h2>
            <p className="mt-2 text-sm text-app-secondary">Filterable compliance traceability across employees, policies, incidents, reviews, training, and risks.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <input value={actorFilter} onChange={(event) => setActorFilter(event.target.value)} placeholder="Actor" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={actionFilter} onChange={(event) => setActionFilter(event.target.value)} placeholder="Action" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={resourceFilter} onChange={(event) => setResourceFilter(event.target.value)} placeholder="Resource type" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} placeholder="Date" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
          </div>
        </div>
      </section>

      {filteredEvents.length ? <RecordTable columns={columns} rows={filteredEvents} onRowClick={setSelectedEvent} /> : <WorkspaceEmptyState title="No audit events match" description="Adjust filters to review actor, action, resource, or timestamp history." />}

      <DetailDrawer open={Boolean(selectedEvent)} onClose={() => setSelectedEvent(null)} title={selectedEvent?.action || "Audit Event"} subtitle={selectedEvent ? `${selectedEvent.actor_name || selectedEvent.actor_email || "System"} · ${formatDateTime(selectedEvent.timestamp)}` : ""}>
        {selectedEvent ? (
          <>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Event Details</h3>
              <div className="mt-4 grid gap-3 text-sm text-app-secondary">
                <p><span className="text-app-muted">Action:</span> {selectedEvent.action}</p>
                <p><span className="text-app-muted">Category:</span> {selectedEvent.category}</p>
                <p><span className="text-app-muted">Resource:</span> {selectedEvent.resource_type || "N/A"} #{selectedEvent.resource_id || "N/A"}</p>
                <p><span className="text-app-muted">Outcome:</span> {selectedEvent.outcome}</p>
                <p><span className="text-app-muted">IP Address:</span> {selectedEvent.ip_address || "Not captured"}</p>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Payload</h3>
              <pre className="mt-4 whitespace-pre-wrap rounded-2xl border border-app bg-app px-4 py-4 text-xs text-app-secondary">{JSON.stringify(selectedEvent.details, null, 2)}</pre>
            </section>
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
