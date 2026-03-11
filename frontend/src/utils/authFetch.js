import { apiUrl } from "./api";
import { getAccessToken } from "./tokenStore";
import { refreshSessionOrExpire } from "./session";

export async function authFetch(path, options = {}) {
  let token = getAccessToken();

  const doRequest = async (accessToken) => {
    return fetch(apiUrl(path), {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      credentials: "include",
    });
  };

  let response = await doRequest(token);

  if (response.status !== 401) {
    return response;
  }

  const recovered = await refreshSessionOrExpire();
  if (!recovered) {
    throw new Error("Session expired. Please log in again.");
  }

  token = getAccessToken();
  return doRequest(token);
}
