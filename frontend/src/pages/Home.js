import { Link } from "react-router-dom";

const capabilities = [
  "Detect likely personally identifiable information across uploaded files",
  "Apply automated and policy-driven redactions",
  "Generate audit-ready compliance reports",
  "Track scan activity with tenant-aware controls",
  "Support operational privacy workflows",
];

const summarySteps = [
  "Upload a supported dataset.",
  "ALEX scans and detects sensitive data signals.",
  "Controlled redaction policies are applied.",
  "Review risk indicators and download protected outputs.",
];

const workflowSteps = [
  {
    step: "01",
    title: "Ingest privacy-sensitive files",
    description:
      "Bring structured datasets into one controlled workspace with a predictable starting point for review.",
  },
  {
    step: "02",
    title: "Detect signals with context",
    description:
      "Surface likely sensitive patterns, highlight risk indicators, and keep the review process focused on operational evidence.",
  },
  {
    step: "03",
    title: "Apply controlled redactions",
    description:
      "Use repeatable redaction workflows to protect sensitive values while preserving oversight and team confidence.",
  },
  {
    step: "04",
    title: "Export protected outputs",
    description:
      "Generate redacted files and audit-ready deliverables that support privacy review, reporting, and downstream collaboration.",
  },
];

const trustControls = [
  "Tenant-aware access controls",
  "Passkey-based authentication",
  "Secure download routes",
  "Auditable platform activity",
  "Controlled redaction workflows",
];

function SectionHeading({ eyebrow, title, description, centered = false }) {
  return (
    <div className={centered ? "mx-auto max-w-3xl text-center" : "max-w-3xl"}>
      {eyebrow ? (
        <p className="text-app-muted text-xs font-semibold uppercase tracking-[0.28em]">{eyebrow}</p>
      ) : null}
      <h2 className="text-app mt-4 text-3xl font-semibold leading-tight sm:text-4xl">{title}</h2>
      {description ? (
        <p className="text-app-secondary mt-4 text-base leading-7 sm:text-[1.05rem]">{description}</p>
      ) : null}
    </div>
  );
}

