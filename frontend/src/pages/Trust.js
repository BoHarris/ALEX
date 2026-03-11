export default function Trust() {
  return (
    <div className="page-shell px-6 py-12">
      <div className="mx-auto max-w-5xl space-y-6">
        <section className="surface-tint p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.26em] text-app-muted">Trust Center</p>
          <h1 className="mt-4 text-4xl font-semibold">Security and privacy, handled with operational discipline.</h1>
          <p className="mt-4 text-sm leading-7 text-app-secondary">
            ALEX is a privacy engineering platform designed to help organizations identify sensitive information,
            apply controlled redactions, generate privacy reports, and operate privacy workflows with accountability.
          </p>
        </section>

        <section className="surface-card p-6">
          <h2 className="text-lg font-semibold">Platform Overview</h2>
          <p className="mt-3 text-sm leading-7 text-app-secondary">
            Privacy work should be operational and observable. ALEX is built to support repeatable privacy workflows so
            teams can review sensitive data handling decisions with clarity, not guesswork.
          </p>
          <p className="mt-3 text-sm leading-7 text-app-secondary">
            The platform focuses on practical privacy operations: detecting sensitive information, applying redactions in
            a controlled workflow, and providing report outputs that help teams communicate outcomes responsibly.
          </p>
        </section>

        <section className="surface-card p-6">
          <h2 className="text-lg font-semibold">Security &amp; Privacy Design Philosophy</h2>
          <div className="text-app-secondary mt-4 space-y-5 text-sm leading-7">
            <div>
              <h3 className="text-app text-base font-semibold">Detection Approach: Machine Learning vs Language Models</h3>
              <p className="mt-2">
                ALEX uses targeted machine learning approaches for structured data analysis rather than relying entirely
                on large language models. Structured datasets benefit from deterministic analysis that is easier to
                evaluate, more predictable to operate, and better suited for privacy-sensitive workflows.
              </p>
              <p className="mt-2">
                Language models can be powerful in many contexts, but privacy operations often require consistent and
                auditable behavior over probabilistic output patterns.
              </p>
            </div>
            <div>
              <h3 className="text-app text-base font-semibold">Authentication Philosophy: Passkeys Instead of Passwords</h3>
              <p className="mt-2">
                ALEX uses passkey-based authentication in place of traditional passwords to reduce common credential risks
                such as phishing, password reuse, and password database exposure.
              </p>
              <p className="mt-2">
                This aligns with modern authentication standards designed to reduce password-related attack paths.
              </p>
            </div>
            <div>
              <h3 className="text-app text-base font-semibold">Deterministic Privacy Workflows</h3>
              <p className="mt-2">
                ALEX prioritizes predictable privacy operations because repeatability matters when handling regulated or
                sensitive information. Consistent workflows support reliable outcomes across detection, redaction, and
                reporting.
              </p>
            </div>
            <div>
              <h3 className="text-app text-base font-semibold">Operational Visibility</h3>
              <p className="mt-2">
                The product is designed to make privacy workflows observable. Teams can review scan activity, inspect
                outputs, and generate reports that describe redaction outcomes in clear operational terms.
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="surface-card p-6">
            <h2 className="text-lg font-semibold">Security Practices: Data Protection</h2>
            <p className="mt-3 text-sm leading-7 text-app-secondary">
              Uploaded files are processed in controlled environments designed to minimize unnecessary exposure. Data is
              handled only for privacy detection and redaction workflows.
            </p>
          </div>
          <div className="surface-card p-6">
            <h2 className="text-lg font-semibold">Security Practices: Access Controls</h2>
            <p className="mt-3 text-sm leading-7 text-app-secondary">
              ALEX enforces authentication and authorization controls so users can access only the resources that belong
              to their organization and role context.
            </p>
          </div>
          <div className="surface-card p-6">
            <h2 className="text-lg font-semibold">Security Practices: Tenant Isolation</h2>
            <p className="mt-3 text-sm leading-7 text-app-secondary">
              Organizations operate in isolated contexts to support company-level data boundaries and prevent cross-tenant
              access during normal product operation.
            </p>
          </div>
          <div className="surface-card p-6">
            <h2 className="text-lg font-semibold">Security Practices: Secure Processing</h2>
            <p className="mt-3 text-sm leading-7 text-app-secondary">
              Files move through controlled processing workflows designed to analyze and redact sensitive information in a
              consistent and privacy-aware manner.
            </p>
          </div>
        </section>

        <section className="surface-card p-6">
          <h2 className="text-lg font-semibold">Operational Transparency</h2>
          <p className="mt-3 text-sm leading-7 text-app-secondary">
            Privacy operations should be observable. ALEX provides visibility into scan outcomes, redaction summaries,
            and operational history so teams can understand how sensitive data is handled throughout the workflow.
          </p>
        </section>

        <section className="surface-card p-6">
          <h2 className="text-lg font-semibold">Responsible Disclosure</h2>
          <p className="mt-3 text-sm leading-7 text-app-secondary">
            If you believe you have identified a potential security issue in ALEX, please report it responsibly so the
            issue can be reviewed and addressed.
          </p>
          <p className="mt-4 text-sm text-app">
            <a href="mailto:security@alexprivacy.com" className="underline hover:text-app-secondary">
              security@alexprivacy.com
            </a>
          </p>
        </section>

        <section className="surface-card p-6">
          <h2 className="text-lg font-semibold">Product Maturity</h2>
          <p className="mt-3 text-sm leading-7 text-app-secondary">
            ALEX is currently in a commercial beta stage. Security controls continue to evolve as the platform matures
            and undergoes ongoing testing and operational refinement.
          </p>
          <p className="mt-3 text-sm leading-7 text-app-muted">
            We aim for transparent progress and avoid overstating certifications or compliance claims that have not been
            formally achieved.
          </p>
        </section>

        <section className="surface-card p-6">
          <h2 className="text-lg font-semibold">Privacy-First Engineering</h2>
          <p className="mt-3 text-sm leading-7 text-app-secondary">
            Privacy should be part of engineering design, not an afterthought. ALEX is built around minimizing unnecessary
            data exposure and helping organizations run privacy workflows responsibly.
          </p>
          <p className="mt-3 text-sm leading-7 text-app-secondary">
            Our approach emphasizes practical safeguards, predictable workflow behavior, and clear accountability for
            sensitive data handling decisions.
          </p>
        </section>

        <section className="surface-tint p-6">
          <h2 className="text-lg font-semibold text-app">Trust Signals</h2>
          <ul className="mt-3 space-y-2 text-sm leading-7 text-app-secondary">
            <li>Privacy-focused product philosophy grounded in operational responsibility.</li>
            <li>Security posture designed around controlled access and predictable behavior.</li>
            <li>Transparent product maturity with clear acknowledgement of ongoing hardening work.</li>
            <li>Operational accountability through observable privacy workflows and outcomes.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
