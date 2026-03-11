export default function About() {
  return (
    <div className="page-shell px-6 py-12">
      <div className="mx-auto max-w-4xl space-y-8">
        <section className="surface-panel p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.26em] text-app-muted">About ALEX</p>
          <h1 className="text-app mt-4 text-4xl font-semibold">
            Privacy tooling for teams that need clarity and accountability.
          </h1>
          <p className="text-app-secondary mt-4 text-sm leading-7">
            ALEX exists to help organizations handle sensitive data responsibly without adding unnecessary complexity. We
            built the platform to make detection, redaction, and reporting practical for day-to-day operations.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="surface-card p-6">
            <h2 className="text-xl font-semibold text-app">Our Mission</h2>
            <p className="text-app-secondary mt-3 text-sm leading-7">
              Give teams a calm, reliable way to run privacy workflows with measurable outcomes.
            </p>
          </div>
          <div className="surface-card p-6">
            <h2 className="text-xl font-semibold text-app">Why We Built ALEX</h2>
            <p className="text-app-secondary mt-3 text-sm leading-7">
              Privacy work is often fragmented and manual. ALEX brings core operational steps into one workflow: scan,
              redact, report, and review.
            </p>
          </div>
        </section>

        <section className="surface-card p-6">
          <h2 className="text-xl font-semibold text-app">What We Believe</h2>
          <p className="text-app-secondary mt-3 text-sm leading-7">
            Privacy should be built into regular product and data operations. The tools should be understandable,
            tenant-safe, and honest about their current maturity.
          </p>
        </section>
      </div>
    </div>
  );
}
