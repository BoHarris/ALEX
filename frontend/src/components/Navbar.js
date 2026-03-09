import React from "react";
import { Link } from "react-router-dom";
import LogoutButton from "./logout";

function Navbar() {
  return (
    <nav className="bg-gray-900 text-white px-6 py-4 shadow-md flex justify-between items-center">
      <div className="text-xl font-bold tracking-wide">
        <Link to="/">
          ALEX<span className="text-red-400">.ai</span>
        </Link>
      </div>
      <div className="space-x-4">
        <Link
          to="/"
          className="hover:text-blue-300 transition-colors duration-200 ml-6 @media (max-width: 768px) { margin-left: 0; }"
        >
          Home
        </Link>
        <Link
          to="/upload"
          className="hover:text-blue-300 transition-colors duration-200 ml-6 @media (max-width: 768px) { margin-left: 0; }"
        >
          Upload
        </Link>
        <Link
          to="/register"
          className="hover:text-blue-300 transition-colors duration-200 ml-6 @media (max-width: 768px) { margin-left: 0; }"
        >
          Register
        </Link>
        <Link
          to="/login"
          className="hover:text-blue-300 transition-colors duration-200 ml-6 @media (max-width: 768px) { margin-left: 0; }"
        >
          Login
        </Link>
        <LogoutButton />
        {/* Future links for other pages */}
        {/* <Link to="/about" className="hover:text-blue-300">About</Link> */}
        {/* <Link to="/contact" className="hover:text-blue-300">Contact</Link> */}
        {/* <Link to="/audit" className="hover:text-blue-300">Audit</Link> */}
        {/* <Link to="/settings" className="hover:text-blue-300">Settings</Link> */}
      </div>
    </nav>
  );
}
export default Navbar;
