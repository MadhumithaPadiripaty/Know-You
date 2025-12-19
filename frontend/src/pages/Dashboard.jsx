import React, { useState } from "react";
import axios from "axios";

export default function Dashboard() {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const [topN, setTopN] = useState(10);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  }; 

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) return alert("Select at least one file");

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    formData.append("top_n", topN);

    setLoading(true);
    try {
      const response = await axios.post(
        "https://know-you-m73y.onrender.com/analyze",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setResults(response.data);
    } catch (err) {
      console.error(err);
      alert("Error uploading files");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard">
      <header className="header">
        <h1>📊 Business Analysis Dashboard</h1>
        <p>Upload sales/cost files to analyze revenue & profit</p>
      </header>

      {/* Upload Card */}
      <div className="card upload-card">
        <form onSubmit={handleSubmit} className="upload-form">
          <input type="file" multiple onChange={handleFileChange} />
          <div className="controls">
            <label>Top N</label>
            <input
              type="number"
              min="1"
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
            />
            <button type="submit">Analyze</button>
          </div>
        </form>
      </div>

      {loading && <div className="loading">⏳ Processing files...</div>}

      {results && (
        <>
          {/* Summary */}
          <div className="grid">
            <div className="card stat">
              <h3>Rows</h3>
              <p>{results.rows}</p>
            </div>
            <div className="card stat">
              <h3>Columns</h3>
              <p>{results.columns.length}</p>
            </div>
            <div className="card stat">
              <h3>Detected Fields</h3>
              <p className="small">{results.columns.join(", ")}</p>
            </div>
          </div>

          {/* Column Totals */}
          <div className="card">
            <h3>📈 Column Totals</h3>
            <div className="totals-grid">
              {Object.entries(results.column_totals).map(([col, total]) => (
                <div key={col} className="total-item">
                  <span>{col}</span>
                  <strong>{total.toLocaleString()}</strong>
                </div>
              ))}
            </div>
          </div>

          {/* Top Items */}
          {results.top_items.length > 0 && (
            <div className="card">
              <h3>🏆 Top {topN} Items by Profit</h3>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      {Object.keys(results.top_items[0]).map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {results.top_items.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((val, j) => (
                          <td key={j}>{val}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}


