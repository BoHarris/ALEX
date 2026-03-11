import { useState, useEffect } from "react";
import { authFetch } from "../utils/authFetch";
import { readResponseData } from "../utils/http";
import { getAccessToken } from "../utils/tokenStore";

let cachedUser = null;
let cachedUserPromise = null;
let cacheInitialized = false;

async function fetchCurrentUser() {
  if (cachedUserPromise) {
    return cachedUserPromise;
  }

  cachedUserPromise = (async () => {
    const res = await authFetch("/protected/me");
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const { data } = await readResponseData(res);
    if (!data) {
      throw new Error("Unexpected response from server");
    }
    cachedUser = data;
    cacheInitialized = true;
    return data;
  })();

  try {
    return await cachedUserPromise;
  } finally {
    cachedUserPromise = null;
  }
}

export function invalidateCurrentUserCache() {
  cachedUser = null;
  cachedUserPromise = null;
  cacheInitialized = false;
}

export function useCurrentUser() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let mounted = true;

    async function loadUser() {
      setLoading(true);
      setError(null);
      try {
        if (!getAccessToken()) {
          invalidateCurrentUserCache();
          if (mounted) {
            setUser(null);
            setLoading(false);
          }
          return;
        }

        if (cacheInitialized && reloadKey === 0) {
          if (mounted) {
            setUser(cachedUser);
            setLoading(false);
          }
          return;
        }

        const loadedUser = await fetchCurrentUser();
        if (mounted) {
          setUser(loadedUser);
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

    loadUser();

    return () => {
      mounted = false;
    };
  }, [reloadKey]);

  return {
    user,
    loading,
    error,
    reload: () => {
      invalidateCurrentUserCache();
      setReloadKey((key) => key + 1);
    },
  };
}
