import { useState } from "react";
import { Button } from "../../components/button";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import RecordTable from "../../components/compliance/RecordTable";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, statusTone } from "./utils";

const initialEmployee = { first_name: "", last_name: "", email: "", role: "operations_admin", department: "", job_title: "", status: "active" };

export default function ComplianceEmployeesPage() {
  const workspace = useCompliancePageContext();
  const employees = workspace.data?.directory?.employees || [];
  const assignments = workspace.data?.assignments?.assignments || [];
  const reviews = workspace.data?.reviews?.access_reviews || [];
  const auditEvents = workspace.data?.auditLog?.events || [];
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [form, setForm] = useState(initialEmployee);
  const [error, setError] = useState(null);

  const filteredEmployees = employees.filter((employee) => {
    const matchesSearch = !search || `${employee.first_name} ${employee.last_name} ${employee.email}`.toLowerCase().includes(search.toLowerCase());
    const matchesRole = !roleFilter || employee.role === roleFilter;
    const matchesDepartment = !departmentFilter || (employee.department || "") === departmentFilter;
    const matchesStatus = !statusFilter || employee.status === statusFilter;
    return matchesSearch && matchesRole && matchesDepartment && matchesStatus;
  });

  async function submitCreate(event) {
    event.preventDefault();
    setError(null);
    try {
      await workspace.createEmployee(form);
      setForm(initialEmployee);
      setCreateOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function updateSelected(payload) {
    if (!selectedEmployee) {
      return;
    }
    setError(null);
    try {
      await workspace.updateEmployee(selectedEmployee.id, payload);
      setSelectedEmployee((current) => ({ ...current, ...payload }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function deactivateSelected() {
    if (!selectedEmployee) {
      return;
    }
    setError(null);
    try {
      await workspace.deactivateEmployee(selectedEmployee.id);
      setSelectedEmployee((current) => ({ ...current, status: "inactive" }));
    } catch (err) {
      setError(err.message);
    }
  }

  const columns = [
    { key: "name", label: "Name", render: (row) => <div><p className="font-semibold text-app">{row.first_name} {row.last_name}</p><p className="text-xs text-app-muted">{row.employee_id}</p></div> },
    { key: "email", label: "Email" },
    { key: "role", label: "Role" },
    { key: "department", label: "Department", render: (row) => row.department || "Not set" },
    { key: "job_title", label: "Job Title", render: (row) => row.job_title || "Not set" },
    { key: "status", label: "Status", render: (row) => <span className={statusTone(row.status)}>{row.status}</span> },
    { key: "last_login", label: "Last Login", render: (row) => formatDateTime(row.last_login) },
  ];

  const selectedAssignments = selectedEmployee ? assignments.filter((item) => item.assignment.employee_id === selectedEmployee.id) : [];
  const selectedReviews = selectedEmployee ? reviews.filter((item) => item.review.reviewed_employee_id === selectedEmployee.id) : [];
  const selectedActivity = selectedEmployee
    ? auditEvents.filter((event) => event.resource_type === "employee" && String(event.resource_id) === String(selectedEmployee.id))
    : [];

  return (
    <div className="space-y-6">
      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Employees</h2>
            <p className="mt-2 text-sm text-app-secondary">{employees.length} employees in the internal directory.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search employees" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} placeholder="Filter role" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={departmentFilter} onChange={(event) => setDepartmentFilter(event.target.value)} placeholder="Filter department" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <input value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} placeholder="Filter status" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            <Button onClick={() => setCreateOpen(true)}>Add Employee</Button>
          </div>
        </div>
      </section>

      {filteredEmployees.length ? (
        <RecordTable columns={columns} rows={filteredEmployees} onRowClick={setSelectedEmployee} />
      ) : (
        <WorkspaceEmptyState title="No employees match" description="Adjust your filters or add a new employee to the directory." action={<Button onClick={() => setCreateOpen(true)}>Add Employee</Button>} />
      )}

      <DetailDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="Add Employee" subtitle="Create an internal employee record without placing the form directly on the page.">
        <form className="grid gap-4 md:grid-cols-2" onSubmit={submitCreate}>
          <label className="text-sm text-app-secondary">First Name<input required value={form.first_name} onChange={(event) => setForm((current) => ({ ...current, first_name: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Last Name<input required value={form.last_name} onChange={(event) => setForm((current) => ({ ...current, last_name: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Email<input required type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Role<input required value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Department<input value={form.department} onChange={(event) => setForm((current) => ({ ...current, department: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="text-sm text-app-secondary">Job Title<input value={form.job_title} onChange={(event) => setForm((current) => ({ ...current, job_title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          {error ? <p className="md:col-span-2 text-sm text-rose-600">{error}</p> : null}
          <div className="md:col-span-2"><Button type="submit">Create employee</Button></div>
        </form>
      </DetailDrawer>

      <DetailDrawer
        open={Boolean(selectedEmployee)}
        onClose={() => setSelectedEmployee(null)}
        title={selectedEmployee ? `${selectedEmployee.first_name} ${selectedEmployee.last_name}` : "Employee"}
        subtitle={selectedEmployee ? `${selectedEmployee.role} · ${selectedEmployee.department || "No department"}` : ""}
      >
        {selectedEmployee ? (
          <>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Profile</h3>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm text-app-secondary">
                <p><span className="text-app-muted">Email:</span> {selectedEmployee.email}</p>
                <p><span className="text-app-muted">Status:</span> <span className={statusTone(selectedEmployee.status)}>{selectedEmployee.status}</span></p>
                <p><span className="text-app-muted">Role:</span> {selectedEmployee.role}</p>
                <p><span className="text-app-muted">Last login:</span> {formatDateTime(selectedEmployee.last_login)}</p>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Actions</h3>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => updateSelected({ role: selectedEmployee.role === "security_admin" ? "operations_admin" : "security_admin" })}>Change Role</Button>
                <Button onClick={() => updateSelected({ status: selectedEmployee.status === "active" ? "inactive" : "active" })}>Toggle Status</Button>
                <Button onClick={deactivateSelected}>Deactivate Employee</Button>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Training Status</h3>
              <div className="mt-4 space-y-3">
                {selectedAssignments.length ? selectedAssignments.map((item) => (
                  <div key={item.assignment.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">{item.record.title}</p>
                    <p className="mt-1">{item.assignment.completion_status}</p>
                  </div>
                )) : <p className="text-sm text-app-muted">No training assigned.</p>}
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Access Reviews</h3>
              <div className="mt-4 space-y-3">
                {selectedReviews.length ? selectedReviews.map((item) => (
                  <div key={item.review.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">{item.record.title}</p>
                    <p className="mt-1">{item.review.decision}</p>
                  </div>
                )) : <p className="text-sm text-app-muted">No access reviews found.</p>}
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Activity History</h3>
              <div className="mt-4 space-y-3">
                {selectedActivity.length ? selectedActivity.map((event) => (
                  <div key={event.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">{event.action}</p>
                    <p className="mt-1 text-xs text-app-muted">{formatDateTime(event.timestamp)}</p>
                  </div>
                )) : <p className="text-sm text-app-muted">No employee-specific audit events yet.</p>}
              </div>
            </section>
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
