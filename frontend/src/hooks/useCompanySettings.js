import { useEffect, useState } from "react";
import { authFetch } from "../utils/authFetch";
import { getResponseMessage, readResponseData } from "../utils/http";

const EMPTY_SETTINGS = {
  default_policy_label: "",
  default_report_display_name: "",
  allowed_upload_types: [],
  contact_email: "",
  compliance_mode: "",
  branding_primary_color: "",
  retention_days_display: "",
  retention_days: "",
};

export function useCompanySettings(enabled = false) {
  const [settings, setSettings] = useState(EMPTY_SETTINGS);
  const [loading, setLoading] = useState(enabled);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setSettings(EMPTY_SETTINGS);
      setLoading(false);
      setError(null);
      return;
    }

    let mounted = true;
    async function loadSettings() {
      setLoading(true);
      setError(null);
      try {
        const response = await authFetch("/admin/company-settings");
        const { data, text } = await readResponseData(response);
        if (!response.ok) {
          throw new Error(getResponseMessage(data, "Unable to load company settings", text));
        }
        if (mounted) {
          setSettings({
            default_policy_label: data?.default_policy_label || "",
            default_report_display_name: data?.default_report_display_name || "",
            allowed_upload_types: data?.allowed_upload_types || [],
            contact_email: data?.contact_email || "",
            compliance_mode: data?.compliance_mode || "",
            branding_primary_color: data?.branding_primary_color || "",
            retention_days_display: data?.retention_days_display || "",
            retention_days: data?.retention_days || "",
          });
        }
      } catch (err) {
        if (mounted) {
          setError(err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadSettings();
    return () => {
      mounted = false;
    };
  }, [enabled, reloadKey]);

  async function save(nextSettings) {
    setSaving(true);
    setSaveMessage(null);
    setError(null);
    try {
      const payload = {
        ...nextSettings,
        retention_days_display: nextSettings.retention_days_display
          ? Number(nextSettings.retention_days_display)
          : null,
        retention_days: nextSettings.retention_days
          ? Number(nextSettings.retention_days)
          : null,
      };
      const response = await authFetch("/admin/company-settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const { data, text } = await readResponseData(response);
      if (!response.ok) {
        throw new Error(getResponseMessage(data, "Unable to save company settings", text));
      }
      setSaveMessage(data?.detail || "Settings saved.");
      setSettings(nextSettings);
      return true;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setSaving(false);
    }
  }

  return {
    settings,
    setSettings,
    loading,
    saving,
    error,
    saveMessage,
    save,
    reload: () => setReloadKey((key) => key + 1),
  };
}
