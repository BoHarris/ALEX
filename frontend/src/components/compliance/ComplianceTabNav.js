import { NavLink } from "react-router-dom";

const tabs = [
  { to: "/compliance", label: "Overview", end: true },
  { to: "/compliance/employees", label: "Employees" },
  { to: "/compliance/policies", label: "Policies" },
  { to: "/compliance/vendors", label: "Vendors" },
  { to: "/compliance/incidents", label: "Incidents" },
  { to: "/compliance/tasks", label: "Tasks" },
  { to: "/compliance/risks", label: "Risks" },
  { to: "/compliance/access-reviews", label: "Access Reviews" },
  { to: "/compliance/training", label: "Training" },
  { to: "/compliance/code-review", label: "Code Review" },
  { to: "/compliance/testing", label: "Testing & Validation" },
  { to: "/compliance/audit-log", label: "Audit Log" },
];

export default function ComplianceTabNav() {
  return (
    <nav className="surface-card overflow-x-auto rounded-3xl p-2" aria-label="Compliance workspace sections">
      <div className="flex min-w-max gap-2">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              isActive
                ? "rounded-2xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950"
                : "rounded-2xl px-4 py-2 text-sm font-medium text-app-secondary hover:bg-white/5 hover:text-app"
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
