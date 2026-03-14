import validationPreview from "../../assets/alex-validation-preview.png";
import { LandingSection, SurfaceFrame } from "./LandingSection";

const previewCards = [
  {
    title: "Testing & Validation dashboard",
    caption: "Monitor privacy validation tests in real time.",
    variant: "matrix",
  },
  {
    title: "Test execution drawer",
    caption: "Inspect test failures and execution history instantly.",
    variant: "drawer",
  },
  {
    title: "Compliance workspace",
    caption: "Track privacy compliance across datasets and systems.",
    variant: "workspace",
  },
  {
    title: "Scan results interface",
    caption: "Review findings, risk signals, and redacted outputs in one place.",
    variant: "results",
  },
];

function FauxProductPanel({ variant }) {
  if (variant === "drawer") {
    return (
      <div className="grid h-full grid-cols-[minmax(0,0.95fr)_minmax(180px,0.75fr)] gap-4 rounded-[1.6rem] border border-white/10 bg-slate-950/70 p-4">
        <div className="rounded-[1.2rem] border border-white/10 bg-white/5 p-4">
          <div className="h-3 w-24 rounded-full bg-cyan-300/30" />
          <div className="mt-4 space-y-3">
            {[72, 56, 48, 65].map((width) => (
              <div key={width} className="h-9 rounded-2xl bg-white/5 px-3 py-3">
                <div className="h-3 rounded-full bg-slate-400/30" style={{ width: `${width}%` }} />
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-[1.2rem] border border-cyan-300/20 bg-cyan-300/8 p-4">
          <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-cyan-200">
            <span>Run History</span>
            <span>Drawer</span>
          </div>
          <div className="mt-4 space-y-3">
            {["Failed", "Passed", "Passed"].map((state, index) => (
              <div key={`${state}-${index}`} className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-app-secondary">
                <div className="flex items-center justify-between">
                  <span>Execution {index + 1}</span>
                  <span className={state === "Failed" ? "text-rose-300" : "text-emerald-300"}>{state}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (variant === "workspace") {
    return (
      <div className="grid h-full gap-4 rounded-[1.6rem] border border-white/10 bg-slate-950/70 p-4">
        <div className="grid gap-3 md:grid-cols-3">
          {["Policies", "Vendors", "Training"].map((title) => (
            <div key={title} className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-app-muted">{title}</div>
              <div className="mt-3 h-8 rounded-xl bg-cyan-300/20" />
            </div>
          ))}
        </div>
        <div className="grid flex-1 gap-3 md:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[1.2rem] border border-white/10 bg-white/5 p-4">
            <div className="h-3 w-28 rounded-full bg-cyan-300/30" />
            <div className="mt-4 space-y-3">
              {[84, 68, 74, 59].map((width) => (
                <div key={width} className="h-10 rounded-2xl bg-slate-400/10 px-3 py-3">
                  <div className="h-3 rounded-full bg-slate-400/30" style={{ width: `${width}%` }} />
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-[1.2rem] border border-cyan-300/20 bg-cyan-300/8 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-cyan-200">At-a-glance</div>
            <div className="mt-4 space-y-3">
              {["Incidents", "Reviews", "Testing"].map((title) => (
                <div key={title} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <div className="text-sm text-app-secondary">{title}</div>
                  <div className="mt-2 h-2 rounded-full bg-white/10">
                    <div className="h-2 rounded-full bg-gradient-to-r from-cyan-400 to-teal-300" style={{ width: `${title === "Testing" ? 82 : title === "Reviews" ? 64 : 55}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (variant === "results") {
    return (
      <div className="grid h-full gap-4 rounded-[1.6rem] border border-white/10 bg-slate-950/70 p-4">
        <div className="grid gap-3 md:grid-cols-[0.85fr_1.15fr]">
          <div className="rounded-[1.2rem] border border-cyan-300/20 bg-cyan-300/8 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-cyan-200">Detected Types</div>
            <div className="mt-4 space-y-2 text-sm text-app-secondary">
              {[
                ["Email", "128"],
                ["Phone", "64"],
                ["SSN", "12"],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
                  <span>{label}</span>
                  <span>{value}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-[1.2rem] border border-white/10 bg-white/5 p-4">
            <div className="h-3 w-32 rounded-full bg-cyan-300/30" />
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {["Redacted Output", "Risk Summary", "Policy Mapping", "Audit Trail"].map((label) => (
                <div key={label} className="rounded-2xl bg-slate-400/10 p-3 text-sm text-app-secondary">
                  <div className="h-3 w-20 rounded-full bg-slate-400/30" />
                  <div className="mt-3">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[1.6rem] border border-white/10 bg-slate-950/70">
      <img
        src={validationPreview}
        alt="Testing and validation product preview"
        className="h-full w-full object-cover"
      />
    </div>
  );
}

export default function ProductPreviewSection() {
  return (
    <LandingSection
      id="product-preview"
      eyebrow="Product Preview"
      title="ALEX turns privacy work into a visible operating system"
      description="Preview the product surfaces teams use to validate privacy rules, investigate failures, monitor compliance workflows, and review scan outputs."
    >
      <div className="grid gap-5 xl:grid-cols-2">
        {previewCards.map(({ title, caption, variant }) => (
          <SurfaceFrame key={title} className="overflow-hidden rounded-[2rem] p-4">
            <div className="h-[320px]">
              <FauxProductPanel variant={variant} />
            </div>
            <div className="px-2 pb-2 pt-5">
              <p className="text-lg font-semibold text-app">{title}</p>
              <p className="mt-2 text-sm leading-7 text-app-secondary">{caption}</p>
            </div>
          </SurfaceFrame>
        ))}
      </div>
    </LandingSection>
  );
}
