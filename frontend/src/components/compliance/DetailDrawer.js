export default function DetailDrawer({ open, title, subtitle, onClose, children, widthClass = "max-w-2xl" }) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/55 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className="h-full flex-1 cursor-default" aria-label="Close drawer overlay" onClick={onClose} />
      <aside className={`h-full w-full ${widthClass} overflow-y-auto border-l border-app bg-app px-6 py-6 shadow-2xl`}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-app">{title}</h2>
            {subtitle ? <p className="mt-2 text-sm leading-6 text-app-secondary">{subtitle}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="rounded-full border border-app px-3 py-1 text-sm text-app-secondary hover:text-app focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300">
            Close
          </button>
        </div>
        <div className="mt-6 space-y-6">{children}</div>
      </aside>
    </div>
  );
}
