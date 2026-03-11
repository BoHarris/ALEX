export async function readResponseData(response) {
  const text = await response.text().catch(() => "");

  if (!text) {
    return { data: null, text: "" };
  }

  try {
    return { data: JSON.parse(text), text };
  } catch {
    return { data: null, text };
  }
}

export function getResponseMessage(data, fallbackMessage, rawText = "") {
  if (data && typeof data === "object") {
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
    if (typeof data.message === "string" && data.message.trim()) {
      return data.message;
    }
    if (typeof data.error === "string" && data.error.trim()) {
      return data.error;
    }
  }

  if (rawText.toLowerCase().includes("proxy error")) {
    return "Unable to reach the server. Check that the API is running.";
  }

  return fallbackMessage;
}
