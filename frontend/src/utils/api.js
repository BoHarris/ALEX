const rawApiBase = process.env.REACT_APP_BACKEND_URL?.trim();

export const API_BASE_URL = rawApiBase
  ? rawApiBase.replace(/\/+$/, "")
  : "";

export function apiUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export const assetUrl = apiUrl;
