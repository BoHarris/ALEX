import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "./button";
import { apiUrl } from "../utils/api";
import { getResponseMessage, readResponseData } from "../utils/http";
import { setAccessToken } from "../utils/tokenStore";

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

function normalizeOptions(options) {
  return {
    ...options,
    challenge: base64UrlToUint8Array(options.challenge),
    allowCredentials: (options.allowCredentials || []).map((cred) => ({
      ...cred,
      id: base64UrlToUint8Array(cred.id),
    })),
  };
}

function normalizeRegistrationOptions(options) {
  return {
    ...options,
    challenge: base64UrlToUint8Array(options.challenge),
    user: {
      ...options.user,
      id: base64UrlToUint8Array(options.user.id),
    },
  };
}

function serializeAssertion(credential) {
  return {
    id: credential.id,
    rawId: arrayBufferToBase64Url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: arrayBufferToBase64Url(credential.response.clientDataJSON),
      authenticatorData: arrayBufferToBase64Url(credential.response.authenticatorData),
      signature: arrayBufferToBase64Url(credential.response.signature),
      userHandle: credential.response.userHandle ? arrayBufferToBase64Url(credential.response.userHandle) : null,
    },
  };
}

function serializeAttestation(credential) {
  return {
    id: credential.id,
    rawId: arrayBufferToBase64Url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: arrayBufferToBase64Url(credential.response.clientDataJSON),
      attestationObject: arrayBufferToBase64Url(credential.response.attestationObject),
    },
  };
}

export default function EmployeeLoginForm() {
  const [email, setEmail] = useState("bo.harris@boharrisllc.internal");
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function runEmployeeLogin() {
    const safeEmail = email.trim().toLowerCase();
    const optionsRes = await fetch(apiUrl("/auth/employee/webauthn/login/options"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email: safeEmail }),
    });
    const { data: optionsData, text: optionsText } = await readResponseData(optionsRes);
    if (!optionsRes.ok) {
      throw new Error(getResponseMessage(optionsData, "Failed to begin employee login", optionsText));
    }
    const credential = await navigator.credentials.get({ publicKey: normalizeOptions(optionsData) });
    if (!credential) {
      throw new Error("Employee passkey authentication was not completed.");
    }
    const verifyRes = await fetch(apiUrl("/auth/employee/webauthn/login/verify"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email: safeEmail, credential: serializeAssertion(credential) }),
    });
    const { data, text } = await readResponseData(verifyRes);
    if (!verifyRes.ok) {
      throw new Error(getResponseMessage(data, "Employee login failed", text));
    }
    setAccessToken(data.access_token);
    navigate("/compliance");
  }

  async function runEmployeeEnrollment() {
    const safeEmail = email.trim().toLowerCase();
    const optionsRes = await fetch(apiUrl("/auth/employee/webauthn/register/options"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email: safeEmail }),
    });
    const { data: optionsData, text: optionsText } = await readResponseData(optionsRes);
    if (!optionsRes.ok) {
      throw new Error(getResponseMessage(optionsData, "Failed to begin employee enrollment", optionsText));
    }
    const credential = await navigator.credentials.create({ publicKey: normalizeRegistrationOptions(optionsData.options) });
    if (!credential) {
      throw new Error("Employee passkey enrollment was not completed.");
    }
    const verifyRes = await fetch(apiUrl("/auth/employee/webauthn/register/verify"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email: safeEmail, credential: serializeAttestation(credential) }),
    });
    const { data, text } = await readResponseData(verifyRes);
    if (!verifyRes.ok) {
      throw new Error(getResponseMessage(data, "Employee passkey enrollment failed", text));
    }
    setMessage(data?.message || "Employee passkey enrolled. You can sign in now.");
  }

  async function handleAction(action) {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      if (!window.PublicKeyCredential) {
        throw new Error("Passkeys are not supported in this browser.");
      }
      if (action === "enroll") {
        await runEmployeeEnrollment();
      } else {
        await runEmployeeLogin();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="surface-card w-full max-w-xl p-8 shadow-lg">
      <h1 className="text-center text-3xl font-bold text-app">Employee Access Portal</h1>
      <p className="mt-3 text-center text-sm leading-relaxed text-app-secondary">
        Internal access for ALEX governance, risk, compliance, and security operations.
      </p>
      <p className="mt-2 text-center text-xs text-app-muted">
        Initial seeded employee account: <span className="font-semibold">{email}</span>
      </p>
      {error ? <p className="mt-4 text-center text-red-500" role="alert">{error}</p> : null}
      {message ? <p className="mt-4 text-center text-emerald-600" role="status">{message}</p> : null}
      <div className="mt-6 space-y-4">
        <label className="block text-sm font-medium text-app-secondary" htmlFor="employee-email">
          Employee Email
        </label>
        <input
          id="employee-email"
          name="employee-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full rounded-xl border border-app bg-app p-3 text-app focus-visible:outline-none"
          required
        />
        <div className="flex flex-wrap gap-3">
          <Button type="button" className="flex-1 py-3 font-semibold" disabled={loading} onClick={() => handleAction("login")}>
            {loading ? "Working..." : "Sign in to Compliance Workspace"}
          </Button>
          <Button type="button" className="flex-1 py-3 font-semibold" disabled={loading} onClick={() => handleAction("enroll")}>
            Enroll Employee Passkey
          </Button>
        </div>
      </div>
    </div>
  );
}
