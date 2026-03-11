import React from "react";
import RegisterForm from "../components/RegisterForm";
function Register() {
  return (
    <div className="page-shell flex flex-col items-center justify-center gap-4 py-12">
      <h1 className="text-2xl font-bold text-app">Register</h1>
      <p className="text-app-secondary text-sm">
        Please fill in the form below to create an account.
      </p>
      <RegisterForm />
    </div>
  );
}

export default Register;
