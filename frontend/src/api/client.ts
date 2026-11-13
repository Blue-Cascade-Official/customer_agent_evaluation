const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export type Evaluation = {
  id: string;
  audio_scores: Record<string, unknown> | null;
  knowledge_scores: Record<string, unknown> | null;
  audio_summary: string | null;
  knowledge_summary: string | null;
  overall_audio_score: number | null;
  overall_knowledge_score: number | null;
  model_meta: Record<string, unknown> | null;
  created_at: string;
};

export type Session = {
  id: string;
  internee_id: string;
  internee_name: string;
  elevenlabs_conversation_id: string | null;
  agent_id: string;
  status: string;
  transcript_json: Array<Record<string, unknown>> | Record<string, unknown> | null;
  audio_gcs_url: string | null;
  audio_content_type: string | null;
  audio_play_url: string | null;
  duration_secs: number | null;
  started_at: string | null;
  ended_at: string | null;
  error_message: string | null;
  created_at: string;
  evaluation: Evaluation | null;
};

export type KnowledgeDocument = {
  id: string;
  filename: string;
  gcs_url: string | null;
  mime_type: string | null;
  status: string;
  error_message: string | null;
  uploaded_at: string;
  chunk_count: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export function createSession(name: string) {
  return request<Session>("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function completeSession(sessionId: string, conversationId: string) {
  return request<Session>(`/api/sessions/${sessionId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId }),
  });
}

export function getSession(sessionId: string) {
  return request<Session>(`/api/sessions/${sessionId}`);
}

export function getResults(name: string) {
  return request<{ name: string; sessions: Session[] }>(
    `/api/results?name=${encodeURIComponent(name)}`,
  );
}

export type UserResultsSummary = {
  name: string;
  session_count: number;
  evaluated_count: number;
  avg_audio_score: number | null;
  avg_knowledge_score: number | null;
  last_session_at: string | null;
};

export function getResultsSummary() {
  return request<{ users: UserResultsSummary[] }>("/api/results/summary");
}

export function getConversationToken(participantName?: string) {
  const q = participantName
    ? `?participant_name=${encodeURIComponent(participantName)}`
    : "";
  return request<{ token: string; conversation_id?: string }>(
    `/api/elevenlabs/conversation-token${q}`,
  );
}

export function listKnowledge() {
  return request<KnowledgeDocument[]>("/api/knowledge");
}

export async function uploadKnowledge(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<KnowledgeDocument>("/api/knowledge/upload", {
    method: "POST",
    body: form,
  });
}

export function deleteKnowledge(id: string) {
  return request<{ ok: boolean }>(`/api/knowledge/${id}`, { method: "DELETE" });
}

export type EvalParam = {
  key: string;
  label: string;
  description: string;
  group: "audio" | "knowledge";
  default_enabled: boolean;
  enabled: boolean;
};

export type EvalSettings = {
  audio: EvalParam[];
  knowledge: EvalParam[];
  enabled: Record<string, boolean>;
};

export function getEvalSettings() {
  return request<EvalSettings>("/api/settings/evaluation");
}

export function updateEvalSettings(enabled: Record<string, boolean>) {
  return request<EvalSettings>("/api/settings/evaluation", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}

export function audioUrl(session: Session): string | null {
  if (session.audio_play_url) {
    if (session.audio_play_url.startsWith("http")) return session.audio_play_url;
    return `${API_BASE}${session.audio_play_url}`;
  }
  if (session.audio_gcs_url?.startsWith("file://")) {
    return `${API_BASE}/api/sessions/${session.id}/audio`;
  }
  return null;
}
