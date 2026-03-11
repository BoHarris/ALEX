import React from "react";
import AnimatedHeading from "../components/animatedHeading";
import EmployeeLoginForm from "../components/EmployeeLoginForm";

export default function EmployeeLogin() {
  return (
    <div className="page-shell flex flex-col items-center justify-center py-12">
      <AnimatedHeading />
      <EmployeeLoginForm />
    </div>
  );
}
