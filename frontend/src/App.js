// import React from "react";
import "./App.css";
// import FileUpload from "./components/FileUpload";
// import Filters from "./components/Filters";
// import ChartCard from "./components/ChartCard";
// import Alerts from "./components/Alerts";
// import InvoiceSection from "./components/InvoiceSection";
// import EmailSection from "./components/EmailSection";
// import Scheduler from "./components/Scheduler";

// export default function App() {
//   return (
//     <div className="container">
//       <header>
//         <h1>🚀 Automated Small Business Dashboard</h1>
//       </header>

//       <FileUpload />
//       <Filters />

//       <ChartCard title="Top 5 Products by Sales" />
//       <ChartCard title="Top 5 Clients by Revenue" />
//       <ChartCard title="Sales Trend Over Time" />

//       <Alerts />
//       <InvoiceSection />
//       <EmailSection />
//       <Scheduler />
//     </div>
//   );
// }

// import UploadAndAnalyze from "./components/UploadAndAnalyze";
import Dashboard from "./pages/Dashboard";

function App() {
  return (
    <div className="container">
      {/* <h1>📊 Business Analysis Dashboard</h1> */}
      {/* <UploadAndAnalyze /> */}
      <Dashboard/>
    </div>
  );
}

export default App;
