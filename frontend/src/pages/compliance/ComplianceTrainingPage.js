import { useState } from "react";
import { Button } from "../../components/button";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, statusTone } from "./utils";

const initialModule = { title: "", description: "", category: "Security", document_link: "" };
const initialAssignment = { title: "", employee_id: "", training_module_id: "" };

export default function ComplianceTrainingPage() {
  const workspace = useCompliancePageContext();
  const modules = workspace.data?.modules?.modules || [];
  const assignments = workspace.data?.assignments?.assignments || [];
  const [statusFilter, setStatusFilter] = useState("");
  const [dueFilter, setDueFilter] = useState("");
  const [employeeFilter, setEmployeeFilter] = useState("");
  const [moduleOpen, setModuleOpen] = useState(false);
  const [assignmentOpen, setAssignmentOpen] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [moduleForm, setModuleForm] = useState(initialModule);
  const [assignmentForm, setAssignmentForm] = useState(initialAssignment);
  const [error, setError] = useState(null);

  const filteredAssignments = assignments.filter((item) => {
    const matchesStatus = !statusFilter || item.assignment.completion_status === statusFilter;
    const matchesDue = !dueFilter || (item.assignment.due_date || "").includes(dueFilter);
    const matchesEmployee = !employeeFilter || String(item.assignment.employee_id) === employeeFilter;
    return matchesStatus && matchesDue && matchesEmployee;
  });

  async function createModule(event) {
    event.preventDefault();
    setError(null);
    try {
      await workspace.createTrainingModule(moduleForm);
      setModuleForm(initialModule);
      setModuleOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function assignTraining(event) {
    event.preventDefault();
    setError(null);
    try {
      await workspace.assignTraining({ ...assignmentForm, employee_id: Number(assignmentForm.employee_id), training_module_id: Number(assignmentForm.training_module_id) });
      setAssignmentForm(initialAssignment);
      setAssignmentOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function completeSelected() {
    if (!selectedAssignment) {
      return;
    }
    setError(null);
    try {
      await workspace.completeTraining(selectedAssignment.assignment.id, { completion_status: "completed" });
      setSelectedAssignment((current) => ({
        ...current,
        assignment: { ...current.assignment, completion_status: "completed", completed_at: new Date().toISOString() },
        record: { ...current.record, status: "completed" },
      }));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="space-y-6">
      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Training</h2>
            <p className="mt-2 text-sm text-app-secondary">Manage training modules, assignments, completion tracking, and overdue status.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <input value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} placeholder="Status" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={dueFilter} onChange={(event) => setDueFilter(event.target.value)} placeholder="Due date" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={employeeFilter} onChange={(event) => setEmployeeFilter(event.target.value)} placeholder="Employee ID" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <Button onClick={() => setModuleOpen(true)}>Create Training Module</Button>
            <Button onClick={() => setAssignmentOpen(true)}>Assign Training</Button>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="surface-card rounded-3xl p-6">
          <h3 className="text-lg font-semibold text-app">Training Modules</h3>
          <div className="mt-4 space-y-3">
            {modules.length ? modules.map((module) => (
              <div key={module.id} className="rounded-2xl border border-app p-4">
                <p className="font-semibold text-app">{module.title}</p>
                <p className="mt-1 text-sm text-app-secondary">{module.category}</p>
                <p className="mt-3 text-sm text-app-secondary">{module.description || "No description"}</p>
              </div>
            )) : <WorkspaceEmptyState title="No training modules" description="Create a module to start assigning workforce training." />}
          </div>
        </section>
        <section className="surface-card rounded-3xl p-6">
          <h3 className="text-lg font-semibold text-app">Assignments</h3>
          <div className="mt-4 space-y-3">
            {filteredAssignments.length ? filteredAssignments.map((item) => (
              <button key={item.assignment.id} type="button" onClick={() => setSelectedAssignment(item)} className="w-full rounded-2xl border border-app p-4 text-left hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300">
                <p className="font-semibold text-app">{item.record.title}</p>
                <p className="mt-1 text-sm text-app-secondary">Employee #{item.assignment.employee_id} · Module #{item.assignment.training_module_id}</p>
                <p className={`mt-2 text-sm font-medium ${statusTone(item.assignment.completion_status)}`}>{item.assignment.completion_status}</p>
                <p className="mt-2 text-xs text-app-muted">Due {formatDateTime(item.assignment.due_date)}</p>
              </button>
            )) : <WorkspaceEmptyState title="No assignments match" description="Adjust filters or assign a module to an employee." />}
          </div>
        </section>
      </div>

      <DetailDrawer open={moduleOpen} onClose={() => setModuleOpen(false)} title="Create Training Module" subtitle="Create modules in a dedicated drawer.">
        <form className="space-y-4" onSubmit={createModule}>
          <label className="block text-sm text-app-secondary">Title<input required value={moduleForm.title} onChange={(event) => setModuleForm((current) => ({ ...current, title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Category<input value={moduleForm.category} onChange={(event) => setModuleForm((current) => ({ ...current, category: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Description<textarea value={moduleForm.description} onChange={(event) => setModuleForm((current) => ({ ...current, description: event.target.value }))} className="mt-2 min-h-32 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Document Link<input value={moduleForm.document_link} onChange={(event) => setModuleForm((current) => ({ ...current, document_link: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <Button type="submit">Create Module</Button>
        </form>
      </DetailDrawer>

      <DetailDrawer open={assignmentOpen} onClose={() => setAssignmentOpen(false)} title="Assign Training" subtitle="Assign modules without embedding forms in the page header.">
        <form className="space-y-4" onSubmit={assignTraining}>
          <label className="block text-sm text-app-secondary">Assignment Title<input required value={assignmentForm.title} onChange={(event) => setAssignmentForm((current) => ({ ...current, title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Employee ID<input required type="number" value={assignmentForm.employee_id} onChange={(event) => setAssignmentForm((current) => ({ ...current, employee_id: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Training Module ID<input required type="number" value={assignmentForm.training_module_id} onChange={(event) => setAssignmentForm((current) => ({ ...current, training_module_id: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <Button type="submit">Assign Training</Button>
        </form>
      </DetailDrawer>

      <DetailDrawer open={Boolean(selectedAssignment)} onClose={() => setSelectedAssignment(null)} title={selectedAssignment?.record.title || "Training Assignment"} subtitle={selectedAssignment ? `Employee #${selectedAssignment.assignment.employee_id}` : ""}>
        {selectedAssignment ? (
          <>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Employee Training Detail</h3>
              <div className="mt-4 grid gap-3 text-sm text-app-secondary">
                <p><span className="text-app-muted">Assigned module:</span> #{selectedAssignment.assignment.training_module_id}</p>
                <p><span className="text-app-muted">Due date:</span> {formatDateTime(selectedAssignment.assignment.due_date)}</p>
                <p><span className="text-app-muted">Completed date:</span> {formatDateTime(selectedAssignment.assignment.completed_at)}</p>
                <p><span className="text-app-muted">Status:</span> <span className={statusTone(selectedAssignment.assignment.completion_status)}>{selectedAssignment.assignment.completion_status}</span></p>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Actions</h3>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={completeSelected}>Mark Complete</Button>
              </div>
            </section>
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
