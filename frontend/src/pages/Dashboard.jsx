import React, { useState } from "react";
import axios from "axios";
// import "./Dashboard.css";

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
        "http://localhost:8000/analyze",
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











// // src/Dashboard.jsx
// import React, { useState } from "react";
// import axios from "axios";

// const Dashboard = () => {
//   const [files, setFiles] = useState([]);
//   const [totals, setTotals] = useState(null);
//   const [topItems, setTopItems] = useState([]);
//   const [columns, setColumns] = useState({});
//   const [rows, setRows] = useState(0);
//   const [topN, setTopN] = useState(10);
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState(null);

//   // Handle file selection
//   const handleFileChange = (e) => {
//     setFiles(Array.from(e.target.files));
//   };

//   // Upload files and get analysis
//   const uploadFiles = async () => {
//     if (files.length === 0) {
//       alert("Please select at least one file.");
//       return;
//     }

//     setLoading(true);
//     setError(null);

//     try {
//       const formData = new FormData();
//       files.forEach((file) => formData.append("files", file));

//       const response = await axios.post(
//         `http://127.0.0.1:8000/analyze?top_n=${topN}`,
//         formData,
//         {
//           headers: {
//             "Content-Type": "multipart/form-data",
//           },
//         }
//       );

//       const data = response.data;

//       if (data.error) {
//         setError(data.error);
//         setTotals(null);
//         setTopItems([]);
//         setColumns({});
//         setRows(0);
//       } else {
//         setTotals(data.totals);
//         setTopItems(data.top_items);
//         setColumns(data.columns_detected);
//         setRows(data.rows);
//       }
//     } catch (err) {
//       console.error(err);
//       setError("Failed to analyze files. Make sure backend is running.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
//       <h1>Business Analysis Dashboard</h1>

//       <div style={{ marginBottom: "20px" }}>
//         <input
//           type="file"
//           multiple
//           onChange={handleFileChange}
//           accept=".csv,.xlsx,.xls,.pdf"
//         />
//         <input
//           type="number"
//           min="1"
//           value={topN}
//           onChange={(e) => setTopN(Number(e.target.value))}
//           style={{ marginLeft: "10px", width: "60px" }}
//         />
//         <button onClick={uploadFiles} style={{ marginLeft: "10px" }}>
//           {loading ? "Analyzing..." : "Upload & Analyze"}
//         </button>
//       </div>

//       {error && <p style={{ color: "red" }}>{error}</p>}

//       {totals && (
//         <div style={{ marginBottom: "20px" }}>
//           <h2>Totals</h2>
//           <ul>
//             <li>Total Rows: {rows}</li>
//             <li>Total Revenue: ${totals.total_revenue.toLocaleString()}</li>
//             <li>Total Cost: ${totals.total_cost.toLocaleString()}</li>
//             <li>Total Profit: ${totals.total_profit.toLocaleString()}</li>
//             <li>Total Items: {totals.total_items}</li>
//             <li>Total Customers: {totals.total_customers}</li>
//           </ul>
//         </div>
//       )}

//       {topItems.length > 0 && (
//         <div>
//             <h2>Top {topN} Profitable Items (Descending by Profit)</h2>
//             <table
//             border="1"
//             cellPadding="8"
//             style={{ borderCollapse: "collapse", width: "100%" }}
//             >
//             <thead>
//                 <tr>
//                 {Object.keys(topItems[0]).map((col) => (
//                     <th key={col}>{col}</th>
//                 ))}
//                 </tr>
//             </thead>
//             <tbody>
//                 {topItems.map((item, idx) => (
//                 <tr key={idx}>
//                     {Object.keys(item).map((col) => (
//                     <td key={col}>
//                         {typeof item[col] === "number"
//                         ? item[col].toLocaleString()
//                         : item[col]}
//                     </td>
//                     ))}
//                 </tr>
//                 ))}
//             </tbody>
//             </table>
//         </div>
//         )}

//     </div>
//   );
// };

// export default Dashboard;








