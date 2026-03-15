export default function LinkedTaskPill({ label, onClick, tone = "default" }) {
  const toneClass =
    tone === "accent"
      ? "border-cyan-300/40 bg-cyan-400/10 text-cyan-100"
      : "border-app bg-app/40 text-app-secondary";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-semibold transition hover:text-app ${toneClass}`}
    >
      {label}
    </button>
  );
}
