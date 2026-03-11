import { createContext, useContext, useEffect, useMemo, useState } from "react";

const DisplayPreferencesContext = createContext(null);

const THEME_KEY = "alex_theme_preference";
const FONT_KEY = "alex_font_preference";
const REDUCED_MOTION_KEY = "alex_reduced_motion";
const HIGH_CONTRAST_KEY = "alex_high_contrast";

function getSystemTheme() {
  if (typeof window === "undefined" || !window.matchMedia) {
    return "dark";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function readStoredPreference(key, fallback) {
  try {
    const value = window.localStorage.getItem(key);
    return value || fallback;
  } catch {
    return fallback;
  }
}

export function DisplayPreferencesProvider({ children }) {
  const [themePreference, setThemePreference] = useState(() => {
    if (typeof window === "undefined") return "system";
    return readStoredPreference(THEME_KEY, "system");
  });
  const [fontPreference, setFontPreference] = useState(() => {
    if (typeof window === "undefined") return "default";
    return readStoredPreference(FONT_KEY, "default");
  });
  const [announcement, setAnnouncement] = useState("");
  const [reducedMotion, setReducedMotion] = useState(() => {
    if (typeof window === "undefined") return "off";
    return readStoredPreference(REDUCED_MOTION_KEY, "off");
  });
  const [highContrast, setHighContrast] = useState(() => {
    if (typeof window === "undefined") return "off";
    return readStoredPreference(HIGH_CONTRAST_KEY, "off");
  });

  const effectiveTheme = themePreference === "system" ? getSystemTheme() : themePreference;

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", effectiveTheme);
  }, [effectiveTheme]);

  useEffect(() => {
    document.documentElement.setAttribute(
      "data-font",
      fontPreference === "dyslexia" ? "dyslexia" : "default",
    );
  }, [fontPreference]);

  useEffect(() => {
    document.documentElement.setAttribute(
      "data-reduced-motion",
      reducedMotion === "on" ? "true" : "false",
    );
  }, [reducedMotion]);

  useEffect(() => {
    document.documentElement.setAttribute(
      "data-contrast",
      highContrast === "on" ? "high" : "normal",
    );
  }, [highContrast]);

  useEffect(() => {
    try {
      window.localStorage.setItem(THEME_KEY, themePreference);
    } catch {
      // Ignore storage failures.
    }
  }, [themePreference]);

  useEffect(() => {
    try {
      window.localStorage.setItem(FONT_KEY, fontPreference);
    } catch {
      // Ignore storage failures.
    }
  }, [fontPreference]);

  useEffect(() => {
    try {
      window.localStorage.setItem(REDUCED_MOTION_KEY, reducedMotion);
    } catch {
      // Ignore storage failures.
    }
  }, [reducedMotion]);

  useEffect(() => {
    try {
      window.localStorage.setItem(HIGH_CONTRAST_KEY, highContrast);
    } catch {
      // Ignore storage failures.
    }
  }, [highContrast]);

  useEffect(() => {
    if (themePreference !== "system" || typeof window === "undefined" || !window.matchMedia) {
      return undefined;
    }
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      document.documentElement.setAttribute("data-theme", getSystemTheme());
    };
    mq.addEventListener("change", handleChange);
    return () => {
      mq.removeEventListener("change", handleChange);
    };
  }, [themePreference]);

  const value = useMemo(
    () => ({
      themePreference,
      fontPreference,
      reducedMotion,
      highContrast,
      effectiveTheme,
      setThemePreference: (valueToSet) => {
        setThemePreference(valueToSet);
        setAnnouncement(
          valueToSet === "system"
            ? "Theme set to system preference."
            : `Theme set to ${valueToSet} mode.`,
        );
      },
      setFontPreference: (valueToSet) => {
        setFontPreference(valueToSet);
        setAnnouncement(
          valueToSet === "dyslexia"
            ? "Dyslexia-friendly font enabled."
            : "Default font enabled.",
        );
      },
      setReducedMotion: (valueToSet) => {
        setReducedMotion(valueToSet);
        setAnnouncement(
          valueToSet === "on" ? "Reduced motion enabled." : "Reduced motion disabled.",
        );
      },
      setHighContrast: (valueToSet) => {
        setHighContrast(valueToSet);
        setAnnouncement(
          valueToSet === "on" ? "High contrast enabled." : "High contrast disabled.",
        );
      },
      announcement,
      clearAnnouncement: () => setAnnouncement(""),
    }),
    [
      themePreference,
      fontPreference,
      reducedMotion,
      highContrast,
      effectiveTheme,
      announcement,
    ],
  );

  return (
    <DisplayPreferencesContext.Provider value={value}>
      {children}
    </DisplayPreferencesContext.Provider>
  );
}

export function useDisplayPreferences() {
  const context = useContext(DisplayPreferencesContext);
  if (!context) {
    throw new Error("useDisplayPreferences must be used within DisplayPreferencesProvider");
  }
  return context;
}
