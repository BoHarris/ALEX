const priorityClass = {
  low: "bg-emerald-500/15 text-emerald-300 border border-emerald-400/30",
  medium: "bg-amber-500/15 text-amber-200 border border-amber-400/30",
  high: "bg-orange-500/15 text-orange-200 border border-orange-400/30",
  critical: "bg-rose-500/15 text-rose-300 border border-rose-400/30",
};

export default function TaskPriorityBadge({ priority }) {
  const normalized = (priority || "medium").toLowerCase();
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${priorityClass[normalized] || "bg-white/5 text-app-secondary border border-app"}`}>
      {normalized}
    </span>
  );
}
