import React, { useState } from "react";
import { Button } from "../components/button";
import TextField from "../components/text_input";
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

function normalizeRegistrationOptions(options) {
  return {
    ...options,
    challenge: base64UrlToUint8Array(options.challenge),
    user: {
      ...options.user,
      id: base64UrlToUint8Array(options.user.id),
    },
    excludeCredentials: (options.excludeCredentials || []).map((cred) => ({
      ...cred,
      id: base64UrlToUint8Array(cred.id),
    })),
  };
}

function serializeAttestation(credential) {
  return {
    id: credential.id,
    rawId: arrayBufferToBase64Url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: arrayBufferToBase64Url(credential.response.clientDataJSON),
      attestationObject: arrayBufferToBase64Url(
        credential.response.attestationObject
      ),
    },
  };
}

function Register() {
  const [first_name, setFirstName] = useState("");
  const [last_name, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [company_name, setCompanyName] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    setLoading(true);
    setMessage("");

    try {
      if (!window.PublicKeyCredential) {
        throw new Error("Passkeys are not supported in this browser.");
      }

      const optionsRes = await fetch(
        apiUrl("/auth/webauthn/register/options"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            email: email.trim().toLowerCase(),
            first_name: first_name.trim(),
            last_name: last_name.trim(),
            company_name: company_name.trim() || null,
            create_company: Boolean(company_name.trim()),
          }),
        }
      );
      const optionsData = await optionsRes.json();
      if (!optionsRes.ok) {
        throw new Error(optionsData.detail || "Failed to begin passkey registration");
      }

      const userId = optionsData.user_id;
      const options = optionsData.options || optionsData;
      if (!userId) {
        throw new Error("Missing user id for passkey verification.");
      }

      const credential = await navigator.credentials.create({
        publicKey: normalizeRegistrationOptions(options),
      });
      if (!credential) {
        throw new Error("Passkey registration was not completed.");
      }

      const verifyRes = await fetch(
        apiUrl(
          `/auth/webauthn/register/verify?user_id=${encodeURIComponent(userId)}`
        ),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(serializeAttestation(credential)),
        }
      );
      const data = await verifyRes.json().catch(async () => {
        const txt = await verifyRes.text();
        throw new Error(txt || "Unexpected response from server");
      });

      if (!verifyRes.ok) {
        const msg = Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg).join(", ")
          : data.detail || data.message || data.error || "Passkey registration failed";

        throw new Error(msg);
      }

      setMessage(data.message || "Passkey registered successfully.");
    } catch (err) {
      setMessage("Error registering passkey: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-xl border border-zinc-700 bg-zinc-900/70 p-6 flex flex-col gap-4">
        <p className="text-sm text-zinc-300">
          ALEX uses passkeys instead of passwords for secure authentication.
          You will be asked to create a passkey on your device.
        </p>

        <TextField
          id="firstName"
          label="First Name"
          type="text"
          value={first_name}
          placeholder="First Name"
          onChange={(e) => setFirstName(e.target.value)}
        />
        <TextField
          id="lastName"
          label="Last Name"
          type="text"
          value={last_name}
          placeholder="Last Name"
          onChange={(e) => setLastName(e.target.value)}
        />
        <TextField
          id="email"
          label="Email"
          type="email"
          value={email}
          placeholder="you@example.com"
          onChange={(e) => setEmail(e.target.value)}
        />
        <TextField
          id="companyName"
          label="Company Name (Optional)"
          type="text"
          value={company_name}
          placeholder="Company Name (Optional)"
          onChange={(e) => setCompanyName(e.target.value)}
        />

        <Button onClick={handleRegister} disabled={loading}>
          {loading ? "Registering..." : "Create Account with Passkey"}
        </Button>
        <p className="text-xs text-zinc-400 text-center">
          No passwords. No tracking. Authentication stays on your device.
        </p>

        {message && (
          <div
            className={`text-sm text-center ${
              message.toLowerCase().includes("success")
                ? "text-green-400"
                : "text-red-400"
            }`}
          >
            {message}
          </div>
        )}
      </div>
    </div>
  );
}

export default Register;
