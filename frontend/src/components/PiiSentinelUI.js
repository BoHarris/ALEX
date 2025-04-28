import React, { useState } from "react";
import { Card, CardContent } from "../components/card";
import { Button } from "../components/button";
import { Input } from "../components/input";
import { SUPPORTED_EXTENSIONS } from "../utils/constants";

export default function PiiSentinelUI() {
  const [file, setFile] = useState(null);
  const [piiColumns, setPiiColumns] = useState([]);
  const [riskScore, setRiskScore] = useState(null);
  const [redactedFile, setRedactedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  // Reset state when a new file is selected
  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setPiiColumns([]);
    setRiskScore(null);
    setRedactedFile(null);
    setError(null);
  };

  // Upload file and handle errors with proper feedback
  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    console.log("Uploading file:", file);

    try {
      const res = await fetch("/predict/", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.statusText}`);
      }

      const data = await res.json();
      console.log("Response data:", data);
      setPiiColumns(data.pii_columns);
      setRiskScore(data.risk_score);
      setRedactedFile(data.redacted_file);
    } catch (error) {
      console.error("Error uploading file:", error);
      setError(
        error.message.includes("Network")
          ? "Network error. Please check your connection."
          : "Failed to scan file. Please try again."
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="py-12 px-4 flex flex-col items-center space-y-8 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold">
        🔐 PII Sentinel – Privacy as a Service
      </h1>

      <Card className="w-full shadow-md border border-gray-300 bg-white">
        <CardContent className="p-6 space-y-5">
          <div className="space-y-3">
            {/* Accessibility improvement: meaningful label */}
            <label
              htmlFor="file-upload"
              className="block font-semibold text-gray-800"
            >
              Upload a File
            </label>
            <Input
              id="file-upload"
              type="file"
              accept={SUPPORTED_EXTENSIONS.join(",")}
              required
              onChange={handleFileChange}
            />
            {file && (
              <p className="text-sm text-gray-500 mt-2">
                Selected file: {file.name}
              </p>
            )}

            <Button onClick={handleUpload} disabled={!file || uploading}>
              {uploading ? "Scanning..." : "Scan File for PII"}
            </Button>

            {/* Improved loading feedback */}
            {uploading && (
              <p className="text-sm italic text-gray-500">
                Uploading and analyzing file...
              </p>
            )}

            {/* Error message now visible when NOT uploading */}
            {error && !uploading && (
              <p className="text-sm text-red-600 font-medium">{error}</p>
            )}

            {/* Optional message when no PII columns found */}
            {piiColumns.length === 0 && !uploading && !error && file && (
              <p className="text-sm text-green-600 font-medium">
                No PII columns detected.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {piiColumns.length > 0 && (
        <Card className="w-full shadow-md bg-gray-800 border border-gray-600 text-white">
          <CardContent className="p-6 space-y-4">
            <h2 className="text-xl font-bold">🔎 PII Columns Detected:</h2>
            <div className="space-y-1 text-sm">
              {piiColumns.map((col) => (
                <div key={col}>{col}</div>
              ))}
            </div>
            <div className="mt-4">
              <p className="font-semibold">
                Risk Score before redaction:{" "}
                <span className="inline-block bg-gray-700 px-2 py-1 rounded text-white">
                  {" "}
                  {Math.round(riskScore * 100).toFixed(1)}%
                </span>
              </p>
            </div>

            {redactedFile && (
              <a
                href={`http://127.0.0.1:8000/${redactedFile}`}
                download
                className="inline-block text-blue-400 underline my-2"
              >
                📥 Download Redacted File
              </a>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
