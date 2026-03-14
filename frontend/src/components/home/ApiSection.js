import { LandingSection, SurfaceFrame } from "./LandingSection";

const apiPayload = `POST /api/v1/redact
{
  "records": [
    {
      "email": "user@example.com",
      "phone": "555-123-4567"
    }
  ],
  "options": {
    "redaction_mode": "strict",
    "policy_pack": "gdpr"
  }
}`;

export default function ApiSection() {
  return (
    <LandingSection
      id="api"
      eyebrow="API Integration"
      title="Privacy Infrastructure for Your Applications"
      description="Engineers can integrate ALEX directly into data pipelines, services, and operational workflows to return safely redacted datasets before downstream systems ever see raw sensitive values."
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(360px,1.05fr)]">
        <SurfaceFrame className="rounded-[2rem] p-7">
          <p className="text-sm leading-7 text-app-secondary">
            Send structured payloads or file-based datasets to ALEX, apply a policy pack, and receive redacted results that are ready for storage, export, or analytics. The platform keeps the redaction policy logic centralized while still fitting naturally into application code.
          </p>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {[
              "Use strict, policy-aware redaction modes",
              "Apply GDPR and regulated-data packs",
              "Return sanitized records to downstream services",
              "Preserve testing and audit visibility for engineering teams",
            ].map((item) => (
              <div key={item} className="rounded-2xl border border-app bg-slate-950/30 px-4 py-4 text-sm text-app-secondary">
                {item}
              </div>
            ))}
          </div>
        </SurfaceFrame>

        <SurfaceFrame className="rounded-[2rem] border-cyan-300/15 bg-slate-950/80 p-0 overflow-hidden">
          <div className="border-b border-white/10 px-5 py-4 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">
            Redaction API Example
          </div>
          <pre className="overflow-x-auto px-5 py-5 text-sm leading-7 text-slate-200">
            <code>{apiPayload}</code>
          </pre>
          <div className="border-t border-white/10 bg-white/5 px-5 py-4 text-sm text-app-secondary">
            ALEX returns a safely redacted dataset plus the metadata teams need for review, policy mapping, and testing validation.
          </div>
        </SurfaceFrame>
      </div>
    </LandingSection>
  );
}
