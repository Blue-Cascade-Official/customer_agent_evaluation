type Turn = {
  role?: string;
  message?: string | null;
  time_in_call_secs?: number;
};

type Props = {
  transcript: Array<Record<string, unknown>> | Record<string, unknown> | null | undefined;
};

function normalize(transcript: Props["transcript"]): Turn[] {
  if (!transcript) return [];
  if (Array.isArray(transcript)) return transcript as Turn[];
  if (Array.isArray((transcript as { transcript?: Turn[] }).transcript)) {
    return (transcript as { transcript: Turn[] }).transcript;
  }
  return [];
}

export default function TranscriptViewer({ transcript }: Props) {
  const turns = normalize(transcript);
  if (!turns.length) {
    return <p className="muted">No transcript yet.</p>;
  }
  return (
    <div className="transcript">
      {turns.map((t, i) => {
        const role = t.role ?? "unknown";
        const message = t.message;
        if (!message) return null;
        return (
          <div className={`bubble ${role}`} key={i}>
            <div className="role">
              {role}
              {typeof t.time_in_call_secs === "number"
                ? ` · ${t.time_in_call_secs}s`
                : ""}
            </div>
            <div>{message}</div>
          </div>
        );
      })}
    </div>
  );
}
