import { useState, useEffect } from "react";
import { apiUrl } from "../utils/api";

export function useCurrentUser() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    async function loadUser() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(apiUrl("/protected/me"), {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        });
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        console.log("me ➡️", data);
        setUser(data);
        setLoading(false);
      } catch (err) {
        console.error("Failed to load user:", err);
        setError(err);
        setLoading(false);
      }
    }
    loadUser();
  }, [reloadKey]);

  return { user, loading, error, reload: () => setReloadKey((key) => key + 1) };
}
