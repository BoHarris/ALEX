import { React, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/button";
import useFingerPrint from "../utils/useFingerprint";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { fingerprint } = useFingerPrint();
  const navigate = useNavigate();

  useEffect(() => {
    if (fingerprint) {
      console.log("Fingerprint loaded ", fingerprint);
    }
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!fingerprint) {
      setError("Device fingerprint not ready yet, please wait a moment.");
    }
    setLoading(true);
    setError(null); // Reset any previous errors

    const formData = new URLSearchParams();
    formData.append("username", email.trim().toLowerCase());
    formData.append("password", password);
    formData.append("grant_type", "password");
    formData.append("device_fingerprint", fingerprint);

    try {
      const res = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/auth/token`,
        {
          method: "POST",
          credentials: "include",
          body: formData,
        }
      );

      const data = await res.json().catch(async () => {
        const txt = await res.text();
        throw new Error(txt || "Unexpected response from server");
      });

      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }

      localStorage.setItem("access_token", data.access_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 flex items-center justify-center bg-gray-900 px-4">
      <div className="max-w-md w-full bg-gray-800 p-8 rounded-lg shadow-lg">
        <h2 className="text-3xl font-bold text-white mb-6 text-center">
          Welcome Back to ALEX.ai
        </h2>
        {error && <p className="text-red-500 mb-4 text-center">{error}</p>}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-300"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 w-full p-3 rounded-md bg-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-300"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 w-full p-3 rounded-md bg-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <Button
            type="submit"
            className="w-full bg-indigo-600 text-white py-3 rounded-md hover:bg-indigo-700 transition-all duration-200 font-semibold"
            disabled={loading}
          >
            {loading ? "Logging in.." : "Log In"}
          </Button>
        </form>

        <div className="text-gray-400 text-center mt-4">
          Don't have an account?{" "}
          <a
            href="/register"
            className="text-indigo-400 hover:text-indigo-200 underline"
          >
            Register here
          </a>
        </div>
      </div>
    </div>
  );
}

export default LoginForm;
