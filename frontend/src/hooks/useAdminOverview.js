import { useEffect, useState } from "react";
import { authFetch } from "../utils/authFetch";
import { readResponseData } from "../utils/http";

export function useAdminOverview(enabled = false) {
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

    async function loadOverview() {
      setLoading(true);
      setError(null);
      try {
        const response = await authFetch("/admin/overview");
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const { data: body } = await readResponseData(response);
        if (!body) {
          throw new Error("Unexpected response from server");
        }
        if (mounted) {
          setData(body);
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

    loadOverview();
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
