import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/button";
import { apiUrl } from "../utils/api";

function base64UrlToUint8Array(base64Url) {
  const padding = "=".repeat((4 - (base64Url.length % 4)) % 4);
  const base64 = (base64Url + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

function arrayBufferToBase64Url(buffer) {
  const bytes = new Uint8Array(buffer);
  let str = "";
  bytes.forEach((b) => {
    str += String.fromCharCode(b);
  });
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function normalizeLoginOptions(options) {
  return {
    ...options,
    challenge: base64UrlToUint8Array(options.challenge),
    allowCredentials: (options.allowCredentials || []).map((cred) => ({
      ...cred,
      id: base64UrlToUint8Array(cred.id),
    })),
  };
}

function serializeAssertion(credential) {
  return {
    id: credential.id,
    rawId: arrayBufferToBase64Url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: arrayBufferToBase64Url(credential.response.clientDataJSON),
      authenticatorData: arrayBufferToBase64Url(
        credential.response.authenticatorData
      ),
      signature: arrayBufferToBase64Url(credential.response.signature),
      userHandle: credential.response.userHandle
        ? arrayBufferToBase64Url(credential.response.userHandle)
        : null,
    },
  };
}

function LoginForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (!window.PublicKeyCredential) {
        throw new Error("Passkeys are not supported in this browser.");
      }

      const safeEmail = encodeURIComponent(email.trim().toLowerCase());
      const optionsRes = await fetch(
        apiUrl(`/auth/webauthn/login/options?email=${safeEmail}`),
        {
          method: "POST",
          credentials: "include",
        }
      );
      const optionsData = await optionsRes.json();
      if (!optionsRes.ok) {
        throw new Error(optionsData.detail || "Failed to begin passkey login");
      }

      const publicKey = normalizeLoginOptions(optionsData);
      const credential = await navigator.credentials.get({ publicKey });
      if (!credential) {
        throw new Error("Passkey authentication was not completed.");
      }

      const verifyRes = await fetch(
        apiUrl(`/auth/webauthn/login/verify?email=${safeEmail}`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(serializeAssertion(credential)),
        }
      );
      const data = await verifyRes.json().catch(async () => {
        const txt = await verifyRes.text();
        throw new Error(txt || "Unexpected response from server");
      });

      if (!verifyRes.ok) {
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
          Welcome to ALEX
        </h2>
        <p className="text-gray-300 text-sm text-center mb-6 leading-relaxed">
          ALEX (Anonymization & Learning EXpert) helps detect and redact personally
          identifiable information while strengthening privacy protection.
        </p>
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

          <Button
            type="submit"
            className="w-full bg-indigo-600 text-white py-3 rounded-md hover:bg-indigo-700 transition-all duration-200 font-semibold"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign in with Passkey"}
          </Button>
          <p className="text-xs text-gray-400 text-center -mt-1">
            Secure passwordless sign-in using your device passkey.
          </p>
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
