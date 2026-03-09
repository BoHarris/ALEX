import React from "react";
import { Button } from "../components/button";
import { useCurrentUser } from "../hooks/useLoadUser";

function LogoutButton() {
  const { user } = useCurrentUser();

  const handleLogout = async () => {
    try {
      const response = await fetch("/auth/logout", {
        method: "POST",
        credentials: "include",
      });
      const data = await response.json();
      console.log(data.message);
      // Clear client-side tokens
      localStorage.removeItem("access_token");
      //redirect to /login
      window.location.href = "/login";
    } catch (err) {
      console.error("Logout failed: ", err);
    }
  };

  if (!user) {
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
