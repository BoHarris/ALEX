jest.mock("react-router-dom", () => require("../test/reactRouterDomMock"), { virtual: true });

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import LoginForm from "./LoginForm";
import RegisterForm from "./RegisterForm";
import { completeLogout } from "../utils/sessionCoordinator";

function createMockCredential() {
  return {
    id: "credential-id",
    rawId: Uint8Array.from([1, 2, 3]).buffer,
    type: "public-key",
    response: {
      clientDataJSON: Uint8Array.from([4, 5, 6]).buffer,
      attestationObject: Uint8Array.from([7, 8, 9]).buffer,
      authenticatorData: Uint8Array.from([10, 11, 12]).buffer,
      signature: Uint8Array.from([13, 14, 15]).buffer,
      userHandle: null,
    },
  };
}

beforeEach(() => {
  completeLogout({ broadcast: false });
  global.fetch = jest.fn();
  Object.defineProperty(window, "PublicKeyCredential", {
    configurable: true,
    value: function PublicKeyCredential() {},
  });
  Object.defineProperty(navigator, "credentials", {
    configurable: true,
    value: {
      create: jest.fn(),
      get: jest.fn(),
    },
  });
});

afterEach(() => {
  jest.resetAllMocks();
});

test("login form renders accessible email field and submit button", () => {
  render(
    <MemoryRouter>
      <LoginForm />
    </MemoryRouter>,
  );

  expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sign in with passkey/i })).toBeInTheDocument();
});

test("register form renders labeled fields and submit action", () => {
  render(
    <MemoryRouter>
      <RegisterForm />
    </MemoryRouter>,
  );

  expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /create account with passkey/i })).toBeInTheDocument();
});

test("registration success routes to login and shows the next-step message", async () => {
  navigator.credentials.create.mockResolvedValue(createMockCredential());
  fetch
    .mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({
        user_id: 42,
        options: {
          challenge: "AQ",
          user: { id: "AQ", name: "you@example.com", displayName: "You" },
          excludeCredentials: [],
        },
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({ status: "ok", message: "Passkey enrolled" }),
    });

  render(
    <MemoryRouter initialEntries={["/register"]}>
      <Routes>
        <Route path="/register" element={<RegisterForm />} />
        <Route path="/login" element={<LoginForm />} />
      </Routes>
    </MemoryRouter>,
  );

  await userEvent.type(screen.getByLabelText(/first name/i), "Alex");
  await userEvent.type(screen.getByLabelText(/last name/i), "User");
  await userEvent.type(screen.getByLabelText(/^email$/i), "you@example.com");
  await userEvent.click(screen.getByRole("button", { name: /create account with passkey/i }));

  expect(await screen.findByText(/registration complete\. your passkey is ready\. please sign in to continue\./i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sign in with passkey/i })).toBeInTheDocument();
});

test("login success still routes the user into the authenticated flow", async () => {
  navigator.credentials.get.mockResolvedValue(createMockCredential());
  fetch
    .mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({
        challenge: "AQ",
        allowCredentials: [{ id: "AQ", type: "public-key" }],
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({ access_token: "access-token" }),
    });

  render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginForm />} />
        <Route path="/dashboard" element={<div>Dashboard home</div>} />
      </Routes>
    </MemoryRouter>,
  );

  await userEvent.type(screen.getByLabelText(/email/i), "you@example.com");
  await userEvent.click(screen.getByRole("button", { name: /sign in with passkey/i }));

  await waitFor(() => {
    expect(screen.getByText(/dashboard home/i)).toBeInTheDocument();
  });
});
