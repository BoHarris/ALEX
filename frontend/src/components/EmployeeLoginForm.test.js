jest.mock("react-router-dom", () => require("../test/reactRouterDomMock"), { virtual: true });

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import EmployeeLoginForm from "./EmployeeLoginForm";
import { completeLogin } from "../utils/sessionCoordinator";

jest.mock("../utils/sessionCoordinator", () => ({
  completeLogin: jest.fn(),
}));

function createMockCredential() {
  return {
    id: "credential-id",
    rawId: Uint8Array.from([1, 2, 3]).buffer,
    type: "public-key",
    response: {
      clientDataJSON: Uint8Array.from([4, 5, 6]).buffer,
      authenticatorData: Uint8Array.from([7, 8, 9]).buffer,
      signature: Uint8Array.from([10, 11, 12]).buffer,
      userHandle: null,
    },
  };
}

beforeEach(() => {
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

test("employee login completes shared session state before navigating to compliance", async () => {
  navigator.credentials.get.mockResolvedValue(createMockCredential());
  fetch
    .mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({
        employee_found: true,
        passkey_enrolled: true,
        is_active: true,
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({
        challenge: "AQ",
        allowCredentials: [{ id: "AQ", type: "public-key" }],
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({ access_token: "employee-access-token" }),
    });

  render(
    <MemoryRouter initialEntries={["/employee-login"]}>
      <Routes>
        <Route path="/employee-login" element={<EmployeeLoginForm />} />
        <Route path="/compliance" element={<div>Compliance home</div>} />
      </Routes>
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByLabelText(/employee email/i), {
    target: { value: "employee@example.com" },
  });

  await waitFor(() => {
    expect(screen.getByText(/employee passkey is enrolled/i)).toBeInTheDocument();
  });

  await userEvent.click(screen.getByRole("button", { name: /sign in to compliance workspace/i }));

  await waitFor(() => {
    expect(completeLogin).toHaveBeenCalledWith("employee-access-token");
    expect(screen.getByText(/compliance home/i)).toBeInTheDocument();
  });
});
