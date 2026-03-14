import { Link } from "react-router-dom";
import { ArrowIcon, LayersIcon, SearchIcon, ShieldIcon } from "./HomeIcons";

const signalCards = [
  { label: "Sensitive Records", value: "18.4M", detail: "streams evaluated this week", Icon: SearchIcon },
  { label: "Policy Packs", value: "GDPR / HIPAA / COPPA", detail: "aligned controls and taxonomy", Icon: LayersIcon },
  { label: "Audit Confidence", value: "Always-on", detail: "logs, tests, and evidence trails", Icon: ShieldIcon },
];

export default function HeroSection() {
  return (
    <section className="relative overflow-hidden rounded-[2.5rem] border border-app bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.24),transparent_28%),radial-gradient(circle_at_80%_20%,rgba(14,116,144,0.28),transparent_26%),linear-gradient(145deg,rgba(15,23,42,0.95),rgba(3,7,18,0.98))] px-6 py-12 shadow-[0_36px_120px_rgba(2,8,23,0.55)] sm:px-10 sm:py-16 lg:px-14 lg:py-20">
      <div className="absolute inset-0 opacity-30">
        <div className="absolute left-8 top-8 h-36 w-36 rounded-full bg-cyan-400/20 blur-3xl" />
        <div className="absolute bottom-10 right-10 h-48 w-48 rounded-full bg-sky-500/10 blur-3xl" />
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-300/80 to-transparent" />
      </div>

      <div className="relative grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] lg:items-center">
        <div>
          <p className="inline-flex items-center rounded-full border border-cyan-300/20 bg-cyan-300/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.26em] text-cyan-200">
            Privacy Infrastructure Platform
          </p>
          <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-tight tracking-tight text-app sm:text-5xl lg:text-6xl">
            Real-Time PII Detection and Redaction for Modern Data Systems
          </h1>
          <p className="mt-6 max-w-3xl text-lg leading-8 text-app-secondary">
            ALEX automatically detects sensitive data like emails, phone numbers, and SSNs and safely redacts them before data leaves your systems.
          </p>
          <p className="mt-4 text-sm uppercase tracking-[0.18em] text-app-muted">
            Built for privacy engineers, security teams, and data platforms.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/register" className="btn-primary-app inline-flex items-center gap-2 text-sm">
              Start Scanning
              <ArrowIcon />
            </Link>
            <a
              href="https://github.com/BoHarris/ALEX#readme"
              target="_blank"
              rel="noreferrer"
              className="btn-secondary-app inline-flex items-center gap-2 text-sm"
            >
              View API Documentation
              <ArrowIcon />
            </a>
          </div>
        </div>

        <div className="surface-card relative overflow-hidden rounded-[2rem] border border-white/10 p-6 backdrop-blur-sm">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-300/80 to-transparent" />
          <div className="grid gap-4">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/60 p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">Live Posture</p>
                  <p className="mt-3 text-4xl font-semibold text-app">82 / 100</p>
                </div>
                <div className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-200">
                  Moderate Risk
                </div>
              </div>
              <div className="mt-6 space-y-3">
                {[
                  ["Detection Coverage", "91%"],
                  ["Redaction Success", "87%"],
                  ["Policy Alignment", "76%"],
                  ["Testing Reliability", "83%"],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div className="flex items-center justify-between text-sm text-app-secondary">
                      <span>{label}</span>
                      <span>{value}</span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-white/10">
                      <div className="h-2 rounded-full bg-gradient-to-r from-cyan-400 to-teal-300" style={{ width: value }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              {signalCards.map(({ label, value, detail, Icon }) => (
                <div key={label} className="rounded-[1.35rem] border border-white/10 bg-white/5 p-4">
                  <Icon />
                  <p className="mt-4 text-xs font-semibold uppercase tracking-[0.18em] text-app-muted">{label}</p>
                  <p className="mt-2 text-xl font-semibold text-app">{value}</p>
                  <p className="mt-2 text-sm leading-6 text-app-secondary">{detail}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