// // src/pages/Dashboard.jsx
// import React, { useState } from "react";
// import axios from "axios";

// export default function Dashboard() {
//   const [files, setFiles] = useState([]);
//   const [analysis, setAnalysis] = useState(null);
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState("");
//   const [topN, setTopN] = useState(10);

//   const handleFileChange = (e) => {
//     setFiles(Array.from(e.target.files));
//   };

//   const uploadFiles = async () => {
//     if (!files.length) return alert("Select files first");
//     const formData = new FormData();
//     files.forEach((file) => formData.append("files", file));

//     try {
//       setLoading(true);
//       setError("");
//       setAnalysis(null);

//       const res = await axios.post("http://127.0.0.1:8000/analyze",
//         formData,
//         {
//           headers: { "Content-Type": "multipart/form-data" },
//         }
//       );

//       setAnalysis(res.data);
//     } catch (err) {
//       console.error(err);
//       setError("Failed to analyze files");
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div style={{ maxWidth: 1200, margin: "auto", padding: 20 }}>
//       <h1>Business Analysis Dashboard</h1>

//       {/* File Upload */}
//       <div style={{ marginBottom: 20 }}>
//         <input
//           type="file"
//           multiple
//           accept=".csv,.xlsx,.xls,.pdf"
//           onChange={handleFileChange}
//         />
//         <input
//           type="number"
//           value={topN}
//           onChange={(e) => setTopN(Number(e.target.value))}
//           style={{ width: 60, marginLeft: 10 }}
//         />
//         <button onClick={uploadFiles} style={{ marginLeft: 10 }}>
//           Upload & Analyze
//         </button>
//       </div>

//       {loading && <p>Analyzing files...</p>}
//       {error && <p style={{ color: "red" }}>{error}</p>}

//       {/* Totals */}
//       {analysis && (
//         <div style={{ display: "flex", gap: 20, marginBottom: 20 }}>
//           {analysis.totals &&
//             Object.entries(analysis.totals).map(([key, value]) => (
//               <div
//                 key={key}
//                 style={{
//                   padding: 10,
//                   border: "1px solid #ccc",
//                   borderRadius: 5,
//                   minWidth: 120,
//                   textAlign: "center",
//                 }}
//               >
//                 <strong>{key.replace(/_/g, " ")}</strong>
//                 <div>{value}</div>
//               </div>
//             ))}
//         </div>
//       )}

//       {/* Top N Table */}
//       {analysis && analysis.top_items && (
//         <div>
//           <h2>Top {topN} Profitable Items</h2>
//           <table
//             style={{
//               width: "100%",
//               borderCollapse: "collapse",
//               marginBottom: 40,
//             }}
//           >
//             <thead>
//               <tr>
//                 {Object.keys(analysis.top_items[0]).map((col) => (
//                   <th
//                     key={col}
//                     style={{
//                       border: "1px solid #ddd",
//                       padding: 8,
//                       background: "#f0f0f0",
//                       textTransform: "capitalize",
//                     }}
//                   >
//                     {col.replace(/_/g, " ")}
//                   </th>
//                 ))}
//               </tr>
//             </thead>
//             <tbody>
//               {analysis.top_items.map((row, i) => (
//                 <tr key={i}>
//                   {Object.values(row).map((val, j) => (
//                     <td
//                       key={j}
//                       style={{ border: "1px solid #ddd", padding: 8 }}
//                     >
//                       {val}
//                     </td>
//                   ))}
//                 </tr>
//               ))}
//             </tbody>
//           </table>
//         </div>
//       )}

//       {/* Column info */}
//       {analysis && analysis.columns_detected && (
//         <div>
//           <h3>Detected Columns</h3>
//           <ul>
//             {Object.entries(analysis.columns_detected).map(([key, val]) => (
//               <li key={key}>
//                 <strong>{key}</strong>: {val}
//               </li>
//             ))}
//           </ul>
//         </div>
//       )}
//     </div>
//   );
// }






