import { apiUrl } from "./api";
import { readResponseData } from "./http";
import { clearAccessToken, getAccessToken, setAccessToken } from "./tokenStore";

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

  const refreshResponse = await fetch(apiUrl("/auth/refresh"), {
    method: "POST",
    credentials: "include",
  });

  if (!refreshResponse.ok) {
    clearAccessToken();
    throw new Error("Session expired. Please log in again.");
  }

  const { data } = await readResponseData(refreshResponse);
  if (!data?.access_token) {
    clearAccessToken();
    throw new Error("Session expired. Please log in again.");
  }
  setAccessToken(data.access_token);

  token = data.access_token;

  return doRequest(token);
}
