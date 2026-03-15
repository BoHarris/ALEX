import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Button } from "../../components/button";
import ComplianceHeader from "../../components/compliance/ComplianceHeader";
import ComplianceTabNav from "../../components/compliance/ComplianceTabNav";
import CreateTaskModal from "../../components/compliance/tasks/CreateTaskModal";
import { useComplianceWorkspace } from "../../hooks/useComplianceWorkspace";

export default function ComplianceLayout() {
  const workspace = useComplianceWorkspace(true);
  const { data, loading, error } = workspace;
  const [createTaskOpen, setCreateTaskOpen] = useState(false);

  if (loading) {
    return <div className="page-shell px-6 py-12 text-app">Loading compliance workspace...</div>;
  }

  if (error) {
    return (
      <div className="page-shell px-6 py-12 text-app">
        <div className="surface-card rounded-3xl p-6">
          <p className="text-rose-600">{error.message}</p>
          <Button className="mt-4" onClick={workspace.reload}>Retry workspace load</Button>
        </div>
      </div>
    );
  }

  const organizationName = data?.overview?.organization?.name || data?.me?.organization_name || "Compliance Workspace";

  return (
    <div className="page-shell px-4 py-8 text-app sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <ComplianceHeader
          title="Internal Governance Platform"
          organizationName={organizationName}
          description="A route-backed compliance command center for policy governance, workforce controls, incident operations, risk tracking, training, testing evidence, and audit visibility."
          actions={(
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => setCreateTaskOpen(true)}>Create Task</Button>
              <Button onClick={workspace.reload}>Refresh data</Button>
            </div>
          )}
        />
        <ComplianceTabNav />
        <CreateTaskModal
          open={createTaskOpen}
          onClose={() => setCreateTaskOpen(false)}
          onSubmit={workspace.createTask}
          employees={data?.directory?.employees || []}
          title="Create Task"
          subtitle="Open a manual governance task without leaving the current workflow."
        />
        <Outlet context={workspace} />
      </div>
    </div>
  );
}
