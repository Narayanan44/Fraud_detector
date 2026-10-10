import { useState, useEffect } from "react";

// Backend address. On deployment set VITE_API_URL to your backend URL.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const emptyForm = { user_id: "", amount: "", location: "", status: "success" };

function App() {
  const [transactions, setTransactions] = useState([]);
  const [levelFilter, setLevelFilter] = useState("ALL");
  const [form, setForm] = useState(emptyForm);
  const [lastResult, setLastResult] = useState(null);
  const [message, setMessage] = useState("");

  // get the list from the backend
  async function loadTransactions() {
    try {
      const url = levelFilter === "ALL" ? `${API_URL}/transactions` : `${API_URL}/transactions?level=${levelFilter}`;
      const response = await fetch(url);
      const data = await response.json();
      setTransactions(data);
    } catch (error) {
      setMessage("Cannot reach the backend. Is it running?");
    }
  }

  // run again whenever the filter changes
  useEffect(() => {
    loadTransactions();
  }, [levelFilter]);

  function handleInputChange(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  // send the form to the backend
  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");

    const body = {
      user_id: form.user_id.trim(),
      amount: Number(form.amount),
      location: form.location.trim() || null,
      status: form.status,
    };

    try {
      const response = await fetch(`${API_URL}/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        setMessage("Please enter a user id and an amount greater than 0.");
        return;
      }

      const saved = await response.json();
      setLastResult(saved);
      setForm(emptyForm);
      loadTransactions();
    } catch (error) {
      setMessage("Cannot reach the backend. Is it running?");
    }
  }

  async function handleLoadSample() {
    setMessage("Loading sample data...");
    try {
      const response = await fetch(`${API_URL}/load-sample`, { method: "POST" });
      if (!response.ok) {
        setMessage("Backend error while loading sample data.");
        return;
      }
      setMessage("Sample data loaded.");
      loadTransactions();
    } catch (error) {
      setMessage("Cannot reach the backend. Is it running?");
    }
  }

  async function handleClearAll() {
    try {
      await fetch(`${API_URL}/transactions`, { method: "DELETE" });
      setLastResult(null);
      setMessage("All transactions deleted.");
      loadTransactions();
    } catch (error) {
      setMessage("Cannot reach the backend. Is it running?");
    }
  }

  // numbers for the summary boxes
  const highCount = transactions.filter((t) => t.risk_level === "HIGH").length;
  const mediumCount = transactions.filter((t) => t.risk_level === "MEDIUM").length;
  const lowCount = transactions.filter((t) => t.risk_level === "LOW").length;

  return (
    <div className="page">
      <h1>Fraud Detection Engine</h1>
      <p className="subtitle">Add a transaction and see its risk score with the reasons.</p>

      {/* ---------- form ---------- */}
      <form className="form" onSubmit={handleSubmit}>
        <input name="user_id" placeholder="User id (e.g. U1)" value={form.user_id} onChange={handleInputChange} required />
        <input name="amount" type="number" step="0.01" placeholder="Amount" value={form.amount} onChange={handleInputChange} required />
        <input name="location" placeholder="Location (e.g. Chennai)" value={form.location} onChange={handleInputChange} />
        <select name="status" value={form.status} onChange={handleInputChange}>
          <option value="success">success</option>
          <option value="failed">failed</option>
        </select>
        <button type="submit">Check transaction</button>
      </form>

      <div className="buttons">
        <button onClick={handleLoadSample}>Load sample data</button>
        <button className="danger" onClick={handleClearAll}>Clear all</button>
        <span className="message">{message}</span>
      </div>

      {/* ---------- result of the last transaction ---------- */}
      {lastResult && (
        <div className={`result ${lastResult.risk_level}`}>
          <h2>Result: {lastResult.risk_score} / 100 ({lastResult.risk_level})</h2>
          <ul>
            {lastResult.reasons.map((reason, index) => (
              <li key={index}>
                <b>{reason.rule}</b> (+{reason.points}): {reason.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ---------- summary ---------- */}
      <div className="summary">
        <div className="box HIGH">High: {highCount}</div>
        <div className="box MEDIUM">Medium: {mediumCount}</div>
        <div className="box LOW">Low: {lowCount}</div>
        <select value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)}>
          <option value="ALL">Show all</option>
          <option value="HIGH">High only</option>
          <option value="MEDIUM">Medium only</option>
          <option value="LOW">Low only</option>
        </select>
      </div>

      {/* ---------- table ---------- */}
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>User</th>
              <th>Amount</th>
              <th>Location</th>
              <th>Status</th>
              <th>Score</th>
              <th>Why</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 && (
              <tr>
                <td colSpan="7">No transactions yet. Add one above or load the sample data.</td>
              </tr>
            )}
            {transactions.map((t) => (
              <tr key={t.id}>
                <td>{t.time.replace("T", " ")}</td>
                <td>{t.user_id}</td>
                <td>{t.amount}</td>
                <td>{t.location || "-"}</td>
                <td>{t.status}</td>
                <td>
                  <span className={`badge ${t.risk_level}`}>
                    {t.risk_score} {t.risk_level}
                  </span>
                </td>
                <td>
                  <ul className="reasons">
                    {t.reasons.map((reason, index) => (
                      <li key={index}>{reason.message}</li>
                    ))}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
