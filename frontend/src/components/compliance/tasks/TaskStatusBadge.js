import { statusBadgeClass } from "../../../pages/compliance/utils";

export default function TaskStatusBadge({ status }) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(status || "todo")}`}>
      {status || "todo"}
    </span>
  );
}
