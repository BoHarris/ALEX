import React from "react";
import AnimatedHeading from "../components/animatedHeading";
import LoginForm from "../components/LoginForm";
function Login() {
  return (
    <div className="page-shell flex flex-col items-center justify-center py-12">
      <AnimatedHeading />
      <LoginForm />
    </div>
  );
}

export default Login;
