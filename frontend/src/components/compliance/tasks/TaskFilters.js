function FilterField({ label, value, onChange, options }) {
  return (
    <label className="min-w-0 flex flex-col gap-2 text-sm text-app-secondary">
      <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-app-muted">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-2xl border border-app bg-app/80 px-3 py-2.5 text-sm text-app focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}

function ToggleChip({ active, label, onClick }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`rounded-full border px-4 py-2.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70 ${active ? "border-cyan-300/40 bg-cyan-400/12 text-cyan-100" : "border-app bg-app/50 text-app-secondary hover:text-app"}`}
    >
      {label}
    </button>
  );
}

export default function TaskFilters({ filters, setFilters, assignees = [] }) {
  return (
    <div className="mt-6 space-y-4">
      <div className="flex flex-wrap gap-3">
        <ToggleChip
          active={filters.myTasks}
          label="Assigned to Me"
          onClick={() => setFilters((current) => ({ ...current, myTasks: !current.myTasks }))}
        />
        <ToggleChip
          active={filters.openOnly}
          label="Open Tasks Only"
          onClick={() => setFilters((current) => ({ ...current, openOnly: !current.openOnly }))}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <label className="min-w-0 flex flex-col gap-2 text-sm text-app-secondary xl:col-span-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-app-muted">Search</span>
          <input
            value={filters.search}
            onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            placeholder="Search tasks, tests, incidents, vendors"
            className="rounded-2xl border border-app bg-app/80 px-3 py-2.5 text-sm text-app focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60"
          />
        </label>
        <FilterField
          label="Status"
          value={filters.status}
          onChange={(value) => setFilters((current) => ({ ...current, status: value }))}
          options={[
            { value: "", label: "All statuses" },
            { value: "todo", label: "To do" },
            { value: "in_progress", label: "In progress" },
            { value: "blocked", label: "Blocked" },
            { value: "ready_for_review", label: "Ready for review" },
            { value: "done", label: "Done" },
            { value: "canceled", label: "Canceled" },
          ]}
        />
        <FilterField
          label="Priority"
          value={filters.priority}
          onChange={(value) => setFilters((current) => ({ ...current, priority: value }))}
          options={[
            { value: "", label: "All priorities" },
            { value: "low", label: "Low" },
            { value: "medium", label: "Medium" },
            { value: "high", label: "High" },
            { value: "critical", label: "Critical" },
          ]}
        />
        <FilterField
          label="Source"
          value={filters.sourceModule}
          onChange={(value) => setFilters((current) => ({ ...current, sourceModule: value }))}
          options={[
            { value: "", label: "All sources" },
            { value: "security", label: "Security" },
            { value: "incidents", label: "Incidents" },
            { value: "vendors", label: "Vendors" },
            { value: "employees", label: "Employees" },
            { value: "testing", label: "Testing" },
            { value: "automation", label: "Automated Changes" },
            { value: "manual", label: "Manual" },
          ]}
        />
        <FilterField
          label="Assignee"
          value={filters.assigneeEmployeeId}
          onChange={(value) => setFilters((current) => ({ ...current, assigneeEmployeeId: value }))}
          options={[
            { value: "", label: "Anyone" },
            ...assignees
              .filter((employee) => employee.status !== "inactive")
              .map((employee) => ({
                value: String(employee.id),
                label: `${employee.first_name} ${employee.last_name}`,
              })),
          ]}
        />
        <label className="min-w-0 flex flex-col gap-2 text-sm text-app-secondary">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-app-muted">Due before</span>
          <input
            type="date"
            value={filters.dueDate}
            onChange={(event) => setFilters((current) => ({ ...current, dueDate: event.target.value }))}
            className="rounded-2xl border border-app bg-app/80 px-3 py-2.5 text-sm text-app focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60"
          />
        </label>
      </div>
    </div>
  );
}
