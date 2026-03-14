import { LandingSection, SurfaceFrame } from "./LandingSection";
import { DocumentIcon, LayersIcon, LockIcon, SearchIcon, ShieldIcon, SparkIcon } from "./HomeIcons";

const capabilities = [
  {
    title: "Automatic PII Detection",
    description: "Detect emails, phone numbers, SSNs, names, and other sensitive identifiers across files and datasets.",
    Icon: SearchIcon,
  },
  {
    title: "Smart Redaction Engine",
    description: "Mask, remove, tokenize, or replace sensitive fields automatically with policy-aware handling.",
    Icon: ShieldIcon,
  },
  {
    title: "Compliance Testing",
    description: "Run automated validation tests to ensure privacy rules remain enforced across releases and datasets.",
    Icon: LayersIcon,
  },
  {
    title: "Privacy Posture Scoring",
    description: "Understand your organization's privacy health at a glance with weighted posture analytics.",
    Icon: SparkIcon,
  },
  {
    title: "Audit-Ready Reports",
    description: "Generate evidence that shows exactly what data was detected, redacted, and validated.",
    Icon: DocumentIcon,
  },
  {
    title: "Controlled Access Workflows",
    description: "Coordinate privacy, compliance, and security stakeholders with governed review surfaces and history.",
    Icon: LockIcon,
  },
];

export default function CapabilitiesSection() {
  return (
    <LandingSection
      id="capabilities"
      eyebrow="Key Capabilities"
      title="Everything teams need to operationalize privacy"
      description="The platform brings detection, redaction, testing, posture scoring, and auditability into one enterprise workflow."
    >
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {capabilities.map(({ title, description, Icon }) => (
          <SurfaceFrame key={title} className="rounded-[2rem] p-6 shadow-[0_18px_40px_rgba(2,8,23,0.18)]">
            <Icon />
            <h3 className="mt-6 text-2xl font-semibold text-app">{title}</h3>
            <p className="mt-4 text-sm leading-7 text-app-secondary">{description}</p>
          </SurfaceFrame>
        ))}
      </div>
    </LandingSection>
  );
}
