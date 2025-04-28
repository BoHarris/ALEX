import { useState, useEffect } from "react";

export function useCurrentUser() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => {
    async function loadUser() {
      try {
        const res = await fetch("/protected/me", {
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
  }, []);

  return { user, loading, error };
}
