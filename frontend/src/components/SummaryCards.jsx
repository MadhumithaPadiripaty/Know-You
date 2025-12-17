import React from "react";

export default function SummaryCards({ analysis }) {
  const cards = [
    { label: "Total Sales", value: analysis.total_sales },
    { label: "Products", value: analysis.total_products },
    { label: "Clients", value: analysis.total_clients },
    { label: "Rows Analyzed", value: analysis.rows },
  ];

  return (
    <section className="cards">
      {cards.map((c) => (
        <div className="card" key={c.label}>
          <h3>{c.label}</h3>
          <p>{c.value}</p>
        </div>
      ))}
    </section>
  );
}
