import { apiUrl } from "./api";
import { SUPPORTED_EXTENSIONS as FALLBACK_SUPPORTED_EXTENSIONS } from "./constants";

export async function fetchSupportedFileTypes() {
  const response = await fetch(apiUrl("/scans/supported-file-types"), {
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`Failed to load supported file types: ${response.status}`);
  }

  const payload = await response.json();
  const supportedExtensions = Array.isArray(payload?.supported_extensions)
    ? payload.supported_extensions
    : [];

  return supportedExtensions.length > 0 ? supportedExtensions : FALLBACK_SUPPORTED_EXTENSIONS;
}

export { FALLBACK_SUPPORTED_EXTENSIONS };
