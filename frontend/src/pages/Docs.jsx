export default function Docs() {
    // blog
  return (
    <div className="doc">
      <h1>How KnowYourPay Works</h1>

      <div className="step">
        <h2>1. Upload Data</h2>
        <p>
          Upload Excel or CSV files containing Unit Price, Cost, Quantity,
          Revenue, or Profit data.
        </p>
      </div>

      <div className="step">
        <h2>2. Automatic Detection</h2>
        <p>
          The system automatically detects Daily, Weekly, Monthly, and
          Yearly financial data — even when column names vary.
        </p>
      </div>

      <div className="step">
        <h2>3. Analyze Results</h2>
        <p>
          Instantly view profit, cost, and revenue insights with clear
          summaries and visual charts.
        </p>
      </div>
    </div>
  );
}