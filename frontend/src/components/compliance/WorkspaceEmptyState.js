export default function WorkspaceEmptyState({ title, description, action }) {
  return (
    <div className="surface-card rounded-3xl border border-dashed border-app p-8 text-center">
      <p className="text-lg font-semibold text-app">{title}</p>
      <p className="mt-2 text-sm leading-7 text-app-secondary">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
