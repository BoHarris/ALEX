import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "./button";
import { apiUrl } from "../utils/api";
import { getResponseMessage, readResponseData } from "../utils/http";
import { completeLogin } from "../utils/sessionCoordinator";

const DEFAULT_EMPLOYEE_EMAIL = process.env.REACT_APP_DEFAULT_EMPLOYEE_EMAIL?.trim() || "";

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

const STATUS_REQUEST_TIMEOUT_MS = 5000;

export default function EmployeeLoginForm() {
  const [email, setEmail] = useState(DEFAULT_EMPLOYEE_EMAIL);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [activeAction, setActiveAction] = useState(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [employeeStatus, setEmployeeStatus] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;

    async function loadEmployeeStatus() {
      const safeEmail = email.trim().toLowerCase();
      if (!safeEmail) {
        setEmployeeStatus(null);
        setStatusLoading(false);
        return;
      }

      setStatusLoading(true);
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), STATUS_REQUEST_TIMEOUT_MS);
      try {
        setError(null);
        const response = await fetch(apiUrl("/auth/employee/webauthn/status"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          signal: controller.signal,
          body: JSON.stringify({ email: safeEmail }),
        });
        const { data, text } = await readResponseData(response);
        if (!response.ok) {
          throw new Error(getResponseMessage(data, "Unable to check employee access status", text));
        }
        if (!cancelled) {
          setEmployeeStatus(data);
        }
      } catch (err) {
        if (!cancelled) {
          setEmployeeStatus(null);
          setError(err.name === "AbortError" ? "Unable to verify employee passkey status. Check that the backend is running." : err.message);
        }
      } finally {
        window.clearTimeout(timeoutId);
        if (!cancelled) {
          setStatusLoading(false);
        }
      }
    }

    loadEmployeeStatus();
    return () => {
      cancelled = true;
    };
  }, [email]);

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
    completeLogin(data.access_token);
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
    const stagedRegistrationId = optionsData?.user_id || null;
    const credential = await navigator.credentials.create({ publicKey: normalizeRegistrationOptions(optionsData.options) });
    if (!credential) {
      throw new Error("Employee passkey enrollment was not completed.");
    }
    const verifyRes = await fetch(apiUrl("/auth/employee/webauthn/register/verify"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email: safeEmail, user_id: stagedRegistrationId, credential: serializeAttestation(credential) }),
    });
    const { data, text } = await readResponseData(verifyRes);
    if (!verifyRes.ok) {
      throw new Error(getResponseMessage(data, "Employee passkey enrollment failed", text));
    }
    setEmployeeStatus({ employee_found: true, passkey_enrolled: true, is_active: true });
    setMessage(data?.message || "Employee passkey enrolled. You can sign in now.");
  }

  async function handleAction(action) {
    setActiveAction(action);
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
      setActiveAction(null);
    }
  }

  const canAttemptLogin = Boolean(
    employeeStatus?.employee_found &&
    employeeStatus?.is_active &&
    employeeStatus?.passkey_enrolled,
  );
  const loginInProgress = activeAction === "login";
  const enrollInProgress = activeAction === "enroll";
  const actionInProgress = activeAction !== null;

  function renderStatusMessage() {
    if (statusLoading) {
      return "Checking employee passkey status...";
    }
    if (!employeeStatus) {
      return "Employee passkey status could not be verified. You can enroll a passkey, then try again.";
    }
    if (!employeeStatus?.employee_found) {
      return "No internal employee account was found for this email.";
    }
    if (!employeeStatus?.is_active) {
      return "This employee account is inactive.";
    }
    if (!employeeStatus?.passkey_enrolled) {
      return "No employee passkey is enrolled for this account yet. Enroll a passkey before signing in.";
    }
    return "Employee passkey is enrolled. You can sign in to the compliance workspace.";
  }

  return (
    <div className="surface-card w-full max-w-xl p-8 shadow-lg">
      <h1 className="text-center text-3xl font-bold text-app">Employee Access Portal</h1>
      <p className="mt-3 text-center text-sm leading-relaxed text-app-secondary">
        Internal access for ALEX governance, risk, compliance, and security operations.
      </p>
      {DEFAULT_EMPLOYEE_EMAIL ? (
        <p className="mt-2 text-center text-xs text-app-muted">
          Suggested employee account: <span className="font-semibold">{DEFAULT_EMPLOYEE_EMAIL}</span>
        </p>
      ) : null}
      <p className="mt-3 text-center text-xs text-app-secondary" role="status">{renderStatusMessage()}</p>
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
          <Button type="button" className="flex-1 py-3 font-semibold" disabled={actionInProgress || statusLoading || !canAttemptLogin} onClick={() => handleAction("login")}>
            {loginInProgress ? "Signing In..." : "Sign in to Compliance Workspace"}
          </Button>
          <Button type="button" className="flex-1 py-3 font-semibold" disabled={actionInProgress} onClick={() => handleAction("enroll")}>
            {enrollInProgress ? "Enrolling Passkey..." : "Enroll Employee Passkey"}
          </Button>
        </div>
      </div>
    </div>
  );
}
