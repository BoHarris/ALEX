export default function SummaryMetricCard({ label, value, hint }) {
  return (
    <div className="surface-card relative overflow-hidden rounded-3xl border p-6 text-app shadow-[0_18px_40px_rgba(2,8,23,0.24)]">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-cyan-300/0 via-cyan-300/70 to-cyan-300/0" />
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-app-muted">{label}</p>
      <div className="mt-5 flex items-end justify-between gap-3">
        <p className="text-4xl font-semibold leading-none md:text-[2.6rem]">{value}</p>
        {hint ? <p className="max-w-[9rem] text-right text-xs leading-5 text-app-secondary">{hint}</p> : null}
      </div>
    </div>
  );
}
