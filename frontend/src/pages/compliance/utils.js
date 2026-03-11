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

export function statusTone(status = "") {
  const normalized = status.toLowerCase();
  if (["failed", "high", "closed", "inactive", "archived", "revoked"].includes(normalized)) {
    return "text-rose-600";
  }
  if (["completed", "approved", "published", "active", "passed"].includes(normalized)) {
    return "text-emerald-600";
  }
  if (["pending", "investigating", "in_review", "flagged"].includes(normalized)) {
    return "text-amber-600";
  }
  return "text-app-secondary";
}
