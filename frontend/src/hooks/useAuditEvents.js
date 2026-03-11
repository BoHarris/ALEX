import { useEffect, useState } from "react";
import { authFetch } from "../utils/authFetch";
import { getResponseMessage, readResponseData } from "../utils/http";

export function useAuditEvents(enabled = false, limit = 50) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setEvents([]);
      setLoading(false);
      setError(null);
      return;
    }

    let mounted = true;

    async function loadEvents() {
      setLoading(true);
      setError(null);
      try {
        const response = await authFetch(`/admin/audit-events?limit=${limit}`);
        const { data, text } = await readResponseData(response);
        if (!response.ok) {
          throw new Error(getResponseMessage(data, "Unable to load activity feed", text));
        }
        if (mounted) {
          setEvents(data?.events || []);
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

    loadEvents();
    return () => {
      mounted = false;
    };
  }, [enabled, limit, reloadKey]);

  return {
    events,
    loading,
    error,
    reload: () => setReloadKey((key) => key + 1),
  };
}
