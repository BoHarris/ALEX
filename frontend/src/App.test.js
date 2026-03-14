jest.mock("react-router-dom", () => require("./test/reactRouterDomMock"), { virtual: true });

import { render, screen } from "@testing-library/react";
import App from "./App";

jest.mock("./hooks/useLoadUser", () => ({
  useCurrentUser: () => ({ user: null, loading: false, error: null, reload: jest.fn() }),
}));

test("app renders the upgraded landing page from the root route", () => {
  render(<App />);

  expect(screen.getByRole("link", { name: /home/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /real-time pii detection and redaction for modern data systems/i })).toBeInTheDocument();
});