// import React, { useState } from "react";
// import axios from "axios";

// export default function Dashboard() {
//   const [analysis, setAnalysis] = useState(null);
//   const [loading, setLoading] = useState(false);
//   const [progress, setProgress] = useState(0);
//   const [error, setError] = useState("");

//   const uploadFile = async (file) => {
//     const formData = new FormData();
//     formData.append("file", file);

//     try {
//       setLoading(true);
//       setError("");
//       setAnalysis(null);

//       const res = await axios.post("http://127.0.0.1:8000/analyze", formData, {
//         headers: { "Content-Type": "multipart/form-data" },
//         onUploadProgress: (e) => setProgress(Math.round((e.loaded * 100) / e.total)),
//       });

//       setAnalysis(res.data);
//     } catch (err) {
//       console.error(err);
//       setError("Failed to analyze file");
//     } finally {
//       setLoading(false);
//       setProgress(0);
//     }
//   };

//   return (
//     <main className="dashboard">
//       <header className="header">
//         <h1>Business Analysis Dashboard</h1>
//         <p>Upload any business file (CSV, Excel, PDF)</p>
//       </header>

//       <label className="upload-box">
//         <input
//           type="file"
//           hidden
//           accept=".csv,.xlsx,.xls,.pdf"
//           onChange={(e) => uploadFile(e.target.files[0])}
//         />
//         Click or Drop File Here
//       </label>

//       {loading && (
//         <div className="loader">
//           <div className="bar">
//             <div style={{ width: `${progress} percent` }} />
//           </div>
//           <p>Analyzing file... {progress} percent</p>
//         </div>
//       )}

//       {error && <p className="error">{error}</p>}

//       {analysis && (
//         <>
//           <section className="summary">
//             <h2>Totals</h2>
//             {analysis.totals && (
//               <ul>
//                 {Object.entries(analysis.totals).map(([key, value]) => (
//                   <li key={key}>
//                     {key.charAt(0).toUpperCase() + key.slice(1)}: {value}
//                   </li>
//                 ))}
//               </ul>
//             )}
//           </section>

//           {analysis.columns_detected && (
//             <section className="columns">
//               <h2>Detected Columns</h2>
//               <ul>
//                 {Object.entries(analysis.columns_detected).map(([key, col]) => (
//                   <li key={key}>{key}: {col}</li>
//                 ))}
//               </ul>
//             </section>
//           )}

//           {analysis.top_products && analysis.top_products.length > 0 && (
//             <section className="table">
//               <h2>Top Products / Services</h2>
//               <table>
//                 <thead>
//                   <tr>
//                     {Object.keys(analysis.top_products[0]).map((k) => <th key={k}>{k}</th>)}
//                   </tr>
//                 </thead>
//                 <tbody>
//                   {analysis.top_products.map((row, idx) => (
//                     <tr key={idx}>
//                       {Object.values(row).map((v, i) => <td key={i}>{v}</td>)}
//                     </tr>
//                   ))}
//                 </tbody>
//               </table>
//             </section>
//           )}

//           {analysis.low_stock && analysis.low_stock.length > 0 && (
//             <section className="table">
//               <h2>Low Stock Items</h2>
//               <table>
//                 <thead>
//                   <tr>
//                     {Object.keys(analysis.low_stock[0]).map((k) => <th key={k}>{k}</th>)}
//                   </tr>
//                 </thead>
//                 <tbody>
//                   {analysis.low_stock.map((row, idx) => (
//                     <tr key={idx}>
//                       {Object.values(row).map((v, i) => <td key={i}>{v}</td>)}
//                     </tr>
//                   ))}
//                 </tbody>
//               </table>
//             </section>
//           )}

