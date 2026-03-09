import { useState, useEffect } from "react";

export function useRedactedFiles() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const backendURL = process.env.REACT_APP_BACKEND_URL;
    fetch(`${backendURL}/redacted/files`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setFiles(data.files || []))
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  return { files, loading, error };
}
