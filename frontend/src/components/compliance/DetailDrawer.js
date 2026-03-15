import { useEffect } from "react";

export default function DetailDrawer({
  open,
  title,
  subtitle,
  onClose,
  children,
  widthClass = "max-w-2xl",
  side = "right",
  containerClass = "",
  panelClass = "",
}) {
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onClose?.();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  const isCenter = side === "center";
  const isLeft = side === "left";
  const alignmentClass = isCenter ? "justify-center items-center p-3 sm:p-6" : (isLeft ? "justify-start" : "justify-end");
  const panelBorderClass = isLeft ? "border-r" : "border-l";
  const overlayButtonOrder = isLeft ? "order-2" : "order-1";
  const panelOrder = isLeft ? "order-1" : "order-2";

  if (isCenter) {
    return (
      <div className={`fixed inset-0 z-50 flex ${alignmentClass} bg-slate-950/45 backdrop-blur-sm ${containerClass}`} role="dialog" aria-modal="true" aria-label={title}>
        <button type="button" className="absolute inset-0 cursor-default" aria-label="Close drawer overlay" onClick={onClose} />
        <aside className={`relative z-10 w-full ${widthClass} max-h-[calc(100vh-1.5rem)] overflow-y-auto rounded-[28px] border border-app bg-app px-5 py-5 shadow-2xl sm:max-h-[calc(100vh-3rem)] sm:px-6 sm:py-6 ${panelClass}`}>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h2 className="text-2xl font-semibold text-app">{title}</h2>
              {subtitle ? <p className="mt-2 break-words text-sm leading-6 text-app-secondary">{subtitle}</p> : null}
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

  return (
    <div className={`fixed inset-0 z-50 flex ${alignmentClass} bg-slate-950/45 backdrop-blur-sm ${containerClass}`} role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className={`h-full flex-1 cursor-default ${overlayButtonOrder}`} aria-label="Close drawer overlay" onClick={onClose} />
      <aside className={`${panelOrder} h-full w-full ${widthClass} overflow-y-auto ${panelBorderClass} border-app bg-app px-6 py-6 shadow-2xl ${panelClass}`}>
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
