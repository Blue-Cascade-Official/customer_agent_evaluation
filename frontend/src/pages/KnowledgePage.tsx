import { useEffect, useState } from "react";
import {
  deleteKnowledge,
  listKnowledge,
  uploadKnowledge,
  type KnowledgeDocument,
} from "../api/client";
import UploadForm from "../components/UploadForm";

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const data = await listKnowledge();
    setDocs(data);
  }

  useEffect(() => {
    refresh().catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load documents"),
    );
  }, []);

  async function onUpload(file: File) {
    setBusy(true);
    setError(null);
    try {
      await uploadKnowledge(file);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      throw err;
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    setBusy(true);
    setError(null);
    try {
      await deleteKnowledge(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <header className="page-head">
        <h1>Knowledge</h1>
        <p>
          Upload company documents used for RAG evaluation of internee call
          transcripts.
        </p>
      </header>

      <UploadForm onUpload={onUpload} busy={busy} />
      {error && <p className="error">{error}</p>}

      <section className="panel" style={{ marginTop: "1rem" }}>
        <h3 style={{ marginTop: 0, fontFamily: "var(--display)" }}>
          Indexed documents
        </h3>
        {docs.length === 0 ? (
          <p className="muted">No documents yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>File</th>
                <th>Status</th>
                <th>Chunks</th>
                <th>Uploaded</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.filename}</td>
                  <td>
                    <span className={`status-pill ${d.status}`}>{d.status}</span>
                  </td>
                  <td>{d.chunk_count}</td>
                  <td>{new Date(d.uploaded_at).toLocaleString()}</td>
                  <td>
                    <button
                      className="btn secondary"
                      type="button"
                      disabled={busy}
                      onClick={() => onDelete(d.id)}
                      style={{ color: "var(--bad)", borderColor: "rgba(163,59,45,0.35)" }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
