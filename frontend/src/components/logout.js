import React from "react";
import { Button } from "../components/button";
import { invalidateCurrentUserCache } from "../hooks/useLoadUser";
import { apiUrl } from "../utils/api";
import { readResponseData } from "../utils/http";
import { clearAccessToken, getAccessToken } from "../utils/tokenStore";

function LogoutButton() {
  const hasToken = Boolean(getAccessToken());

  const handleLogout = async () => {
    try {
      const response = await fetch(apiUrl("/auth/logout"), {
        method: "POST",
        credentials: "include",
      });
      await readResponseData(response);
      clearAccessToken();
      invalidateCurrentUserCache();
      //redirect to /login
      window.location.href = "/login";
    } catch (err) {
      console.error("Logout failed: ", err);
    }
  };

  if (!hasToken) {
    return null;
  }
  return (
    <Button
      onClick={handleLogout}
      className="text-sm text-red-600 hover:underline"
    >
      Logout
    </Button>
  );
}

export default LogoutButton;
