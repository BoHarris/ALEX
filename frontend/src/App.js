import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard"; // or wherever your file lives

// Ensure these components exist and are correctly exported from their respective files.

function App() {
  return (
    <Router>
      <Navbar />
      <main className="min-h-screen bg-gray-900 text-white">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Dashboard />} />
          {/* Future routes for other pages */}
          {/* <Route path="/about" element={<About />} /> */}
          {/* <Route path="/contact" element={<Contact />} /> */}
          {/* <Route path="/audit" element={<Audit />} /> */}
          {/* <Route path="/settings" element={<Settings />} /> */}
          {/* Add more routes as needed */}
        </Routes>
      </main>
    </Router>
  );
}

export default App;
