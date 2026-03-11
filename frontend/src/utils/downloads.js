import { authFetch } from "./authFetch";

const SESSION_EXPIRED_MESSAGE = "Your session expired. Please log in again.";

function getFilenameFromDisposition(disposition, fallbackName) {
  const utfMatch = disposition?.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) {
    return decodeURIComponent(utfMatch[1]);
  }

  const asciiMatch = disposition?.match(/filename="?([^"]+)"?/i);
  return asciiMatch?.[1] || fallbackName;
}

export function getDownloadErrorMessage(status) {
  if (status === 401) {
    return SESSION_EXPIRED_MESSAGE;
  }
  if (status === 403) {
    return "You do not have permission to access this file or report.";
  }
  if (status === 404) {
    return "The requested file or report could not be found.";
  }
  if (status === 500) {
    return "The server could not complete the request.";
  }
  if (status === 501) {
    return "PDF report generation is currently unavailable.";
  }
  return "An unexpected error occurred while downloading the file or report.";
}

function buildDownloadError(status) {
  const error = new Error(getDownloadErrorMessage(status));
  error.status = status;
  return error;
}

export async function downloadProtectedAsset(path, fallbackName, expectedType = null) {
  let response;

  try {
    response = await authFetch(path);
  } catch (error) {
    if (error?.message === "Session expired. Please log in again.") {
      throw buildDownloadError(401);
    }
    throw buildDownloadError(null);
  }

  if (!response.ok) {
    throw buildDownloadError(response.status);
  }

  const contentType = (response.headers.get("Content-Type") || "").toLowerCase();
  if (expectedType === "pdf" && !contentType.includes("application/pdf")) {
    throw buildDownloadError(501);
  }

  const blob = await response.blob();
  const href = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = getFilenameFromDisposition(
    response.headers.get("Content-Disposition"),
    fallbackName || "download",
  );
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(href);
}