function BulletList({ items }) {
  return (
    <ul className="space-y-3 text-sm leading-7 text-app-secondary sm:text-[0.98rem]">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3">
          <span className="mt-2 h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_0_6px_rgba(34,211,238,0.08)]" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function Home() {
  return (
    <div className="page-shell overflow-hidden px-6 py-10 sm:py-14">
      <div className="mx-auto max-w-[1160px] space-y-20 sm:space-y-[5rem]">
        <section className="pt-6 sm:pt-10">
          <div className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.2),transparent_28%),radial-gradient(circle_at_80%_20%,rgba(8,145,178,0.18),transparent_30%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.92))] px-6 py-12 shadow-[0_24px_80px_rgba(2,8,23,0.42)] sm:px-10 sm:py-16 lg:px-14 lg:py-20">
            <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.04),transparent_38%,transparent_62%,rgba(34,211,238,0.08))]" />
            <div className="absolute -right-20 top-10 h-44 w-44 rounded-full bg-cyan-400/10 blur-3xl" />
            <div className="absolute -left-10 bottom-0 h-40 w-40 rounded-full bg-sky-500/10 blur-3xl" />
            <div className="relative mx-auto max-w-4xl text-center">
              <p className="text-app-muted text-xs font-semibold uppercase tracking-[0.34em]">
                Privacy Operations Platform
              </p>
              <h1 className="text-app mt-5 text-4xl font-semibold leading-[1.05] sm:text-5xl lg:text-[4.15rem]">
                Detect sensitive data, redact with control, and produce audit-ready outputs.
              </h1>
              <p className="text-app-secondary mx-auto mt-6 max-w-3xl text-base leading-8 sm:text-lg">
                ALEX helps organizations turn privacy review into an operational process instead of an
                afterthought. Upload datasets, detect sensitive signals, apply controlled redactions, and
                generate compliance-ready outputs from one unified platform.
              </p>
              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
                <Link to="/register" className="btn-primary-app min-w-[180px] px-6 py-3 text-sm sm:text-base">
                  Get Started
                </Link>
                <Link
                  to="/trust"
                  className="btn-secondary-app min-w-[180px] border-white/15 px-6 py-3 text-sm sm:text-base"
                >
                  View Trust Center
                </Link>
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-8">
          <SectionHeading
            eyebrow="Capabilities"
            title="Operate privacy review with structure, speed, and visibility."
            description="Designed for privacy teams that need clean workflows, clear outputs, and consistent controls across every stage of review."
          />

          <div className="grid gap-6 lg:grid-cols-2">
            <article className="surface-card relative overflow-hidden rounded-[1.75rem] p-8 shadow-[0_18px_50px_rgba(2,8,23,0.3)]">
              <div className="absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-cyan-300/60 to-transparent" />
              <p className="text-app-muted text-xs font-semibold uppercase tracking-[0.24em]">Key Capabilities</p>
              <BulletList items={capabilities} />
            </article>

            <article className="surface-tint relative overflow-hidden rounded-[1.75rem] p-8 shadow-[0_18px_50px_rgba(2,8,23,0.28)]">
              <div className="absolute inset-0 bg-[linear-gradient(160deg,rgba(34,211,238,0.08),transparent_45%,rgba(255,255,255,0.03))]" />
              <div className="relative">
                <p className="text-app-muted text-xs font-semibold uppercase tracking-[0.24em]">How It Works</p>
                <ol className="mt-5 space-y-4 text-sm leading-7 text-app-secondary sm:text-[0.98rem]">
                  {summarySteps.map((step, index) => (
                    <li key={step} className="flex gap-4">
                      <span className="text-app inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-cyan-300/25 bg-cyan-300/10 text-xs font-semibold">
                        {index + 1}
                      </span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
                <p className="text-app-secondary mt-6 border-t border-white/10 pt-5 text-sm leading-7">
                  Privacy operations should be transparent, repeatable, and auditable.
                </p>
              </div>
            </article>
          </div>
        </section>

        <section id="how-it-works" className="space-y-8">
          <SectionHeading
            eyebrow="How It Works"
            title="A clear operational path from upload to protected output."
            description="Each stage is designed to help privacy teams move from raw input to accountable decision-making without losing clarity."
          />

          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {workflowSteps.map((item) => (
              <article
                key={item.step}
                className="surface-card group relative overflow-hidden rounded-[1.75rem] p-8 shadow-[0_18px_50px_rgba(2,8,23,0.26)]"
              >
                <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(34,211,238,0.08),transparent_40%)] opacity-70 transition-opacity duration-300 group-hover:opacity-100" />
                <div className="relative">
                  <p className="text-app-muted text-xs font-semibold uppercase tracking-[0.3em]">{item.step}</p>
                  <h3 className="text-app mt-5 text-xl font-semibold leading-tight">{item.title}</h3>
                  <p className="text-app-secondary mt-4 text-sm leading-7">{item.description}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="space-y-8">
          <SectionHeading
            eyebrow="Security and Platform Trust"
            title="Built for security-focused privacy teams"
            description="ALEX is designed for teams running real privacy operations."
          />

          <article className="surface-card relative overflow-hidden rounded-[2rem] p-8 shadow-[0_20px_60px_rgba(2,8,23,0.34)] sm:p-10">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(34,211,238,0.12),transparent_30%),linear-gradient(180deg,transparent,rgba(255,255,255,0.02))]" />
            <div className="relative grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)] lg:items-start">
              <div>
                <p className="text-app-secondary max-w-2xl text-base leading-8">
                  The platform includes:
                </p>
                <div className="mt-6 max-w-2xl">
                  <BulletList items={trustControls} />
                </div>
                <p className="text-app-secondary mt-8 max-w-3xl text-sm leading-8 sm:text-[0.98rem]">
                  These controls help organizations review and protect sensitive data responsibly while
                  maintaining full visibility into privacy operations.
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-cyan-300/12 bg-slate-950/45 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
                <p className="text-app-muted text-xs font-semibold uppercase tracking-[0.26em]">Platform Trust</p>
                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-5">
                    <p className="text-app text-2xl font-semibold">Tenant Aware</p>
                    <p className="text-app-secondary mt-2 text-sm leading-6">
                      Privacy workflows are organized for teams that need scoped visibility and controlled access.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-5">
                    <p className="text-app text-2xl font-semibold">Audit Ready</p>
                    <p className="text-app-secondary mt-2 text-sm leading-6">
                      Reports, activity, and protected outputs remain aligned with operational accountability.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </section>

        <section className="pb-8 text-center sm:pb-12">
          <div className="relative mx-auto max-w-4xl overflow-hidden rounded-[2rem] border border-cyan-300/12 bg-[linear-gradient(180deg,rgba(8,15,28,0.94),rgba(3,10,22,0.96))] px-6 py-12 shadow-[0_22px_70px_rgba(2,8,23,0.38)] sm:px-10 sm:py-14">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.14),transparent_30%)]" />
            <div className="relative mx-auto max-w-2xl">
              <SectionHeading
                centered
                eyebrow="Final Call to Action"
                title="Start running privacy operations with clarity."
                description="Upload your first dataset, detect sensitive signals, and generate protected outputs in minutes."
              />
              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
                <Link to="/upload" className="btn-primary-app min-w-[180px] px-6 py-3 text-sm sm:text-base">
                  Start a Scan
                </Link>
                <Link to="/about" className="btn-secondary-app min-w-[180px] px-6 py-3 text-sm sm:text-base">
                  View Documentation
                </Link>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
