import { useEffect, useState } from "react";
import { authFetch } from "../utils/authFetch";
import { readResponseData } from "../utils/http";

function getCompanyUsersErrorMessage(status) {
  if (status === 401) {
    return "Your session expired. Please log in again.";
  }
  if (status === 403) {
    return "You do not have permission to view company users.";
  }
  if (status === 404) {
    return "Company user data could not be found.";
  }
  return "Unable to load company users right now.";
}

export function useCompanyUsers(enabled = false) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setUsers([]);
      setLoading(false);
      setError(null);
      return;
    }

    async function loadUsers() {
      setLoading(true);
      setError(null);
      try {
        const res = await authFetch("/companies/me/users");
        if (!res.ok) {
          throw new Error(getCompanyUsersErrorMessage(res.status));
        }

        const { data } = await readResponseData(res);
        if (!data) {
          throw new Error("Unable to load company users right now.");
        }

        setUsers(data.users || []);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    }

    loadUsers();
  }, [enabled, reloadKey]);

  return {
    users,
    loading,
    error,
    reload: () => setReloadKey((key) => key + 1),
  };
}
