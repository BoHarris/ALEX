import React, { useState, useEffect } from "react";
import { Button } from "../components/button";
import TextField from "../components/text_input";
import useFingerprint from "../utils/useFingerprint";

function Register() {
  const [first_name, setFirstName] = useState("");
  const [last_name, setLastName] = useState("");
  const [tier, setTier] = useState("free");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const { fingerprint } = useFingerprint();

  useEffect(() => {
    if (!fingerprint) {
      console.log("Fingerprint loaded: ", fingerprint);
    }
  }, [fingerprint]);

  const handleRegister = async () => {
    if (!fingerprint) {
      setMessage("Still generating device fingerprint please wait");
    }

    setLoading(true);
    setMessage("");

    const backendUrl = `${process.env.REACT_APP_BACKEND_URL}/auth/register`;
    console.log("Sending registration to:", backendUrl);

    const payload = {
      first_name: first_name,
      last_name: last_name,
      email: email.trim().toLowerCase(),
      password,
      tier,
      device_fingerprint: fingerprint,
    };

    const backendURL =
      process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";

    try {
      const res = await fetch(`${backendURL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(async () => {
        const txt = await res.txt();
        throw new Error(txt || "Unexpected response from server");
      });

      if (!res.ok) {
        const msg = Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg).join(", ")
          : data.detail || data.message || data.error || "Registration failed";

        throw new Error(msg);
      }

      setMessage(data.message);
    } catch (err) {
      setMessage("Error registering user: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 items-center justify-center py-12 max-w-md mx-auto">
      <TextField
        id="firstName"
        label="First_Name"
        type="text"
        value={first_name}
        placeholder="First Name"
        onChange={(e) => setFirstName(e.target.value)}
      />
      <TextField
        id="lastName"
        label="Last_name"
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
