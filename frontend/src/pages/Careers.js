export default function Careers() {
  return (
    <div className="page-shell px-6 py-12">
      <div className="mx-auto max-w-4xl space-y-8">
        <section className="surface-panel p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.26em] text-app-muted">Careers</p>
          <h1 className="text-app mt-4 text-4xl font-semibold">Thoughtful builders wanted.</h1>
          <p className="text-app-secondary mt-4 text-sm leading-7">
            We care about privacy, trust, and practical software craftsmanship. If that resonates with you, we would
            like to hear from you.
          </p>
        </section>

        <section className="surface-card p-6">
          <h2 className="text-xl font-semibold text-app">Why Work With Us</h2>
          <ul className="text-app-secondary mt-4 list-disc space-y-2 pl-5 text-sm">
            <li>Privacy as infrastructure, not decoration</li>
            <li>Calm seriousness over noisy growth language</li>
            <li>Practical systems that respect sensitive data handling</li>
            <li>Clear ownership and accountable engineering standards</li>
          </ul>
        </section>

        <section className="surface-tint p-6">
          <h2 className="text-xl font-semibold text-app">Current Openings</h2>
          <p className="text-app-secondary mt-3 text-sm leading-7">
            We are not hiring for specific roles at the moment, but we are always interested in hearing from thoughtful
            builders who care about privacy, trust, and product craftsmanship.
          </p>
          <p className="mt-4 text-sm text-app">Reach out: careers@alexprivacy.local</p>
        </section>
      </div>
    </div>
  );
}