//           {["sales", "cost", "profit"].map((col) => (
//             <div key={col}>
//               {analysis[`${col}_per_day`] && analysis[`${col}_per_day`].length > 0 && (
//                 <section className="table">
//                   <h2>Daily {col}</h2>
//                   <table>
//                     <thead>
//                       <tr>{Object.keys(analysis[`${col}_per_day`][0]).map((k) => <th key={k}>{k}</th>)}</tr>
//                     </thead>
//                     <tbody>
//                       {analysis[`${col}_per_day`].map((row, idx) => (
//                         <tr key={idx}>{Object.values(row).map((v,i) => <td key={i}>{v}</td>)}</tr>
//                       ))}
//                     </tbody>
//                   </table>
//                 </section>
//               )}

//               {analysis[`${col}_per_week`] && analysis[`${col}_per_week`].length > 0 && (
//                 <section className="table">
//                   <h2>Weekly {col}</h2>
//                   <table>
//                     <thead>
//                       <tr>{Object.keys(analysis[`${col}_per_week`][0]).map((k) => <th key={k}>{k}</th>)}</tr>
//                     </thead>
//                     <tbody>
//                       {analysis[`${col}_per_week`].map((row, idx) => (
//                         <tr key={idx}>{Object.values(row).map((v,i) => <td key={i}>{v}</td>)}</tr>
//                       ))}
//                     </tbody>
//                   </table>
//                 </section>
//               )}

//               {analysis[`${col}_per_month`] && analysis[`${col}_per_month`].length > 0 && (
//                 <section className="table">
//                   <h2>Monthly {col}</h2>
//                   <table>
//                     <thead>
//                       <tr>{Object.keys(analysis[`${col}_per_month`][0]).map((k) => <th key={k}>{k}</th>)}</tr>
//                     </thead>
//                     <tbody>
//                       {analysis[`${col}_per_month`].map((row, idx) => (
//                         <tr key={idx}>{Object.values(row).map((v,i) => <td key={i}>{v}</td>)}</tr>
//                       ))}
//                     </tbody>
//                   </table>
//                 </section>
//               )}
//             </div>
//           ))}
//         </>
//       )}
//     </main>
//   );
// }




// import React, { useState } from "react";
// import axios from "axios";
// import SummaryCards from "../components/SummaryCards";
// import DetectedColumns from "../components/DetectedColumns";
// import DynamicTable from "../components/DynamicTable";

// export default function Dashboard() {
//   const [analysis, setAnalysis] = useState(null);
//   const [loading, setLoading] = useState(false);
//   const [progress, setProgress] = useState(0);
//   const [error, setError] = useState("");

//   const uploadFile = async (file) => {
//     const formData = new FormData();
//     formData.append("file", file);

//     try {
//       setLoading(true);
//       setError("");
//       setAnalysis(null);

//       const res = await axios.post("http://127.0.0.1:8000/analyze", formData, {
//         headers: { "Content-Type": "multipart/form-data" },
//         onUploadProgress: (e) => {
//           setProgress(Math.round((e.loaded * 100) / e.total));
//         },
//       });

//       setAnalysis(res.data);
//     } catch {
//       setError("Failed to analyze file");
//     } finally {
//       setLoading(false);
//       setProgress(0);
//     }
//   };

//   return (
//     <main className="dashboard">
//       <header className="header">
//         <h1>📊 Business Analysis Dashboard</h1>
//         <p>Upload any business file (CSV, Excel, PDF)</p>
//       </header>

//       <label className="upload-box">
//         <input
//           type="file"
//           hidden
//           accept=".csv,.xlsx,.xls,.pdf"
//           onChange={(e) => uploadFile(e.target.files[0])}
//         />
//         📤 Click or Drop File Here
//       </label>

//       {loading && (
//         <div className="loader">
//           <div className="bar">
//             <div style={{ width: `${progress}%` }} />
//           </div>
//           <p>Analyzing file… {progress}%</p>
//         </div>
//       )}

//       {error && <p className="error">{error}</p>}

//       {analysis && (
//         <>
//           <SummaryCards analysis={analysis} />
//           <DetectedColumns columns={analysis.columns_detected} />
//           <DynamicTable title="🔥 Top Products" rows={analysis.top_products} />
//           <DynamicTable title="⚠ Low Stock" rows={analysis.low_stock} />
//         </>
//       )}
//     </main>
//   );
// }




