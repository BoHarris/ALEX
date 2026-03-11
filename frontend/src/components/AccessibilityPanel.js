import { useEffect, useId, useRef, useState } from "react";
import { useDisplayPreferences } from "../context/DisplayPreferencesContext";

export default function AccessibilityPanel() {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);
  const panelRef = useRef(null);
  const panelId = useId();
  const {
    themePreference,
    fontPreference,
    reducedMotion,
    highContrast,
    setThemePreference,
    setFontPreference,
    setReducedMotion,
    setHighContrast,
    announcement,
    clearAnnouncement,
  } = useDisplayPreferences();

  useEffect(() => {
    if (!announcement) return undefined;
    const timer = window.setTimeout(clearAnnouncement, 2500);
    return () => window.clearTimeout(timer);
  }, [announcement, clearAnnouncement]);

  useEffect(() => {
    if (!open) return undefined;

    const handleOutsideClick = (event) => {
      const target = event.target;
      if (
        panelRef.current &&
        !panelRef.current.contains(target) &&
        buttonRef.current &&
        !buttonRef.current.contains(target)
      ) {
        setOpen(false);
      }
    };

    const handleEscape = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  useEffect(() => {
    if (open) {
      panelRef.current?.querySelector("select, button")?.focus();
      return;
    }
    buttonRef.current?.focus();
  }, [open]);

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        className="btn-secondary-app px-4 py-1.5 text-sm"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
      >
        Accessibility
      </button>

      {open ? (
        <section
          ref={panelRef}
          id={panelId}
          role="dialog"
          aria-label="Accessibility preferences"
          className="surface-card absolute right-0 z-50 mt-2 w-[20rem] space-y-4 p-4 shadow-xl"
        >
          <header>
            <h2 className="text-sm font-semibold text-app">Accessibility</h2>
            <p className="mt-1 text-xs text-app-secondary">
              Configure display and motion preferences.
            </p>
          </header>

          <div className="space-y-1">
            <label htmlFor="accessibility-theme" className="text-xs font-medium uppercase tracking-[0.16em] text-app-muted">
              Theme
            </label>
            <select
              id="accessibility-theme"
              value={themePreference}
              onChange={(event) => setThemePreference(event.target.value)}
              className="w-full rounded-lg border border-app bg-app px-2 py-2 text-sm text-app"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </div>

          <div className="space-y-1">
            <label htmlFor="accessibility-font" className="text-xs font-medium uppercase tracking-[0.16em] text-app-muted">
              Font
            </label>
            <select
              id="accessibility-font"
              value={fontPreference}
              onChange={(event) => setFontPreference(event.target.value)}
              className="w-full rounded-lg border border-app bg-app px-2 py-2 text-sm text-app"
            >
              <option value="default">Default</option>
              <option value="dyslexia">OpenDyslexic</option>
            </select>
          </div>

          <div className="space-y-1">
            <label htmlFor="accessibility-motion" className="text-xs font-medium uppercase tracking-[0.16em] text-app-muted">
              Reduced Motion
            </label>
            <select
              id="accessibility-motion"
              value={reducedMotion}
              onChange={(event) => setReducedMotion(event.target.value)}
              className="w-full rounded-lg border border-app bg-app px-2 py-2 text-sm text-app"
            >
              <option value="off">Off</option>
              <option value="on">On</option>
            </select>
          </div>

          <div className="space-y-1">
            <label htmlFor="accessibility-contrast" className="text-xs font-medium uppercase tracking-[0.16em] text-app-muted">
              High Contrast
            </label>
            <select
              id="accessibility-contrast"
              value={highContrast}
              onChange={(event) => setHighContrast(event.target.value)}
              className="w-full rounded-lg border border-app bg-app px-2 py-2 text-sm text-app"
            >
              <option value="off">Off</option>
              <option value="on">On</option>
            </select>
          </div>

          <span className="sr-only" role="status" aria-live="polite">
            {announcement}
          </span>
        </section>
      ) : null}
    </div>
  );
}

