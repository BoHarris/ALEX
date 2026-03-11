import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LoginForm from "./LoginForm";
import RegisterForm from "./RegisterForm";

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
