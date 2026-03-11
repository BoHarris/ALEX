import { useState, useEffect } from "react";
import { authFetch } from "../utils/authFetch";
import {
  getCachedUser,
  getCachedUserPromise,
  invalidateCurrentUserCache,
  isCurrentUserCacheInitialized,
  setCachedUser,
  setCachedUserPromise,
} from "../utils/currentUserCache";
import { readResponseData } from "../utils/http";
import { getAccessToken } from "../utils/tokenStore";

async function fetchCurrentUser() {
  const existingPromise = getCachedUserPromise();
  if (existingPromise) {
    return existingPromise;
  }

  const nextPromise = (async () => {
    const res = await authFetch("/protected/me");
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const { data } = await readResponseData(res);
    if (!data) {
      throw new Error("Unexpected response from server");
    }
    setCachedUser(data);
    return data;
  })();
  setCachedUserPromise(nextPromise);

  try {
    return await nextPromise;
  } finally {
    setCachedUserPromise(null);
  }
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

        if (isCurrentUserCacheInitialized() && reloadKey === 0) {
          if (mounted) {
            setUser(getCachedUser());
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
