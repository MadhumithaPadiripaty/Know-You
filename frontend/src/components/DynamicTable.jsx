import React from "react";

export default function DynamicTable({ title, rows }) {
  if (!rows || rows.length === 0) return null;

  const headers = Object.keys(rows[0]);

  return (
    <section className="table-box">
      <h3>{title}</h3>
      <table>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h.replace("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {headers.map((h) => (
                <td key={h}>{row[h]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