// import React, { useState, useEffect } from 'react';

// const API_BASE = 'http://localhost:5000';

// function App() {
//   const [tasks, setTasks] = useState([]);
//   const [description, setDescription] = useState('');
//   const [deadline, setDeadline] = useState('');
//   const [amounts, setAmounts] = useState({}); // Track amount per task
//   const [projection, setProjection] = useState([]);

//   useEffect(() => {
//     fetchTasks();
//     fetchProjection();
//   }, []);

//   async function fetchTasks() {
//     try {
//       const res = await fetch(`${API_BASE}/tasks`);
//       if (!res.ok) throw new Error('Failed to fetch tasks');
//       const data = await res.json();
//       setTasks(data);
//     } catch (error) {
//       console.error(error);
//       alert('Error fetching tasks');
//     }
//   }

//   async function fetchProjection() {
//     try {
//       const res = await fetch(`${API_BASE}/cashflow/projection`);
//       if (!res.ok) throw new Error('Failed to fetch projection');
//       const data = await res.json();
//       setProjection(data);
//     } catch (error) {
//       console.error(error);
//       alert('Error fetching cash flow projection');
//     }
//   }

//   async function addTask() {
//     if (!description || !deadline) return alert('Description and deadline required');
//     try {
//       const res = await fetch(`${API_BASE}/tasks`, {
//         method: 'POST',
//         headers: {'Content-Type': 'application/json'},
//         body: JSON.stringify({description, deadline})
//       });
//       if (!res.ok) throw new Error('Failed to add task');
//       setDescription('');
//       setDeadline('');
//       fetchTasks();
//     } catch (error) {
//       console.error(error);
//       alert('Error adding task');
//     }
//   }

//   async function completeTask(taskId) {
//     const amt = parseFloat(amounts[taskId]) || 100;
//     try {
//       const res = await fetch(`${API_BASE}/tasks/${taskId}/complete`, {
//         method: 'POST',
//         headers: {'Content-Type': 'application/json'},
//         body: JSON.stringify({amount: amt})
//       });
//       if (!res.ok) throw new Error('Failed to complete task');
//       setAmounts(prev => ({ ...prev, [taskId]: '' }));
//       fetchTasks();
//     } catch (error) {
//       console.error(error);
//       alert('Error completing task');
//     }
//   }

//   return (
//     <div style={{ maxWidth: 600, margin: 'auto', padding: 20 }}>
//       <h2>PMS Task Tracking</h2>
//       <div>
//         <input
//           placeholder="Task description"
//           value={description}
//           onChange={e => setDescription(e.target.value)}
//           style={{width: '60%'}}
//         />
//         <input
//           type="datetime-local"
//           value={deadline}
//           onChange={e => setDeadline(e.target.value)}
//           style={{width: '35%', marginLeft: 5}}
//         />
//         <button onClick={addTask}>Add Task</button>
//       </div>

//       <ul>
//         {tasks.map(t => (
//           <li key={t.id} style={{marginTop: 10}}>
//             <b>{t.description}</b> (Deadline: {new Date(t.deadline).toLocaleString()}) — 
//             {t.completed ? ' Completed' : (
//               <>
//                 <input
//                   placeholder="Invoice amount"
//                   value={amounts[t.id] || ''}
//                   onChange={e => setAmounts(prev => ({ ...prev, [t.id]: e.target.value }))}
//                   style={{width: 100, marginLeft: 10}}
//                 />
//                 <button onClick={() => completeTask(t.id)}>Complete & Invoice</button>
//               </>
//             )}
//           </li>
//         ))}
//       </ul>

//       <h2>Cash Flow Projection (Next 30 days)</h2>
//       <ul>
//         {projection.map(day => (
//           <li key={day.day}>
//             Day {day.day}: ${day.projected_balance}
//           </li>
//         ))}
//       </ul>
//     </div>
//   );
// }

// export default App;