import { FormEvent, useState } from "react";

type Props = {
  onUpload: (file: File) => Promise<void>;
  busy?: boolean;
};

export default function UploadForm({ onUpload, busy }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Choose a PDF, DOCX, TXT, or MD file.");
      return;
    }
    setError(null);
    try {
      await onUpload(file);
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  return (
    <form className="panel stack" onSubmit={handleSubmit}>
      <label className="field">
        <span>Document (PDF, DOCX, TXT, MD)</span>
        <input
          type="file"
          accept=".pdf,.docx,.txt,.md,application/pdf,text/plain"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>
      <div className="row">
        <button className="btn" type="submit" disabled={busy || !file}>
          {busy ? "Uploading…" : "Upload & index"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
