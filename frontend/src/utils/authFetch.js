import { apiUrl } from "./api";

export async function authFetch(path, options = {}) {
  let token = localStorage.getItem("access_token");

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
    localStorage.removeItem("access_token");
    throw new Error("Session expired. Please log in again.");
  }

  const data = await refreshResponse.json();
  localStorage.setItem("access_token", data.access_token);

  token = data.access_token;

  return doRequest(token);
}
