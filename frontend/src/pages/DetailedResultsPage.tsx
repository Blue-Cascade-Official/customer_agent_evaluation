import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { audioUrl, getResults, type Session } from "../api/client";
import ScoreCard from "../components/ScoreCard";
import TranscriptViewer from "../components/TranscriptViewer";

export default function DetailedResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [name, setName] = useState(searchParams.get("name") ?? "");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selected, setSelected] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runSearch(query: string) {
    const trimmed = query.trim();
    if (!trimmed) return;
    setError(null);
    setLoading(true);
    try {
      const res = await getResults(trimmed);
      setSessions(res.sessions);
      setSelected(res.sessions[0] ?? null);
      if (!res.sessions.length) {
        setError("No sessions found for that name.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const initial = searchParams.get("name");
    if (initial?.trim()) {
      setName(initial);
      void runSearch(initial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    setSearchParams(trimmed ? { name: trimmed } : {});
    await runSearch(trimmed);
  }

  const playUrl = selected ? audioUrl(selected) : null;

  return (
    <div className="detailed-results">
      <div className="detailed-results-top">
        <div className="page-head detailed-results-head">
          <h1>Detailed results</h1>
          <p>Search a name, then inspect scores and transcript without leaving this view.</p>
        </div>

        <form className="panel row detailed-search" onSubmit={onSearch}>
          <label className="field" style={{ flex: 1, minWidth: 180 }}>
            <span>Name</span>
            <input
              type="search"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Search by name"
            />
          </label>
          <button className="btn" type="submit" disabled={loading || !name.trim()}>
            {loading ? "Searching…" : "Search"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
      </div>

      {sessions.length > 0 ? (
        <div className={`detailed-results-body ${selected ? "has-selection" : ""}`}>
          <aside className="panel detailed-pane detailed-sessions">
            <h3>Sessions</h3>
            <div className="session-list">
              {sessions.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className={`session-item ${selected?.id === s.id ? "active" : ""}`}
                  onClick={() => setSelected(s)}
                >
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <strong>{new Date(s.created_at).toLocaleString()}</strong>
                    <span className={`status-pill ${s.status}`}>{s.status}</span>
                  </div>
                  <div className="muted">
                    Audio {s.evaluation?.overall_audio_score ?? "—"} · Knowledge{" "}
                    {s.evaluation?.overall_knowledge_score ?? "—"}
                  </div>
                </button>
              ))}
            </div>
          </aside>

          {selected && (
            <>
              <div className="detailed-pane score-card-wrap">
                <ScoreCard
                  title="Audio parameters"
                  overall={selected.evaluation?.overall_audio_score}
                  summary={selected.evaluation?.audio_summary}
                  scores={selected.evaluation?.audio_scores}
                  highlightKeys={[
                    "fluency_score",
                    "reluctance_score",
                    "speaking_rate_wpm",
                    "silence_ratio",
                    "avg_pause_sec",
                    "avg_response_latency_sec",
                    "filler_word_rate",
                    "interruption_count",
                  ]}
                />
              </div>

              <div className="detailed-pane score-card-wrap">
                <ScoreCard
                  title="Knowledge parameters"
                  overall={selected.evaluation?.overall_knowledge_score}
                  summary={selected.evaluation?.knowledge_summary}
                  scores={selected.evaluation?.knowledge_scores}
                  highlightKeys={[
                    "factual_accuracy",
                    "coverage",
                    "hallucination",
                    "relevance",
                    "completeness",
                    "confidence_hedging",
                  ]}
                />
              </div>

              <section className="panel detailed-pane detailed-transcript-col">
                <h3>Recording and transcript</h3>
                {playUrl ? (
                  <audio controls src={playUrl} preload="metadata" />
                ) : (
                  <p className="muted">No audio available for this session.</p>
                )}
                {selected.error_message && (
                  <p className="error">{selected.error_message}</p>
                )}
                <div className="detailed-transcript-scroll">
                  <TranscriptViewer transcript={selected.transcript_json} />
                </div>
              </section>
            </>
          )}
        </div>
      ) : (
        !loading &&
        !error && (
          <div className="panel muted" style={{ marginTop: "0.75rem" }}>
            Search a name to load sessions.
          </div>
        )
      )}
    </div>
  );
}
