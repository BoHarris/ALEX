function formatRiskLevel(riskLevel) {
  const normalized = String(riskLevel || "").trim().toLowerCase();
  if (!normalized) {
    return "Unavailable";
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function ProgressRow({ label, value }) {
  const percent = Math.max(0, Math.min(Math.round((Number(value) || 0) * 100), 100));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-app-secondary">{label}</p>
        <p className="text-sm font-medium text-app">{percent}%</p>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-teal-300 to-emerald-300 transition-[width] duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

export default function PrivacyPostureCard({ posture }) {
  if (!posture) {
    return (
      <section className="surface-card rounded-3xl border p-6 text-app shadow-[0_18px_40px_rgba(2,8,23,0.24)]">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-app-muted">Privacy Posture</p>
        <p className="mt-5 text-3xl font-semibold leading-none">--</p>
        <p className="mt-3 text-sm text-app-secondary">Available when privacy metrics access is permitted for the current account.</p>
      </section>
    );
  }

  const componentScores = posture.component_scores || posture.components || {};

  return (
    <section className="surface-card rounded-3xl border p-6 text-app shadow-[0_18px_40px_rgba(2,8,23,0.24)]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-app-muted">Privacy Posture</p>
          <div className="mt-4 flex items-end gap-2">
            <p className="text-4xl font-semibold leading-none md:text-[2.8rem]">{posture.posture_score ?? 0}</p>
            <p className="pb-1 text-sm text-app-muted">/ 100</p>
          </div>
          <p className="mt-3 text-sm text-app-secondary">Risk Level: <span className="font-medium text-app">{formatRiskLevel(posture.risk_level)}</span></p>
        </div>
        {posture.top_risks?.length ? (
          <div className="max-w-md rounded-2xl border border-app px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-app-muted">Top Risk</p>
            <p className="mt-2 text-sm text-app-secondary">{posture.top_risks[0]}</p>
          </div>
        ) : null}
      </div>

      <div className="mt-6 space-y-4">
        <ProgressRow label="Detection Coverage" value={componentScores.detection_coverage} />
        <ProgressRow label="Redaction Success" value={componentScores.redaction_effectiveness} />
        <ProgressRow label="Policy Compliance" value={componentScores.policy_compliance} />
        <ProgressRow label="Testing Reliability" value={componentScores.testing_reliability} />
      </div>
    </section>
  );
}
