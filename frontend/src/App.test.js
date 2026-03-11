import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { DisplayPreferencesProvider } from "./context/DisplayPreferencesContext";

jest.mock("./utils/session", () => ({
  rehydrateSession: jest.fn().mockResolvedValue(false),
}));

jest.mock("./hooks/useLoadUser", () => ({
  useCurrentUser: () => ({ user: null, loading: false, error: null, reload: jest.fn() }),
}));

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
    expect(screen.getByText(/welcome to alex/i)).toBeInTheDocument();
  });
});

test("accessibility panel opens and closes with Escape", async () => {
  window.history.pushState({}, "", "/login");
  const user = userEvent.setup();

  render(
    <DisplayPreferencesProvider>
      <App />
    </DisplayPreferencesProvider>,
  );

  const accessibilityButton = await screen.findByRole("button", { name: /accessibility/i });
  await user.click(accessibilityButton);
  expect(screen.getByRole("dialog", { name: /accessibility preferences/i })).toBeInTheDocument();

  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog", { name: /accessibility preferences/i })).not.toBeInTheDocument();
});

test("accessibility panel closes on outside click", async () => {
  window.history.pushState({}, "", "/login");
  const user = userEvent.setup();

  render(
    <DisplayPreferencesProvider>
      <App />
    </DisplayPreferencesProvider>,
  );

  const accessibilityButton = await screen.findByRole("button", { name: /accessibility/i });
  await user.click(accessibilityButton);
  expect(screen.getByRole("dialog", { name: /accessibility preferences/i })).toBeInTheDocument();

  await user.click(screen.getByRole("link", { name: /home/i }));
  expect(screen.queryByRole("dialog", { name: /accessibility preferences/i })).not.toBeInTheDocument();
});

test("accessibility preferences update theme, font, motion, and contrast attributes", async () => {
  window.history.pushState({}, "", "/login");
  const user = userEvent.setup();

  render(
    <DisplayPreferencesProvider>
      <App />
    </DisplayPreferencesProvider>,
  );

  expect(screen.queryByRole("combobox", { name: /theme/i })).not.toBeInTheDocument();
  const accessibilityButton = await screen.findByRole("button", { name: /accessibility/i });
  await user.click(accessibilityButton);

  const themeSelect = screen.getByLabelText(/^theme$/i);
  const fontSelect = screen.getByLabelText(/^font$/i);
  const motionSelect = screen.getByLabelText(/reduced motion/i);
  const contrastSelect = screen.getByLabelText(/high contrast/i);

  await user.selectOptions(themeSelect, "light");
  await user.selectOptions(fontSelect, "dyslexia");
  await user.selectOptions(motionSelect, "on");
  await user.selectOptions(contrastSelect, "on");

  expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  expect(document.documentElement.getAttribute("data-font")).toBe("dyslexia");
  expect(document.documentElement.getAttribute("data-reduced-motion")).toBe("true");
  expect(document.documentElement.getAttribute("data-contrast")).toBe("high");
});
