import { Link } from "react-router-dom";

const features = [
  "Detect likely PII across uploaded files",
  "Apply redaction and generate audit-ready outputs",
  "Track scan activity with tenant-aware controls",
  "Support privacy operations with practical workflows",
];

const howItWorks = [
  "Upload a supported dataset.",
  "ALEX scans and redacts sensitive values.",
  "Review risk signals and download protected outputs.",
];

export default function Home() {
  return (
    <div className="page-shell px-6 py-10">
      <div className="mx-auto max-w-7xl space-y-10">
        <section className="surface-panel rounded-[2rem] p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-app-muted">Privacy Operations Platform</p>
          <h1 className="text-app mt-4 max-w-4xl text-4xl font-semibold leading-tight sm:text-5xl">
            Detect sensitive data, redact with control, and produce audit-ready outputs.
          </h1>
          <p className="text-app-secondary mt-5 max-w-3xl text-base leading-7">
            ALEX helps organizations handle privacy review as an operational process, not an afterthought. Scan uploaded
            files, generate redacted results, and keep visibility across activity in one platform.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/register" className="btn-primary-app text-sm">
              Get Started
            </Link>
            <Link to="/trust" className="btn-secondary-app text-sm">
              View Trust Center
            </Link>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="surface-card p-6">
            <p className="text-app-secondary text-xs font-semibold uppercase tracking-[0.24em]">Key Capabilities</p>
            <ul className="text-app-secondary mt-4 list-disc space-y-3 pl-5 text-sm">
              {features.map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
          </div>
          <div className="surface-tint p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">How It Works</p>
            <ol className="text-app-secondary mt-4 space-y-3 text-sm">
              {howItWorks.map((step, index) => (
                <li key={step}>{index + 1}. {step}</li>
              ))}
            </ol>
            <p className="text-app-secondary mt-6 text-sm">Privacy work should be clear, usable, and accountable.</p>
          </div>
        </section>

        <section className="surface-card p-6">
          <p className="text-app-secondary text-xs font-semibold uppercase tracking-[0.24em]">Built for Credible Beta Pilots</p>
          <p className="text-app-secondary mt-3 max-w-3xl text-sm leading-7">
            ALEX is designed for practical pilots with security-minded teams. Current controls include tenant-aware
            access, passkey authentication, protected download routes, and auditable platform activity.
          </p>
        </section>
      </div>
    </div>
  );
}
