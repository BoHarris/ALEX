jest.mock("react-router-dom", () => require("./test/reactRouterDomMock"), { virtual: true });

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { DisplayPreferencesProvider } from "./context/DisplayPreferencesContext";
import { useSessionState } from "./utils/sessionCoordinator";

jest.mock("./utils/session", () => ({
  rehydrateSession: jest.fn().mockResolvedValue(false),
}));

jest.mock("./utils/sessionCoordinator", () => ({
  initializeSessionCoordinator: jest.fn(() => jest.fn()),
  useSessionState: jest.fn(() => ({
    status: "anonymous",
    message: null,
    messageTone: "info",
  })),
}));

jest.mock("./hooks/useLoadUser", () => ({
  useCurrentUser: () => ({ user: null, loading: false, error: null, reload: jest.fn() }),
}));

beforeEach(() => {
  useSessionState.mockReturnValue({
    status: "anonymous",
    message: null,
    messageTone: "info",
  });
});

test("shows skip link for keyboard navigation", async () => {
  render(
    <DisplayPreferencesProvider>
      <App />
    </DisplayPreferencesProvider>,
  );
  const skip = await screen.findByRole("link", { name: /skip to main content/i });
  expect(skip).toBeInTheDocument();
});

test("dashboard route redirects to login when unauthenticated", async () => {
  window.history.pushState({}, "", "/dashboard");
  render(
    <DisplayPreferencesProvider>
      <App />
    </DisplayPreferencesProvider>,
  );
  await waitFor(() => {
    expect(screen.getByRole("button", { name: /sign in with passkey/i })).toBeInTheDocument();
  });
});

test("session-expired state redirects to login and shows a clear message", async () => {
  window.history.pushState({}, "", "/dashboard");
  useSessionState.mockReturnValue({
    status: "expired",
    message: "Session expired. Please sign in again.",
    messageTone: "warning",
  });

  render(
    <DisplayPreferencesProvider>
      <App />
    </DisplayPreferencesProvider>,
  );

  expect(await screen.findByText(/session expired\. please sign in again\./i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sign in with passkey/i })).toBeInTheDocument();
});

test("accessibility panel opens and closes with Escape", async () => {
  window.history.pushState({}, "", "/login");

  render(
    <DisplayPreferencesProvider>
      <App />
    </DisplayPreferencesProvider>,
  );

  const accessibilityButton = await screen.findByRole("button", { name: /accessibility/i });
  await userEvent.click(accessibilityButton);
  expect(screen.getByRole("dialog", { name: /accessibility preferences/i })).toBeInTheDocument();

  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("dialog", { name: /accessibility preferences/i })).not.toBeInTheDocument();
});

test("accessibility panel closes on outside click", async () => {
  window.history.pushState({}, "", "/login");

  render(
    <DisplayPreferencesProvider>
      <App />
    </DisplayPreferencesProvider>,
  );

  const accessibilityButton = await screen.findByRole("button", { name: /accessibility/i });
  await userEvent.click(accessibilityButton);
  expect(screen.getByRole("dialog", { name: /accessibility preferences/i })).toBeInTheDocument();

  await userEvent.click(screen.getByRole("link", { name: /home/i }));
  expect(screen.queryByRole("dialog", { name: /accessibility preferences/i })).not.toBeInTheDocument();
});

test("accessibility preferences update theme, font, motion, and contrast attributes", async () => {
  window.history.pushState({}, "", "/login");

  render(
    <DisplayPreferencesProvider>
      <App />
    </DisplayPreferencesProvider>,
  );

  expect(screen.queryByRole("combobox", { name: /theme/i })).not.toBeInTheDocument();
  const accessibilityButton = await screen.findByRole("button", { name: /accessibility/i });
  await userEvent.click(accessibilityButton);

  const themeSelect = screen.getByLabelText(/^theme$/i);
  const fontSelect = screen.getByLabelText(/^font$/i);
  const motionSelect = screen.getByLabelText(/reduced motion/i);
  const contrastSelect = screen.getByLabelText(/high contrast/i);

  await userEvent.selectOptions(themeSelect, "light");
  await userEvent.selectOptions(fontSelect, "dyslexia");
  await userEvent.selectOptions(motionSelect, "on");
  await userEvent.selectOptions(contrastSelect, "on");

  expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  expect(document.documentElement.getAttribute("data-font")).toBe("dyslexia");
  expect(document.documentElement.getAttribute("data-reduced-motion")).toBe("true");
  expect(document.documentElement.getAttribute("data-contrast")).toBe("high");
});
