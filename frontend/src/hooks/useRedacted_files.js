import { useState, useEffect } from "react";
import { authFetch } from "../utils/authFetch";
import { readResponseData } from "../utils/http";

export function useRedactedFiles() {
  const [files, setFiles] = useState([]);
  const [archivedFiles, setArchivedFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    async function loadFiles() {
      setLoading(true);
      setError(null);
      try {
        const res = await authFetch("/scans");
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const { data } = await readResponseData(res);
        if (!data) {
          throw new Error("Unexpected response from server");
        }

        setFiles(data.scans || []);
        setArchivedFiles(data.archived_scans || []);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    }

    loadFiles();
  }, [reloadKey]);

  async function archiveScan(scanId) {
    const res = await authFetch(`/scans/${scanId}/archive`, { method: "POST" });
    if (!res.ok) {
      throw new Error(`Failed to archive scan (HTTP ${res.status})`);
    }
    setReloadKey((key) => key + 1);
  }

  async function restoreScan(scanId) {
    const res = await authFetch(`/scans/${scanId}/restore`, { method: "POST" });
    if (!res.ok) {
      throw new Error(`Failed to restore scan (HTTP ${res.status})`);
    }
    setReloadKey((key) => key + 1);
  }

  return {
    files,
    archivedFiles,
    loading,
    error,
    archiveScan,
    restoreScan,
    reload: () => setReloadKey((key) => key + 1),
  };
}
