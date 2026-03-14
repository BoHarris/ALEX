jest.mock("react-router-dom", () => require("../test/reactRouterDomMock"), { virtual: true });

import { render, screen } from "@testing-library/react";
import Home from "./Home";

function renderHome() {
  return render(<Home />);
}

test("landing page renders the core marketing message", () => {
  renderHome();

  expect(screen.getByRole("heading", { name: /real-time pii detection and redaction for modern data systems/i })).toBeInTheDocument();
  expect(screen.getByText(/ALEX automatically detects sensitive data like emails, phone numbers, and SSNs/i)).toBeInTheDocument();
});

test("hero buttons render for primary calls to action", () => {
  renderHome();

  expect(screen.getByRole("link", { name: /start scanning/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /view api documentation/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /start free scan/i })).toBeInTheDocument();
});

test("major landing sections mount successfully", () => {
  renderHome();

  expect(screen.getByRole("heading", { name: /sensitive data spreads faster than most teams can see/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /a privacy control plane built for operational speed/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /everything teams need to operationalize privacy/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /privacy infrastructure for your applications/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /protect sensitive data before it leaks/i })).toBeInTheDocument();
});

test("product preview image asset loads with accessible alt text", () => {
  renderHome();

  expect(screen.getByAltText(/testing and validation product preview/i)).toBeInTheDocument();
  expect(screen.getByText(/monitor privacy validation tests in real time/i)).toBeInTheDocument();
});
