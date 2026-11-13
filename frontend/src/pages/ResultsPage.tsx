import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getResultsSummary, type UserResultsSummary } from "../api/client";

export default function ResultsPage() {
  const [users, setUsers] = useState<UserResultsSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getResultsSummary();
        if (!cancelled) setUsers(data.users);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load results");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="results-page">
      <div className="results-page-top">
        <header className="page-head detailed-results-head">
          <h1>Results</h1>
          <p>
            All internees with average audio and knowledge scores. Open Details to
            inspect a specific call.
          </p>
        </header>
        {loading && <p className="muted">Loading users…</p>}
        {error && <p className="error">{error}</p>}
      </div>

      {!loading && !error && (
        <section className="panel results-table-panel">
          {users.length === 0 ? (
            <p className="muted">No sessions yet. Scores appear after practice calls.</p>
          ) : (
            <div className="results-table-scroll">
              <table className="table results-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Sessions</th>
                    <th>Evaluated</th>
                    <th>Avg audio</th>
                    <th>Avg knowledge</th>
                    <th>Last call</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.name.toLowerCase()}>
                      <td>
                        <strong>{u.name}</strong>
                      </td>
                      <td className="mono">{u.session_count}</td>
                      <td className="mono">{u.evaluated_count}</td>
                      <td className="mono">
                        {u.avg_audio_score != null ? u.avg_audio_score : "—"}
                      </td>
                      <td className="mono">
                        {u.avg_knowledge_score != null ? u.avg_knowledge_score : "—"}
                      </td>
                      <td className="muted">
                        {u.last_session_at
                          ? new Date(u.last_session_at).toLocaleString()
                          : "—"}
                      </td>
                      <td>
                        <Link
                          className="btn secondary"
                          to={`/settings/detailed-results?name=${encodeURIComponent(u.name)}`}
                          style={{ padding: "0.4rem 0.75rem", fontSize: "0.85rem" }}
                        >
                          Details
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
