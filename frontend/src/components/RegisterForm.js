import React, { useState, useEffect } from "react";
import { Button } from "./button";
import TextField from "./text_input";
import useFingerprint from "../utils/useFingerprint";

function Register() {
  const [name, setName] = useState("");
  const [tier, setTier] = useState("free");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const { fingerprint } = useFingerprint();

  useEffect(() => {
    if (fingerprint) {
      console.log("Fingerprint loaded: ", fingerprint);
    }
  }, [fingerprint]);

  const handleRegister = async () => {
    setLoading(true);
    setMessage("");

    const backendUrl = `${process.env.REACT_APP_BACKEND_URL}/auth/register`;
    console.log("Sending registration to:", backendUrl);

    try {
      const res = await fetch(backendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          email,
          password,
          tier,
          device_fingerprint: fingerprint,
        }),
      });

      let data;
      try {
        data = await res.clone().json();
      } catch {
        const fallbackText = await res.text();
        throw new Error(fallbackText || "Unexpected response from server");
      }

      if (!res.ok) {
        const msg = Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg).join(", ")
          : data.detail || data.message || data.error || "Registration failed";

        throw new Error(msg);
      }

      setMessage(data.message || "Registration successful!");
    } catch (err) {
      setMessage("Error registering user: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 items-center justify-center py-12 max-w-md mx-auto">
      <TextField
        id="name"
        label="Name"
        type="text"
        value={name}
        placeholder="Enter your name"
        onChange={(e) => setName(e.target.value)}
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
        id="password"
        label="Password"
        type="password"
        value={password}
        placeholder="Enter your password"
        onChange={(e) => setPassword(e.target.value)}
      />
      <label className="text-sm font-medium text-gray-300">Tier</label>
      <select
        className="w-full border rounded px-3 py-2 text-sm text-gray-700"
        value={tier}
        onChange={(e) => setTier(e.target.value)}
      >
        <option value="free">Free</option>
        <option value="pro">Pro</option>
        <option value="business">Business</option>
      </select>
      <p className="text-xs text-gray-400 italic text-center mt-2">
        We use a{" "}
        <span className="text-green-400">secure device fingerprint </span> to
        identify this device.
        <span className="text-red-400 font-semibold"> No hardware </span>
        data is collected.
      </p>

      <Button onClick={handleRegister} disabled={loading}>
        {loading ? "Registering..." : "Register"}
      </Button>

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
  );
}

export default Register;
