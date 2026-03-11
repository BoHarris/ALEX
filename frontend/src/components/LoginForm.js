import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button } from "../components/button";
import { apiUrl } from "../utils/api";
import { getResponseMessage, readResponseData } from "../utils/http";
import { completeLogin } from "../utils/sessionCoordinator";

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
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [flash, setFlash] = useState(() => location.state?.flashMessage || null);
  const [flashTone, setFlashTone] = useState(() => location.state?.flashTone || "success");
  const [loading, setLoading] = useState(false);
  const flashMessage = location.state?.flashMessage || null;

  useEffect(() => {
    if (!flashMessage) {
      return;
    }

    setFlash(flashMessage);
    setFlashTone(location.state?.flashTone || "success");
    navigate(location.pathname, {
      replace: true,
      state: {},
    });
  }, [flashMessage, location.pathname, location.state, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (!window.PublicKeyCredential) {
        throw new Error("Passkeys are not supported in this browser.");
      }

      const safeEmail = email.trim().toLowerCase();
      const optionsRes = await fetch(
        apiUrl("/auth/webauthn/login/options"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ email: safeEmail }),
        }
      );
      const { data: optionsData, text: optionsText } = await readResponseData(optionsRes);
      if (!optionsRes.ok) {
        throw new Error(
          getResponseMessage(optionsData, "Failed to begin passkey login", optionsText),
        );
      }
      if (!optionsData) {
        throw new Error("Unexpected response from server");
      }

      const publicKey = normalizeLoginOptions(optionsData);
      const credential = await navigator.credentials.get({ publicKey });
      if (!credential) {
        throw new Error("Passkey authentication was not completed.");
      }

      const verifyRes = await fetch(
        apiUrl("/auth/webauthn/login/verify"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            email: safeEmail,
            credential: serializeAssertion(credential),
          }),
        }
      );
      const { data, text: verifyText } = await readResponseData(verifyRes);

      if (!verifyRes.ok) {
        throw new Error(getResponseMessage(data, "Login failed", verifyText));
      }
      if (!data) {
        throw new Error("Unexpected response from server");
      }

      completeLogin(data.access_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center gap-4 px-4">
      <div className="surface-card w-full max-w-md p-8 shadow-lg">
        <h1 className="mb-6 text-center text-3xl font-bold text-app">
          Welcome to ALEX
        </h1>
        <p className="mb-6 text-center text-sm leading-relaxed text-app-secondary">
          ALEX (Anonymization & Learning EXpert) helps detect and redact personally
          identifiable information while strengthening privacy protection.
        </p>
        {error && (
          <p className="mb-4 text-center text-red-500" role="alert">
            {error}
          </p>
        )}
        {flash && !error ? (
          <p
            className={`mb-4 text-center ${flashTone === "warning" ? "text-amber-500" : "text-emerald-600"}`}
            role="status"
          >
            {flash}
          </p>
        ) : null}

        <form onSubmit={handleSubmit} className="space-y-5" aria-busy={loading}>
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-app-secondary"
            >
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 w-full rounded-xl border border-app bg-app p-3 text-app focus-visible:outline-none"
            />
          </div>

          <Button
            type="submit"
            className="w-full py-3 font-semibold"
            disabled={loading}
            aria-disabled={loading}
          >
            {loading ? "Signing in..." : "Sign in with Passkey"}
          </Button>
          <p className="-mt-1 text-center text-xs text-app-muted" aria-live="polite">
            Secure passwordless sign-in using your device passkey.
          </p>
        </form>

        <div className="mt-4 text-center text-app-secondary">
          Don't have an account?{" "}
          <a
            href="/register"
            className="underline transition-colors hover:text-app"
          >
            Register here
          </a>
        </div>
      </div>
    </div>
  );
}

export default LoginForm;
