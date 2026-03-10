import { useState, useEffect } from "react";
import { apiUrl } from "../utils/api";

export function useRedactedFiles() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(apiUrl("/scans"), {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setFiles(data.scans || []))
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, [reloadKey]);

  return { files, loading, error, reload: () => setReloadKey((key) => key + 1) };
}
