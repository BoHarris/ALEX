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

  const isLeft = side === "left";
  const isCenter = side === "center";
  const alignmentClass = isCenter ? "items-center justify-center" : isLeft ? "justify-start" : "justify-end";
  const panelBorderClass = isCenter ? "border" : isLeft ? "border-r" : "border-l";
  const overlayButtonOrder = isLeft ? "order-2" : "order-1";
  const panelOrder = isLeft ? "order-1" : "order-2";

  return (
    <div className={`fixed inset-0 z-50 flex ${alignmentClass} bg-slate-950/45 backdrop-blur-sm ${containerClass}`} role="dialog" aria-modal="true" aria-label={title}>
      <button
        type="button"
        className={`${isCenter ? "absolute inset-0" : `h-full flex-1 cursor-default ${overlayButtonOrder}`}`}
        aria-label="Close drawer overlay"
        onClick={onClose}
      />
      <aside className={`${isCenter ? "relative max-h-[calc(100vh-7rem)]" : `${panelOrder} h-full`} w-full ${widthClass} overflow-y-auto ${panelBorderClass} border-app bg-app px-6 py-6 shadow-2xl ${panelClass}`}>
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
