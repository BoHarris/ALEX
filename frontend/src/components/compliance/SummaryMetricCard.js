export default function SummaryMetricCard({ label, value, hint }) {
  return (
    <div className="surface-card rounded-3xl border p-5 text-app">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">{label}</p>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
      {hint ? <p className="mt-2 text-sm text-app-secondary">{hint}</p> : null}
    </div>
  );
}
