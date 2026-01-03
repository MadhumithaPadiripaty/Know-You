import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import About from "./pages/About";
import "./App.css";
import Docs from "./pages/Docs";

function App() {
  return (
    <Router>
      <div className="container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/about" element={<About />} />
          <Route path="/docs" element={<Docs />} />

        </Routes>
      </div>
    </Router>
  );
} 

export default App;
