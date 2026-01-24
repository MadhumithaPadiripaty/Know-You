import React, { useState } from "react";

export default function About() {
  const [showDescription, setShowDescription] = useState(false);

  const handleToggle = () => {
    setShowDescription(!showDescription);
  };
  return (
    <div className="about-container">
      <h1>About KnowYourPay</h1>

      <button className="toggle-btn" onClick={handleToggle}>
        {showDescription ? "Hide Description" : "Show Description"}
      </button>

      {showDescription && (
        <div className="about-content">
          <p className="about-intro">
            KnowYourPay empowers users to analyze{" "}
            <strong>pricing, costs, revenue, and profit</strong> from uploaded
            data files. Perfect for <em>students, analysts, startups, and
            businesses</em>, it helps you understand financial performance
            quickly and efficiently.
          </p>

          <p className="about-details">
            Upload your data, visualize trends, and gain actionable insights
            instantly — no complex setup or expertise required.
          </p>
        </div>
      )}
    </div>
  );
}
