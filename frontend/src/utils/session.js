import { apiUrl } from "./api";
import { readResponseData } from "./http";
import { clearAccessToken, setAccessToken } from "./tokenStore";

export async function rehydrateSession() {
  try {
    const response = await fetch(apiUrl("/auth/refresh"), {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      clearAccessToken();
      return false;
    }

    const { data } = await readResponseData(response);
    if (!data?.access_token) {
      clearAccessToken();
      return false;
    }

    setAccessToken(data.access_token);
    return true;
  } catch {
    clearAccessToken();
    return false;
  }
}
