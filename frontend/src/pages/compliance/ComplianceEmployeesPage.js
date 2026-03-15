import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/button";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import RecordTable from "../../components/compliance/RecordTable";
import SummaryMetricCard from "../../components/compliance/SummaryMetricCard";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import LinkedTaskPill from "../../components/compliance/tasks/LinkedTaskPill";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, statusTone } from "./utils";

const COMMON_EMPLOYEE_ROLES = [
  "security_admin",
  "compliance_admin",
  "operations_admin",
  "engineering_lead",
];
const COMMON_EMPLOYEE_STATUSES = ["active", "inactive", "suspended"];

const initialEmployee = {
  first_name: "",
  last_name: "",
  email: "",
  role: "operations_admin",
  department: "",
  job_title: "",
  status: "active",
};

function uniqueSortedValues(values) {
  return Array.from(
    new Set(
      (values || [])
        .map((value) => (value == null ? "" : String(value).trim()))
        .filter(Boolean),
    ),
  ).sort((left, right) => left.localeCompare(right));
}

function normalizeEmployeeForm(form) {
  return {
    first_name: form.first_name.trim(),
    last_name: form.last_name.trim(),
    email: form.email.trim().toLowerCase(),
    role: form.role.trim(),
    department: form.department.trim(),
    job_title: form.job_title.trim(),
    status: (form.status || "active").trim() || "active",
  };
}

