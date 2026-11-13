import { useCallback, useRef, useState } from "react";
import { useConversation } from "@elevenlabs/react";
import {
  completeSession,
  createSession,
  getConversationToken,
  getSession,
  type Session,
} from "../api/client";

const AGENT_ID =
  import.meta.env.VITE_ELEVENLABS_AGENT_ID ?? "agent_8801m754zcqefqatys0hhnr0x82s";

type Props = {
  onSessionUpdate?: (session: Session) => void;
};

function normalizeConversationId(raw: string | null | undefined): string {
  if (!raw) return "";
  const match = raw.match(/(conv_[a-zA-Z0-9]+)/);
  return match?.[1] ?? raw.trim();
}

export default function CallPanel({ onSessionUpdate }: Props) {
  const [name, setName] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusNote, setStatusNote] = useState(
    "Type your name, then start when you are ready.",
  );
  const completingRef = useRef(false);
  const conversationIdRef = useRef<string>("");

  const conversation = useConversation({
    onConnect: () => setStatusNote("Connected — speak clearly with the agent."),
    onDisconnect: () => setStatusNote("Call ended. Scoring your session…"),
    onError: (message) => {
      setError(typeof message === "string" ? message : "Call error");
    },
  });

  const pollUntilDone = useCallback(
    async (sessionId: string) => {
      for (let i = 0; i < 90; i++) {
        try {
          const updated = await getSession(sessionId);
          setSession(updated);
          onSessionUpdate?.(updated);
          if (updated.status === "evaluated") {
            const audio = updated.evaluation?.overall_audio_score;
            const knowledge = updated.evaluation?.overall_knowledge_score;
            setStatusNote(
              `Ready — Audio ${audio ?? "—"} · Knowledge ${knowledge ?? "—"}. Open Settings → Results.`,
            );
            return;
          }
          if (updated.status === "failed") {
            setStatusNote(
              `Evaluation failed: ${updated.error_message ?? "unknown error"}`,
            );
            return;
          }
          setStatusNote(`Scoring in progress (${updated.status})…`);
        } catch {
          setStatusNote("Scoring in progress (reconnecting)…");
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
      setStatusNote("Still processing. Check Settings → Results.");
    },
    [onSessionUpdate],
  );

  const finishCall = useCallback(
    async (conversationId: string) => {
      if (!session || completingRef.current) return;
      const normalized = normalizeConversationId(conversationId);
      if (!normalized) {
        setError("Missing conversation id — cannot evaluate.");
        return;
      }
      completingRef.current = true;
      try {
        const updated = await completeSession(session.id, normalized);
        setSession(updated);
        onSessionUpdate?.(updated);
        setStatusNote("Call submitted. Fetching transcript and scoring…");
        void pollUntilDone(session.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to complete session");
      } finally {
        completingRef.current = false;
      }
    },
    [session, onSessionUpdate, pollUntilDone],
  );

  async function handleStart() {
    setError(null);
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Please enter your name.");
      return;
    }
    setBusy(true);
    completingRef.current = false;
    conversationIdRef.current = "";
    try {
      const created = await createSession(trimmed);
      setSession(created);
      onSessionUpdate?.(created);
      setStatusNote("Starting secure call session…");

      let conversationId = "";
      try {
        const tokenRes = await getConversationToken(trimmed);
        if (tokenRes.conversation_id) {
          conversationId = normalizeConversationId(tokenRes.conversation_id);
          conversationIdRef.current = conversationId;
        }
        const startedId = await conversation.startSession({
          conversationToken: tokenRes.token,
          dynamicVariables: { session_id: created.id, internee_name: trimmed },
        });
        conversationId =
          normalizeConversationId(startedId) ||
          conversationId ||
          normalizeConversationId(conversation.getId());
      } catch {
        const startedId = await conversation.startSession({
          agentId: AGENT_ID,
          dynamicVariables: { session_id: created.id, internee_name: trimmed },
        });
        conversationId =
          normalizeConversationId(startedId) ||
          normalizeConversationId(conversation.getId());
      }

      if (conversationId) {
        conversationIdRef.current = conversationId;
        setSession((prev) =>
          prev
            ? { ...prev, elevenlabs_conversation_id: conversationId, status: "in_call" }
            : prev,
        );
      }
      setStatusNote("Call in progress. End the call when finished.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start call");
    } finally {
      setBusy(false);
    }
  }

  async function handleEnd() {
    setBusy(true);
    setError(null);
    try {
      const convId =
        conversationIdRef.current ||
        normalizeConversationId(conversation.getId()) ||
        normalizeConversationId(session?.elevenlabs_conversation_id);
      await conversation.endSession();
      if (convId) {
        await finishCall(convId);
      } else {
        setError("Missing conversation id — cannot evaluate.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to end call");
    } finally {
      setBusy(false);
    }
  }

  const isLive = conversation.status === "connected";

  return (
    <div className="stack">
      <label className="field">
        <span>Your name</span>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Ayesha Khan"
          disabled={isLive || busy}
        />
      </label>

      <div className={`call-meter ${isLive ? "live" : ""}`} aria-hidden />

      <p className="muted" style={{ margin: 0 }}>
        {statusNote}
      </p>

      <div className="row">
        {!isLive ? (
          <button className="btn" type="button" onClick={handleStart} disabled={busy}>
            Start call
          </button>
        ) : (
          <button className="btn danger" type="button" onClick={handleEnd} disabled={busy}
            style={{ color: "var(--bad)", borderColor: "rgba(163,59,45,0.35)" }}
          >
            End call
          </button>
        )}
      </div>

      {session && (
        <p className="muted" style={{ margin: 0 }}>
          Session <span className="mono">{session.id.slice(0, 8)}</span>{" "}
          <span className={`status-pill ${session.status}`}>{session.status}</span>
        </p>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
