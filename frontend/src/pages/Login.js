import React from "react";
import AnimatedHeading from "../components/animatedHeading";
import LoginForm from "../components/LoginForm";
function Login() {
  return (
    <div className="py-12 bg-gray-900 text-white flex flex-col items-center justify-center">
      <AnimatedHeading />
      <LoginForm />
    </div>
  );
}

export default Login;
