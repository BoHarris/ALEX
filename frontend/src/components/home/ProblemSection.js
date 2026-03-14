import { LandingSection, SurfaceFrame } from "./LandingSection";

const exposures = [
  "emails",
  "phone numbers",
  "SSNs",
  "personal addresses",
  "internal identifiers",
];

export default function ProblemSection() {
  return (
    <LandingSection
      id="problem"
      eyebrow="The Problem"
      title="Sensitive data spreads faster than most teams can see"
      description="Sensitive data flows through logs, analytics pipelines, backups, exports, and third-party integrations. Most organizations do not discover the exposure until after the data has already leaked."
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]">
        <SurfaceFrame className="rounded-[2rem] p-7">
          <p className="text-sm uppercase tracking-[0.2em] text-app-muted">High-risk paths</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {[
              "Application and API logs",
              "Analytics warehouses",
              "Support exports and CSV shares",
              "Backups and archival copies",
              "Vendor and integration payloads",
              "ML training and QA datasets",
            ].map((item) => (
              <div key={item} className="rounded-2xl border border-app bg-slate-950/30 px-4 py-4 text-sm text-app-secondary">
                {item}
              </div>
            ))}
          </div>
        </SurfaceFrame>

        <SurfaceFrame className="rounded-[2rem] border-cyan-300/15 bg-[linear-gradient(160deg,rgba(14,116,144,0.18),rgba(2,6,23,0.6))] p-7">
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-200">One mistake can expose</p>
          <ul className="mt-5 space-y-3 text-base text-app-secondary">
            {exposures.map((item) => (
              <li key={item} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                <span className="h-2.5 w-2.5 rounded-full bg-cyan-300" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <p className="mt-6 text-sm leading-7 text-app-secondary">
            ALEX detects and removes sensitive data before it becomes a privacy incident, operational bottleneck, or audit surprise.
          </p>
        </SurfaceFrame>
      </div>
    </LandingSection>
  );
}
