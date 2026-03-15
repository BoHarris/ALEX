import { useEffect, useState } from "react";
import { authFetch } from "../utils/authFetch";
import { readResponseData } from "../utils/http";

export function useLLMStatus(companyId, enabled = false) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!enabled || !companyId) {
      setStatus(null);
      setLoading(false);
      setError(null);
      return;
    }

    let mounted = true;

    async function loadStatus() {
      setLoading(true);
      setError(null);
      try {
        const response = await authFetch(
          `/api/llm/status?company_id=${companyId}`,
        );
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const { data: body } = await readResponseData(response);
        if (!body) {
          throw new Error("Unexpected response from server");
        }
        if (mounted) {
          setStatus(body);
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

    loadStatus();
    return () => {
      mounted = false;
    };
  }, [companyId, enabled, reloadKey]);

  return { status, loading, error, reload: () => setReloadKey((k) => k + 1) };
}

export function useLLMTaskHistory(companyId, taskId, enabled = false) {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!enabled || !companyId || !taskId) {
      setHistory(null);
      setLoading(false);
      setError(null);
      return;
    }

    let mounted = true;

    async function loadHistory() {
      setLoading(true);
      setError(null);
      try {
        const response = await authFetch(
          `/api/llm/task-history/${taskId}?company_id=${companyId}`,
        );
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const { data: body } = await readResponseData(response);
        if (!body) {
          throw new Error("Unexpected response from server");
        }
        if (mounted) {
          setHistory(body);
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

    loadHistory();
    return () => {
      mounted = false;
    };
  }, [companyId, taskId, enabled, reloadKey]);

  return { history, loading, error, reload: () => setReloadKey((k) => k + 1) };
}

export async function updateLLMSettings(companyId, settings) {
  try {
    const params = new URLSearchParams();
    if (settings.enabled !== undefined) {
      params.append("enabled", settings.enabled);
    }
    if (settings.model) {
      params.append("model", settings.model);
    }
    if (settings.max_tokens !== undefined) {
      params.append("max_tokens", settings.max_tokens);
    }
    if (settings.temperature !== undefined) {
      params.append("temperature", settings.temperature);
    }

    const response = await authFetch(`/api/llm/settings?${params.toString()}`, {
      method: "POST",
    });

    if (!response.ok) {
      const body = await response.json();
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    const { data: result } = await readResponseData(response);
    return result;
  } catch (err) {
    throw err;
  }
}

export async function triggerLLMCompletion(companyId, taskId) {
  try {
    const response = await authFetch(
      `/api/llm/generate-completion/${taskId}?company_id=${companyId}`,
      {
        method: "POST",
      },
    );

    if (!response.ok) {
      const body = await response.json();
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    const { data: result } = await readResponseData(response);
    return result;
  } catch (err) {
    throw err;
  }
}
