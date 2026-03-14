import { LandingSection, SurfaceFrame } from "./LandingSection";

const frameworks = ["GDPR", "HIPAA", "COPPA"];

export default function SecuritySection() {
  return (
    <LandingSection
      id="security"
      eyebrow="Security and Compliance"
      title="Support privacy programs with auditable controls"
      description="ALEX helps teams operationalize privacy workflows aligned with major regulatory frameworks while keeping evidence generation and validation visible to security and compliance stakeholders."
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(280px,0.85fr)_minmax(0,1.15fr)]">
        <SurfaceFrame className="rounded-[2rem] p-7">
          <p className="text-sm uppercase tracking-[0.22em] text-app-muted">Aligned workflows</p>
          <div className="mt-5 flex flex-wrap gap-3">
            {frameworks.map((item) => (
              <span key={item} className="rounded-full border border-cyan-300/25 bg-cyan-300/10 px-4 py-2 text-sm font-semibold text-cyan-200">
                {item}
              </span>
            ))}
          </div>
        </SurfaceFrame>

        <div className="grid gap-5 md:grid-cols-3">
          {[
            {
              title: "Audit logs",
              text: "Track who ran scans, what was changed, and which controls were exercised across the platform.",
            },
            {
              title: "Compliance reports",
              text: "Generate evidence packages that show findings, redaction outcomes, and workflow history.",
            },
            {
              title: "Automated validation testing",
              text: "Continuously verify that privacy rules still work as systems evolve, integrations change, and releases ship.",
            },
          ].map((item) => (
            <SurfaceFrame key={item.title} className="rounded-[2rem] p-6">
              <p className="text-xl font-semibold text-app">{item.title}</p>
              <p className="mt-4 text-sm leading-7 text-app-secondary">{item.text}</p>
            </SurfaceFrame>
          ))}
        </div>
      </div>
    </LandingSection>
  );
}
