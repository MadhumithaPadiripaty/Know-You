import React from "react";

export default function DetectedColumns({ columns }) {
  if (!columns) return null;

  return (
    <section className="columns">
      <h3>✅ Detected Fields</h3>
      <ul>
        {Object.entries(columns).map(([k, v]) => (
          <li key={k}>
            <b>{k}</b> → {v}
          </li>
        ))}
      </ul>
    </section>
  );
}
