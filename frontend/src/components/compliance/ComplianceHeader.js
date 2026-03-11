export default function ComplianceHeader({ title, organizationName, description, actions }) {
  return (
    <section className="surface-panel rounded-[2rem] p-8 shadow-2xl">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-app-muted">Compliance Workspace</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-app">{title}</h1>
          <p className="mt-3 text-sm font-medium text-cyan-500">{organizationName}</p>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-app-secondary">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </div>
    </section>
  );
}
