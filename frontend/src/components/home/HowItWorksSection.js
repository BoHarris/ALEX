import { LandingSection, SurfaceFrame } from "./LandingSection";
import { LayersIcon, SearchIcon, ShieldIcon } from "./HomeIcons";

const steps = [
  {
    number: "01",
    title: "Send data or files to ALEX",
    description: "Connect uploads, exports, pipelines, or operational datasets to the platform without changing how teams work.",
    Icon: LayersIcon,
  },
  {
    number: "02",
    title: "ALEX detects sensitive data",
    description: "Pattern detection, taxonomy classification, and explainable scoring work together so teams understand what was found and why.",
    Icon: SearchIcon,
  },
  {
    number: "03",
    title: "Redact before data leaves your systems",
    description: "Sensitive values are masked, removed, or transformed before datasets are stored, exported, or shared downstream.",
    Icon: ShieldIcon,
  },
];

export default function HowItWorksSection() {
  return (
    <LandingSection
      id="how-it-works"
      eyebrow="How ALEX Works"
      title="A privacy control plane built for operational speed"
      description="ALEX combines detection, policy logic, and redaction workflows so privacy becomes an enforceable system instead of a manual checklist."
    >
      <div className="grid gap-5 lg:grid-cols-3">
        {steps.map(({ number, title, description, Icon }) => (
          <SurfaceFrame key={number} className="rounded-[2rem] p-6">
            <div className="flex items-center justify-between gap-4">
              <Icon />
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-app-muted">Step {number}</span>
            </div>
            <h3 className="mt-6 text-2xl font-semibold text-app">{title}</h3>
            <p className="mt-4 text-sm leading-7 text-app-secondary">{description}</p>
          </SurfaceFrame>
        ))}
      </div>
    </LandingSection>
  );
}
