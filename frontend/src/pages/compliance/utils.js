export function formatDateTime(value) {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function formatDate(value) {
  if (!value) {
    return "Not set";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString();
}

export function formatStatusLabel(value) {
  const normalized = (value || "").toLowerCase();
  if (!normalized) {
    return "Not set";
  }
  const labels = {
    todo: "To do",
    in_progress: "In progress",
    ready_for_review: "Ready for review",
  };
  if (labels[normalized]) {
    return labels[normalized];
  }
  return normalized
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export function formatTaskPriorityLabel(value) {
  const normalized = (value || "").toLowerCase();
  if (!normalized) {
    return "Not set";
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

export function statusTone(status = "") {
  const normalized = status.toLowerCase();
  if (["failed", "high", "critical", "closed", "inactive", "archived", "revoked", "degrading", "failing", "regressed", "canceled", "overdue"].includes(normalized)) {
    return "text-rose-600";
  }
  if (["completed", "approved", "published", "active", "passed", "stable", "improving", "low", "done"].includes(normalized)) {
    return "text-emerald-600";
  }
  if (["ready_for_review"].includes(normalized)) {
    return "text-blue-300";
  }
  if (["pending", "todo", "investigating", "in_review", "flagged", "skipped", "not_run", "resolved", "medium", "queued"].includes(normalized)) {
    return "text-amber-600";
  }
  if (["flaky", "unstable", "running", "in_progress", "blocked"].includes(normalized)) {
    return "text-cyan-300";
  }
  return "text-app-secondary";
}

export function statusBadgeClass(status = "") {
  const normalized = status.toLowerCase();
  if (["failed", "high", "critical", "closed", "inactive", "archived", "revoked", "degrading", "failing", "regressed", "canceled", "overdue"].includes(normalized)) {
    return "bg-rose-500/15 text-rose-300 border border-rose-400/30";
  }
  if (["completed", "approved", "published", "active", "passed", "stable", "improving", "low", "done"].includes(normalized)) {
    return "bg-emerald-500/15 text-emerald-300 border border-emerald-400/30";
  }
  if (["ready_for_review"].includes(normalized)) {
    return "bg-blue-500/15 text-blue-200 border border-blue-400/30";
  }
  if (["pending", "todo", "investigating", "in_review", "flagged", "skipped", "not_run", "resolved", "medium", "queued"].includes(normalized)) {
    return "bg-amber-500/15 text-amber-200 border border-amber-400/30";
  }
  if (["flaky", "unstable", "running", "in_progress", "blocked"].includes(normalized)) {
    return "bg-cyan-500/15 text-cyan-200 border border-cyan-400/30";
  }
  return "bg-white/5 text-app-secondary border border-app";
}

export function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return "N/A";
  }
  return `${Number(value).toFixed(0)}%`;
}
