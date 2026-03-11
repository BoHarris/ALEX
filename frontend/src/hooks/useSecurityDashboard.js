import { useEffect, useState } from "react";
import { authFetch } from "../utils/authFetch";
import { getResponseMessage, readResponseData } from "../utils/http";

export function useSecurityDashboard(enabled = false) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    let mounted = true;
    async function loadSecurityDashboard() {
      setLoading(true);
      setError(null);
      try {
        const response = await authFetch("/admin/security-dashboard");
        const { data: body, text } = await readResponseData(response);
        if (!response.ok) {
          throw new Error(getResponseMessage(body, "Unable to load security dashboard", text));
        }
        if (mounted) {
          setData(body || null);
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

    loadSecurityDashboard();
    return () => {
      mounted = false;
    };
  }, [enabled, reloadKey]);

  return {
    data,
    loading,
    error,
    reload: () => setReloadKey((key) => key + 1),
  };
}
