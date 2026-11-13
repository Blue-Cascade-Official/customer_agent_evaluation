type Props = {
  title: string;
  overall: number | null | undefined;
  summary?: string | null;
  scores?: Record<string, unknown> | null;
  highlightKeys?: string[];
};

function formatValue(value: unknown): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (value == null) return "—";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

const SKIP_KEYS = new Set(["summary", "citations", "retrieved_chunk_ids", "model"]);

export default function ScoreCard({
  title,
  overall,
  summary,
  scores,
  highlightKeys,
}: Props) {
  const entries = Object.entries(scores ?? {}).filter(([k]) => !SKIP_KEYS.has(k));
  const ordered =
    highlightKeys && highlightKeys.length
      ? [
          ...highlightKeys
            .filter((k) => k in (scores ?? {}))
            .map((k) => [k, scores![k]] as const),
          ...entries.filter(([k]) => !highlightKeys.includes(k)),
        ]
      : entries;

  const citations = Array.isArray(scores?.citations) ? scores.citations : [];

  return (
    <article className="panel score-card">
      <h3>{title}</h3>
      <p className="score-big">{overall != null ? Math.round(overall) : "—"}</p>
      {summary && <p className="muted">{summary}</p>}
      <ul className="metric-list">
        {ordered.map(([key, value]) => (
          <li key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <span>{formatValue(value)}</span>
          </li>
        ))}
      </ul>
      {citations.length > 0 && (
        <div className="citations">
          {citations.map((c, idx) => {
            const item = c as { chunk_id?: string; quote?: string };
            return (
              <div className="citation" key={idx}>
                {item.quote || JSON.stringify(item)}
              </div>
            );
          })}
        </div>
      )}
    </article>
  );
}
