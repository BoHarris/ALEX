import { Link } from "react-router-dom";

const plans = [
  {
    name: "Free",
    price: "$0",
    cta: "Current for New Users",
    limits: ["1 scan/day", "5MB file size", "Personal scan view", "Core redaction and report download"],
  },
  {
    name: "Pro",
    price: "Contact",
    cta: "Upgrade",
    limits: ["100 scans/day", "10MB file size", "Admin analytics access", "Audit trail visibility", "Company settings access"],
  },
  {
    name: "Business",
    price: "Contact Sales",
    cta: "Contact Sales",
    limits: ["500 scans/day", "25MB file size", "Company-wide admin controls", "Expanded analytics and reporting visibility", "Priority support pathway (pilot phase)"],
  },
];

export default function Pricing() {
  return (
    <div className="page-shell px-6 py-12">
      <div className="mx-auto max-w-6xl space-y-8">
        <section className="surface-panel p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.26em] text-app-muted">Plans</p>
          <h1 className="text-app mt-4 text-4xl font-semibold">
            Pricing-ready plan structure for commercial rollout.
          </h1>
          <p className="text-app-secondary mt-4 max-w-3xl text-sm leading-7">
            ALEX plan tiers are already reflected in feature access and usage controls. Billing integration is planned
            as a separate phase.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {plans.map((plan) => (
            <article key={plan.name} className="surface-card p-6">
              <p className="text-app-muted text-xs font-semibold uppercase tracking-[0.24em]">{plan.name}</p>
              <p className="text-app mt-3 text-3xl font-semibold">{plan.price}</p>
              <ul className="text-app-secondary mt-4 list-disc space-y-2 pl-5 text-sm">
                {plan.limits.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <button className="btn-primary-app mt-6 text-sm">{plan.cta}</button>
            </article>
          ))}
        </section>

        <section className="surface-card p-6">
          <p className="text-app-secondary text-sm">
            Looking for pilot access details or a tailored company plan?{" "}
            <Link to="/about" className="text-app underline hover:text-app-secondary">
              Talk with the ALEX team.
            </Link>
          </p>
        </section>
      </div>
    </div>
  );
}