function EmployeeFilterSelect({
  value,
  onChange,
  options,
  placeholder,
  ariaLabel,
}) {
  return (
    <select
      aria-label={ariaLabel}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app"
    >
      <option value="">{placeholder}</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

export default function ComplianceEmployeesPage() {
  const navigate = useNavigate();
  const workspace = useCompliancePageContext();
  const employees = workspace.data?.directory?.employees || [];
  const tasks = workspace.data?.tasks?.tasks || [];
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
  const [createError, setCreateError] = useState(null);
  const [actionError, setActionError] = useState(null);

  const normalizedSearch = search.trim().toLowerCase();
  const roleOptions = uniqueSortedValues([
    ...COMMON_EMPLOYEE_ROLES,
    ...employees.map((employee) => employee.role),
  ]);
  const departmentOptions = uniqueSortedValues(
    employees.map((employee) => employee.department),
  );
  const statusOptions = uniqueSortedValues([
    ...COMMON_EMPLOYEE_STATUSES,
    ...employees.map((employee) => employee.status),
  ]);

  const filteredEmployees = employees.filter((employee) => {
    const searchableFields = [
      employee.first_name,
      employee.last_name,
      employee.email,
      employee.role,
      employee.department,
      employee.job_title,
      employee.employee_id,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesSearch =
      !normalizedSearch || searchableFields.includes(normalizedSearch);
    const matchesRole = !roleFilter || employee.role === roleFilter;
    const matchesDepartment =
      !departmentFilter || (employee.department || "") === departmentFilter;
    const matchesStatus = !statusFilter || employee.status === statusFilter;
    return (
      matchesSearch && matchesRole && matchesDepartment && matchesStatus
    );
  });

  const openEmployeeFollowups = tasks.filter(
    (task) => task.source_type === "employee_followup" && task.is_open,
  );
  const incompleteProfileCount = employees.filter(
    (employee) => !employee.department || !employee.job_title,
  ).length;
  const activeEmployeeCount = employees.filter(
    (employee) => employee.status === "active",
  ).length;
  const inactiveEmployeeCount = employees.filter(
    (employee) => employee.status === "inactive",
  ).length;
  const hasActiveFilters = Boolean(
    normalizedSearch || roleFilter || departmentFilter || statusFilter,
  );

  function openCreateDrawer() {
    setCreateError(null);
    setForm(initialEmployee);
    setCreateOpen(true);
  }

  function closeCreateDrawer() {
    setCreateOpen(false);
    setCreateError(null);
  }

  function openEmployeeDetail(employee) {
    setActionError(null);
    setSelectedEmployee(employee);
  }

  function closeEmployeeDetail() {
    setSelectedEmployee(null);
    setActionError(null);
  }

  function clearFilters() {
    setSearch("");
    setRoleFilter("");
    setDepartmentFilter("");
    setStatusFilter("");
  }

  async function submitCreate(event) {
    event.preventDefault();
    setCreateError(null);
    const normalizedForm = normalizeEmployeeForm(form);
    if (
      !normalizedForm.first_name ||
      !normalizedForm.last_name ||
      !normalizedForm.email ||
      !normalizedForm.role
    ) {
      setCreateError("Complete the required employee profile fields before saving.");
      return;
    }
    try {
      await workspace.createEmployee(normalizedForm);
      setForm(initialEmployee);
      closeCreateDrawer();
    } catch (err) {
      setCreateError(err.message);
    }
  }

  async function updateSelected(payload) {
    if (!selectedEmployee) {
      return;
    }
    setActionError(null);
    try {
      await workspace.updateEmployee(selectedEmployee.id, payload);
      setSelectedEmployee((current) => ({ ...current, ...payload }));
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function deactivateSelected() {
    if (!selectedEmployee) {
      return;
    }
    setActionError(null);
    try {
      await workspace.deactivateEmployee(selectedEmployee.id);
      setSelectedEmployee((current) => ({ ...current, status: "inactive" }));
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function createEmployeeTask() {
    if (!selectedEmployee) {
      return;
    }
    setActionError(null);
    try {
      await workspace.createTaskFromEmployee(selectedEmployee.id, {});
      navigate("/compliance/tasks");
    } catch (err) {
      setActionError(err.message);
    }
  }

  function employeeTasks(employeeId) {
    return tasks.filter(
      (task) =>
        task.source_type === "employee_followup" &&
        String(task.source_id) === String(employeeId),
    );
  }

  const columns = [
    {
      key: "name",
      label: "Name",
      render: (row) => (
        <div>
          <p className="font-semibold text-app">
            {row.first_name} {row.last_name}
          </p>
          <p className="text-xs text-app-muted">{row.employee_id}</p>
        </div>
      ),
    },
    { key: "email", label: "Email" },
    { key: "role", label: "Role" },
    {
      key: "department",
      label: "Department",
      render: (row) => row.department || "Not set",
    },
    {
      key: "job_title",
      label: "Job Title",
      render: (row) => row.job_title || "Not set",
    },
    { key: "tasks", label: "Tasks", render: (row) => employeeTasks(row.id).length },
    {
      key: "status",
      label: "Status",
      render: (row) => (
        <span className={statusTone(row.status)}>{row.status}</span>
      ),
    },
    {
      key: "last_login",
      label: "Last Login",
      render: (row) => formatDateTime(row.last_login),
    },
  ];

  const selectedAssignments = selectedEmployee
    ? assignments.filter(
        (item) => item.assignment.employee_id === selectedEmployee.id,
      )
    : [];
  const selectedReviews = selectedEmployee
    ? reviews.filter(
        (item) => item.review.reviewed_employee_id === selectedEmployee.id,
      )
    : [];
  const selectedActivity = selectedEmployee
    ? auditEvents.filter(
        (event) =>
          event.resource_type === "employee" &&
          String(event.resource_id) === String(selectedEmployee.id),
      )
    : [];
  const selectedTasks = selectedEmployee
    ? employeeTasks(selectedEmployee.id)
    : [];
  const selectedHasIncompleteProfile = Boolean(
    selectedEmployee &&
      (!selectedEmployee.department || !selectedEmployee.job_title),
  );

  return (
    <div className="space-y-6">
      <section className="surface-card rounded-3xl p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-app">Employees</h2>
            <p className="mt-2 text-sm text-app-secondary">
              {hasActiveFilters
                ? `Showing ${filteredEmployees.length} of ${employees.length} employees in the internal directory.`
                : `${employees.length} employees in the internal directory.`}
            </p>
          </div>
          <div className="w-full max-w-4xl space-y-3">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <input
                aria-label="Search employees"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search employees"
                className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app"
              />
              <EmployeeFilterSelect
                ariaLabel="Filter by role"
                value={roleFilter}
                onChange={setRoleFilter}
                options={roleOptions}
                placeholder="All roles"
              />
              <EmployeeFilterSelect
                ariaLabel="Filter by department"
                value={departmentFilter}
                onChange={setDepartmentFilter}
                options={departmentOptions}
                placeholder="All departments"
              />
              <EmployeeFilterSelect
                ariaLabel="Filter by status"
                value={statusFilter}
                onChange={setStatusFilter}
                options={statusOptions}
                placeholder="All statuses"
              />
            </div>
            <div className="flex flex-wrap justify-end gap-3">
              {hasActiveFilters ? (
                <Button onClick={clearFilters}>Clear Filters</Button>
              ) : null}
              <Button onClick={openCreateDrawer}>Add Employee</Button>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <SummaryMetricCard
          label="Directory"
          value={employees.length}
          hint="Current internal employee records"
        />
        <SummaryMetricCard
          label="Active"
          value={activeEmployeeCount}
          hint="Employees with active status"
        />
        <SummaryMetricCard
          label="Inactive"
          value={inactiveEmployeeCount}
          hint="Inactive directory records"
        />
        <SummaryMetricCard
          label="Incomplete Profiles"
          value={incompleteProfileCount}
          hint="Missing department or job title"
        />
        <SummaryMetricCard
          label="Open Follow-ups"
          value={openEmployeeFollowups.length}
          hint="Employee governance tasks still open"
        />
      </section>

      {filteredEmployees.length ? (
        <RecordTable
          columns={columns}
          rows={filteredEmployees}
          onRowClick={openEmployeeDetail}
        />
      ) : (
        <WorkspaceEmptyState
          title="No employees match"
          description="Adjust your filters or add a new employee to the directory."
          action={<Button onClick={openCreateDrawer}>Add Employee</Button>}
        />
      )}

      <DetailDrawer
        open={createOpen}
        onClose={closeCreateDrawer}
        title="Add Employee"
        subtitle="Create an internal employee record without placing the form directly on the page."
      >
        <form className="grid gap-4 md:grid-cols-2" onSubmit={submitCreate}>
          <label className="text-sm text-app-secondary">
            First Name
            <input
              required
              value={form.first_name}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  first_name: event.target.value,
                }))
              }
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            />
          </label>
          <label className="text-sm text-app-secondary">
            Last Name
            <input
              required
              value={form.last_name}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  last_name: event.target.value,
                }))
              }
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            />
          </label>
          <label className="text-sm text-app-secondary">
            Email
            <input
              required
              type="email"
              value={form.email}
              onChange={(event) =>
                setForm((current) => ({ ...current, email: event.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            />
          </label>
          <label className="text-sm text-app-secondary">
            Role
            <input
              required
              list="employee-role-options"
              value={form.role}
              onChange={(event) =>
                setForm((current) => ({ ...current, role: event.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            />
          </label>
          <label className="text-sm text-app-secondary">
            Department
            <input
              list="employee-department-options"
              value={form.department}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  department: event.target.value,
                }))
              }
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            />
          </label>
          <label className="text-sm text-app-secondary">
            Job Title
            <input
              value={form.job_title}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  job_title: event.target.value,
                }))
              }
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            />
          </label>
          <label className="text-sm text-app-secondary md:col-span-2">
            Status
            <select
              value={form.status}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  status: event.target.value,
                }))
              }
              className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app"
            >
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <datalist id="employee-role-options">
            {roleOptions.map((role) => (
              <option key={role} value={role} />
            ))}
          </datalist>
          <datalist id="employee-department-options">
            {departmentOptions.map((department) => (
              <option key={department} value={department} />
            ))}
          </datalist>
          {createError ? (
            <p className="text-sm text-rose-600 md:col-span-2">{createError}</p>
          ) : null}
          <div className="md:col-span-2">
            <Button type="submit">Create employee</Button>
          </div>
        </form>
      </DetailDrawer>

      <DetailDrawer
        open={Boolean(selectedEmployee)}
        onClose={closeEmployeeDetail}
        title={
          selectedEmployee
            ? `${selectedEmployee.first_name} ${selectedEmployee.last_name}`
            : "Employee"
        }
        subtitle={
          selectedEmployee
            ? `${selectedEmployee.role} | ${selectedEmployee.department || "No department"}`
            : ""
        }
      >
        {selectedEmployee ? (
          <>
            {selectedHasIncompleteProfile ? (
              <section className="surface-card rounded-3xl border border-amber-400/30 p-5">
                <h3 className="text-lg font-semibold text-app">
                  Profile Attention
                </h3>
                <p className="mt-3 text-sm text-app-secondary">
                  Department or job title is still missing. The employee record
                  can stay in the directory, but governance follow-up work will
                  remain easier to track once the profile is complete.
                </p>
              </section>
            ) : null}
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Profile</h3>
              <div className="mt-4 grid gap-3 text-sm text-app-secondary sm:grid-cols-2">
                <p>
                  <span className="text-app-muted">Email:</span>{" "}
                  {selectedEmployee.email}
                </p>
                <p>
                  <span className="text-app-muted">Status:</span>{" "}
                  <span className={statusTone(selectedEmployee.status)}>
                    {selectedEmployee.status}
                  </span>
                </p>
                <p>
                  <span className="text-app-muted">Role:</span>{" "}
                  {selectedEmployee.role}
                </p>
                <p>
                  <span className="text-app-muted">Department:</span>{" "}
                  {selectedEmployee.department || "Not set"}
                </p>
                <p>
                  <span className="text-app-muted">Job title:</span>{" "}
                  {selectedEmployee.job_title || "Not set"}
                </p>
                <p>
                  <span className="text-app-muted">Last login:</span>{" "}
                  {formatDateTime(selectedEmployee.last_login)}
                </p>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Actions</h3>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button
                  onClick={() =>
                    updateSelected({
                      role:
                        selectedEmployee.role === "security_admin"
                          ? "operations_admin"
                          : "security_admin",
                    })
                  }
                >
                  Change Role
                </Button>
                <Button
                  onClick={() =>
                    updateSelected({
                      status:
                        selectedEmployee.status === "active"
                          ? "inactive"
                          : "active",
                    })
                  }
                >
                  Toggle Status
                </Button>
                <Button
                  disabled={selectedEmployee.status === "inactive"}
                  onClick={deactivateSelected}
                >
                  {selectedEmployee.status === "inactive"
                    ? "Employee inactive"
                    : "Deactivate Employee"}
                </Button>
                <Button onClick={createEmployeeTask}>Create follow-up task</Button>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Linked Tasks</h3>
              <div className="mt-4 flex flex-wrap gap-2">
                {selectedTasks.length ? (
                  selectedTasks.map((task) => (
                    <LinkedTaskPill
                      key={task.id}
                      label={`${task.task_key} ${task.status}`}
                      onClick={() => navigate("/compliance/tasks")}
                      tone="accent"
                    />
                  ))
                ) : (
                  <p className="text-sm text-app-muted">
                    No employee governance tasks linked yet.
                  </p>
                )}
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Training Status</h3>
              <div className="mt-4 space-y-3">
                {selectedAssignments.length ? (
                  selectedAssignments.map((item) => (
                    <div
                      key={item.assignment.id}
                      className="rounded-2xl border border-app p-4 text-sm text-app-secondary"
                    >
                      <p className="font-semibold text-app">
                        {item.record.title}
                      </p>
                      <p className="mt-1">
                        {item.assignment.completion_status}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-app-muted">
                    No training assigned.
                  </p>
                )}
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Access Reviews</h3>
              <div className="mt-4 space-y-3">
                {selectedReviews.length ? (
                  selectedReviews.map((item) => (
                    <div
                      key={item.review.id}
                      className="rounded-2xl border border-app p-4 text-sm text-app-secondary"
                    >
                      <p className="font-semibold text-app">
                        {item.record.title}
                      </p>
                      <p className="mt-1">{item.review.decision}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-app-muted">
                    No access reviews found.
                  </p>
                )}
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">
                Activity History
              </h3>
              <div className="mt-4 space-y-3">
                {selectedActivity.length ? (
                  selectedActivity.map((event) => (
                    <div
                      key={event.id}
                      className="rounded-2xl border border-app p-4 text-sm text-app-secondary"
                    >
                      <p className="font-semibold text-app">{event.action}</p>
                      <p className="mt-1 text-xs text-app-muted">
                        {formatDateTime(event.timestamp)}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-app-muted">
                    No employee-specific audit events yet.
                  </p>
                )}
              </div>
            </section>
            {actionError ? (
              <p className="text-sm text-rose-600">{actionError}</p>
            ) : null}
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
