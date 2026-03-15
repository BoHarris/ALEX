import { formatStatusLabel, statusBadgeClass } from "../../../pages/compliance/utils";

export default function TaskStatusBadge({ status }) {
  const normalized = status || "todo";

  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(normalized)}`}>
      {formatStatusLabel(normalized)}
    </span>
  );
}
