import FingerprintJS from "@fingerprintjs/fingerprintjs";
import { useState, useEffect } from "react";

export default function useFingerprint() {
  const [fingerprint, setFingerprint] = useState("");

  // Load fingerprint on component mount
  useEffect(() => {
    const getFingerprint = async () => {
      // Initialize FingerprintJS
      const fp = await FingerprintJS.load();
      // Get the visitor identifier
      const result = await fp.get();
      setFingerprint(result.visitorId); // Set the fingerprint ID
    };
    getFingerprint();
  }, []);

  return { fingerprint };
}
